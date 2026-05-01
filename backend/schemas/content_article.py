"""
schemas/content_article.py

Schemas Pydantic v2 para Content Article (link share LinkedIn Posts API).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.content import _normalize_content_publish_date

ArticleStatus = Literal["draft", "approved", "scheduled", "published", "failed", "deleted"]
FirstCommentStatus = Literal["pending", "posted", "failed"]
FirstCommentPinStatus = Literal["unpinned", "pinned", "failed"]


class ArticleCreate(BaseModel):
    source_url: str = Field(..., min_length=8)
    title: str | None = Field(default=None, max_length=300)
    description: str | None = None
    thumbnail_url: str | None = None
    thumbnail_s3_key: str | None = None
    commentary: str | None = Field(default=None, max_length=3000)
    scheduled_for: datetime | None = None
    source_newsletter_id: uuid.UUID | None = None
    auto_scraped: bool = False
    first_comment_text: str | None = Field(default=None, max_length=1250)

    @field_validator("scheduled_for")
    @classmethod
    def _norm(cls, value: datetime | None) -> datetime | None:
        return _normalize_content_publish_date(value)


class ArticleUpdate(BaseModel):
    source_url: str | None = Field(default=None, min_length=8)
    title: str | None = Field(default=None, max_length=300)
    description: str | None = None
    thumbnail_url: str | None = None
    thumbnail_s3_key: str | None = None
    commentary: str | None = Field(default=None, max_length=3000)
    status: ArticleStatus | None = None
    scheduled_for: datetime | None = None
    first_comment_text: str | None = Field(default=None, max_length=1250)

    @field_validator("scheduled_for")
    @classmethod
    def _norm(cls, value: datetime | None) -> datetime | None:
        return _normalize_content_publish_date(value)


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    source_url: str
    title: str | None
    description: str | None
    thumbnail_url: str | None
    thumbnail_s3_key: str | None
    linkedin_image_urn: str | None
    commentary: str | None
    status: ArticleStatus
    scheduled_for: datetime | None
    published_at: datetime | None
    linkedin_post_urn: str | None
    error_message: str | None

    first_comment_text: str | None
    first_comment_status: FirstCommentStatus | None
    first_comment_pin_status: FirstCommentPinStatus | None
    first_comment_urn: str | None
    first_comment_posted_at: datetime | None
    first_comment_error: str | None

    impressions: int
    likes: int
    comments: int
    shares: int
    engagement_rate: float | None
    metrics_updated_at: datetime | None

    source_newsletter_id: uuid.UUID | None
    auto_scraped: bool
    scraped_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ArticleScrapeRequest(BaseModel):
    source_url: str = Field(..., min_length=8)


class ArticleScrapeResponse(BaseModel):
    title: str | None
    description: str | None
    thumbnail_url: str | None
    cached: bool


class ArticleScheduleRequest(BaseModel):
    scheduled_for: datetime

    @field_validator("scheduled_for")
    @classmethod
    def _norm(cls, value: datetime) -> datetime:
        normalized = _normalize_content_publish_date(value)
        assert normalized is not None
        return normalized


class ArticleMetricsUpdate(BaseModel):
    impressions: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
