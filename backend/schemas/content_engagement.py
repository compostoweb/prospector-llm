"""
schemas/content_engagement.py

Schemas Pydantic v2 para o modulo LinkedIn Engagement Scanner (Content Hub).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Tipos literais ─────────────────────────────────────────────────────────────

SessionStatus = Literal["running", "completed", "partial", "failed"]
EngagementPostType = Literal["reference", "icp"]
CommentStatus = Literal["pending", "selected", "posted", "discarded"]
HookType = Literal["loop_open", "contrarian", "identification", "shortcut", "benefit", "data"]
PostPillar = Literal["authority", "case", "vision"]


# ── Requests ───────────────────────────────────────────────────────────────────


class IcpFilters(BaseModel):
    titles: list[str] | None = None
    sectors: list[str] | None = None


class GoogleDiscoveryComposeRequest(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    exact_phrases: list[str] | None = None
    titles: list[str] | None = None
    sectors: list[str] | None = None
    company: str | None = None
    linked_post_id: uuid.UUID | None = None
    max_queries: int = Field(default=8, ge=1, le=20)


class RunScanRequest(BaseModel):
    linked_post_id: uuid.UUID | None = None
    keywords: list[str] | None = None
    manual_keywords: list[str] | None = None
    selected_theme_ids: list[uuid.UUID] | None = None
    icp_filters: IcpFilters | None = None


class AddManualPostRequest(BaseModel):
    source: Literal["manual", "google"] = "manual"
    post_url: str | None = None
    post_text: str = Field(..., min_length=1)
    author_name: str | None = None
    author_title: str | None = None
    author_company: str | None = None
    author_profile_url: str | None = None
    post_type: EngagementPostType = "icp"
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)


class ImportExternalPostsRequest(BaseModel):
    discovery_query_id: uuid.UUID | None = None
    posts: list[AddManualPostRequest] = Field(default_factory=list, min_length=1, max_length=50)


# ── Responses ──────────────────────────────────────────────────────────────────


class EngagementCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engagement_post_id: uuid.UUID
    session_id: uuid.UUID
    comment_text: str
    variation: int
    status: str
    posted_at: datetime | None
    created_at: datetime


class EngagementPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    session_id: uuid.UUID
    post_type: str
    source: str
    merged_sources: list[str] | None
    merge_count: int
    author_name: str | None
    author_title: str | None
    author_company: str | None
    author_linkedin_urn: str | None
    author_profile_url: str | None
    post_url: str | None
    canonical_post_url: str | None
    dedup_key: str | None
    post_text: str
    post_published_at: datetime | None
    likes: int
    comments: int
    shares: int
    engagement_score: int | None
    hook_type: str | None
    pillar: str | None
    why_it_performed: str | None
    what_to_replicate: str | None
    is_saved: bool
    suggested_comments: list[EngagementCommentResponse] = []
    created_at: datetime


class EngagementSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    linked_post_id: uuid.UUID | None
    status: str
    current_step: int | None = None
    references_found: int
    icp_posts_found: int
    comments_generated: int
    comments_posted: int
    scan_source: str
    selected_theme_ids: list[str] | None = None
    selected_theme_titles: list[str] | None = None
    manual_keywords: list[str] | None = None
    effective_keywords: list[str] | None = None
    linked_post_context_keywords: list[str] | None = None
    icp_titles_used: list[str] | None = None
    icp_sectors_used: list[str] | None = None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class EngagementSessionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    event_type: str
    payload: dict[str, object] | None
    created_at: datetime


class EngagementSessionDetailResponse(EngagementSessionResponse):
    """Sessao com posts e comentarios incluidos."""

    posts: list[EngagementPostResponse] = []
    events: list[EngagementSessionEventResponse] = []


class GoogleDiscoveryQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    query_text: str
    criteria: dict[str, object] | None
    imported_session_id: uuid.UUID | None
    created_at: datetime


class RunScanResponse(BaseModel):
    session_id: uuid.UUID
    status: SessionStatus


class ImportExternalPostsResponse(BaseModel):
    session_id: uuid.UUID
    created_count: int
    merged_count: int
    posts: list[EngagementPostResponse] = []
