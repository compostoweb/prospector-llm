from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_article import ContentArticle
from models.content_lead_magnet import ContentLeadMagnet
from models.content_newsletter import ContentNewsletter
from models.content_post import ContentPost
from models.tenant import Tenant

pytestmark = pytest.mark.asyncio


async def test_article_thumbnail_rejects_mismatched_magic_bytes(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    article = ContentArticle(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        source_url="https://example.com/article",
        title="Article",
        status="draft",
    )
    db.add(article)
    await db.flush()

    response = await client.post(
        f"/api/content/articles/{article.id}/upload-thumbnail",
        files={"file": ("thumb.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conteudo do arquivo nao corresponde a uma imagem suportada."


async def test_newsletter_cover_rejects_mismatched_magic_bytes(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    newsletter = ContentNewsletter(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        edition_number=1,
        title="Newsletter",
        status="draft",
    )
    db.add(newsletter)
    await db.flush()

    response = await client.post(
        f"/api/content/newsletters/{newsletter.id}/upload-cover",
        files={"file": ("cover.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conteudo do arquivo nao corresponde a uma imagem suportada."


async def test_landing_page_image_rejects_mismatched_magic_bytes(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    lead_magnet = ContentLeadMagnet(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="pdf",
        title="Lead magnet",
        status="draft",
    )
    db.add(lead_magnet)
    await db.flush()

    response = await client.post(
        f"/api/content/landing-pages/{lead_magnet.id}/upload-lp-image",
        files={"file": ("hero.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conteudo do arquivo nao corresponde a uma imagem suportada."


async def test_carousel_image_rejects_mismatched_magic_bytes(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Carousel post",
        body="Texto",
        pillar="case",
        status="draft",
    )
    db.add(post)
    await db.flush()

    response = await client.post(
        f"/api/content/posts/{post.id}/carousel/images",
        files={"file": ("carousel.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conteudo do arquivo nao corresponde a uma imagem suportada."


async def test_lead_magnet_pdf_rejects_non_pdf_content(
    client: AsyncClient,
    db: AsyncSession,
    tenant: Tenant,
) -> None:
    lead_magnet = ContentLeadMagnet(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="pdf",
        title="Lead magnet pdf",
        status="draft",
    )
    db.add(lead_magnet)
    await db.flush()

    response = await client.post(
        f"/api/content/lead-magnets/{lead_magnet.id}/upload-pdf",
        files={"file": ("material.pdf", b"not-a-pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conteudo do arquivo nao corresponde a um PDF valido."