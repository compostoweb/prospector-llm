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

    # ── Edge TTS (Microsoft Neural — gratuito) ───────────────────────
    EDGE_TTS_ENABLED: bool = True
    EDGE_TTS_DEFAULT_VOICE: str = "pt-BR-FranciscaNeural"

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

    # ── MinIO / S3 — armazenamento de arquivos ────────────────────────
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_BUCKET: str = "prospector"
    S3_REGION: str = "us-east-1"

    # ── Rate limits por canal (por tenant/dia) ────────────────────────
    LIMIT_LINKEDIN_CONNECT: int = 20
    LIMIT_LINKEDIN_DM: int = 40
    LIMIT_EMAIL: int = 300

    # ── Cold Email / Tracking ─────────────────────────────────────────
    TRACKING_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="URL pública da API — usada em pixels de rastreamento e links de unsubscribe",
    )

    # ── Email Providers (Google OAuth direto para Gmail) ──────────────
    GOOGLE_CLIENT_ID_EMAIL: str | None = Field(
        default=None,
        description="Google OAuth Client ID com escopo gmail.send (app separada do login)",
    )
    GOOGLE_CLIENT_SECRET_EMAIL: str | None = Field(
        default=None,
        description="Google OAuth Client Secret para gmail.send",
    )
    GOOGLE_REDIRECT_URI_EMAIL: str = Field(
        default="http://localhost:8000/email-accounts/google/callback",
        description="URI de redirect OAuth para contas de e-mail",
    )
    EMAIL_ACCOUNT_ENCRYPTION_KEY: str | None = Field(
        default=None,
        description="Fernet key (base64) para encriptar tokens/senhas de contas de e-mail",
    )

    # ── LinkedIn Accounts (native provider) ───────────────────────────
    LINKEDIN_ACCOUNT_ENCRYPTION_KEY: str | None = Field(
        default=None,
        description="Fernet key para encriptar cookie li_at (nativo). Pode reusar EMAIL_ACCOUNT_ENCRYPTION_KEY.",
    )

    # ── Content Hub — LinkedIn OAuth (Share on LinkedIn product) ──────
    LINKEDIN_CLIENT_ID: str | None = Field(
        default=None,
        description="LinkedIn App Client ID para OAuth do Content Hub (Share on LinkedIn).",
    )
    LINKEDIN_CLIENT_SECRET: str | None = Field(
        default=None,
        description="LinkedIn App Client Secret para OAuth do Content Hub.",
    )
    LINKEDIN_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/content/linkedin/callback",
        description="URI de redirect OAuth do Content Hub. Deve ser registrado no LinkedIn Developer Portal.",
    )

    # ── Content Hub — geração com IA ───────────────────────────────────
    CONTENT_GEN_PROVIDER: str = Field(
        default="openai",
        description="Provider LLM para geração de posts (openai | gemini).",
    )
    CONTENT_GEN_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Modelo LLM para geração de posts.",
    )


# Singleton — importar de qualquer lugar com: from core.config import settings
settings = Settings()
