"""
core/redis_client.py

Cliente Redis assíncrono + helpers de cache e rate limiting.

Responsabilidades:
  - Expor a classe RedisClient (usada pelo LLMRegistry e outros serviços)
  - Prover helpers de alto nível: check_and_increment, get_cache, set_cache
  - Exportar o singleton redis_client para uso em todo o sistema

Padrão de rate limiting:
  Chave: ratelimit:{tenant_id}:{channel}:{YYYY-MM-DD}
  TTL:   86400s (1 dia)
  Retorna True se abaixo do limite, False se atingiu ou superou.

Uso:
    from core.redis_client import redis_client
    allowed = await redis_client.check_and_increment("linkedin_dm", tenant_id, limit=40)
"""

from __future__ import annotations

import asyncio
import random
import uuid
from collections.abc import Awaitable
from datetime import date
from typing import Any, cast

import redis.asyncio as aioredis
import structlog

from core.config import settings

logger = structlog.get_logger()


class RedisClient:
    """
    Wrapper sobre redis.asyncio.Redis.

    Expõe os métodos nativos get/set/incr/expire do Redis
    e adiciona helpers de domínio (rate limiting, cache).
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._redis: aioredis.Redis | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_redis(self) -> aioredis.Redis:
        """
        Recria o cliente por event loop.

        Workers Celery usam asyncio.run() por task, então conexões persistidas
        no cliente anterior podem ficar presas ao loop anterior e quebrar.
        """
        loop = asyncio.get_running_loop()
        if self._redis is None or self._loop is not loop:
            self._redis = aioredis.from_url(
                self._url,
                decode_responses=True,
            )
            self._loop = loop
        assert self._redis is not None
        return self._redis

    # ── Métodos nativos proxiados (usados pelo LLMRegistry) ───────────

    async def get(self, key: str) -> str | None:
        return await self._get_redis().get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        await self._get_redis().set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        await self._get_redis().delete(key)

    async def delete_many(self, *keys: str) -> None:
        if keys:
            await self._get_redis().delete(*keys)

    async def keys(self, pattern: str) -> list[str]:
        result = await self._get_redis().keys(pattern)
        return list(result)

    async def increment_with_ttl(self, key: str, ttl: int) -> int:
        redis = self._get_redis()
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, ttl)
        return int(current)

    async def check_and_increment_key(
        self,
        key: str,
        limit: int,
        ttl: int = 86400,
    ) -> bool:
        """
        Incrementa um contador arbitrário com teto e TTL.
        Retorna True se a reserva foi aceita, False se o limite já foi atingido.
        """
        redis = self._get_redis()
        current = await cast(
            Awaitable[Any],
            redis.eval(
                """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local ttl = tonumber(ARGV[2])

            local current = redis.call('GET', key)
            if not current then
                redis.call('SET', key, 1, 'EX', ttl)
                return 1
            end

            current = tonumber(current)
            if current >= limit then
                return current
            end

            return redis.call('INCR', key)
            """,
                1,
                key,
                str(limit),
                str(ttl),
            ),
        )
        return int(current) <= limit

    async def ping(self) -> bool:
        try:
            return await self._get_redis().ping()
        except Exception:
            return False

    # ── Rate limiting ─────────────────────────────────────────────────

    async def check_and_increment(
        self,
        channel: str,
        tenant_id: uuid.UUID,
        limit: int,
    ) -> bool:
        """
        Incrementa o contador do canal para o tenant hoje.
        Retorna True se ainda está abaixo do limite (envio permitido).
        Retorna False se atingiu ou superou o limite (envio bloqueado).
        """
        key = f"ratelimit:{tenant_id}:{channel}:{date.today()}"
        allowed = await self.check_and_increment_key(key, limit=limit, ttl=86400)
        if not allowed:
            logger.warning(
                "rate_limit.exceeded",
                channel=channel,
                tenant_id=str(tenant_id),
                limit=limit,
            )
        return allowed

    async def release_rate_limit_key(self, key: str) -> int:
        """
        Libera uma reserva previamente criada para uma chave arbitrária.
        Nunca deixa o contador ficar negativo.
        """
        redis = self._get_redis()
        current = await cast(
            Awaitable[Any],
            redis.eval(
                """
            local key = KEYS[1]
            local current = redis.call('GET', key)
            if not current then
                return 0
            end

            current = tonumber(current)
            if current <= 1 then
                redis.call('DEL', key)
                return 0
            end

            return redis.call('DECR', key)
            """,
                1,
                key,
            ),
        )
        return int(current)

    async def release_rate_limit(self, channel: str, tenant_id: uuid.UUID) -> int:
        """
        Libera uma reserva de rate limit quando um envio enfileirado termina sem sucesso.
        Nunca deixa o contador ficar negativo.
        """
        key = f"ratelimit:{tenant_id}:{channel}:{date.today()}"
        return await self.release_rate_limit_key(key)

    async def reserve_delivery_slot(
        self,
        *,
        throttle_scope: str,
        now_ts: int,
        min_gap_seconds: int,
        max_gap_seconds: int,
        per_minute_limit: int,
        ttl: int = 7200,
    ) -> int:
        """
        Reserva atomicamente um slot de envio com espaçamento e teto por minuto.

        Retorna o timestamp UNIX do slot reservado.
        """
        jitter_seconds = random.randint(
            max(1, min_gap_seconds),
            max(max_gap_seconds, min_gap_seconds, 1),
        )
        next_key = f"ratelimit:next:{throttle_scope}"
        minute_prefix = f"ratelimit:minute:{throttle_scope}"
        scheduled_ts = await cast(
            Awaitable[Any],
            self._get_redis().eval(
                """
            local next_key = KEYS[1]
            local minute_prefix = ARGV[1]
            local now_ts = tonumber(ARGV[2])
            local jitter_seconds = tonumber(ARGV[3])
            local per_minute_limit = tonumber(ARGV[4])
            local ttl = tonumber(ARGV[5])

            local scheduled_ts = now_ts
            local next_ts_raw = redis.call('GET', next_key)
            if next_ts_raw then
                local next_ts = tonumber(next_ts_raw)
                if next_ts and next_ts > scheduled_ts then
                    scheduled_ts = next_ts
                end
            end

            local minute_bucket = math.floor(scheduled_ts / 60)
            for _ = 1, 180 do
                local minute_key = minute_prefix .. ':' .. tostring(minute_bucket)
                local current = tonumber(redis.call('GET', minute_key) or '0')

                if current < per_minute_limit then
                    local minute_start = minute_bucket * 60
                    if scheduled_ts < minute_start then
                        scheduled_ts = minute_start
                    end

                    redis.call('INCR', minute_key)
                    redis.call('EXPIRE', minute_key, ttl)
                    redis.call('SET', next_key, tostring(scheduled_ts + jitter_seconds), 'EX', ttl)
                    return scheduled_ts
                end

                minute_bucket = minute_bucket + 1
                local next_minute_start = minute_bucket * 60
                if scheduled_ts < next_minute_start then
                    scheduled_ts = next_minute_start
                end
            end

            redis.call('SET', next_key, tostring(scheduled_ts + jitter_seconds), 'EX', ttl)
            return scheduled_ts
            """,
                1,
                next_key,
                minute_prefix,
                str(now_ts),
                str(jitter_seconds),
                str(max(per_minute_limit, 1)),
                str(ttl),
            ),
        )
        return int(scheduled_ts)

    # ── Cache genérico ────────────────────────────────────────────────

    async def get_cache(self, key: str) -> str | None:
        """Retorna o valor cacheado ou None se não existir / expirado."""
        return await self._get_redis().get(key)

    async def set_cache(self, key: str, value: str, ttl: int) -> None:
        """Salva valor no cache com TTL em segundos."""
        await self._get_redis().set(key, value, ex=ttl)

    async def set_if_absent(self, key: str, value: str, ttl: int) -> bool:
        """SET NX (only if not exists) com TTL. Retorna True se setou, False se já existia."""
        result = await self._get_redis().set(key, value, ex=ttl, nx=True)
        return result is not None

    async def set_bytes(self, key: str, value: bytes, ttl: int) -> None:
        """Salva bytes no Redis como base64 com TTL em segundos."""
        import base64

        await self._get_redis().set(key, base64.b64encode(value).decode("ascii"), ex=ttl)

    async def get_bytes(self, key: str) -> bytes | None:
        """Recupera bytes armazenados via set_bytes. Retorna None se não encontrado."""
        import base64

        raw: str | None = await self._get_redis().get(key)
        if raw is None:
            return None
        return base64.b64decode(raw)

    async def close(self) -> None:
        redis = self._redis
        self._redis = None
        self._loop = None
        if redis is not None:
            await redis.aclose()


# Singleton — compartilhado por todo o sistema
redis_client = RedisClient(settings.REDIS_URL)
