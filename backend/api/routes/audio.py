"""
api/routes/audio.py

Rota de servimento temporário de áudio para voice notes.

Fluxo:
  1. Worker de dispatch gera áudio via Speechify (bytes MP3)
  2. Armazena os bytes no Redis com chave uuid4 e TTL de 1 hora
  3. Passa a URL pública desta rota para a Unipile
  4. Unipile busca o áudio neste endpoint para entregar a voice note

Endpoint:
  GET /audio/{key}  — retorna MP3 como application/octet-stream
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from core.redis_client import redis_client

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.get("/{key}", response_class=Response)
async def serve_audio(key: str) -> Response:
    """
    Serve bytes de áudio armazenados temporariamente no Redis.

    Os bytes são armazenados pelo worker de dispatch antes de chamar a Unipile.
    O TTL padrão é 3600 s (1 hora) — suficiente para a Unipile buscar o arquivo.
    """
    audio_bytes = await redis_client.get_bytes(f"audio:{key}")
    if audio_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Áudio não encontrado ou expirado.",
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"inline; filename={key}.mp3"},
    )
