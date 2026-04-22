from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import LeadStatus
from models.lead import Lead
from workers.email_inbox_poll import _process_email_reply

pytestmark = pytest.mark.asyncio


class _SessionFactory:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def __aenter__(self) -> AsyncSession:
        return self._db

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _session_factory(db: AsyncSession) -> _SessionFactory:
    return _SessionFactory(db)


async def test_process_email_reply_marks_bounce_for_gmail_friendly_ndr(
    db: AsyncSession,
    tenant,
) -> None:
    lead = Lead(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Lead Gmail Bounce",
        email_corporate="bounce-test@empresa-invalid.invalid",
        status=LeadStatus.IN_CADENCE,
        source="manual",
    )
    db.add(lead)
    await db.flush()

    with patch("services.inbound_message_service.process_inbound_reply", new=AsyncMock()) as mocked:
        await _process_email_reply(
            tenant_id=tenant.id,
            from_email="mailer-daemon@googlemail.com",
            subject="Delivery Status Notification (Failure)",
            body=(
                "Endereço não encontrado\n"
                "A mensagem não foi entregue para bounce-test@empresa-invalid.invalid "
                "porque o domínio empresa-invalid.invalid não foi encontrado.\n"
                "A resposta foi:\n"
                "DNS Error: DNS type 'mx' lookup of empresa-invalid.invalid responded with code "
                "NXDOMAIN Domain name not found."
            ),
            message_id="gmail-bounce-1",
            session_factory=lambda: _session_factory(db),
        )

    mocked.assert_not_awaited()
    await db.refresh(lead)
    assert lead.email_bounced_at is not None
    assert lead.email_bounce_type == "hard"