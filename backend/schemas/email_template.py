"""
schemas/email_template.py

Schemas Pydantic v2 para CRUD de EmailTemplate.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EmailTemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    subject: str = Field(..., min_length=1, max_length=500)
    body_html: str = Field(..., min_length=1)


class EmailTemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    body_html: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class EmailTemplateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    subject: str
    body_html: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
