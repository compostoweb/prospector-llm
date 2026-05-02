"""
api/routes/files.py

Proxy transparente para arquivos armazenados no MinIO.

Permite mascarar as URLs internas do MinIO com o domínio público do Prospector.
Não exige autenticação — estas rotas são acessadas por leads e visitantes externos.

Padrão de URL: /files/{prefix}/{tenant_id}/{filename}

Exemplos:
  GET /files/lm-pdfs/{tenant_id}/{filename}   → PDF do lead magnet
  GET /files/lm-images/{tenant_id}/{filename} → Imagem da landing page
"""

from __future__ import annotations

from urllib.parse import urlsplit

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from core.config import settings
from core.file_security import sanitize_download_filename

logger = structlog.get_logger()

router = APIRouter(prefix="/files", tags=["Files — Proxy público"])


def _build_pdf_embed_headers(filename: str) -> dict[str, str]:
    frontend_origin = urlsplit(settings.FRONTEND_URL).scheme + "://" + urlsplit(settings.FRONTEND_URL).netloc
    safe_filename = sanitize_download_filename(filename, fallback="document.pdf")
    return {
        "Content-Disposition": f'inline; filename="{safe_filename}"',
        "Content-Security-Policy": f"frame-ancestors 'self' {frontend_origin}",
        "Cache-Control": "public, max-age=300",
    }


@router.get("/lm-pdfs/{tenant_id}/{filename}", include_in_schema=False)
async def proxy_lm_pdf(tenant_id: str, filename: str) -> Response:
    """Proxy para PDFs de lead magnets armazenados no MinIO."""
    from integrations.s3_client import S3Client

    key = f"lm-pdfs/{tenant_id}/{filename}"
    try:
        s3 = S3Client()
        data, content_type = s3.get_bytes(key)
    except Exception:
        logger.warning("files.proxy.not_found", key=key)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado.",
        )
    return Response(
        content=data,
        media_type=content_type or "application/pdf",
        headers=_build_pdf_embed_headers(filename),
    )


@router.get("/lm-images/{tenant_id}/{filename}", include_in_schema=False)
async def proxy_lm_image(tenant_id: str, filename: str) -> Response:
    """Proxy para imagens de landing pages armazenadas no MinIO."""
    from integrations.s3_client import S3Client

    key = f"lm-images/{tenant_id}/{filename}"
    try:
        s3 = S3Client()
        data, content_type = s3.get_bytes(key)
    except Exception:
        logger.warning("files.proxy.not_found", key=key)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem não encontrada.",
        )
    return Response(
        content=data,
        media_type=content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )
