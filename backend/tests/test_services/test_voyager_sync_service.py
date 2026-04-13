from __future__ import annotations

import pytest
from sqlalchemy import select

from models.content_post import ContentPost
from models.linkedin_account import LinkedInAccount
from services.content import voyager_sync_service

pytestmark = pytest.mark.asyncio


class _FakeUnipileClient:
    def __init__(
        self,
        *,
        own_profile: dict | None = None,
        own_profile_error: Exception | None = None,
        posts_by_identifier: dict[str, list[dict]] | None = None,
    ) -> None:
        self._own_profile = own_profile or None
        self._own_profile_error = own_profile_error
        self._posts_by_identifier = posts_by_identifier or {}
        self.requested_identifiers: list[str] = []

    async def __aenter__(self) -> _FakeUnipileClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get_own_profile(self, account_id: str) -> dict:
        if self._own_profile_error is not None:
            raise self._own_profile_error
        return self._own_profile or {}

    async def get_own_posts_with_metrics(
        self,
        account_id: str,
        identifier: str,
        limit: int = 50,
    ) -> list[dict]:
        self.requested_identifiers.append(identifier)
        if identifier not in self._posts_by_identifier:
            raise RuntimeError(f"identifier {identifier} not found")
        return self._posts_by_identifier[identifier][:limit]


async def test_sync_voyager_uses_saved_linkedin_username_when_profile_lookup_times_out(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-123",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile_error=RuntimeError("Falha de conexao com Unipile: ReadTimeout"),
        posts_by_identifier={
            "adrianovaladao": [
                {
                    "id": "unipile-post-1",
                    "social_id": "urn:li:ugcPost:123",
                    "text": "Post importado do LinkedIn",
                    "impressions_counter": 120,
                    "reaction_counter": 10,
                    "comment_counter": 4,
                    "repost_counter": 2,
                    "save_counter": 1,
                    "parsed_datetime": "2026-04-10T12:00:00Z",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 1
    assert result.posts_updated == 0
    assert result.posts_skipped == 0
    assert fake_client.requested_identifiers == ["adrianovaladao"]

    saved_post = (
        await db.execute(
            select(ContentPost).where(
                ContentPost.tenant_id == tenant.id,
                ContentPost.linkedin_post_urn == "urn:li:ugcPost:123",
            )
        )
    ).scalar_one()
    assert saved_post.title.startswith("[LinkedIn] Post importado do LinkedIn")
    assert saved_post.impressions == 120
    assert saved_post.likes == 10
    assert saved_post.comments == 4
    assert saved_post.shares == 2
    assert saved_post.saves == 1


async def test_sync_voyager_fails_when_no_identifier_can_be_resolved(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta sem username",
        linkedin_username=None,
        provider_type="unipile",
        unipile_account_id="acc-456",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile_error=RuntimeError("Falha de conexao com Unipile: ReadTimeout"),
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is False
    assert result.posts_created == 0
    assert result.posts_updated == 0
    assert result.posts_skipped == 0
    assert "Nao foi possivel identificar o perfil LinkedIn na Unipile" in (result.error or "")
    assert fake_client.requested_identifiers == []

    existing_posts = (
        (await db.execute(select(ContentPost.id).where(ContentPost.tenant_id == tenant.id)))
        .scalars()
        .all()
    )
    assert existing_posts == []
