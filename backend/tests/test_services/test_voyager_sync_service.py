from __future__ import annotations

from datetime import datetime

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
        own_profile_errors: list[Exception] | None = None,
        posts_by_identifier: dict[str, list[dict]] | None = None,
    ) -> None:
        self._own_profile = own_profile or None
        self._own_profile_error = own_profile_error
        self._own_profile_errors = own_profile_errors or []
        self._posts_by_identifier = posts_by_identifier or {}
        self.requested_identifiers: list[str] = []

    async def __aenter__(self) -> _FakeUnipileClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get_own_profile(self, account_id: str) -> dict:
        if self._own_profile_errors:
            raise self._own_profile_errors.pop(0)
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

    async def _fake_cached_identifiers(account_id: str) -> dict[str, str]:
        assert account_id == "acc-123"
        return {}

    monkeypatch.setattr(
        voyager_sync_service,
        "_get_cached_own_profile_identifiers",
        _fake_cached_identifiers,
    )

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


async def test_sync_voyager_prefers_profile_identifiers_before_saved_username(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-789",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile={
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
            "first_name": "Adriano",
        },
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-2",
                    "social_id": "urn:li:ugcPost:456",
                    "text": "Post importado usando provider id",
                    "impressions_counter": 200,
                    "reaction_counter": 25,
                    "comment_counter": 8,
                    "repost_counter": 3,
                    "save_counter": 2,
                    "parsed_datetime": "2026-04-11T15:00:00Z",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)
    cached_profiles: list[tuple[str, dict]] = []

    async def _fake_cache(account_id: str, profile: dict) -> None:
        cached_profiles.append((account_id, profile))

    monkeypatch.setattr(voyager_sync_service, "_cache_own_profile_identifiers", _fake_cache)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 1
    assert fake_client.requested_identifiers == ["ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ"]
    assert cached_profiles == [
        (
            "acc-789",
            {
                "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
                "public_identifier": "adrianovaladao",
                "first_name": "Adriano",
            },
        )
    ]


