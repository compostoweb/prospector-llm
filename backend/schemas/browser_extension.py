from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ExtensionBrowser = Literal["chrome", "edge"]
ExtensionDestinationType = Literal["reference", "engagement"]
ExtensionCaptureResult = Literal["created", "merged"]
ExtensionCaptureSource = Literal["feed", "post_detail", "unknown"]
EngagementImportPostType = Literal["reference", "icp"]


class BrowserExtensionUserSummary(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    is_superuser: bool


class BrowserExtensionStartSessionRequest(BaseModel):
    extension_id: str = Field(..., min_length=8, max_length=64)
    extension_version: str = Field(..., min_length=1, max_length=32)
    browser: ExtensionBrowser


class BrowserExtensionStartSessionResponse(BaseModel):
    auth_session_id: uuid.UUID
    authorization_url: str
    expires_in: int


class BrowserExtensionExchangeRequest(BaseModel):
    grant_code: str = Field(..., min_length=8, max_length=255)
    extension_id: str = Field(..., min_length=8, max_length=64)


class BrowserExtensionExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: BrowserExtensionUserSummary


class BrowserExtensionFeatureFlags(BaseModel):
    capture_reference: bool
    capture_engagement: bool


class BrowserExtensionLinkedInStatus(BaseModel):
    connected: bool
    display_name: str | None = None


class BrowserExtensionRecentEngagementSession(BaseModel):
    id: uuid.UUID
    status: str
    scan_source: str
    created_at: datetime


class BrowserExtensionBootstrapResponse(BaseModel):
    user: BrowserExtensionUserSummary
    linkedin: BrowserExtensionLinkedInStatus
    features: BrowserExtensionFeatureFlags
    recent_engagement_sessions: list[BrowserExtensionRecentEngagementSession]


class BrowserExtensionCaptureDestination(BaseModel):
    type: ExtensionDestinationType
    session_id: uuid.UUID | None = None


class BrowserExtensionPostPayload(BaseModel):
    post_url: str | None = Field(default=None, max_length=500)
    canonical_post_url: str | None = Field(default=None, max_length=500)
    post_text: str = Field(..., min_length=1)
    author_name: str | None = Field(default=None, max_length=300)
    author_title: str | None = Field(default=None, max_length=500)
    author_company: str | None = Field(default=None, max_length=300)
    author_profile_url: str | None = Field(default=None, max_length=500)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    post_type: EngagementImportPostType = "reference"


class BrowserExtensionClientContext(BaseModel):
    captured_from: ExtensionCaptureSource = "unknown"
    page_url: str | None = Field(default=None, max_length=500)
    captured_at: datetime | None = None
    extension_version: str | None = Field(default=None, max_length=32)


class BrowserExtensionCaptureRequest(BaseModel):
    destination: BrowserExtensionCaptureDestination
    post: BrowserExtensionPostPayload
    client_context: BrowserExtensionClientContext


class BrowserExtensionImportStatusCandidate(BaseModel):
    candidate_key: str = Field(..., min_length=1, max_length=400)
    post_url: str | None = Field(default=None, max_length=500)
    canonical_post_url: str | None = Field(default=None, max_length=500)
    post_text: str = Field(..., min_length=1)
    author_name: str | None = Field(default=None, max_length=300)


class BrowserExtensionImportStatusRequest(BaseModel):
    candidates: list[BrowserExtensionImportStatusCandidate] = Field(..., min_length=1, max_length=50)


class BrowserExtensionImportStatusMatch(BaseModel):
    candidate_key: str
    imported: bool
    destination_type: ExtensionDestinationType | None = None
    linked_object_type: str | None = None
    linked_object_id: uuid.UUID | None = None


class BrowserExtensionImportStatusResponse(BaseModel):
    matches: list[BrowserExtensionImportStatusMatch]


class BrowserExtensionCaptureResponse(BaseModel):
    destination: ExtensionDestinationType
    result: ExtensionCaptureResult
    dedup_key: str | None = None
    reference_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    engagement_post_id: uuid.UUID | None = None
