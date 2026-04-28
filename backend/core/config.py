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
from typing import TYPE_CHECKING, Literal

from pydantic import Field, model_validator
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
    GOOGLE_EXTENSION_REDIRECT_URI: str = Field(
        default="http://localhost:8000/auth/extension/google/callback",
        description="URI de redirecionamento do Google OAuth usada pela extensao do navegador.",
    )
    SUPERUSER_EMAIL: str = Field(
        default="adriano@compostoweb.com.br",
        description="Email do admin master — criado automaticamente no startup se não existir",
    )
    DEFAULT_TENANT_NAME: str = Field(
        default="Composto Web",
        description="Nome do tenant padrao criado automaticamente quando o banco esta vazio.",
    )
    DEFAULT_TENANT_SLUG: str = Field(
        default="composto-web",
        description="Slug do tenant padrao criado automaticamente quando o banco esta vazio.",
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
    EXTENSION_LINKEDIN_CAPTURE_ENABLED: bool = Field(
        default=False,
        description="Kill switch para captura/importacao via extensao do LinkedIn.",
    )
    EXTENSION_CAPTURE_DAILY_LIMIT: int = Field(
        default=250,
        description="Limite diario de capturas/importacoes por usuario na extensao.",
    )
    EXTENSION_ALLOWED_IDS: str | None = Field(
        default=None,
        description="Lista separada por virgula com extension IDs autorizados por ambiente.",
    )

    # ── CORS ──────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])

    # ── LLM — OpenAI ──────────────────────────────────────────────────
    OPENAI_API_KEY: str | None = None
    OPENAI_DEFAULT_MODEL: str = "gpt-5.4-mini"

    # ── LLM — Gemini ──────────────────────────────────────────────────
    GEMINI_API_KEY: str | None = None
    GEMINI_DEFAULT_MODEL: str = "gemini-2.5-flash"

    # ── LLM — Anthropic ───────────────────────────────────────────────
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_DEFAULT_MODEL: str = "claude-sonnet-4-6"

    # ── LLM — OpenRouter (acesso multi-modelo: free + pagos) ──────────
    OPENROUTER_API_KEY: str | None = None

    # ── LLM — Reply parser (fallback legado de compatibilidade) ───────
    REPLY_PARSER_PROVIDER: str = "openai"
    REPLY_PARSER_MODEL: str = "gpt-5.4-mini"

    # ── LLM — Budget diário por tenant (proteção contra loop) ────────
    LLM_DAILY_BUDGET_TOKENS: int = 500_000

    # ── Voz / TTS ────────────────────────────────────────────────────
    VOICE_PROVIDER: str = "elevenlabs"

    # ── ElevenLabs (provider ativo) ───────────────────────────────────
    ELEVENLABS_API_KEY: str | None = None
    ELEVENLABS_VOICE_ID: str = ""
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"

    # ── Speechify (desativado — preserve código) ──────────────────────
    SPEECHIFY_API_KEY: str | None = None
    SPEECHIFY_VOICE_ID: str = "henry"

    # ── Voicebox (self-hosted TTS) ────────────────────────────────────
    VOICEBOX_BASE_URL: str = "http://localhost:17493"
    VOICEBOX_ENABLED: bool = False

    # ── Edge TTS (desativado — preserve código) ───────────────────────
    EDGE_TTS_ENABLED: bool = False
    EDGE_TTS_DEFAULT_VOICE: str = "pt-BR-FranciscaNeural"

    # ── Unipile ───────────────────────────────────────────────────────
    UNIPILE_API_KEY: str | None = None
    UNIPILE_BASE_URL: str = "https://api2.unipile.com:13246/api/v1"
    UNIPILE_ACCOUNT_ID_LINKEDIN: str | None = None
    UNIPILE_ACCOUNT_ID_GMAIL: str | None = None
    UNIPILE_WEBHOOK_SECRET: str | None = None

    # ── Apify ─────────────────────────────────────────────────────────
    APIFY_API_TOKEN: str | None = None
    APIFY_GOOGLE_MAPS_ACTOR_ID: str = "compass/google-maps-extractor"
    APIFY_B2B_LEADS_ACTOR_ID: str = "code_crafter/leads-finder"
    APIFY_LINKEDIN_ENRICH_ACTOR_ID: str = "harvestapi/linkedin-profile-scraper"
    # Defaults para captura agendada (beat) — JSON list em env var
    # Ex: APIFY_DEFAULT_MAPS_QUERIES='["academias São Paulo", "clínicas odontológicas SP"]'
    APIFY_DEFAULT_MAPS_QUERIES: list[str] = []
    # Ex: APIFY_DEFAULT_LINKEDIN_TITLES='["CEO", "Sócio", "Diretor"]'
    APIFY_DEFAULT_LINKEDIN_TITLES: list[str] = []
    # Ex: APIFY_DEFAULT_LINKEDIN_LOCATIONS='["São Paulo", "Rio de Janeiro"]'
    APIFY_DEFAULT_LINKEDIN_LOCATIONS: list[str] = []
    APIFY_DEFAULT_MAX_ITEMS_MAPS: int = 100
    APIFY_DEFAULT_MAX_ITEMS_LINKEDIN: int = 50
    # Limite de cobrança para atores PAY_PER_EVENT (ex: code_crafter/leads-finder)
    # $0.002/lead + $0.02 start; 5.0 cobre até ~2490 leads por run
    APIFY_B2B_MAX_CHARGE_USD: float = 5.0

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
    RESEND_FROM_EMAIL: str = "Composto Web <site@compostoweb.com.br>"
    CONTENT_CALCULATOR_NOTIFY_EMAIL: str = Field(
        default="adriano@compostoweb.com.br",
        description="Email que recebe notificações de envio do formulário final da calculadora pública.",
    )
    CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL: str = Field(
        default="site@compostoweb.com.br",
        description="Remetente usado nas notificações da calculadora pública.",
    )
    CONTENT_CALCULATOR_REPLY_TO_EMAIL: str = Field(
        default="contato@compostoweb.com.br",
        description="Reply-To usado nos emails enviados ao lead a partir da calculadora pública.",
    )
    COMPOSTO_WEB_LOGO_EMAIL_URL: str | None = Field(
        default=None,
        description="URL pública da logo Composto Web para usar em emails HTML. Se não definida, usa data URI (dev) ou URL da API (prod).",
    )
    # ── SendPulse (lead magnets / nurturing inbound) ─────────────────
    SENDPULSE_API_KEY: str | None = None
    SENDPULSE_CLIENT_ID: str | None = None
    SENDPULSE_CLIENT_SECRET: str | None = None
    SENDPULSE_WEBHOOK_SECRET: str | None = None
    SENDPULSE_BASE_URL: str = "https://api.sendpulse.com"

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
    CADENCE_LINKEDIN_CONNECT_MIN_INTERVAL_SECONDS: int = 90
    CADENCE_LINKEDIN_CONNECT_MAX_INTERVAL_SECONDS: int = 180
    CADENCE_LINKEDIN_CONNECT_MAX_PER_MINUTE: int = 1
    CADENCE_LINKEDIN_DM_MIN_INTERVAL_SECONDS: int = 45
    CADENCE_LINKEDIN_DM_MAX_INTERVAL_SECONDS: int = 90
    CADENCE_LINKEDIN_DM_MAX_PER_MINUTE: int = 1
    CADENCE_LINKEDIN_ENGAGEMENT_MIN_INTERVAL_SECONDS: int = 30
    CADENCE_LINKEDIN_ENGAGEMENT_MAX_INTERVAL_SECONDS: int = 60
    CADENCE_LINKEDIN_ENGAGEMENT_MAX_PER_MINUTE: int = 2
    CADENCE_LINKEDIN_INMAIL_MIN_INTERVAL_SECONDS: int = 90
    CADENCE_LINKEDIN_INMAIL_MAX_INTERVAL_SECONDS: int = 180
    CADENCE_LINKEDIN_INMAIL_MAX_PER_MINUTE: int = 1
    CADENCE_EMAIL_MIN_INTERVAL_SECONDS: int = 30
    CADENCE_EMAIL_MAX_INTERVAL_SECONDS: int = 55
    CADENCE_EMAIL_MAX_PER_MINUTE: int = 2

    # ── Cold Email / Tracking ─────────────────────────────────────────
    TRACKING_BASE_URL: str | None = Field(
        default=None,
        description="URL pública da API — usada em pixels de rastreamento e links de unsubscribe",
    )

    @model_validator(mode="after")
    def apply_tracking_base_url_fallback(self) -> Settings:
        def _normalize_delivery_window(min_attr: str, max_attr: str, per_minute_attr: str) -> None:
            min_value = max(int(getattr(self, min_attr)), 1)
            max_value = max(int(getattr(self, max_attr)), min_value)
            per_minute_value = max(int(getattr(self, per_minute_attr)), 1)
            setattr(self, min_attr, min_value)
            setattr(self, max_attr, max_value)
            setattr(self, per_minute_attr, per_minute_value)

        if not self.TRACKING_BASE_URL:
            self.TRACKING_BASE_URL = self.API_PUBLIC_URL
        _normalize_delivery_window(
            "CADENCE_LINKEDIN_CONNECT_MIN_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_CONNECT_MAX_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_CONNECT_MAX_PER_MINUTE",
        )
        _normalize_delivery_window(
            "CADENCE_LINKEDIN_DM_MIN_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_DM_MAX_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_DM_MAX_PER_MINUTE",
        )
        _normalize_delivery_window(
            "CADENCE_LINKEDIN_ENGAGEMENT_MIN_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_ENGAGEMENT_MAX_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_ENGAGEMENT_MAX_PER_MINUTE",
        )
        _normalize_delivery_window(
            "CADENCE_LINKEDIN_INMAIL_MIN_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_INMAIL_MAX_INTERVAL_SECONDS",
            "CADENCE_LINKEDIN_INMAIL_MAX_PER_MINUTE",
        )
        _normalize_delivery_window(
            "CADENCE_EMAIL_MIN_INTERVAL_SECONDS",
            "CADENCE_EMAIL_MAX_INTERVAL_SECONDS",
            "CADENCE_EMAIL_MAX_PER_MINUTE",
        )
        return self

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
        default="gpt-5.4-mini",
        description="Modelo LLM para geração de posts.",
    )
    CONTENT_PUBLIC_BASE_URL: str = Field(
        default="http://localhost:3000",
        description="URL pública base do frontend para landing pages e calculadora do Content Hub.",
    )


# Singleton — importar de qualquer lugar com: from core.config import settings
if TYPE_CHECKING:
    settings = Settings(DATABASE_URL="", SECRET_KEY="")
else:
    settings = Settings()
