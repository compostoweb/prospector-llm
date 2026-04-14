"""
api/routes/email_accounts.py

Endpoints para gerenciamento de contas de e-mail do tenant.

Rotas:
  GET    /email-accounts               — lista contas do tenant
  POST   /email-accounts/unipile       — conecta conta Unipile Gmail
  POST   /email-accounts/smtp          — conecta conta SMTP
  POST   /email-accounts/smtp/test     — testa conexão SMTP sem salvar
  GET    /email-accounts/google/authorize — inicia OAuth Google
  GET    /email-accounts/google/callback  — callback OAuth Google
  GET    /email-accounts/{id}          — detalhe de uma conta
  PATCH  /email-accounts/{id}          — edita campos não-sensíveis
  DELETE /email-accounts/{id}          — remove conta
  GET    /email-accounts/{id}/status   — ping ao provider

Autenticação: user token ou tenant token (get_session_flexible).
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_effective_tenant_id, get_session_flexible, get_session_no_auth
from models.email_account import EmailAccount
from models.enums import EmailProviderType
from schemas.email_account import (
    EmailAccountListResponse,
    EmailAccountResponse,
    EmailAccountSMTPCreateRequest,
    EmailAccountStatusResponse,
    EmailAccountUnipileCreateRequest,
    EmailAccountUpdateRequest,
    GmailSignatureResponse,
    GoogleOAuthUrlResponse,
    SMTPTestRequest,
    SMTPTestResponse,
)
from services.email_account_service import (
    build_email_account_response,
    build_google_auth_url,
    encrypt_credential,
    exchange_google_code,
    fetch_gmail_signature_details,
    get_tenant_id_from_oauth_state,
    test_smtp_connection,
)

router = APIRouter(prefix="/email-accounts", tags=["Email Accounts"])
logger = structlog.get_logger()


# ── Listagem ──────────────────────────────────────────────────────────


@router.get("", response_model=EmailAccountListResponse)
async def list_email_accounts(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailAccountListResponse:
    """Lista todas as contas de e-mail do tenant."""
    result = await db.execute(
        select(EmailAccount)
        .where(EmailAccount.tenant_id == tenant_id)
        .order_by(EmailAccount.created_at)
    )
    accounts = result.scalars().all()
    response_accounts = [await build_email_account_response(db, account) for account in accounts]
    return EmailAccountListResponse(
        accounts=response_accounts,
        total=len(accounts),
    )


# ── Conectar via Unipile ──────────────────────────────────────────────


@router.post(
    "/unipile",
    response_model=EmailAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unipile_account(
    body: EmailAccountUnipileCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailAccountResponse:
    """Conecta uma conta Gmail via Unipile (account_id já existe no Unipile)."""
    account = EmailAccount(
        tenant_id=tenant_id,
        display_name=body.display_name,
        email_address=str(body.email_address),
        from_name=body.from_name,
        provider_type=EmailProviderType.UNIPILE_GMAIL,
        unipile_account_id=body.unipile_account_id,
        daily_send_limit=body.daily_send_limit,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    logger.info(
        "email_account.created",
        provider="unipile_gmail",
        account_id=str(account.id),
        tenant_id=str(tenant_id),
    )
    return await build_email_account_response(db, account)


# ── Teste de SMTP ─────────────────────────────────────────────────────


@router.post("/smtp/test", response_model=SMTPTestResponse)
async def test_smtp(
    body: SMTPTestRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> SMTPTestResponse:
    """Testa a conexão SMTP sem criar a conta."""
    ok, error = await test_smtp_connection(
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_username=body.smtp_username,
        smtp_password=body.smtp_password,
        smtp_use_tls=body.smtp_use_tls,
    )
    return SMTPTestResponse(ok=ok, error=error)


# ── Conectar via SMTP ─────────────────────────────────────────────────


@router.post(
    "/smtp",
    response_model=EmailAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_smtp_account(
    body: EmailAccountSMTPCreateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailAccountResponse:
    """Conecta uma conta SMTP. Testa a conexão antes de salvar."""
    ok, error = await test_smtp_connection(
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_username=body.smtp_username,
        smtp_password=body.smtp_password,
        smtp_use_tls=body.smtp_use_tls,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Falha na conexão SMTP: {error}",
        )

    encrypted_password = encrypt_credential(body.smtp_password)
    encrypted_imap_password: str | None = None
    if body.imap_password:
        encrypted_imap_password = encrypt_credential(body.imap_password)

    account = EmailAccount(
        tenant_id=tenant_id,
        display_name=body.display_name,
        email_address=str(body.email_address),
        from_name=body.from_name,
        provider_type=EmailProviderType.SMTP,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_username=body.smtp_username,
        smtp_password=encrypted_password,
        smtp_use_tls=body.smtp_use_tls,
        daily_send_limit=body.daily_send_limit,
        imap_host=body.imap_host,
        imap_port=body.imap_port,
        imap_use_ssl=body.imap_use_ssl,
        imap_password=encrypted_imap_password,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    logger.info(
        "email_account.created",
        provider="smtp",
        account_id=str(account.id),
        tenant_id=str(tenant_id),
    )
    return await build_email_account_response(db, account)


# ── OAuth Google — iniciar ────────────────────────────────────────────


@router.get("/google/authorize", response_model=GoogleOAuthUrlResponse)
async def google_authorize(
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
) -> GoogleOAuthUrlResponse:
    """
    Retorna a URL de autorização OAuth do Google.
    O frontend deve redirecionar o usuário para essa URL.
    """
    try:
        auth_url = build_google_auth_url(tenant_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return GoogleOAuthUrlResponse(auth_url=auth_url)


# ── OAuth Google — callback ───────────────────────────────────────────


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    display_name: str = "Gmail (OAuth)",
    from_name: str | None = None,
    daily_send_limit: int = 50,
    db: AsyncSession = Depends(get_session_no_auth),
):
    """
    Callback OAuth do Google. Troca o code por refresh_token e salva a conta.
    Redireciona para o frontend após salvar.

    Não exige JWT — autenticação é feita via HMAC no state parameter.
    """
    # Extrai tenant_id do state HMAC antes de qualquer operação
    try:
        tenant_id = get_tenant_id_from_oauth_state(state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        refresh_token, email_address = await exchange_google_code(code=code, state=state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("email_account.google_callback_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao trocar o código Google por token.",
        ) from exc

    encrypted_token = encrypt_credential(refresh_token)

    account = EmailAccount(
        tenant_id=tenant_id,
        display_name=display_name,
        email_address=email_address,
        from_name=from_name,
        provider_type=EmailProviderType.GOOGLE_OAUTH,
        google_refresh_token=encrypted_token,
        daily_send_limit=daily_send_limit,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)

    logger.info(
        "email_account.created",
        provider="google_oauth",
        account_id=str(account.id),
        email=email_address,
        tenant_id=str(tenant_id),
    )

    from core.config import settings as _settings  # noqa: PLC0415

    redirect_url = f"{_settings.FRONTEND_URL}/configuracoes/email-accounts?connected=1"
    return RedirectResponse(url=redirect_url)


# ── Detalhe ───────────────────────────────────────────────────────────


@router.get("/{account_id}", response_model=EmailAccountResponse)
async def get_email_account(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailAccountResponse:
    account = await _get_or_404(account_id, tenant_id, db)
    return await build_email_account_response(db, account)


# ── Editar ────────────────────────────────────────────────────────────


@router.patch("/{account_id}", response_model=EmailAccountResponse)
async def update_email_account(
    account_id: uuid.UUID,
    body: EmailAccountUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailAccountResponse:
    account = await _get_or_404(account_id, tenant_id, db)

    updates = body.model_dump(exclude_none=True)

    # imap_password precisa ser criptografada antes de persistir
    if "imap_password" in updates:
        updates["imap_password"] = encrypt_credential(updates["imap_password"])

    for field, value in updates.items():
        setattr(account, field, value)

    await db.flush()
    await db.refresh(account)
    return await build_email_account_response(db, account)


# ── Remover ───────────────────────────────────────────────────────────


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_email_account(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> None:
    account = await _get_or_404(account_id, tenant_id, db)
    await db.delete(account)
    logger.info(
        "email_account.deleted",
        account_id=str(account_id),
        tenant_id=str(tenant_id),
    )


# ── Status (ping) ─────────────────────────────────────────────────────


@router.get("/{account_id}/status", response_model=EmailAccountStatusResponse)
async def get_account_status(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> EmailAccountStatusResponse:
    """Faz um ping no provider para verificar se a conta está funcionando."""
    account = await _get_or_404(account_id, tenant_id, db)

    from core.config import settings as _settings  # noqa: PLC0415
    from integrations.email import EmailRegistry  # noqa: PLC0415

    registry = EmailRegistry(settings=_settings)
    try:
        is_reachable = await registry.ping(account)
        error = None
    except Exception as exc:
        is_reachable = False
        error = str(exc)

    return EmailAccountStatusResponse(
        account_id=account.id,
        email_address=account.email_address,
        provider_type=account.provider_type,
        is_reachable=is_reachable,
        error=error,
    )


# ── Assinatura Gmail ──────────────────────────────────────────────────


@router.get("/{account_id}/gmail-signature", response_model=GmailSignatureResponse)
async def get_gmail_signature(
    account_id: uuid.UUID,
    save: bool = False,
    tenant_id: uuid.UUID = Depends(get_effective_tenant_id),
    db: AsyncSession = Depends(get_session_flexible),
) -> GmailSignatureResponse:
    """
    Busca a assinatura padrão do Gmail via API.
    Disponível apenas para contas google_oauth.
    Se save=true, salva a assinatura na conta automaticamente.
    """
    account = await _get_or_404(account_id, tenant_id, db)

    if account.provider_type != "google_oauth":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sincronização de assinatura disponível apenas para contas Google OAuth.",
        )
    if not account.google_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conta sem refresh_token — reconecte via OAuth.",
        )

    try:
        signature, send_as_email, display_name = await fetch_gmail_signature_details(
            account.google_refresh_token
        )
    except PermissionError as exc:
        logger.warning(
            "email_account.gmail_signature_scope_error",
            account_id=str(account_id),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "email_account.gmail_signature_error",
            account_id=str(account_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao buscar assinatura do Gmail: {exc}",
        ) from exc

    if save and signature is not None:
        account.email_signature = signature
        if display_name:
            account.from_name = display_name
        await db.flush()

    return GmailSignatureResponse(
        signature=signature,
        send_as_email=send_as_email,
        display_name=display_name,
    )


# ── Helper ────────────────────────────────────────────────────────────


async def _get_or_404(
    account_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> EmailAccount:
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.tenant_id == tenant_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta de e-mail não encontrada.",
        )
    return account
