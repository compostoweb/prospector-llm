"""
schemas/audio_file.py — Pydantic v2 schemas para áudios pré-gravados.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AudioFileResponse(BaseModel):
    """Representação de um arquivo de áudio na API."""

    model_config = {"from_attributes": True}

    id: UUID
    tenant_id: UUID
    name: str
    s3_key: str
    url: str
    content_type: str
    size_bytes: int
    duration_seconds: float | None = None
    language: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AudioFileUploadResponse(BaseModel):
    """Resposta após upload de áudio."""
    audio_file: AudioFileResponse
    message: str = "Áudio enviado com sucesso."


class AudioFileListResponse(BaseModel):
    """Lista de arquivos de áudio."""
    items: list[AudioFileResponse]
    total: int


class AudioFileUpdateRequest(BaseModel):
    """Atualização de metadados de um áudio."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
    language: str | None = Field(default=None, max_length=10)
