from __future__ import annotations

import hashlib
import hmac

from api.webhooks import sendpulse as sendpulse_webhook


def test_verify_signature_accepts_valid_hmac(
    monkeypatch,
) -> None:
    monkeypatch.setattr(sendpulse_webhook.settings, "SENDPULSE_WEBHOOK_SECRET", "secret-123")

    body = b'{"event":"open"}'
    digest = hmac.new(b"secret-123", body, hashlib.sha256).hexdigest()

    assert sendpulse_webhook._verify_signature(body, digest) is True


def test_verify_signature_rejects_when_secret_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(sendpulse_webhook.settings, "SENDPULSE_WEBHOOK_SECRET", "")
    monkeypatch.setattr(sendpulse_webhook.settings, "ENV", "dev")

    assert sendpulse_webhook._verify_signature(b"{}", "") is False
