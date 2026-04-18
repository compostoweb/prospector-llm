from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from integrations.linkedin.unipile_provider import UnipileLinkedInProvider


@pytest.mark.asyncio
async def test_send_inmail_maps_body_to_message_arg() -> None:
    client = AsyncMock()
    client.send_linkedin_inmail = AsyncMock(
        return_value=type("Result", (), {"success": True, "message_id": "inmail-1"})()
    )
    provider = UnipileLinkedInProvider(client=client, account_id="acc-1")

    result = await provider.send_inmail("profile-1", "Assunto", "Corpo")

    assert result.success is True
    client.send_linkedin_inmail.assert_awaited_once_with(
        account_id="acc-1",
        linkedin_profile_id="profile-1",
        subject="Assunto",
        message="Corpo",
    )


@pytest.mark.asyncio
async def test_comment_and_reaction_map_unipile_kwargs() -> None:
    client = AsyncMock()
    client.comment_on_latest_post = AsyncMock(return_value=True)
    client.react_to_latest_post = AsyncMock(return_value=True)
    provider = UnipileLinkedInProvider(client=client, account_id="acc-2")

    comment_result = await provider.comment_on_latest_post("profile-2", "Bom ponto")
    reaction_result = await provider.react_to_latest_post("profile-2", "PRAISE")

    assert comment_result.success is True
    assert reaction_result.success is True
    client.comment_on_latest_post.assert_awaited_once_with(
        account_id="acc-2",
        provider_id="profile-2",
        comment_text="Bom ponto",
    )
    client.react_to_latest_post.assert_awaited_once_with(
        account_id="acc-2",
        provider_id="profile-2",
        emoji="PRAISE",
    )
