"""
workers/email_inbox_poll.py

Task Celery para polling de inbox de e-mail — detecta replies de leads.

Contas suportadas:
  - google_oauth:  Gmail History API (incremental, baseado em historyId)
  - smtp:          IMAP polling com imaplib (requer imap_host configurado)
  - unipile_gmail: Tratado pelo webhook Unipile — não precisa polling

Frequência: a cada 5 minutos (Beat schedule "email-inbox-poll")

Fluxo por reply detectado:
  1. Identifica lead pelo remetente (email_corporate ou email_personal)
  2. Verifica se há step EMAIL com status SENT para esse lead
  3. Roda ReplyParser para classificar intent
  4. Salva Interaction INBOUND
  5. Atualiza CadenceStep → REPLIED
  6. Ações por intent: INTEREST → CONVERTED, NOT_INTERESTED → ARCHIVED
"""

from __future__ import annotations

import asyncio
import email as email_lib
import imaplib
import re
import uuid as uuid_mod
from typing import Any

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="workers.email_inbox_poll.email_inbox_poll_tick",
    max_retries=1,
    queue="cadence",
)
def email_inbox_poll_tick(self) -> dict:
    """Polling de inbox de e-mail para contas google_oauth e smtp."""
    return asyncio.run(_poll_all())


async def _poll_all() -> dict:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from core.config import settings
    from models.email_account import EmailAccount

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    processed = 0
    errors = 0

    async with session_factory() as db:
        result = await db.execute(
            select(EmailAccount).where(
                EmailAccount.is_active == True,  # noqa: E712
                EmailAccount.provider_type.in_(["google_oauth", "smtp"]),
            )
        )
        accounts = list(result.scalars().all())

    for account in accounts:
        try:
            if account.provider_type == "google_oauth":
                count = await _poll_gmail_oauth(account, session_factory)
            else:  # smtp com IMAP configurado
                if not account.imap_host:
                    continue
                count = await _poll_smtp_imap(account, session_factory)
            processed += count
        except Exception as exc:
            errors += 1
            logger.error(
                "email_inbox_poll.account_error",
                account_id=str(account.id),
                provider=account.provider_type,
                error=str(exc),
            )

    await engine.dispose()
    return {"processed": processed, "errors": errors}


# ── Gmail OAuth — Gmail History API ──────────────────────────────────


async def _poll_gmail_oauth(
    account: Any,
    session_factory: Any,
) -> int:
    """
    Polls Gmail API for new messages since the last historyId.
    On first run: fetches the current historyId and stores it (no messages processed).
    """
    import httpx  # noqa: PLC0415

    from core.config import settings  # noqa: PLC0415
    from services.email_account_service import decrypt_credential  # noqa: PLC0415

    if not account.google_refresh_token:
        return 0

    refresh_token = decrypt_credential(account.google_refresh_token)

    # Troca refresh_token por access_token
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID_EMAIL,
                "client_secret": settings.GOOGLE_CLIENT_SECRET_EMAIL,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if token_resp.status_code != 200:
            logger.warning(
                "email_inbox_poll.gmail.token_error",
                account_id=str(account.id),
                status=token_resp.status_code,
            )
            return 0
        access_token: str = token_resp.json()["access_token"]

    if not account.gmail_history_id:
        # Primeira execução — apenas salva o historyId atual como âncora
        return await _gmail_bootstrap_history_id(account, access_token, session_factory)

    # Busca histórico desde o último checkpoint
    messages = await _gmail_fetch_since_history(
        access_token=access_token,
        history_id=account.gmail_history_id,
        account_email=account.email_address,
    )

    if not messages:
        return 0

    processed = 0
    new_history_id = account.gmail_history_id

    for msg_meta in messages:
        msg_id = msg_meta.get("id")
        if not msg_id:
            continue
        new_history_id = msg_meta.get("historyId", new_history_id)

        # Busca detalhes da mensagem
        msg_data = await _gmail_get_message(access_token, msg_id)
        if not msg_data:
            continue

        sender_email = _extract_gmail_sender(msg_data)
        body = _extract_gmail_body(msg_data)
        subject = _extract_gmail_subject(msg_data)

        if not sender_email or sender_email.lower() == account.email_address.lower():
            continue  # ignora mensagens próprias

        await _process_email_reply(
            tenant_id=account.tenant_id,
            from_email=sender_email,
            body=body,
            message_id=msg_id,
            subject=subject,
            session_factory=session_factory,
        )
        processed += 1

    # Atualiza historyId
    if new_history_id != account.gmail_history_id:
        async with session_factory() as db:
            from sqlalchemy import select  # noqa: PLC0415

            from models.email_account import EmailAccount  # noqa: PLC0415

            result = await db.execute(select(EmailAccount).where(EmailAccount.id == account.id))
            acc = result.scalar_one_or_none()
            if acc:
                acc.gmail_history_id = str(new_history_id)
                await db.commit()

    logger.info(
        "email_inbox_poll.gmail.done",
        account_id=str(account.id),
        messages_processed=processed,
    )
    return processed


