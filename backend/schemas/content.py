"""
schemas/content.py

Schemas Pydantic v2 para o modulo Content Hub.

Cobre: ContentPost, ContentTheme, ContentSettings,
       ContentReference, ContentPublishLog, ContentLinkedInAccount.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Tipos literais ────────────────────────────────────────────────────

PostPillar = Literal["authority", "case", "vision"]
PostStatus = Literal["draft", "approved", "scheduled", "published", "failed"]
HookType = Literal["loop_open", "contrarian", "identification", "shortcut", "benefit", "data"]
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


class ContentPostUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    body: str | None = None
    pillar: PostPillar | None = None
    hook_type: HookType | None = None
    hashtags: str | None = None
    character_count: int | None = None
    publish_date: datetime | None = None
    week_number: int | None = Field(default=None, ge=1, le=54)
    error_message: str | None = None


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
    image_url: str | None
    image_s3_key: str | None
    image_style: str | None
    image_prompt: str | None
    image_aspect_ratio: str | None
    linkedin_image_urn: str | None
    video_url: str | None
    video_s3_key: str | None
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
    created_at: datetime
    updated_at: datetime
    # Preenchido apenas na resposta do PUT quando post já foi publicado no LinkedIn
    linkedin_sync_warning: str | None = None


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


class ContentSettingsResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    default_publish_time: str | None
    posts_per_week: int
    author_name: str | None
    author_voice: str | None
    created_at: datetime
    updated_at: datetime


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


# ─────────────────────────────────────────────────────────────────────
# Geração de imagem (Nano Banana 2)
# ─────────────────────────────────────────────────────────────────────

ImageStyle = Literal["clean", "with_text", "infographic"]
ImageSubType = Literal["metrics", "steps", "comparison"]
ImageAspectRatio = Literal["4:5", "1:1", "16:9"]


class GeneratePostImageRequest(BaseModel):
    post_id: uuid.UUID
    style: ImageStyle
    aspect_ratio: ImageAspectRatio = "4:5"
    sub_type: ImageSubType | None = None
    custom_prompt: str | None = Field(default=None, max_length=1000)


class GeneratePostImageResponse(BaseModel):
    image_url: str
    image_prompt: str
