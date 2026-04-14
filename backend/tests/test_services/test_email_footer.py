from __future__ import annotations

import uuid

from services.email_footer import inject_tracking


def test_inject_tracking_keeps_pixel_and_signature_without_unsubscribe_footer() -> None:
    html = inject_tracking(
        body_html="<p>Ola</p>",
        interaction_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="lead@empresa.com",
        signature_html="<p><strong>Adriano Valadao</strong></p>",
    )

    assert "Adriano Valadao" in html
    assert "/track/open/" in html
    assert "lista de prospecção" not in html
    assert "Clique aqui para não receber mais e-mails" not in html
    assert "/track/unsubscribe/" not in html
