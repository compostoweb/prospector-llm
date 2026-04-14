from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from integrations.email.unipile_provider import UnipileEmailProvider


@pytest.mark.asyncio
async def test_unipile_email_provider_forwards_from_name(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = UnipileEmailProvider(account_id="acc_123")
    send_mock = AsyncMock(
        return_value=type("Result", (), {"success": True, "message_id": "msg_1"})()
    )

    from integrations import unipile_client as unipile_module

    monkeypatch.setattr(unipile_module.unipile_client, "send_email", send_mock)

    result = await provider.send(
        to_email="adrianovaladao01@gmail.com",
        subject="Teste",
        body_html="<p>Teste</p>",
        from_name="Adriano Valadão",
    )

    assert result.success is True
    assert result.message_id == "msg_1"
    assert send_mock.await_count == 1
    assert send_mock.await_args_list[0].kwargs == {
        "account_id": "acc_123",
        "to_email": "adrianovaladao01@gmail.com",
        "subject": "Teste",
        "body_html": "<p>Teste</p>",
    }
