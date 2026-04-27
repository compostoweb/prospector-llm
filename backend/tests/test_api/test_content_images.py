from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from integrations.s3_client import S3Client
from models.content_gallery_image import ContentGalleryImage
from models.content_post import ContentPost
from models.tenant import Tenant
from services.content import image_generator as image_generator_service

pytestmark = pytest.mark.asyncio


async def test_generate_standalone_image_creates_independent_gallery_asset(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate_standalone_image(**_: object) -> tuple[bytes, str]:
        return (b"fake-image-bytes", "Prompt final usado")

    def fake_upload_bytes(
        self: S3Client,
        data: bytes,
        key: str,
        content_type: str,
    ) -> str:
        assert data == b"fake-image-bytes"
        assert content_type == "image/png"
        return f"https://example.com/{key}"

    monkeypatch.setattr(
        image_generator_service,
        "generate_standalone_image",
        fake_generate_standalone_image,
    )
    monkeypatch.setattr(S3Client, "upload_bytes", fake_upload_bytes)

    posts_before = await db.scalar(select(func.count()).select_from(ContentPost))

    response = await client.post(
        "/api/content/images/generate",
        json={
            "prompt": "O problema, na maioria das vezes, nunca esta onde voce pensa!",
            "style": "with_text",
            "aspect_ratio": "1:1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["image_url"].startswith("https://example.com/gallery/images/")
    assert body["image_prompt"] == "Prompt final usado"
    assert body["image_id"]

    posts_after = await db.scalar(select(func.count()).select_from(ContentPost))
    assert posts_after == posts_before

    generated_image = await db.get(ContentGalleryImage, uuid.UUID(body["image_id"]))
    assert generated_image is not None
    assert generated_image.linked_post_id is None
    assert generated_image.source == "generated"
    assert generated_image.title == "O problema, na maioria das vezes, nunca esta onde voce pensa!"

    gallery_response = await client.get("/api/content/images")
    assert gallery_response.status_code == 200
    gallery_items = gallery_response.json()["images"]
    assert len(gallery_items) == 1
    assert gallery_items[0]["id"] == body["image_id"]
    assert gallery_items[0]["linked_post_id"] is None
    assert gallery_items[0]["title"] == generated_image.title
    assert gallery_items[0]["post_status"] is None


async def test_get_gallery_image_file_proxies_standalone_asset(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gallery_image = ContentGalleryImage(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Imagem standalone",
        source="generated",
        image_url="https://example.com/gallery/image.png",
        image_s3_key="gallery/images/test.png",
        image_style="clean",
        image_prompt="Prompt standalone",
    )
    db.add(gallery_image)
    await db.commit()

    def fake_get_bytes(self: S3Client, key: str) -> tuple[bytes, str]:
        assert key == "gallery/images/test.png"
        return (b"image-bytes", "image/png")

    monkeypatch.setattr(S3Client, "get_bytes", fake_get_bytes)

    response = await client.get(f"/api/content/images/{gallery_image.id}/file")

    assert response.status_code == 200
    assert response.content == b"image-bytes"
    assert response.headers["content-type"].startswith("image/png")


async def test_delete_gallery_image_blocks_scheduled_post(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Post agendado com imagem",
        body="Texto",
        pillar="case",
        status="scheduled",
        image_url="https://example.com/image.png",
    )
    db.add(post)
    await db.flush()

    response = await client.delete(f"/api/content/images/{post.id}")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Nao e possivel excluir a imagem de posts agendados ou publicados. "
        "Altere o status do post antes de remover a imagem."
    )


async def test_delete_gallery_image_clears_image_for_draft_post(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Rascunho com imagem",
        body="Texto",
        pillar="case",
        status="draft",
        image_url="https://example.com/image.png",
        image_style="clean",
        image_prompt="Prompt de teste",
        image_aspect_ratio="4:5",
        image_filename="imagem.png",
        image_size_bytes=12345,
    )
    db.add(post)
    await db.flush()

    response = await client.delete(f"/api/content/images/{post.id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    await db.refresh(post)

    assert post.image_url is None
    assert post.image_s3_key is None
    assert post.image_style is None
    assert post.image_prompt is None
    assert post.image_aspect_ratio is None
    assert post.image_filename is None
    assert post.image_size_bytes is None
    assert post.linkedin_image_urn is None


async def test_upload_standalone_image_creates_independent_gallery_asset(
    client: AsyncClient,
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_upload_bytes(
        self: S3Client,
        data: bytes,
        key: str,
        content_type: str,
    ) -> str:
        assert data == b"fake-upload-bytes"
        assert content_type == "image/png"
        return f"https://example.com/{key}"

    monkeypatch.setattr(S3Client, "upload_bytes", fake_upload_bytes)

    posts_before = await db.scalar(select(func.count()).select_from(ContentPost))

    response = await client.post(
        "/api/content/images/upload",
        files={"file": ("galeria.png", b"fake-upload-bytes", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["image_url"].startswith("https://example.com/gallery/uploads/")
    assert body["filename"] == "galeria.png"
    assert body["size_bytes"] == len(b"fake-upload-bytes")
    assert body["image_id"]

    posts_after = await db.scalar(select(func.count()).select_from(ContentPost))
    assert posts_after == posts_before

    uploaded_image = await db.get(ContentGalleryImage, uuid.UUID(body["image_id"]))
    assert uploaded_image is not None
    assert uploaded_image.linked_post_id is None
    assert uploaded_image.source == "uploaded"
    assert uploaded_image.title == "galeria.png"


async def test_delete_gallery_image_removes_standalone_asset(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    gallery_image = ContentGalleryImage(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Imagem standalone",
        source="generated",
        image_url="https://example.com/gallery/image.png",
        image_s3_key="gallery/images/test.png",
        image_style="clean",
        image_prompt="Prompt standalone",
    )
    db.add(gallery_image)
    await db.flush()

    response = await client.delete(f"/api/content/images/{gallery_image.id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert await db.get(ContentGalleryImage, gallery_image.id) is None