async def _gmail_bootstrap_history_id(
    account: Any,
    access_token: str,
    session_factory: Any,
) -> int:
    """
    Salva o historyId atual como ponto de partida.
    Chamado na primeira execução — zerado quando gmail_history_id é NULL.
    """
    import httpx  # noqa: PLC0415

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            return 0
        history_id = str(resp.json().get("historyId", ""))

    if history_id:
        async with session_factory() as db:
            from sqlalchemy import select  # noqa: PLC0415

            from models.email_account import EmailAccount  # noqa: PLC0415

            result = await db.execute(select(EmailAccount).where(EmailAccount.id == account.id))
            acc = result.scalar_one_or_none()
            if acc:
                acc.gmail_history_id = history_id
                await db.commit()

        logger.info(
            "email_inbox_poll.gmail.bootstrapped",
            account_id=str(account.id),
            history_id=history_id,
        )

    return 0  # Primeira execução não processa mensagens


async def _gmail_fetch_since_history(
    access_token: str,
    history_id: str,
    account_email: str,
) -> list[dict]:
    """
    Retorna mensagens adicionadas à INBOX desde o historyId informado.
    Exclui mensagens enviadas pela própria conta.
    """
    import httpx  # noqa: PLC0415

    messages = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/history",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "startHistoryId": history_id,
                "labelId": "INBOX",
                "historyTypes": "messageAdded",
                "maxResults": "100",
            },
        )

        if resp.status_code == 404:
            # historyId expirado — reseta
            logger.warning(
                "email_inbox_poll.gmail.history_expired",
                history_id=history_id,
            )
            return []

        if resp.status_code != 200:
            logger.warning(
                "email_inbox_poll.gmail.history_error",
                status=resp.status_code,
                body=resp.text[:200],
            )
            return []

        data = resp.json()
        for record in data.get("history", []):
            for added in record.get("messagesAdded", []):
                msg = added.get("message", {})
                label_ids = msg.get("labelIds", [])
                # Só mensagens na INBOX que não são do remetente
                if "INBOX" in label_ids and "SENT" not in label_ids:
                    messages.append(
                        {
                            "id": msg.get("id"),
                            "historyId": data.get("historyId", history_id),
                        }
                    )

    return messages


async def _gmail_get_message(access_token: str, message_id: str) -> dict | None:
    import httpx  # noqa: PLC0415

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"},
        )
        if resp.status_code != 200:
            return None
        return resp.json()


def _extract_gmail_sender(msg_data: dict) -> str:
    """Extrai endereço de e-mail do remetente dos headers da mensagem Gmail."""
    headers = msg_data.get("payload", {}).get("headers", [])
    from_header = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
    # From pode ser "Nome <email>" ou apenas "email"
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1).strip().lower()
    return from_header.strip().lower()


def _extract_gmail_subject(msg_data: dict) -> str:
    """Extrai assunto da mensagem Gmail."""
    headers = msg_data.get("payload", {}).get("headers", [])
    return next((h["value"] for h in headers if h["name"].lower() == "subject"), "")


