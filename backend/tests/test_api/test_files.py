from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_proxy_lm_pdf_allows_embed_from_frontend(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from api.routes import files as files_route
    from integrations import s3_client as s3_client_module

    class _FakeS3Client:
        def get_bytes(self, key: str) -> tuple[bytes, str]:
            assert key == "lm-pdfs/tenant-123/arquivo.pdf"
            return (b"%PDF-1.4 fake", "application/pdf")

    monkeypatch.setattr(files_route.settings, "FRONTEND_URL", "https://prospector.compostoweb.com.br")
    monkeypatch.setattr(s3_client_module, "S3Client", _FakeS3Client)

    response = await client.get("/files/lm-pdfs/tenant-123/arquivo.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == 'inline; filename="arquivo.pdf"'
    assert response.headers["content-security-policy"] == (
        "frame-ancestors 'self' https://prospector.compostoweb.com.br"
    )
    assert "x-frame-options" not in response.headers


def test_extract_storage_key_from_masked_url_from_other_environment() -> None:
    from api.routes.content.lead_magnets import _extract_storage_key_from_file_url

    key = _extract_storage_key_from_file_url(
        "https://api.prospector.compostoweb.com.br/files/lm-pdfs/tenant-123/arquivo.pdf"
    )

    assert key == "lm-pdfs/tenant-123/arquivo.pdf"


def test_extract_storage_key_from_bucket_url() -> None:
    from api.routes.content.lead_magnets import _extract_storage_key_from_file_url

    key = _extract_storage_key_from_file_url(
        "https://chatwoot-minio-prospector.ylkjah.easypanel.host/prospector/lm-pdfs/tenant-123/arquivo.pdf"
    )

    assert key == "lm-pdfs/tenant-123/arquivo.pdf"