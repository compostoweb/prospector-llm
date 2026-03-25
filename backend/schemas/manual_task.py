"""
schemas/manual_task.py

Schemas Pydantic v2 para tarefas manuais da cadência semi-automática.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from models.enums import Channel, ManualTaskStatus
from schemas.lead import LeadResponse


class ManualTaskResponse(BaseModel):
    """Representação completa de uma tarefa manual."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    cadence_id: uuid.UUID
    lead_id: uuid.UUID
    cadence_step_id: uuid.UUID | None = None
    channel: Channel
    step_number: int
    status: ManualTaskStatus
    generated_text: str | None = None
    generated_audio_url: str | None = None
    edited_text: str | None = None
    sent_at: datetime | None = None
    unipile_message_id: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    # Lead aninhado (carregado via selectin)
    lead: LeadResponse | None = None


class ManualTaskListResponse(BaseModel):
    """Paginação de tarefas manuais."""
    items: list[ManualTaskResponse]
    total: int
    page: int
    page_size: int


class ManualTaskUpdateRequest(BaseModel):
    """Atualizar texto editado pelo operador."""
    edited_text: str = Field(..., min_length=1)


class ManualTaskDoneExternalRequest(BaseModel):
    """Marcar tarefa como executada externamente."""
    notes: str | None = None


class ManualTaskStatsResponse(BaseModel):
    """Estatísticas de tarefas manuais."""
    pending: int = 0
    content_generated: int = 0
    sent: int = 0
    done_external: int = 0
