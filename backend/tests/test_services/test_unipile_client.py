from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import httpx
import pytest

from integrations.unipile_client import _OWN_PROFILE_TIMEOUT, UnipileClient


@pytest.mark.asyncio
async def test_send_email_uses_identifier_and_provider_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = UnipileClient()
    captured: dict[str, object] = {}

    class _Response:
        status_code = 201
        text = '{"object":"EmailSent","provider_id":"provider_123"}'

        def json(self) -> dict[str, str]:
            return {"object": "EmailSent", "provider_id": "provider_123"}

        def raise_for_status(self) -> None:
            return None

    async def _fake_post(path: str, json: dict) -> _Response:  # type: ignore[override]
        captured["path"] = path
        captured["json"] = json
        return _Response()

    monkeypatch.setattr(client, "_client", SimpleNamespace(post=_fake_post))

    result = await client.send_email(
        account_id="acc_123",
        to_email="adrianovaladao01@gmail.com",
        subject="Teste",
        body_html="<p>Teste</p>",
    )

    assert captured["path"] == "/emails"
    assert captured["json"] == {
        "account_id": "acc_123",
        "to": [{"identifier": "adrianovaladao01@gmail.com"}],
        "subject": "Teste",
        "body": "<p>Teste</p>",
    }
    assert result.success is True
    assert result.message_id == "provider_123"


@pytest.mark.asyncio
async def test_get_own_profile_uses_shorter_request_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = UnipileClient()
    captured: dict[str, object] = {}

    class _Response:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"provider_id": "provider_123", "public_identifier": "adriano"}

    async def _fake_get(path: str, **kwargs: object) -> _Response:  # type: ignore[override]
        captured["path"] = path
        captured["kwargs"] = kwargs
        return _Response()

    monkeypatch.setattr(client, "_client", SimpleNamespace(get=_fake_get))

    result = await client.get_own_profile("acc_123")

    assert result == {"provider_id": "provider_123", "public_identifier": "adriano"}
    assert captured["path"] == "/users/me"
    assert captured["kwargs"] == {
        "params": {"account_id": "acc_123"},
        "timeout": _OWN_PROFILE_TIMEOUT,
    }
    assert isinstance(cast(dict[str, object], captured["kwargs"])["timeout"], httpx.Timeout)


@pytest.mark.asyncio
async def test_resolve_attendee_prefers_large_profile_picture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = UnipileClient()

    class _RedisStub:
        async def get(self, key: str) -> None:
            return None

        async def set(self, key: str, value: str, ex: int | None = None) -> None:
            return None

    class _Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "first_name": "Davi",
                "last_name": "Bernardes",
                "public_identifier": "davi-bernardes",
                "profile_picture_url": "https://cdn.example.com/avatar-small.jpg",
                "profile_picture_url_large": "https://cdn.example.com/avatar-large.jpg",
            }

    async def _fake_get(path: str, **kwargs: object) -> _Response:  # type: ignore[override]
        return _Response()

    monkeypatch.setattr(client, "_client", SimpleNamespace(get=_fake_get))

    import core.redis_client as redis_module

    monkeypatch.setattr(redis_module, "redis_client", _RedisStub())

    attendee = await client._resolve_attendee("provider_123", "acc_123")

    assert attendee.name == "Davi Bernardes"
    assert attendee.profile_url == "https://www.linkedin.com/in/davi-bernardes"
    assert attendee.profile_picture_url == "https://cdn.example.com/avatar-large.jpg"
