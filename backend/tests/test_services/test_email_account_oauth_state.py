from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

from core.config import settings
from services.email_account_service import (
    build_google_auth_url,
    get_tenant_id_from_oauth_state,
    get_user_id_from_oauth_state,
)


def test_google_auth_url_state_carries_tenant_and_user(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID_EMAIL", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI_EMAIL", "https://api.test/google/callback")

    auth_url = build_google_auth_url(tenant_id, user_id=user_id)
    query = parse_qs(urlparse(auth_url).query)
    state = query["state"][0]

    assert get_tenant_id_from_oauth_state(state) == tenant_id
    assert get_user_id_from_oauth_state(state) == user_id
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
