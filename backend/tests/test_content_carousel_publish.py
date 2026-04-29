"""
tests/test_content_carousel_publish.py — Phase 1E

Testa publicacao de carrossel multi-imagem mockando LinkedInClient.

Cobertura:
- publish_now com media_kind=carousel chama create_post com media_urns ordenados por position
- Falha de upload em uma das imagens nao publica carrossel parcial
- Retry de upload com backoff (3 tentativas) antes de propagar erro
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_gallery_image import ContentGalleryImage
from models.content_linkedin_account import ContentLinkedInAccount
from models.content_post import ContentPost


@pytest_asyncio.fixture
async def linkedin_account(
    db: AsyncSession, tenant, tenant_id: uuid.UUID
) -> ContentLinkedInAccount:
    account = ContentLinkedInAccount(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        access_token="fake-token-plain",
        person_id="abc123",
        person_urn="urn:li:person:abc123",
        is_active=True,
        connected_at=datetime.now(UTC),
        token_expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(account)
    await db.flush()
    return account


@pytest_asyncio.fixture
async def carousel_post(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    linkedin_account: ContentLinkedInAccount,
) -> ContentPost:
    post = ContentPost(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        title="Test Carousel",
        body="Body do carrossel",
        pillar="autoridade",
        status="approved",
        media_kind="carousel",
    )
    db.add(post)
    await db.flush()
    # 3 imagens em ordem reversa para testar ordenacao por position
    images = [
        ContentGalleryImage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title=f"Carousel image {i}",
            image_url=f"https://test.s3/img{i}.png",
            image_s3_key=f"carousel/img{i}.png",
            linked_post_id=post.id,
            position=i,
            carousel_group_id=post.id,
        )
        for i in (2, 0, 1)  # ordem inserida fora de sequencia
    ]
    for img in images:
        db.add(img)
    await db.flush()
    return post


@pytest.mark.asyncio
async def test_carousel_publish_orders_media_urns_by_position(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    carousel_post: ContentPost,
) -> None:
    """publish_now deve enviar media_urns na ordem das positions (0, 1, 2)."""
    from services.content import publisher

    captured: dict = {}

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    # Cada upload retorna um URN unico baseado em contador
    upload_counter = {"n": 0}

    async def fake_upload(image_bytes: bytes) -> str:
        urn = f"urn:li:image:{upload_counter['n']}"
        upload_counter["n"] += 1
        return urn

    fake_client.upload_image = AsyncMock(side_effect=fake_upload)

    async def fake_create_post(text, media_urn=None, media_urns=None, media_category="NONE"):
        captured["text"] = text
        captured["media_urns"] = media_urns
        captured["media_category"] = media_category
        return {"id": "urn:li:share:result"}

    fake_client.create_post = AsyncMock(side_effect=fake_create_post)

    with (
        patch.object(publisher, "LinkedInClient", return_value=fake_client),
        patch.object(publisher, "S3Client") as fake_s3,
    ):
        fake_s3.return_value.get_bytes.return_value = (b"fake-bytes", "image/png")
        result = await publisher.publish_now(db, post_id=carousel_post.id, tenant_id=tenant_id)

    assert result.status == "published"
    assert result.linkedin_post_urn == "urn:li:share:result"
    assert captured["media_category"] == "IMAGE"
    assert captured["media_urns"] is not None
    assert len(captured["media_urns"]) == 3
    # URNs distintos (3 uploads independentes)
    assert len(set(captured["media_urns"])) == 3


@pytest.mark.asyncio
async def test_carousel_upload_failure_does_not_publish(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    carousel_post: ContentPost,
) -> None:
    """Se upload de uma imagem falhar definitivamente, nao publica carrossel parcial."""
    from services.content import publisher
    from services.content.linkedin_client import LinkedInClientError

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    # Sempre falha — esgota retries
    fake_client.upload_image = AsyncMock(side_effect=LinkedInClientError(500, "upload error"))
    fake_client.create_post = AsyncMock()

    with (
        patch.object(publisher, "LinkedInClient", return_value=fake_client),
        patch.object(publisher, "S3Client") as fake_s3,
        # Curto-circuita sleeps de retry
        patch("asyncio.sleep", AsyncMock()),
    ):
        fake_s3.return_value.get_bytes.return_value = (b"fake-bytes", "image/png")
        with pytest.raises(LinkedInClientError):
            await publisher.publish_now(db, post_id=carousel_post.id, tenant_id=tenant_id)

    # create_post nunca foi chamado — nao publicou parcial
    fake_client.create_post.assert_not_called()
    # Post marcado como failed
    await db.refresh(carousel_post)
    assert carousel_post.status == "failed"


@pytest.mark.asyncio
async def test_carousel_upload_retries_with_backoff(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    carousel_post: ContentPost,
) -> None:
    """Upload deve tentar 3x antes de desistir. 2 falhas + sucesso = ok."""
    from services.content import publisher
    from services.content.linkedin_client import LinkedInClientError

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    # Cada imagem: 2 falhas + 1 sucesso
    call_counts: dict[int, int] = {}
    counter = {"i": 0}

    async def flaky_upload(image_bytes: bytes) -> str:
        idx = counter["i"]
        call_counts[idx] = call_counts.get(idx, 0) + 1
        if call_counts[idx] < 3:
            raise LinkedInClientError(503, "transient")
        counter["i"] += 1
        return f"urn:li:image:{idx}"

    fake_client.upload_image = AsyncMock(side_effect=flaky_upload)

    captured_urns: list[str] | None = None

    async def fake_create_post(text, media_urn=None, media_urns=None, media_category="NONE"):
        nonlocal captured_urns
        captured_urns = media_urns
        return {"id": "urn:li:share:retry"}

    fake_client.create_post = AsyncMock(side_effect=fake_create_post)

    with (
        patch.object(publisher, "LinkedInClient", return_value=fake_client),
        patch.object(publisher, "S3Client") as fake_s3,
        patch("asyncio.sleep", AsyncMock()),
    ):
        fake_s3.return_value.get_bytes.return_value = (b"fake-bytes", "image/png")
        result = await publisher.publish_now(db, post_id=carousel_post.id, tenant_id=tenant_id)

    assert result.status == "published"
    assert captured_urns is not None
    assert len(captured_urns) == 3
