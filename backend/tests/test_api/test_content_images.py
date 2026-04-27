from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_post import ContentPost
from models.tenant import Tenant

pytestmark = pytest.mark.asyncio


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
