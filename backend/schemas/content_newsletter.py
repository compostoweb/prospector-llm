"""
schemas/content_newsletter.py

Schemas Pydantic v2 para Newsletter "Operacao Inteligente".
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.content import _normalize_content_publish_date

NewsletterStatus = Literal["draft", "approved", "scheduled", "published", "deleted"]


# ── Section payloads (livres — validados pelo rules.py em runtime) ──


class NewsletterTextSection(BaseModel):
    heading: str | None = None
    body: str = Field(default="")


class NewsletterTutorialSection(BaseModel):
    heading: str = Field(default="")
    steps: list[str] = Field(default_factory=list)
    example: str | None = None
    impact: str | None = None


class NewsletterRadarTool(BaseModel):
    name: str
    what: str
    when: str
    limitation: str


class NewsletterRadarData(BaseModel):
    fact: str
    source: str
    context: str | None = None


class NewsletterRadarReading(BaseModel):
    title: str
    url: str
    description: str | None = None


class NewsletterRadarSection(BaseModel):
    tool: NewsletterRadarTool | None = None
    data: NewsletterRadarData | None = None
    reading: NewsletterRadarReading | None = None


class NewsletterPerguntaSection(BaseModel):
    body: str = Field(default="")


class NewsletterFullPayload(BaseModel):
    """
    Estrutura completa que vive em ContentNewsletter.sections_payload (JSONB).
    """

    model_config = ConfigDict(extra="allow")

    title: str = ""
    subtitle: str | None = None
    opening_line: str | None = None
    section_tema_quinzena: NewsletterTextSection | None = None
    section_visao_opiniao: NewsletterTextSection | None = None
    section_mini_tutorial: NewsletterTutorialSection | None = None
    section_radar: NewsletterRadarSection | None = None
    section_pergunta: NewsletterPerguntaSection | None = None


# ── CRUD payloads ────────────────────────────────────────────────────


class NewsletterCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    subtitle: str | None = Field(default=None, max_length=300)
    body_markdown: str | None = None
    body_html: str | None = None
    sections_payload: dict[str, Any] | None = None
    cover_image_url: str | None = None
    cover_image_s3_key: str | None = None
    scheduled_for: datetime | None = None
    notion_page_id: str | None = None

    @field_validator("scheduled_for")
    @classmethod
    def _norm_scheduled(cls, value: datetime | None) -> datetime | None:
        return _normalize_content_publish_date(value)


class NewsletterUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    subtitle: str | None = Field(default=None, max_length=300)
    body_markdown: str | None = None
    body_html: str | None = None
    sections_payload: dict[str, Any] | None = None
    cover_image_url: str | None = None
    cover_image_s3_key: str | None = None
    status: NewsletterStatus | None = None
    scheduled_for: datetime | None = None
    linkedin_pulse_url: str | None = None
    notion_page_id: str | None = None

    @field_validator("scheduled_for")
    @classmethod
    def _norm_scheduled(cls, value: datetime | None) -> datetime | None:
        return _normalize_content_publish_date(value)


class NewsletterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    edition_number: int
    title: str
    subtitle: str | None
    body_markdown: str | None
    body_html: str | None
    sections_payload: dict[str, Any] | None
    cover_image_url: str | None
    cover_image_s3_key: str | None
    status: NewsletterStatus
    scheduled_for: datetime | None
    published_at: datetime | None
    linkedin_pulse_url: str | None
    derived_article_id: uuid.UUID | None
    last_reminder_sent_at: datetime | None
    created_by: uuid.UUID | None
    notion_page_id: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ── LLM payloads ─────────────────────────────────────────────────────


class NewsletterGenerateDraftRequest(BaseModel):
    theme_central: str = Field(..., min_length=3)
    vision_topic: str = Field(..., min_length=3)
    tutorial_topic: str = Field(..., min_length=3)
    radar_tool: dict[str, str] | str
    radar_data: dict[str, str]
    provider: str = Field(default="gemini")
    model: str = Field(default="gemini-2.5-pro")
    temperature: float = Field(default=0.6, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, ge=512, le=8192)


class NewsletterImproveSectionRequest(BaseModel):
    section_id: Literal[
        "tema_quinzena",
        "visao_opiniao",
        "mini_tutorial",
        "radar",
        "pergunta",
    ]
    instruction: str = Field(..., min_length=3)
    provider: str = Field(default="gemini")
    model: str = Field(default="gemini-2.5-pro")
    temperature: float = Field(default=0.5, ge=0.0, le=1.0)


class NewsletterMarkPublishedRequest(BaseModel):
    linkedin_pulse_url: str = Field(..., min_length=8)
    create_derived_article: bool = Field(default=True)


class NewsletterScheduleRequest(BaseModel):
    scheduled_for: datetime

    @field_validator("scheduled_for")
    @classmethod
    def _norm(cls, value: datetime) -> datetime:
        normalized = _normalize_content_publish_date(value)
        assert normalized is not None
        return normalized


class NewsletterExportFormat(BaseModel):
    format: Literal["markdown", "html"] = "markdown"
    content: str


class NewsletterGenerateCoverRequest(BaseModel):
    """Geração de capa via IA (Gemini Nano Banana)."""

    prompt: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "Prompt customizado. Se vazio, usa título + tema central da edição."
        ),
    )
    style: Literal["clean", "with_text", "infographic"] = "clean"
    visual_direction: str = Field(default="auto", max_length=50)
    aspect_ratio: Literal["4:5", "1:1", "16:9"] = "16:9"
    image_size: Literal["512", "1K", "2K", "4K"] = "1K"
