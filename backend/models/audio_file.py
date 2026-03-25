"""
models/audio_file.py — Arquivo de áudio pré-gravado no S3.

Permite que o usuário faça upload de áudios próprios
e os utilize em steps de cadência como voice notes.
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TenantMixin, TimestampMixin


class AudioFile(Base, TenantMixin, TimestampMixin):
    """Arquivo de áudio armazenado no S3/MinIO."""

    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="Nome amigável (ex: 'Abertura padrão')",
    )
    s3_key: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True,
        comment="Chave do objeto no bucket S3",
    )
    url: Mapped[str] = mapped_column(
        String(1000), nullable=False,
        comment="URL pública do arquivo",
    )
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="audio/mpeg",
        comment="MIME type (ex: audio/mpeg, audio/wav)",
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="Tamanho do arquivo em bytes",
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        nullable=True, default=None,
        comment="Duração do áudio em segundos (preenchido se disponível)",
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pt-BR",
        comment="Idioma do áudio",
    )
