"""
services/email_footer.py

Serviço de rodapé de e-mail para cold email.

Responsabilidades:
    1. Gerar link de unsubscribe seguro (HMAC-SHA256)
    2. Gerar URL de tracking pixel (abertura)
    3. Anexar assinatura HTML da conta ao corpo do e-mail
    4. Injetar pixel de rastreamento de abertura no HTML
"""

from __future__ import annotations

import hashlib
import hmac
import uuid

import structlog

from core.config import settings

logger = structlog.get_logger()

# ── Pixel GIF 1×1 transparente (43 bytes — GIF87a) ───────────────────
_TRANSPARENT_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)

TRANSPARENT_GIF_BYTES: bytes = _TRANSPARENT_GIF


# ── Unsubscribe token ─────────────────────────────────────────────────


def build_unsubscribe_token(tenant_id: uuid.UUID, email: str) -> str:
    """
    Gera um token HMAC-SHA256 para o link de descadastro.
    Formato: {email}:{tenant_id} assinado com settings.SECRET_KEY.
    Retorna hex digest de 64 chars.
    """
    message = f"{email.lower()}:{tenant_id}".encode()
    return hmac.new(
        settings.SECRET_KEY.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_unsubscribe_token(token: str, tenant_id: uuid.UUID, email: str) -> bool:
    """Verifica se o token é válido para o par email+tenant."""
    expected = build_unsubscribe_token(tenant_id, email)
    return hmac.compare_digest(expected, token)


def build_unsubscribe_url(tenant_id: uuid.UUID, email: str) -> str:
    """Retorna URL pública de descadastro com token embutido."""
    token = build_unsubscribe_token(tenant_id, email)
    import urllib.parse

    encoded_email = urllib.parse.quote(email.lower())
    return f"{settings.TRACKING_BASE_URL}/track/unsubscribe/{token}?e={encoded_email}&t={tenant_id}"


def build_open_pixel_url(interaction_id: uuid.UUID) -> str:
    """Retorna URL pública do pixel de rastreamento de abertura."""
    return f"{settings.TRACKING_BASE_URL}/track/open/{interaction_id}"


# ── Injeção no HTML ───────────────────────────────────────────────────


def inject_tracking(
    body_html: str,
    interaction_id: uuid.UUID,
    tenant_id: uuid.UUID,
    email: str,
    signature_html: str | None = None,
) -> str:
    """
    Injeta no corpo HTML:
      1. Assinatura HTML da conta, se existir
      2. Pixel de rastreamento de abertura (1×1 GIF invisível)

    Retorna o HTML modificado.
    """
    _ = (tenant_id, email)

    pixel_url = build_open_pixel_url(interaction_id)

    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" '
        f'alt="" style="display:none;width:1px;height:1px;" />'
    )

    signature_block = ""
    if signature_html and signature_html.strip():
        signature_block = f"""
<div style="margin-top:24px;">
  {signature_html}
</div>
"""

    footer_html = f"{signature_block}\n{pixel_tag}"

    # Inserir antes de </body> se existir, senão apenda no final
    if "</body>" in body_html.lower():
        idx = body_html.lower().rfind("</body>")
        return body_html[:idx] + footer_html + body_html[idx:]

    return body_html + footer_html