def _extract_gmail_body(msg_data: dict) -> str:
    """Extrai corpo de texto da mensagem Gmail (text/plain prioritário)."""
    import base64  # noqa: PLC0415

    payload = msg_data.get("payload", {})
    parts = payload.get("parts", [])

    def _decode_part(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        except Exception:
            return ""

    # Mensagem sem parts (body direto)
    if not parts and payload.get("body", {}).get("data"):
        return _decode_part(payload["body"]["data"])

    # Procura text/plain primeiro
    for part in parts:
        if part.get("mimeType") == "text/plain":
            return _decode_part(part.get("body", {}).get("data", ""))

    # Fallback: primeiro part com data
    for part in parts:
        if part.get("body", {}).get("data"):
            return _decode_part(part["body"]["data"])

    return ""


# ── SMTP — IMAP polling ───────────────────────────────────────────────


async def _poll_smtp_imap(
    account: Any,
    session_factory: Any,
) -> int:
    """
    Conecta ao servidor IMAP da conta SMTP e busca e-mails não lidos.
    Usa asyncio.to_thread pois imaplib é síncrono.
    """
    from services.email_account_service import decrypt_credential  # noqa: PLC0415

    if not account.imap_host or not account.smtp_username:
        return 0

    imap_password = decrypt_credential(account.imap_password) if account.imap_password else ""
    if not imap_password:
        # Tenta usar mesma senha do SMTP
        if account.smtp_password:
            imap_password = decrypt_credential(account.smtp_password)
        else:
            return 0

    imap_host = account.imap_host
    imap_port = account.imap_port or (993 if account.imap_use_ssl else 143)
    username = account.smtp_username
    last_uid = account.imap_last_uid

    try:
        messages = await asyncio.to_thread(
            _imap_fetch_messages,
            imap_host=imap_host,
            imap_port=imap_port,
            use_ssl=account.imap_use_ssl,
            username=username,
            password=imap_password,
            last_uid=last_uid,
        )
    except Exception as exc:
        logger.error(
            "email_inbox_poll.imap.connect_error",
            account_id=str(account.id),
            host=imap_host,
            error=str(exc),
        )
        return 0

    if not messages:
        return 0

    processed = 0
    new_last_uid = last_uid

    for msg_data in messages:
        sender_email = msg_data.get("from", "").lower()
        body = msg_data.get("body", "")
        uid = msg_data.get("uid", "")
        subject = msg_data.get("subject", "")

        if not sender_email or sender_email == account.email_address.lower():
            continue

        await _process_email_reply(
            tenant_id=account.tenant_id,
            from_email=sender_email,
            body=body,
            message_id=f"imap:{account.id}:{uid}",
            subject=subject,
            session_factory=session_factory,
        )
        new_last_uid = uid
        processed += 1

    # Salva novo cursor
    if new_last_uid != last_uid:
        async with session_factory() as db:
            from sqlalchemy import select  # noqa: PLC0415

            from models.email_account import EmailAccount  # noqa: PLC0415

            result = await db.execute(select(EmailAccount).where(EmailAccount.id == account.id))
            acc = result.scalar_one_or_none()
            if acc:
                acc.imap_last_uid = str(new_last_uid)
                await db.commit()

    logger.info(
        "email_inbox_poll.imap.done",
        account_id=str(account.id),
        messages_processed=processed,
    )
    return processed


def _imap_fetch_messages(
    imap_host: str,
    imap_port: int,
    use_ssl: bool,
    username: str,
    password: str,
    last_uid: str | None,
) -> list[dict]:
    """
    Função síncrona — executada via asyncio.to_thread.
    Conecta ao IMAP, busca mensagens não processadas e retorna lista de dicts.
    """
    conn: imaplib.IMAP4
    if use_ssl:
        conn = imaplib.IMAP4_SSL(imap_host, imap_port)
    else:
        conn = imaplib.IMAP4(imap_host, imap_port)

    try:
        conn.login(username, password)
        conn.select("INBOX", readonly=True)

        # Busca mensagens mais recentes que o último UID processado
        if last_uid:
            status, data = conn.uid("SEARCH", "", f"UID {int(last_uid) + 1}:*")
        else:
            # Primeira execução: processa os últimos 50 e-mails não lidos
            status, data = conn.uid("SEARCH", "", "UNSEEN")

        if status != "OK" or not data[0]:
            return []

        uids = data[0].split()[-50:]  # Limita a 50 mais recentes
        messages = []

        for uid_bytes in uids:
            uid = uid_bytes.decode()
            status, msg_data = conn.uid("FETCH", uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw = msg_data[0][1]
            if not isinstance(raw, bytes):
                continue

            msg = email_lib.message_from_bytes(raw)

            # Extrai remetente
            from_header = msg.get("From", "")
            match = re.search(r"<([^>]+)>", from_header)
            from_email = match.group(1).strip().lower() if match else from_header.strip().lower()

            # Extrai assunto
            subject = msg.get("Subject", "")

            # Extrai corpo texto
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            if isinstance(payload, (bytes, bytearray)):
                                body = payload.decode("utf-8", errors="replace")
                                break
                        except Exception:
                            pass
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if isinstance(payload, (bytes, bytearray)):
                        body = payload.decode("utf-8", errors="replace")
                except Exception:
                    pass

            messages.append({"uid": uid, "from": from_email, "body": body, "subject": subject})

        return messages
    finally:
        try:
            conn.logout()
        except Exception:
            pass


# ── Processamento comum — inbound reply ──────────────────────────────


async def _process_email_reply(
    tenant_id: uuid_mod.UUID,
    from_email: str,
    body: str,
    message_id: str,
    session_factory: Any,
    subject: str = "",
) -> None:
    """
    Processa uma resposta de e-mail recebida:
      1. Detecta NDR/bounce por remetente e subject
      2. Encontra o lead pelo remetente
      3. Verifica se há step EMAIL enviado para esse lead
      4. Roda ReplyParser
      5. Salva Interaction INBOUND
      6. Atualiza step + lead
    """
    from sqlalchemy import select  # noqa: PLC0415

    from core.config import settings  # noqa: PLC0415
    from core.redis_client import redis_client  # noqa: PLC0415
    from integrations.llm import LLMRegistry  # noqa: PLC0415
    from models.cadence_step import CadenceStep  # noqa: PLC0415
    from models.enums import Channel, StepStatus  # noqa: PLC0415
    from models.interaction import Interaction  # noqa: PLC0415
    from services.email_event_service import (  # noqa: PLC0415
        classify_inbound_email_event,
        record_email_bounce,
    )
    from services.inbound_message_service import (  # noqa: PLC0415
        find_lead_by_email,
        process_inbound_reply,
    )

    if not body.strip():
        return

    async with session_factory() as db:
        # Idempotência: verifica se message_id já foi processado
        existing = await db.execute(
            select(Interaction.id).where(Interaction.unipile_message_id == message_id).limit(1)
        )
        if existing.scalar_one_or_none():
            return

        inbound_event = classify_inbound_email_event(
            from_email=from_email,
            subject=subject,
            body=body,
        )
        if inbound_event.kind == "ignored":
            return
        if inbound_event.kind == "bounce":
            if inbound_event.matched_email:
                await record_email_bounce(
                    db,
                    tenant_id,
                    inbound_event.matched_email,
                    source="email_inbox_poll",
                    bounce_type=inbound_event.bounce_type or "hard",
                )
            else:
                logger.info(
                    "email_inbox_poll.bounce_unmatched",
                    tenant_id=str(tenant_id),
                    from_email=from_email,
                    subject=subject,
                )
            return

        # Busca lead pelo e-mail do remetente
        lead = await find_lead_by_email(from_email, tenant_id, db)
        if not lead:
            logger.debug(
                "email_inbox_poll.lead_not_found",
                from_email=from_email,
                tenant_id=str(tenant_id),
            )
            return

        # Verifica se há step EMAIL enviado para este lead (confirmação que enviamos)
        step_result = await db.execute(
            select(CadenceStep)
            .where(
                CadenceStep.lead_id == lead.id,
                CadenceStep.tenant_id == tenant_id,
                CadenceStep.channel == Channel.EMAIL,
                CadenceStep.status == StepStatus.SENT,
            )
            .order_by(CadenceStep.sent_at.desc())
            .limit(1)
        )
        latest_step = step_result.scalar_one_or_none()
        if not latest_step:
            # Não enviamos e-mail para este lead — ignorar
            return

        registry = LLMRegistry(settings=settings, redis=redis_client)
        try:
            result = await process_inbound_reply(
                db=db,
                registry=registry,
                tenant_id=tenant_id,
                lead=lead,
                channel=Channel.EMAIL,
                reply_text=body,
                external_message_id=message_id,
            )
        finally:
            from integrations.llm.base import close_async_resource

            await close_async_resource(registry)

        logger.info(
            "email_inbox_poll.reply_processed",
            lead_id=str(lead.id),
            from_email=from_email,
            intent=result.intent.value,
            confidence=result.classification.get("confidence"),
        )
