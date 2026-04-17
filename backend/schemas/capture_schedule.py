"""
schemas/capture_schedule.py

Schemas Pydantic v2 para CaptureScheduleConfig.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CaptureSource = Literal["google_maps", "b2b_database"]


class GoogleMapsConfigFields(BaseModel):
    search_terms: list[str] = Field(default_factory=list)
    location: str | None = None
    categories: list[str] = Field(default_factory=list)


class B2BConfigFields(BaseModel):
    job_titles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    company_keywords: list[str] = Field(default_factory=list)
    company_sizes: list[str] = Field(default_factory=list)


class CaptureScheduleUpsert(BaseModel):
    """Payload para criar ou atualizar a configuração de captura de uma fonte."""

    source: CaptureSource
    is_active: bool = True
    max_items: int = Field(default=25, ge=1, le=500)

    # Google Maps
    maps_search_terms: list[str] = Field(default_factory=list)
    maps_location: str | None = None
    maps_locations: list[str] = Field(default_factory=list)
    maps_categories: list[str] = Field(default_factory=list)

    # B2B Database
    b2b_job_titles: list[str] = Field(default_factory=list)
    b2b_locations: list[str] = Field(default_factory=list)
    b2b_cities: list[str] = Field(default_factory=list)
    b2b_industries: list[str] = Field(default_factory=list)
    b2b_company_keywords: list[str] = Field(default_factory=list)
    b2b_company_sizes: list[str] = Field(default_factory=list)


class CaptureScheduleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    is_active: bool
    max_items: int

    maps_search_terms: list[str] | None
    maps_location: str | None
    maps_locations: list[str] | None
    maps_categories: list[str] | None

    b2b_job_titles: list[str] | None
    b2b_locations: list[str] | None
    b2b_cities: list[str] | None
    b2b_industries: list[str] | None
    b2b_company_keywords: list[str] | None
    b2b_company_sizes: list[str] | None

    maps_combo_index: int
    b2b_rotation_index: int
    last_run_at: datetime | None
    last_list_id: uuid.UUID | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaptureExecutionLogResponse(BaseModel):
    id: uuid.UUID
    capture_config_id: uuid.UUID
    source: str
    list_id: uuid.UUID | None
    list_name: str | None
    combo_label: str | None
    leads_received: int
    leads_inserted: int
    leads_skipped: int
    status: str
    error_message: str | None
    executed_at: datetime

    model_config = {"from_attributes": True}
