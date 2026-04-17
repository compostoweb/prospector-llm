from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

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
