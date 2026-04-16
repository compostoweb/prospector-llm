"""
schemas/enrichment_job.py

Schemas Pydantic para a fila de enriquecimento de perfis LinkedIn.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EnrichmentJobCreate(BaseModel):
    """Criação de um novo job de enriquecimento em lote."""

    linkedin_urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Lista completa de URLs de perfis LinkedIn a enriquecer.",
    )
    batch_size: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Quantas URLs processar por execução (default: 50).",
    )
    target_list_id: uuid.UUID | None = Field(
        default=None,
        description="Lista de leads onde os resultados serão inseridos. Se None, leads ficam sem lista.",
    )
    target_list_name: str | None = Field(
        default=None,
        max_length=200,
        description="Cria uma nova lista com este nome. Ignorado se target_list_id for informado.",
    )


class EnrichmentJobResponse(BaseModel):
    """Representação de um job de enriquecimento."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    target_list_id: uuid.UUID | None
    target_list_name: str | None = None
    total_count: int
    processed_count: int
    batch_size: int
    status: str
    progress_pct: int
    remaining_count: int
    batches_remaining: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
