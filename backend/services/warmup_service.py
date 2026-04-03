"""
services/warmup_service.py

Serviço de warmup de e-mail.

Responsabilidades:
  - Calcular o volume diário de envio (curva de ramp-up linear)
  - Selecionar parceiros do seed pool para o envio
  - Enviar e-mails de warmup via EmailRegistry
  - Verificar inbox das sementes para registrar respostas
  - Atualizar contadores da campanha

A lógica de agendamento (quando chamar) fica em workers/warmup.py.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.warmup import WarmupCampaign, WarmupLog, WarmupSeedPool
from models.enums import WarmupStatus

logger = structlog.get_logger()


# ── Conteúdo dos e-mails de warmup ───────────────────────────────────
# Textos genéricos e variados para parecer conversa real.
# Quanto mais variados, menor a chance de filtros anti-spam.

_WARMUP_SUBJECTS = [
    "Oi, tudo bem?",
    "Feliz segunda-feira!",
    "Só passando para dizer oi",
    "Um pensamento para hoje",
    "Você viu isso?",
    "Novidade rápida",
    "Atualização rápida",
    "Dica do dia",
]

_WARMUP_BODIES = [
    "<p>Olá! Espero que esteja tudo bem por aí. Abraços!</p>",
    "<p>Só queria mandar um oi e saber como você está. Qualquer coisa sabe que pode contar comigo!</p>",
    "<p>Bom dia! Passando para deixar boas energias. Tenha um excelente dia.</p>",
    "<p>Oi! Estava lembrando de você e resolvi mandar uma mensagem. Tudo certo por aí?</p>",
    "<p>Olá! Que seu dia seja incrível. Um abraço forte!</p>",
]


def _warmup_email_content() -> tuple[str, str]:
    """Retorna (subject, body_html) aleatório para o e-mail de warmup."""
    return (
        random.choice(_WARMUP_SUBJECTS),
        random.choice(_WARMUP_BODIES),
    )


# ── Volume diário (curva de ramp-up) ─────────────────────────────────


def calculate_daily_volume(campaign: WarmupCampaign) -> int:
    """
    Calcula o volume de e-mails para o dia atual da campanha.
    Curva linear: vol_start → vol_target ao longo de ramp_days dias.

    Exemplo: start=5, target=80, ramp_days=30
      Dia 0  → 5
      Dia 15 → ~42
      Dia 30 → 80 (cap)
    """
    if campaign.current_day >= campaign.ramp_days:
        return campaign.daily_volume_target

    slope = (campaign.daily_volume_target - campaign.daily_volume_start) / max(campaign.ramp_days, 1)
    volume = campaign.daily_volume_start + int(slope * campaign.current_day)
    return max(volume, campaign.daily_volume_start)


# ── Seleção de sementes ───────────────────────────────────────────────


async def pick_seed_partners(
    n: int,
    db: AsyncSession,
) -> list[WarmupSeedPool]:
    """
    Seleciona até `n` sementes ativas do pool, priorizando as menos usadas.
    Retorna lista com até `n` sementes (pode ser menor se pool for pequeno).
    """
    result = await db.execute(
        select(WarmupSeedPool)
        .where(WarmupSeedPool.is_active.is_(True))
        .order_by(WarmupSeedPool.last_used_at.asc().nullsfirst())
        .limit(n * 3)  # pega mais para ter margem de escolha aleatória
    )
    seeds = list(result.scalars().all())
    if len(seeds) <= n:
        return seeds
    return random.sample(seeds, n)


# ── Envio de e-mails de warmup ────────────────────────────────────────


async def run_daily_warmup(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """
    Executa o ciclo diário de warmup para uma campanha.

    Calcula o volume do dia, seleciona sementes e envia os e-mails.
    Retorna um resumo do que foi enviado.
    """
    from models.email_account import EmailAccount  # noqa: PLC0415
    from integrations.email import EmailRegistry  # noqa: PLC0415
    from core.config import settings  # noqa: PLC0415

    # Carrega campanha
    camp_result = await db.execute(
        select(WarmupCampaign).where(
            WarmupCampaign.id == campaign_id,
            WarmupCampaign.tenant_id == tenant_id,
        )
    )
    campaign = camp_result.scalar_one_or_none()
    if campaign is None:
        logger.warning("warmup.campaign_not_found", campaign_id=str(campaign_id))
        return {"sent": 0, "error": "campaign_not_found"}

    if campaign.status != WarmupStatus.ACTIVE:
        return {"sent": 0, "skipped": True, "reason": f"status_{campaign.status}"}

    # Carrega EmailAccount
    acc_result = await db.execute(
        select(EmailAccount).where(EmailAccount.id == campaign.email_account_id)
    )
    email_account = acc_result.scalar_one_or_none()
    if email_account is None:
        logger.warning(
            "warmup.account_not_found",
            campaign_id=str(campaign_id),
            email_account_id=str(campaign.email_account_id),
        )
        return {"sent": 0, "error": "email_account_not_found"}

    # Volume do dia
    volume = calculate_daily_volume(campaign)
    seeds = await pick_seed_partners(volume, db)

    if not seeds:
        logger.warning("warmup.no_seeds_available", campaign_id=str(campaign_id))
        return {"sent": 0, "error": "no_seeds_available"}

    registry = EmailRegistry(settings=settings)
    sent_count = 0
    errors = 0

    for seed in seeds:
        subject, body_html = _warmup_email_content()
        try:
            result = await registry.send(
                account=email_account,
                to_email=seed.email,
                subject=subject,
                body_html=body_html,
                headers={"X-Warmup-Campaign": str(campaign_id)},
            )
        except Exception as exc:
            logger.error(
                "warmup.send_error",
                campaign_id=str(campaign_id),
                seed_email=seed.email,
                error=str(exc),
            )
            errors += 1
            continue

        now = datetime.now(timezone.utc)
        log = WarmupLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            direction="sent",
            status="delivered" if result.success else "failed",
            partner_email=seed.email,
            message_id_sent=result.message_id,
            sent_at=now,
        )
        db.add(log)

        # Atualiza last_used_at da semente
        seed.last_used_at = now

        if result.success:
            sent_count += 1
        else:
            errors += 1

    # Atualiza contadores da campanha
    campaign.total_sent += sent_count
    campaign.current_day += 1

    if campaign.current_day >= campaign.ramp_days:
        campaign.status = WarmupStatus.COMPLETED
        logger.info(
            "warmup.campaign_completed",
            campaign_id=str(campaign_id),
            total_sent=campaign.total_sent,
        )

    await db.commit()

    logger.info(
        "warmup.daily_cycle_done",
        campaign_id=str(campaign_id),
        day=campaign.current_day,
        volume=volume,
        sent=sent_count,
        errors=errors,
    )
    return {
        "sent": sent_count,
        "errors": errors,
        "volume_target": volume,
        "day": campaign.current_day,
    }


# ── Estatísticas da campanha ──────────────────────────────────────────


async def get_campaign_stats(
    campaign_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Retorna métricas consolidadas da campanha de warmup."""
    from sqlalchemy import func  # noqa: PLC0415

    camp_result = await db.execute(
        select(WarmupCampaign).where(
            WarmupCampaign.id == campaign_id,
            WarmupCampaign.tenant_id == tenant_id,
        )
    )
    campaign = camp_result.scalar_one_or_none()
    if campaign is None:
        return {}

    # Contagem de logs por status
    logs_result = await db.execute(
        select(WarmupLog.status, func.count(WarmupLog.id).label("count"))
        .where(WarmupLog.campaign_id == campaign_id)
        .group_by(WarmupLog.status)
    )
    log_counts: dict[str, int] = {row.status: row.count for row in logs_result}

    daily_volume = calculate_daily_volume(campaign)
    reply_rate = (
        round(campaign.total_replied / campaign.total_sent * 100, 1)
        if campaign.total_sent > 0
        else 0.0
    )
    spam_rate = (
        round(campaign.spam_count / campaign.total_sent * 100, 1)
        if campaign.total_sent > 0
        else 0.0
    )

    return {
        "campaign_id": str(campaign_id),
        "status": campaign.status,
        "current_day": campaign.current_day,
        "ramp_days": campaign.ramp_days,
        "progress_pct": round(campaign.current_day / campaign.ramp_days * 100, 1),
        "daily_volume_today": daily_volume,
        "daily_volume_target": campaign.daily_volume_target,
        "total_sent": campaign.total_sent,
        "total_replied": campaign.total_replied,
        "spam_count": campaign.spam_count,
        "reply_rate_pct": reply_rate,
        "spam_rate_pct": spam_rate,
        "log_counts": log_counts,
    }
