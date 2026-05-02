from __future__ import annotations

from datetime import UTC, datetime
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.s3_client import S3Client
from models.content_post import ContentPost
from models.tenant import Tenant

pytestmark = pytest.mark.asyncio


async def test_create_post_normalizes_naive_publish_date_from_brasilia_to_utc(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/content/posts",
        json={
            "title": "Post com horario local",
            "body": "Texto do post",
            "pillar": "case",
            "publish_date": "2026-04-10T09:00:00",
        },
    )

    assert response.status_code == 201
    body = response.json()

    publish_date = datetime.fromisoformat(body["publish_date"].replace("Z", "+00:00"))
    assert publish_date == datetime(2026, 4, 10, 12, 0, tzinfo=UTC)


async def test_update_post_normalizes_naive_publish_date_from_brasilia_to_utc(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/content/posts",
        json={
            "title": "Post para atualizar horario",
            "body": "Texto do post",
            "pillar": "case",
        },
    )

    assert created.status_code == 201
    post_id = created.json()["id"]

    updated = await client.put(
        f"/api/content/posts/{post_id}",
        json={"publish_date": "2026-04-11T09:00:00"},
    )

    assert updated.status_code == 200
    body = updated.json()

    publish_date = datetime.fromisoformat(body["publish_date"].replace("Z", "+00:00"))
    assert publish_date == datetime(2026, 4, 11, 12, 0, tzinfo=UTC)


async def test_upload_post_image_rejects_mismatched_magic_bytes(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Post com imagem",
        body="Texto do post",
        pillar="case",
        status="draft",
    )
    db.add(post)
    await db.flush()

    response = await client.post(
        f"/api/content/posts/{post.id}/upload-image",
        files={"file": ("imagem.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conteudo do arquivo nao corresponde a uma imagem suportada."


async def test_upload_post_video_rejects_mismatched_magic_bytes(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Post com video",
        body="Texto do post",
        pillar="case",
        status="draft",
    )
    db.add(post)
    await db.flush()

    response = await client.post(
        f"/api/content/posts/{post.id}/upload-video",
        files={"file": ("video.mp4", b"not-a-video", "video/mp4")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conteudo do arquivo nao corresponde a um video suportado."


async def test_upload_post_image_sanitizes_filename_and_extension(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Post com imagem valida",
        body="Texto do post",
        pillar="case",
        status="draft",
    )
    db.add(post)
    await db.flush()

    def fake_upload_bytes(self: S3Client, data: bytes, key: str, content_type: str) -> str:
        assert data.startswith(b"\x89PNG")
        assert key == f"images/{tenant.id}/{post.id}.png"
        assert content_type == "image/png"
        return f"https://example.com/{key}"

    monkeypatch.setattr(S3Client, "upload_bytes", fake_upload_bytes)

    response = await client.post(
        f"/api/content/posts/{post.id}/upload-image",
        files={"file": ("..\\evil\r\nname.png", b"\x89PNG\r\n\x1a\nrest", "image/png")},
    )

    assert response.status_code == 200
    await db.refresh(post)
    assert post.image_filename == "evil_0D_0Aname.png"
