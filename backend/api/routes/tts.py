"""
api/routes/tts.py

Endpoints para gerenciamento de provedores TTS e vozes.

GET    /tts/providers               → lista providers disponíveis
GET    /tts/voices                  → todas as vozes de todos os providers
GET    /tts/voices/{provider}       → vozes de um provider
POST   /tts/voices/{provider}       → upload de áudio para voice clone
DELETE /tts/voices/{provider}/{id}  → deletar voz clonada
POST   /tts/test                    → gerar sample de áudio de teste
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from api.dependencies import get_tts_registry
from core.file_security import detect_audio_content_type, sanitize_download_filename
from integrations.tts import TTSRegistry, TTSVoice

logger = structlog.get_logger()

router = APIRouter(prefix="/tts", tags=["TTS"])

_MAX_AUDIO_SIZE = 5 * 1024 * 1024  # 5 MB


# ── Schemas ───────────────────────────────────────────────────────────


class VoiceResponse(BaseModel):
    id: str
    name: str
    language: str
    provider: str
    is_cloned: bool

    @classmethod
    def from_tts_voice(cls, v: TTSVoice) -> VoiceResponse:
        return cls(
            id=v.id,
            name=v.name,
            language=v.language,
            provider=v.provider,
            is_cloned=v.is_cloned,
        )


class VoicesListResponse(BaseModel):
    providers: list[str]
    total: int
    voices: list[VoiceResponse]


class TestRequest(BaseModel):
    provider: str
    voice_id: str
    text: str = Field(
        default="Olá! Isso é um teste de voz do Prospector.",
        max_length=500,
    )
    language: str = "pt-BR"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-50.0, le=50.0)


# ── Rotas ─────────────────────────────────────────────────────────────


@router.get("/providers", summary="Lista provedores TTS configurados")
async def get_providers(
    registry: TTSRegistry = Depends(get_tts_registry),
) -> dict:
    return {"providers": registry.available_providers()}


@router.get(
    "/voices",
    response_model=VoicesListResponse,
    summary="Lista todas as vozes de todos os providers",
)
async def get_all_voices(
    force_refresh: bool = False,
    registry: TTSRegistry = Depends(get_tts_registry),
) -> VoicesListResponse:
    voices = await registry.list_all_voices(force_refresh=force_refresh)
    return VoicesListResponse(
        providers=registry.available_providers(),
        total=len(voices),
        voices=[VoiceResponse.from_tts_voice(v) for v in voices],
    )


@router.get(
    "/voices/{provider}",
    response_model=VoicesListResponse,
    summary="Lista vozes de um provider específico",
)
async def get_voices_by_provider(
    provider: str,
    registry: TTSRegistry = Depends(get_tts_registry),
) -> VoicesListResponse:
    if provider not in registry.available_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' não encontrado. Disponíveis: {registry.available_providers()}",
        )
    voices = await registry.list_voices_by_provider(provider)
    return VoicesListResponse(
        providers=[provider],
        total=len(voices),
        voices=[VoiceResponse.from_tts_voice(v) for v in voices],
    )


@router.post(
    "/voices/{provider}",
    response_model=VoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria voice clone via upload de áudio",
)
async def create_voice(
    provider: str,
    name: str = Form(..., min_length=2, max_length=100),
    language: str = Form(default="pt-BR"),
    audio: UploadFile = File(..., description="Áudio de referência (10-30s, <5MB)"),
    registry: TTSRegistry = Depends(get_tts_registry),
) -> VoiceResponse:
    if provider not in registry.available_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' não encontrado.",
        )

    audio_data = await audio.read()
    if len(audio_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de referencia vazio.",
        )
    if len(audio_data) > _MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo: {_MAX_AUDIO_SIZE // (1024 * 1024)} MB.",
        )

    detected_content_type = detect_audio_content_type(audio_data)
    if detected_content_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de referencia invalido ou formato nao reconhecido.",
        )

    voice = await registry.create_voice(
        provider=provider,
        name=name,
        audio_data=audio_data,
        language=language,
        filename=sanitize_download_filename(audio.filename or "audio", fallback="audio"),
        content_type=detected_content_type,
    )
    logger.info("tts.voice.created", provider=provider, voice_id=voice.id, name=name)
    return VoiceResponse.from_tts_voice(voice)


@router.delete(
    "/voices/{provider}/{voice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Deleta voz clonada",
)
async def delete_voice(
    provider: str,
    voice_id: str,
    registry: TTSRegistry = Depends(get_tts_registry),
) -> None:
    if provider not in registry.available_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' não encontrado.",
        )
    await registry.delete_voice(provider=provider, voice_id=voice_id)
    logger.info("tts.voice.deleted", provider=provider, voice_id=voice_id)


@router.post(
    "/test",
    summary="Gera sample de áudio para teste",
    responses={200: {"content": {"audio/mpeg": {}}}},
)
async def test_tts(
    body: TestRequest,
    registry: TTSRegistry = Depends(get_tts_registry),
) -> Response:
    if body.provider not in registry.available_providers():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{body.provider}' não encontrado.",
        )
    audio_bytes = await registry.synthesize(
        provider=body.provider,
        voice_id=body.voice_id,
        text=body.text,
        language=body.language,
        speed=body.speed,
        pitch=body.pitch,
    )
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": (
                f"inline; filename={sanitize_download_filename(f'tts_test_{uuid.uuid4().hex[:8]}.mp3', fallback='tts_test.mp3')}"
            )
        },
    )
