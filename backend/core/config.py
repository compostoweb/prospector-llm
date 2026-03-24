"""
core/config.py

Configurações centrais da aplicação via pydantic-settings.

Responsabilidades:
  - Detectar o ambiente (dev | prod) via variável ENV
  - Carregar o arquivo .env.{ENV} correspondente
  - Expor todas as configurações como atributos tipados
  - Exportar o singleton `settings` para uso em todo o sistema

Uso:
    from core.config import settings
    db_url = settings.DATABASE_URL
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Detecta o ambiente antes de instanciar Settings
ENV: str = os.getenv("ENV", "dev")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f".env.{ENV}",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── API ────────────────────────────────────────────────────────────
    API_PUBLIC_URL: str = Field(
        default="http://localhost:8000",
        description="URL pública da API — usada para gerar links de áudio para voice notes",
    )

    # ── Google OAuth ──────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str | None = Field(
        default=None,
        description="Client ID do app OAuth no Google Cloud Console",
    )
    GOOGLE_CLIENT_SECRET: str | None = Field(
        default=None,
        description="Client Secret do app OAuth no Google Cloud Console",
    )
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/auth/google/callback",
        description="URI de redirecionamento registrada no Google Cloud Console",
    )
    SUPERUSER_EMAIL: str = Field(
        default="adriano@compostoweb.com.br",
        description="Email do admin master — criado automaticamente no startup se não existir",
    )
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="URL pública do frontend Next.js — usado para redirecionar após OAuth",
    )

    # ── Ambiente ─────────────────────────────────────────────────────
    ENV: Literal["dev", "prod"] = "dev"
    DEBUG: bool = True

    # ── Banco de dados ────────────────────────────────────────────────
    DATABASE_URL: str = Field(..., description="PostgreSQL async URL (asyncpg)")

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # ── Segurança ─────────────────────────────────────────────────────
    SECRET_KEY: str = Field(..., description="Chave secreta para assinar JWTs")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias

    # ── CORS ──────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = Field(default=["*"])

    # ── LLM — OpenAI ──────────────────────────────────────────────────
    OPENAI_API_KEY: str | None = None
    OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"

    # ── LLM — Gemini ──────────────────────────────────────────────────
    GEMINI_API_KEY: str | None = None
    GEMINI_DEFAULT_MODEL: str = "gemini-2.5-flash"

    # ── LLM — Reply parser (config global, não por cadência) ──────────
    REPLY_PARSER_PROVIDER: str = "openai"
    REPLY_PARSER_MODEL: str = "gpt-4o-mini"

    # ── Voz / TTS ────────────────────────────────────────────────────
    VOICE_PROVIDER: str = "speechify"
    SPEECHIFY_API_KEY: str | None = None
    SPEECHIFY_VOICE_ID: str = "henry"

    # ── Voicebox (self-hosted TTS) ────────────────────────────────────
    VOICEBOX_BASE_URL: str = "http://localhost:17493"
    VOICEBOX_ENABLED: bool = False

    # ── Unipile ───────────────────────────────────────────────────────
    UNIPILE_API_KEY: str | None = None
    UNIPILE_BASE_URL: str = "https://api2.unipile.com:13246/api/v1"
    UNIPILE_ACCOUNT_ID_LINKEDIN: str | None = None
    UNIPILE_ACCOUNT_ID_GMAIL: str | None = None
    UNIPILE_WEBHOOK_SECRET: str | None = None

    # ── Apify ─────────────────────────────────────────────────────────
    APIFY_API_TOKEN: str | None = None

    # ── Email finders ─────────────────────────────────────────────────
    PROSPEO_API_KEY: str | None = None
    HUNTER_API_KEY: str | None = None
    APOLLO_API_KEY: str | None = None
    ZEROBOUNCE_API_KEY: str | None = None

    # ── Contexto / Web scraping ───────────────────────────────────────
    JINA_API_KEY: str | None = None
    FIRECRAWL_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None

    # ── Pipedrive ─────────────────────────────────────────────────────
    PIPEDRIVE_API_TOKEN: str | None = None
    PIPEDRIVE_DOMAIN: str | None = None
    PIPEDRIVE_STAGE_INTEREST: int | None = None
    PIPEDRIVE_STAGE_OBJECTION: int | None = None
    PIPEDRIVE_OWNER_ID: int | None = None
    PIPEDRIVE_NOTIFY_EMAIL: str | None = None

    # ── Resend (email transacional) ───────────────────────────────────
    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str = "Prospector <noreply@prospector.app>"

    # ── Rate limits por canal (por tenant/dia) ────────────────────────
    LIMIT_LINKEDIN_CONNECT: int = 20
    LIMIT_LINKEDIN_DM: int = 40
    LIMIT_EMAIL: int = 300


# Singleton — importar de qualquer lugar com: from core.config import settings
settings = Settings()
