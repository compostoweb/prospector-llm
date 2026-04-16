"""
workers/linkedin_params_refresh.py

Task Celery para atualizar o cache de parâmetros de busca LinkedIn
(LOCATION, INDUSTRY) a partir da Unipile API.

A Unipile retorna no máximo 100 items por chamada sem paginação real.
Para capturar todos, usamos keyword sweep: busca vazia + cada letra a-z
+ prefixos comuns. Cada combinação retorna um subconjunto diferente.

Agendado nos finais de semana via Beat schedule.
"""

from __future__ import annotations

import asyncio
import string
from typing import Any, cast

import structlog

from workers.celery_app import celery_app

logger = structlog.get_logger()

# Keywords for exhaustive sweep (empty + a-z + common prefixes)
_SWEEP_KEYWORDS: list[str] = (
    [""] + list(string.ascii_lowercase) + ["são", "rio", "san", "new", "sul", "nor", "est", "oes"]
)


async def _refresh_params() -> dict[str, int]:
    """Busca LOCATION e INDUSTRY na Unipile via keyword sweep e atualiza o BD."""
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from core.config import settings
    from core.database import WorkerSessionLocal
    from integrations.unipile_client import unipile_client
    from models.linkedin_search_param import LinkedInSearchParam
    from models.tenant import TenantIntegration

    # Descobrir um account_id válido
    account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN or ""
    if not account_id:
        async with WorkerSessionLocal() as db:
            result = await db.execute(
                select(TenantIntegration.unipile_linkedin_account_id)
                .where(TenantIntegration.unipile_linkedin_account_id.is_not(None))
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                account_id = str(row)

    if not account_id:
        logger.warning("linkedin_params_refresh.no_account_id")
        return {"LOCATION": 0, "INDUSTRY": 0}

    counts: dict[str, int] = {}

    for param_type in ("LOCATION", "INDUSTRY"):
        seen: dict[str, str] = {}  # external_id -> title

        for kw in _SWEEP_KEYWORDS:
            try:
                data = await cast(Any, unipile_client).search_linkedin_params(
                    account_id=account_id,
                    param_type=param_type,
                    query=kw,
                )
                items = data.get("items", [])
                for item in items:
                    eid = str(item.get("id", ""))
                    title = str(item.get("title", ""))
                    if eid:
                        seen[eid] = title
            except Exception:
                logger.warning(
                    "linkedin_params_refresh.keyword_error",
                    param_type=param_type,
                    keyword=kw,
                )
            # Small delay between API calls
            await asyncio.sleep(0.15)

        if not seen:
            logger.info(
                "linkedin_params_refresh.empty",
                param_type=param_type,
            )
            counts[param_type] = 0
            continue

        # Persist all unique items to DB
        try:
            async with WorkerSessionLocal() as db:
                for eid, title in seen.items():
                    stmt = (
                        pg_insert(LinkedInSearchParam)
                        .values(
                            param_type=param_type,
                            external_id=eid,
                            title=title,
                        )
                        .on_conflict_do_update(
                            constraint="uq_li_search_param_type_eid",
                            set_={"title": title},
                        )
                    )
                    await db.execute(stmt)
                await db.commit()

            counts[param_type] = len(seen)
            logger.info(
                "linkedin_params_refresh.done",
                param_type=param_type,
                count=len(seen),
            )
        except Exception:
            logger.exception(
                "linkedin_params_refresh.persist_error",
                param_type=param_type,
            )
            counts[param_type] = 0

    return counts


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def refresh_linkedin_search_params(self: Any) -> dict[str, int]:
    """Atualiza cache de LOCATION e INDUSTRY no BD via Unipile."""
    try:
        return asyncio.run(_refresh_params())
    except Exception as exc:
        logger.exception("refresh_linkedin_search_params.failed")
        raise self.retry(exc=exc) from exc
