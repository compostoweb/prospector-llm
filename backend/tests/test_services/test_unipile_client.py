from __future__ import annotations

from types import SimpleNamespace

import pytest

from integrations.unipile_client import UnipileClient


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
