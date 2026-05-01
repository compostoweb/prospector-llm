"""
schemas/content.py

Schemas Pydantic v2 para o modulo Content Hub.

Cobre: ContentPost, ContentTheme, ContentSettings,
       ContentReference, ContentPublishLog, ContentLinkedInAccount.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ExtraValues

CONTENT_HUB_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def _normalize_content_publish_date(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=CONTENT_HUB_TIMEZONE).astimezone(UTC)
    return value.astimezone(UTC)


# ── Tipos literais ────────────────────────────────────────────────────

PostPillar = Literal["authority", "case", "vision"]
PostStatus = Literal["draft", "approved", "scheduled", "published", "failed"]
HookType = Literal[
    "loop_open",
    "contrarian",
    "identification",
    "contrast_direct",
    "data_isolated",
    "short_reflection",
    "personal_story",
    "shortcut",
    "dm_offer",
    # Aliases legados (mantidos para retrocompat com posts antigos)
    "benefit",
    "data",
]
MediaKind = Literal["none", "image", "video", "carousel"]
PublishAction = Literal["schedule", "publish", "cancel", "fail"]
ContentGoal = Literal["editorial", "lead_magnet_launch"]
LMDistributionType = Literal["comment", "dm", "link_bio"]


# ─────────────────────────────────────────────────────────────────────
# ContentPost
# ─────────────────────────────────────────────────────────────────────


class ContentPostCreate(BaseModel):
    title: str = Field(..., max_length=255)
    body: str = Field(..., min_length=1)
    pillar: PostPillar
    hook_type: HookType | None = None
    hashtags: str | None = None
    character_count: int | None = None
    publish_date: datetime | None = None
    week_number: int | None = Field(default=None, ge=1, le=54)
    media_kind: MediaKind = "none"
    first_comment_text: str | None = Field(default=None, max_length=1250)

    @field_validator("publish_date")
    @classmethod
    def normalize_publish_date_to_utc(cls, value: datetime | None) -> datetime | None:
        return _normalize_content_publish_date(value)


class ContentPostUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    body: str | None = None
    pillar: PostPillar | None = None
    hook_type: HookType | None = None
    hashtags: str | None = None
    character_count: int | None = None
    publish_date: datetime | None = None
    week_number: int | None = Field(default=None, ge=1, le=54)
    media_kind: MediaKind | None = None
    first_comment_text: str | None = Field(default=None, max_length=1250)
    error_message: str | None = None

    @field_validator("publish_date")
    @classmethod
    def normalize_publish_date_to_utc(cls, value: datetime | None) -> datetime | None:
        return _normalize_content_publish_date(value)


class ContentPostMetricsUpdate(BaseModel):
    impressions: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    engagement_rate: float | None = Field(default=None, ge=0.0, le=100.0)


class ContentPostResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    body: str
    pillar: str
    status: str
    hook_type: str | None
    hashtags: str | None
    character_count: int | None
    publish_date: datetime | None
    week_number: int | None
    linkedin_post_urn: str | None
    linkedin_scheduled_id: str | None
    media_kind: str = "none"
    image_url: str | None
    image_s3_key: str | None
    image_style: str | None
    image_prompt: str | None
    image_aspect_ratio: str | None
    image_filename: str | None
    image_size_bytes: int | None
    linkedin_image_urn: str | None
    video_url: str | None
    video_s3_key: str | None
    video_filename: str | None
    video_size_bytes: int | None
    linkedin_video_urn: str | None
    impressions: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float | None
    metrics_updated_at: datetime | None
    published_at: datetime | None
    error_message: str | None
    notion_page_id: str | None = None
    created_at: datetime
    updated_at: datetime
    # Preenchido apenas na resposta do PUT quando post já foi publicado no LinkedIn
    linkedin_sync_warning: str | None = None
    # Imagens vinculadas ao carrossel (preenchido quando media_kind == "carousel")
    carousel_images: list[CarouselImageItem] = []
    # First comment + pin
    first_comment_text: str | None = None
    first_comment_status: str = "pending"
    first_comment_pin_status: str = "pending"
    first_comment_urn: str | None = None
    first_comment_posted_at: datetime | None = None
    first_comment_error: str | None = None


class CarouselImageItem(BaseModel):
    """Imagem vinculada a um post como item de carrossel."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    image_url: str
    image_s3_key: str | None = None
    position: int
    linkedin_image_urn: str | None = None
    carousel_group_id: uuid.UUID | None = None


class CarouselReorderRequest(BaseModel):
    """Body do PATCH /posts/{id}/carousel/reorder."""

    order: list[uuid.UUID] = Field(..., min_length=2, max_length=9)


class CarouselImportFromGalleryRequest(BaseModel):
    """Body do POST /posts/{id}/carousel/images/from-gallery."""

    image_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=9)


