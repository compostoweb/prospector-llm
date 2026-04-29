from __future__ import annotations

from types import SimpleNamespace

import pytest

from integrations.email_finders.prospeo import ProspeoClient


@pytest.mark.asyncio
async def test_enrich_person_extracts_email_and_mobile(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ProspeoClient()

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "person": {
                    "email": {
                        "email": "jane@acme.com",
                        "status": "VERIFIED",
                        "revealed": True,
                    },
                    "mobile": {
                        "number": "+55 11 99999-1111",
                        "status": "VERIFIED",
                    },
                }
            }

    async def _fake_post(*args: object, **kwargs: object) -> _Response:
        return _Response()

    monkeypatch.setattr(client, "_client", SimpleNamespace(post=_fake_post))

    result = await client.enrich_person("Jane", "Doe", "acme.com", include_mobile=True)

    assert result is not None
    assert result.email == "jane@acme.com"
    assert result.email_status == "VERIFIED"
    assert result.mobile == "+55 11 99999-1111"
    assert result.mobile_status == "VERIFIED"
    assert result.email_confidence == 1.0
