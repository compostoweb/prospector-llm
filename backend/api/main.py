"""
api/main.py

FastAPI app factory do Prospector.

Responsabilidades:
  - Criar e configurar a instância FastAPI
  - Registrar todos os routers da API
  - Configurar CORS, lifespan (startup/shutdown), middleware de logging
  - Expor GET /health para health checks de infra (Docker, balanceador)
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth as auth_router
from api.routes import analytics as analytics_router
from api.routes import audio as audio_router
from api.routes import audio_files as audio_files_router
from api.routes import cadences as cadences_router
from api.routes import lead_lists as lead_lists_router
from api.routes import sandbox as sandbox_router
from api.routes import leads as leads_router
from api.routes import llm as llm_router
from api.routes import pipedrive as pipedrive_router
from api.routes import tts as tts_router
from api.routes import tenants as tenants_router
from api.routes import admin_users as admin_users_router
from api.routes import ws as ws_router
from api.webhooks import unipile as unipile_webhook
from core.config import settings
from core.database import AsyncSessionLocal, init_db
from core.logging import configure_logging
from core.redis_client import redis_client

logger = structlog.get_logger()


# ── Seed: superadmin ─────────────────────────────────────────────────

async def _seed_superuser() -> None:
    """
    Garante que o superadmin master existe na tabela users.
    Executado no startup — idempotente (não duplica se já existir).
    """
    from sqlalchemy import select
    from models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == settings.SUPERUSER_EMAIL)
        )
        if result.scalar_one_or_none() is None:
            db.add(User(
                email=settings.SUPERUSER_EMAIL,
                is_superuser=True,
                is_active=True,
            ))
            await db.commit()
            logger.info("auth.superuser_seeded", email=settings.SUPERUSER_EMAIL)
        else:
            logger.debug("auth.superuser_already_exists", email=settings.SUPERUSER_EMAIL)


# ── Lifespan (startup + shutdown) ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    configure_logging()
    await init_db()
    await _seed_superuser()
    logger.info("api.startup", env=settings.ENV, debug=settings.DEBUG)

    yield

    # Shutdown
    await redis_client.close()
    logger.info("api.shutdown")


# ── App factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="Prospector API",
    version="1.0.0",
    description="Sistema de prospecção B2B automatizado — Composto Web",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware de logging de requests ─────────────────────────────────

@app.middleware("http")
async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start = time.perf_counter()
    response: Response = await call_next(request)  # type: ignore[operator]
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# ── Routers ───────────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(analytics_router.router)
app.include_router(audio_router.router)
app.include_router(audio_files_router.router)
app.include_router(llm_router.router)
app.include_router(pipedrive_router.router)
app.include_router(tts_router.router)
app.include_router(leads_router.router)
app.include_router(lead_lists_router.router)
app.include_router(cadences_router.router)
app.include_router(sandbox_router.router)
app.include_router(tenants_router.router)
app.include_router(admin_users_router.router)
app.include_router(ws_router.router)
app.include_router(unipile_webhook.router)


# ── Health check ──────────────────────────────────────────────────────

@app.get("/health", tags=["Infra"], summary="Verifica saúde da API")
async def health_check() -> dict[str, Any]:
    """
    Verifica a conectividade com o banco de dados e o Redis.
    Retorna HTTP 200 se tudo estiver saudável, HTTP 503 caso contrário.
    """
    from fastapi import HTTPException, status
    from sqlalchemy import text
    from core.database import engine

    checks: dict[str, str] = {}

    # Verifica banco
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error("health.database_error", error=str(exc))
        checks["database"] = "error"

    # Verifica Redis
    redis_ok = await redis_client.ping()
    checks["redis"] = "ok" if redis_ok else "error"

    if any(v == "error" for v in checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "checks": checks},
        )

    return {"status": "healthy", "checks": checks}
