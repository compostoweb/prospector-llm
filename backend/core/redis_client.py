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
                "86400",
            ),
        )
        current = int(current)
        allowed = current <= limit
        if not allowed:
            logger.warning(
                "rate_limit.exceeded",
                channel=channel,
                tenant_id=str(tenant_id),
                current=current,
                limit=limit,
            )
        return allowed

    async def release_rate_limit(self, channel: str, tenant_id: uuid.UUID) -> int:
        """
        Libera uma reserva de rate limit quando um envio enfileirado termina sem sucesso.
        Nunca deixa o contador ficar negativo.
        """
        key = f"ratelimit:{tenant_id}:{channel}:{date.today()}"
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
