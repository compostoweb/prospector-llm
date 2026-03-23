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

import uuid
from datetime import date

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
        self._redis: aioredis.Redis = aioredis.from_url(
            url,
            decode_responses=True,
        )

    # ── Métodos nativos proxiados (usados pelo LLMRegistry) ───────────

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        await self._redis.set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def ping(self) -> bool:
        try:
            return await self._redis.ping()
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
        current = await self._redis.incr(key)
        if current == 1:
            # Primeira vez hoje — define TTL para expirar à meia-noite aproximada
            await self._redis.expire(key, 86400)
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

    # ── Cache genérico ────────────────────────────────────────────────

    async def get_cache(self, key: str) -> str | None:
        """Retorna o valor cacheado ou None se não existir / expirado."""
        return await self._redis.get(key)

    async def set_cache(self, key: str, value: str, ttl: int) -> None:
        """Salva valor no cache com TTL em segundos."""
        await self._redis.set(key, value, ex=ttl)

    async def set_bytes(self, key: str, value: bytes, ttl: int) -> None:
        """Salva bytes no Redis como base64 com TTL em segundos."""
        import base64
        await self._redis.set(key, base64.b64encode(value).decode("ascii"), ex=ttl)

    async def get_bytes(self, key: str) -> bytes | None:
        """Recupera bytes armazenados via set_bytes. Retorna None se não encontrado."""
        import base64
        raw: str | None = await self._redis.get(key)
        if raw is None:
            return None
        return base64.b64decode(raw)

    async def close(self) -> None:
        await self._redis.aclose()


# Singleton — compartilhado por todo o sistema
redis_client = RedisClient(settings.REDIS_URL)