async def test_sync_voyager_uses_cached_provider_id_before_querying_own_profile(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-cache-first",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile_error=AssertionError("nao deveria consultar /users/me quando o cache resolve"),
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-cache-first",
                    "social_id": "urn:li:ugcPost:cache-first",
                    "text": "Post importado direto do provider id cacheado",
                    "impressions_counter": 210,
                    "reaction_counter": 18,
                    "comment_counter": 6,
                    "repost_counter": 2,
                    "save_counter": 1,
                    "parsed_datetime": "2026-04-14T10:00:00Z",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    async def _fake_cached_identifiers(account_id: str) -> dict[str, str]:
        assert account_id == "acc-cache-first"
        return {
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        }

    monkeypatch.setattr(
        voyager_sync_service,
        "_get_cached_own_profile_identifiers",
        _fake_cached_identifiers,
    )

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 1
    assert fake_client.requested_identifiers == ["ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ"]


async def test_sync_voyager_uses_cached_profile_identifiers_when_profile_lookup_times_out(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-999",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile_error=RuntimeError("Falha de conexao com Unipile: ReadTimeout"),
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-3",
                    "social_id": "urn:li:ugcPost:789",
                    "text": "Post importado usando cache do provider id",
                    "impressions_counter": 350,
                    "reaction_counter": 30,
                    "comment_counter": 9,
                    "repost_counter": 4,
                    "save_counter": 5,
                    "parsed_datetime": "2026-04-12T10:30:00Z",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    async def _fake_cached_identifiers(account_id: str) -> dict[str, str]:
        assert account_id == "acc-999"
        return {
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        }

    monkeypatch.setattr(
        voyager_sync_service,
        "_get_cached_own_profile_identifiers",
        _fake_cached_identifiers,
    )

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 1
    assert fake_client.requested_identifiers == ["ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ"]


async def test_sync_voyager_retries_profile_lookup_before_fallback(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-321",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile_errors=[RuntimeError("Falha de conexao com Unipile: ReadTimeout")],
        own_profile={
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        },
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-4",
                    "social_id": "urn:li:ugcPost:999",
                    "text": "Post importado apos retry do profile",
                    "impressions_counter": 180,
                    "reaction_counter": 14,
                    "comment_counter": 5,
                    "repost_counter": 1,
                    "save_counter": 1,
                    "parsed_datetime": "2026-04-13T09:15:00Z",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    async def _fake_cache(account_id: str, profile: dict) -> None:
        return None

    monkeypatch.setattr(voyager_sync_service, "_cache_own_profile_identifiers", _fake_cache)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert fake_client.requested_identifiers == ["ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ"]


async def test_sync_voyager_updates_existing_post_metrics(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-update",
        is_active=True,
    )
    db.add(account)

    existing_post = ContentPost(
        tenant_id=tenant.id,
        title="Post existente",
        body="Texto existente",
        pillar="authority",
        status="published",
        linkedin_post_urn="urn:li:ugcPost:existing",
        impressions=10,
        likes=1,
        comments=0,
        shares=0,
        saves=0,
    )
    db.add(existing_post)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile={
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        },
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-existing",
                    "social_id": "urn:li:ugcPost:existing",
                    "text": "Texto atualizado da metrica",
                    "impressions_counter": 999,
                    "reaction_counter": 42,
                    "comment_counter": 12,
                    "repost_counter": 5,
                    "save_counter": 3,
                    "parsed_datetime": "2026-04-13T10:00:00Z",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 0
    assert result.posts_updated == 1

    refreshed_post = (
        await db.execute(
            select(ContentPost).where(
                ContentPost.tenant_id == tenant.id,
                ContentPost.linkedin_post_urn == "urn:li:ugcPost:existing",
            )
        )
    ).scalar_one()
    assert refreshed_post.impressions == 999
    assert refreshed_post.likes == 42
    assert refreshed_post.comments == 12
    assert refreshed_post.shares == 5
    assert refreshed_post.saves == 3


async def test_sync_voyager_reconciles_content_hub_post_when_unipile_returns_activity_urn(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-reconcile-activity",
        is_active=True,
    )
    db.add(account)

    existing_post = ContentPost(
        tenant_id=tenant.id,
        title="A clínica que queria chatbot",
        body="Uma clínica me chamou porque queria um chatbot no WhatsApp.\n\nQuando entrei nos processos, vi que o gargalo era outro.",
        pillar="case",
        status="published",
        linkedin_post_urn="urn:li:share:7450905912996786177",
        published_at=datetime.fromisoformat("2026-04-17T14:00:01+00:00"),
        impressions=0,
        likes=0,
        comments=0,
        shares=0,
        saves=0,
    )
    db.add(existing_post)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile={
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        },
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-activity",
                    "social_id": "urn:li:activity:7450905913617522688",
                    "text": "Uma clínica me chamou porque queria um chatbot no WhatsApp.\n\nQuando entrei nos processos, vi que o gargalo era outro.",
                    "impressions_counter": 20,
                    "reaction_counter": 3,
                    "comment_counter": 1,
                    "repost_counter": 0,
                    "save_counter": 0,
                    "parsed_datetime": "2026-04-17T14:00:00.944000+00:00",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 0
    assert result.posts_updated == 1

    posts = (
        (await db.execute(select(ContentPost).where(ContentPost.tenant_id == tenant.id)))
        .scalars()
        .all()
    )
    assert len(posts) == 1
    assert posts[0].id == existing_post.id
    assert posts[0].linkedin_post_urn == "urn:li:share:7450905912996786177"
    assert posts[0].impressions == 20
    assert posts[0].likes == 3
    assert posts[0].comments == 1


async def test_sync_voyager_reconciles_content_hub_post_when_unipile_text_includes_hashtags(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-reconcile-hashtags",
        is_active=True,
    )
    db.add(account)

    existing_post = ContentPost(
        tenant_id=tenant.id,
        title="Tecnologia não é o fim. É o meio.",
        body=(
            "Quando essa resposta fica clara, a tecnologia deixa de ser aposta e vira alavanca.\n\n"
            "É aí que o negócio ganha velocidade de verdade.\n\n"
            "Na sua empresa, a discussão ainda começa pela ferramenta ou pelo processo?"
        ),
        pillar="authority",
        status="published",
        linkedin_post_urn="urn:li:share:7450905912996786177",
        published_at=datetime.fromisoformat("2026-04-26T14:00:01+00:00"),
        hashtags="#gestao #processos #tecnologia #negocios #lideranca",
        impressions=0,
        likes=0,
        comments=0,
        shares=0,
        saves=0,
    )
    db.add(existing_post)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile={
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        },
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-activity-hashtag",
                    "social_id": "urn:li:activity:7450905913617522688",
                    "text": (
                        "Quando essa resposta fica clara, a tecnologia deixa de ser aposta e vira alavanca.\n\n"
                        "É aí que o negócio ganha velocidade de verdade.\n\n"
                        "Na sua empresa, a discussão ainda começa pela ferramenta ou pelo processo?\n\n"
                        "#gestao #processos #tecnologia #negocios #lideranca"
                    ),
                    "impressions_counter": 11,
                    "reaction_counter": 2,
                    "comment_counter": 1,
                    "repost_counter": 0,
                    "save_counter": 0,
                    "parsed_datetime": "2026-04-26T14:00:00.944000+00:00",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 0
    assert result.posts_updated == 1

    posts = (
        (await db.execute(select(ContentPost).where(ContentPost.tenant_id == tenant.id)))
        .scalars()
        .all()
    )
    assert len(posts) == 1
    assert posts[0].id == existing_post.id
    assert posts[0].title == "Tecnologia não é o fim. É o meio."
    assert posts[0].impressions == 11
    assert posts[0].likes == 2
    assert posts[0].comments == 1


async def test_sync_voyager_preserves_content_hub_post_when_legacy_duplicate_already_exists(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-preserve-content-hub-post",
        is_active=True,
    )
    db.add(account)

    original_post = ContentPost(
        tenant_id=tenant.id,
        title="A clínica que queria chatbot",
        body="Uma clínica me chamou porque queria um chatbot no WhatsApp.\n\nQuando entrei nos processos, vi que o gargalo era outro.",
        pillar="case",
        status="published",
        publish_date=datetime.fromisoformat("2026-04-17T14:00:00+00:00"),
        linkedin_post_urn="urn:li:share:7450905912996786177",
        published_at=datetime.fromisoformat("2026-04-17T14:00:01+00:00"),
    )
    duplicate_imported_post = ContentPost(
        tenant_id=tenant.id,
        title="[LinkedIn] Uma clínica me chamou porque queria um chatbot no WhatsApp...",
        body="Uma clínica me chamou porque queria um chatbot no WhatsApp.\n\nQuando entrei nos processos, vi que o gargalo era outro.",
        pillar="authority",
        status="published",
        linkedin_post_urn="urn:li:activity:7450905913617522688",
        published_at=datetime.fromisoformat("2026-04-17T14:00:00.944000+00:00"),
        impressions=20,
    )
    db.add(original_post)
    db.add(duplicate_imported_post)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile={
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        },
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-activity-legacy-duplicate",
                    "social_id": "urn:li:activity:7450905913617522688",
                    "text": "Uma clínica me chamou porque queria um chatbot no WhatsApp.\n\nQuando entrei nos processos, vi que o gargalo era outro.",
                    "impressions_counter": 25,
                    "reaction_counter": 4,
                    "comment_counter": 2,
                    "repost_counter": 1,
                    "save_counter": 0,
                    "parsed_datetime": "2026-04-17T14:00:00.944000+00:00",
                }
            ]
        },
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert result.posts_created == 0
    assert result.posts_updated == 1

    posts = (
        (await db.execute(select(ContentPost).where(ContentPost.tenant_id == tenant.id)))
        .scalars()
        .all()
    )
    assert len(posts) == 1
    assert posts[0].id == original_post.id
    assert posts[0].title == "A clínica que queria chatbot"
    assert posts[0].linkedin_post_urn == "urn:li:share:7450905912996786177"
    assert posts[0].impressions == 25
    assert posts[0].likes == 4
    assert posts[0].comments == 2
    assert posts[0].shares == 1


