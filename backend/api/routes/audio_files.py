"""
api/routes/audio_files.py — CRUD de arquivos de áudio pré-gravados.

Permite upload, listagem e deleção de áudios no S3/MinIO.
Os áudios podem ser usados em cadence steps como voice notes personalizados.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible
from integrations.s3_client import s3_client
from models.audio_file import AudioFile
from schemas.audio_file import (
    AudioFileListResponse,
    AudioFileResponse,
    AudioFileUpdateRequest,
    AudioFileUploadResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/audio-files", tags=["Audio Files"])

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_TYPES = {"audio/mpeg", "audio/wav", "audio/mp3", "audio/ogg", "audio/webm", "audio/x-wav", "audio/mp4"}


@router.post("", response_model=AudioFileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    language: str = Form(default="pt-BR"),
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> AudioFileUploadResponse:
    """Upload de um arquivo de áudio para o S3."""
    if s3_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Armazenamento S3 não configurado.",
        )

    # Normaliza content_type (remove parâmetros como ;codecs=opus)
    raw_ct = file.content_type or "audio/mpeg"
    content_type = raw_ct.split(";")[0].strip()

    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado: {content_type}. Use: {sorted(_ALLOWED_TYPES)}",
        )

    # Lê bytes e valida tamanho
    data = await file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo muito grande ({len(data)} bytes). Máximo: {_MAX_FILE_SIZE} bytes (10 MB).",
        )
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    # Upload para S3
    filename = file.filename or "audio.mp3"
    s3_key, url = s3_client.upload_audio(
        data=data,
        tenant_id=str(tenant_id),
        filename=filename,
        content_type=content_type,
    )

    # Salva no banco
    audio_file = AudioFile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name.strip(),
        s3_key=s3_key,
        url=url,
        content_type=content_type,
        size_bytes=len(data),
        language=language,
    )
    db.add(audio_file)
    await db.commit()
    await db.refresh(audio_file)

    logger.info(
        "audio_file.uploaded",
        audio_file_id=str(audio_file.id),
        tenant_id=str(tenant_id),
        s3_key=s3_key,
        size=len(data),
    )

    return AudioFileUploadResponse(
        audio_file=AudioFileResponse.model_validate(audio_file),
    )


@router.get("", response_model=AudioFileListResponse)
async def list_audio_files(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> AudioFileListResponse:
    """Lista todos os arquivos de áudio do tenant."""
    result = await db.execute(
        select(AudioFile)
        .where(AudioFile.tenant_id == tenant_id)
        .order_by(AudioFile.created_at.desc())
    )
    items = list(result.scalars().all())

    count_result = await db.execute(
        select(func.count()).select_from(AudioFile).where(AudioFile.tenant_id == tenant_id)
    )
    total = count_result.scalar() or 0

    return AudioFileListResponse(
        items=[AudioFileResponse.model_validate(af) for af in items],
        total=total,
    )


@router.get("/{audio_file_id}", response_model=AudioFileResponse)
async def get_audio_file(
    audio_file_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> AudioFileResponse:
    """Busca um arquivo de áudio por ID."""
    result = await db.execute(
        select(AudioFile).where(
            AudioFile.id == audio_file_id,
            AudioFile.tenant_id == tenant_id,
        )
    )
    af = result.scalar_one_or_none()
    if af is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Áudio não encontrado.")
    return AudioFileResponse.model_validate(af)


@router.patch("/{audio_file_id}", response_model=AudioFileResponse)
async def update_audio_file(
    audio_file_id: uuid.UUID,
    body: AudioFileUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> AudioFileResponse:
    """Atualiza metadados de um arquivo de áudio."""
    result = await db.execute(
        select(AudioFile).where(
            AudioFile.id == audio_file_id,
            AudioFile.tenant_id == tenant_id,
        )
    )
    af = result.scalar_one_or_none()
    if af is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Áudio não encontrado.")

    if body.name is not None:
        af.name = body.name
    if body.language is not None:
        af.language = body.language

    await db.commit()
    await db.refresh(af)
    return AudioFileResponse.model_validate(af)


@router.delete("/{audio_file_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_audio_file(
    audio_file_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    """Remove um arquivo de áudio do S3 e do banco."""
    result = await db.execute(
        select(AudioFile).where(
            AudioFile.id == audio_file_id,
            AudioFile.tenant_id == tenant_id,
        )
    )
    af = result.scalar_one_or_none()
    if af is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Áudio não encontrado.")

    # Remove do S3
    if s3_client is not None and af.s3_key:
        try:
            s3_client.delete_object(af.s3_key)
        except Exception:
            logger.warning("audio_file.s3_delete_failed", s3_key=af.s3_key, audio_file_id=str(audio_file_id))

    await db.delete(af)
    await db.commit()

    logger.info(
        "audio_file.deleted",
        audio_file_id=str(audio_file_id),
        tenant_id=str(tenant_id),
    )