class ContentPostRevisionResponse(BaseModel):
    """Snapshot historico de um ContentPost (Phase 3D)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    post_id: uuid.UUID
    tenant_id: uuid.UUID
    snapshot: dict
    reason: str
    created_by: uuid.UUID | None = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────
# ContentTheme
# ─────────────────────────────────────────────────────────────────────


class ContentThemeCreate(BaseModel):
    title: str = Field(..., max_length=255)
    pillar: PostPillar


class ContentThemeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    pillar: str
    used: bool
    used_at: datetime | None
    used_in_post_id: uuid.UUID | None
    is_custom: bool
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────
# ContentSettings
# ─────────────────────────────────────────────────────────────────────


class ContentSettingsUpdate(BaseModel):
    default_publish_time: str | None = Field(
        default=None,
        description="Horario no formato HH:MM, ex: '09:00'",
        pattern=r"^\d{2}:\d{2}$",
    )
    posts_per_week: int | None = Field(default=None, ge=1, le=7)
    author_name: str | None = Field(default=None, max_length=100)
    author_voice: str | None = None
    # Notion — enviar apenas ao alterar; None = nao modifica o valor existente
    notion_api_key: str | None = Field(
        default=None,
        description="Internal Integration token do Notion (secret_xxx). Enviar None para nao alterar.",
    )
    notion_database_id: str | None = Field(
        default=None, max_length=100, description="UUID do banco de dados Notion (extraido da URL)"
    )
    notion_column_mappings: NotionColumnMappings | None = Field(
        default=None, description="Mapeamento de colunas Notion para campos internos"
    )


class ContentSettingsResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    default_publish_time: str | None
    posts_per_week: int
    author_name: str | None
    author_voice: str | None
    # Notion — chave nunca exposta; apenas indica se esta configurada
    notion_api_key_set: bool = Field(
        default=False, description="True se notion_api_key esta configurada"
    )
    notion_database_id: str | None
    notion_column_mappings: NotionColumnMappings | None = Field(
        default=None, description="Mapeamento de colunas Notion configurado pelo tenant"
    )
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> ContentSettingsResponse:
        import json

        from models.content_settings import ContentSettings

        if isinstance(obj, ContentSettings):
            mappings: NotionColumnMappings | None = None
            if obj.notion_column_mappings:
                try:
                    mappings = NotionColumnMappings(**json.loads(obj.notion_column_mappings))
                except Exception:
                    mappings = None
            return cls(  # type: ignore[call-arg]
                id=obj.id,
                tenant_id=obj.tenant_id,
                default_publish_time=str(obj.default_publish_time)
                if obj.default_publish_time
                else None,
                posts_per_week=obj.posts_per_week,
                author_name=obj.author_name,
                author_voice=obj.author_voice,
                notion_api_key_set=obj.notion_api_key is not None,
                notion_database_id=obj.notion_database_id,
                notion_column_mappings=mappings,
                created_at=obj.created_at,
                updated_at=obj.updated_at,
            )
        return super().model_validate(
            obj,
            strict=strict,
            extra=extra,
            from_attributes=from_attributes,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )


# ─────────────────────────────────────────────────────────────────────
# ContentReference
# ─────────────────────────────────────────────────────────────────────


class ContentReferenceCreate(BaseModel):
    body: str = Field(..., min_length=1)
    author_name: str | None = Field(default=None, max_length=150)
    author_title: str | None = Field(default=None, max_length=200)
    author_company: str | None = Field(default=None, max_length=200)
    hook_type: HookType | None = None
    pillar: PostPillar | None = None
    engagement_score: int | None = Field(default=None, ge=0)
    source_url: str | None = Field(default=None, max_length=500)
    notes: str | None = None


class ContentReferenceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    author_name: str | None
    author_title: str | None
    author_company: str | None
    body: str
    hook_type: str | None
    pillar: str | None
    engagement_score: int | None
    source_url: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────
# ContentPublishLog
# ─────────────────────────────────────────────────────────────────────


class ContentPublishLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    post_id: uuid.UUID
    tenant_id: uuid.UUID
    action: str
    linkedin_response: dict | None
    error_detail: str | None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────
# LinkedIn OAuth
# ─────────────────────────────────────────────────────────────────────


class LinkedInAuthUrl(BaseModel):
    url: str


class ContentLinkedInAccountResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    person_id: str
    person_urn: str
    display_name: str | None
    is_active: bool
    scopes: str | None
    connected_at: datetime
    token_expires_at: datetime | None
    updated_at: datetime
    # Analytics via Unipile
    has_unipile: bool = False
    last_voyager_sync_at: datetime | None = None

    @classmethod
    def from_orm_with_computed(
        cls,
        obj: object,
        *,
        has_unipile: bool = False,
    ) -> ContentLinkedInAccountResponse:
        """Popula campos computados a partir do model + flag externa."""
        data = cls.model_validate(obj)
        data.has_unipile = has_unipile
        data.last_voyager_sync_at = getattr(obj, "last_voyager_sync_at", None)
        return data


# ─────────────────────────────────────────────────────────────────────
# Analytics Sync
# ─────────────────────────────────────────────────────────────────────


class VoyagerSyncResponse(BaseModel):
    success: bool
    posts_created: int
    posts_updated: int
    posts_skipped: int
    error: str | None = None
    synced_at: datetime


# ─────────────────────────────────────────────────────────────────────
# Sprint 3 — Geração com IA
# ─────────────────────────────────────────────────────────────────────


class GeneratePostRequest(BaseModel):
    theme: str = Field(..., min_length=3, max_length=500)
    pillar: PostPillar
    content_goal: ContentGoal = "editorial"
    lead_magnet_id: uuid.UUID | None = None
    hook_type: HookType | None = None
    launch_distribution_type: LMDistributionType | None = None
    launch_trigger_word: str | None = Field(default=None, min_length=2, max_length=50)
    publish_date: datetime | None = None
    week: int | None = Field(default=None, ge=1, le=54)
    variations: int = Field(default=3, ge=1, le=5)
    use_references: bool = False
    provider: str | None = None
    model: str | None = None
    temperature: float = Field(default=0.8, ge=0.0, le=1.0)


class GeneratePostVariation(BaseModel):
    text: str
    character_count: int
    hook_type_used: str
    violations: list[str] = Field(default_factory=list)


class GeneratePostResponse(BaseModel):
    variations: list[GeneratePostVariation]


class ImprovePostRequest(BaseModel):
    post_id: uuid.UUID | None = None
    body: str | None = Field(default=None, min_length=1)
    instruction: str = Field(..., min_length=3, max_length=500)
    provider: str | None = None
    model: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class ImprovePostResponse(BaseModel):
    text: str
    character_count: int
    violations: list[str] = Field(default_factory=list)


class ThemeSuggestion(BaseModel):
    theme: ContentThemeResponse
    reason: str
    lead_count: int
    sector: str


class VaryThemeRequest(BaseModel):
    theme_title: str = Field(..., min_length=3, max_length=300)
    pillar: str = Field(..., pattern="^(authority|case|vision)$")


class VaryThemeResponse(BaseModel):
    variation: str


class DetectHookRequest(BaseModel):
    body: str = Field(..., min_length=10, max_length=5000)


class DetectHookResponse(BaseModel):
    hook_type: str


# ─────────────────────────────────────────────────────────────────────
# Geração de imagem (Nano Banana 2)
# ─────────────────────────────────────────────────────────────────────

ImageStyle = Literal["clean", "with_text", "infographic"]
ImageSubType = Literal["metrics", "steps", "comparison"]
ImageAspectRatio = Literal["4:5", "1:1", "16:9"]
ImageVisualDirection = Literal["auto", "editorial", "minimal", "bold", "organic"]


class GeneratePostImageRequest(BaseModel):
    post_id: uuid.UUID
    style: ImageStyle
    aspect_ratio: ImageAspectRatio = "4:5"
    sub_type: ImageSubType | None = None
    visual_direction: ImageVisualDirection = "auto"
    custom_prompt: str | None = Field(default=None, max_length=1000)


class GeneratePostImageResponse(BaseModel):
    image_url: str
    image_prompt: str


# ─────────────────────────────────────────────────────────────────────
# Notion Import
# ─────────────────────────────────────────────────────────────────────


class NotionDatabaseColumn(BaseModel):
    """Uma coluna disponivel no banco de dados Notion."""

    name: str
    type: str


class NotionColumnMappings(BaseModel):
    """Mapeamento de campos internos ContentPost para colunas Notion."""

    title: str = Field(..., description="Coluna Notion que contem o titulo do post (tipo: title)")
    body: str = Field(..., description="Coluna Notion que contem o texto do post (tipo: rich_text)")
    pillar: str | None = Field(
        default=None, description="Coluna Notion para o pilar (tipo: select)"
    )
    status: str | None = Field(
        default=None, description="Coluna Notion para o status (tipo: select)"
    )
    publish_date: str | None = Field(
        default=None, description="Coluna Notion para a data de publicacao (tipo: date)"
    )
    week_number: str | None = Field(
        default=None, description="Coluna Notion para o numero da semana (tipo: number)"
    )
    hashtags: str | None = Field(
        default=None, description="Coluna Notion para hashtags (tipo: rich_text)"
    )


class NotionPostPreview(BaseModel):
    """Preview de uma page Notion antes de importar."""

    page_id: str
    title: str
    pillar: str | None
    status_notion: str | None
    publish_date: str | None
    week_number: int | None
    hashtags: str | None
    body_preview: str = Field(description="Primeiros 120 caracteres do corpo do post")
    body: str = Field(default="", description="Texto completo do post")
    already_imported: bool = Field(
        default=False,
        description="True se este page_id ja foi importado por este tenant",
    )


class NotionImportRequest(BaseModel):
    page_ids: list[str] = Field(..., min_length=1, description="IDs das pages Notion a importar")


class NotionImportResult(BaseModel):
    imported: int
    skipped: int
    failed: int
    post_ids: list[str] = Field(default_factory=list, description="UUIDs dos ContentPost criados")