async def test_sync_voyager_retries_provider_id_posts_without_falling_back_to_username(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-654",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile_error=RuntimeError("Falha de conexao com Unipile: ReadTimeout"),
        own_profile=None,
        posts_by_identifier={
            "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ": [
                {
                    "id": "unipile-post-5",
                    "social_id": "urn:li:ugcPost:321",
                    "text": "Post importado apos retry do provider id cacheado",
                    "impressions_counter": 500,
                    "reaction_counter": 41,
                    "comment_counter": 12,
                    "repost_counter": 6,
                    "save_counter": 7,
                    "parsed_datetime": "2026-04-13T12:45:00Z",
                }
            ]
        },
    )
    attempts = {"provider": 0}

    async def _fake_get_posts(account_id: str, identifier: str, limit: int = 50) -> list[dict]:
        fake_client.requested_identifiers.append(identifier)
        if identifier == "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ" and attempts["provider"] == 0:
            attempts["provider"] += 1
            raise RuntimeError("Falha de conexao com Unipile: ReadTimeout")
        if identifier not in fake_client._posts_by_identifier:
            raise RuntimeError(f"identifier {identifier} not found")
        return fake_client._posts_by_identifier[identifier][:limit]

    monkeypatch.setattr(fake_client, "get_own_posts_with_metrics", _fake_get_posts)
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    async def _fake_cached_identifiers(account_id: str) -> dict[str, str]:
        assert account_id == "acc-654"
        return {
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        }

    monkeypatch.setattr(
        voyager_sync_service,
        "_get_cached_own_profile_identifiers",
        _fake_cached_identifiers,
    )

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is True
    assert fake_client.requested_identifiers == [
        "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
        "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
    ]


async def test_sync_voyager_does_not_try_public_identifier_after_cached_provider_failure(
    db,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = LinkedInAccount(
        tenant_id=tenant.id,
        display_name="Conta principal",
        linkedin_username="adrianovaladao",
        provider_type="unipile",
        unipile_account_id="acc-777",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    fake_client = _FakeUnipileClient(
        own_profile_error=RuntimeError("Falha de conexao com Unipile: ReadTimeout"),
    )
    monkeypatch.setattr(voyager_sync_service, "UnipileClient", lambda: fake_client)

    async def _fake_cached_identifiers(account_id: str) -> dict[str, str]:
        assert account_id == "acc-777"
        return {
            "provider_id": "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
            "public_identifier": "adrianovaladao",
        }

    monkeypatch.setattr(
        voyager_sync_service,
        "_get_cached_own_profile_identifiers",
        _fake_cached_identifiers,
    )

    result = await voyager_sync_service.sync_voyager_for_tenant(str(tenant.id), db)

    assert result.success is False
    assert fake_client.requested_identifiers == [
        "ACoAAA67iMoBbojHonHEtRD-byA0CEuERMcFRCQ",
    ]
    assert "cached_public_identifier" not in (result.error or "")
    assert "linkedin_username" not in (result.error or "")
