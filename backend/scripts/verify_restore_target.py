from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@dataclass
class DatabaseTenantReport:
    slug: str
    tenant_id: str | None = None
    is_active: bool | None = None
    integration_present: bool | None = None
    leads_count: int | None = None
    content_posts_count: int | None = None


@dataclass
class DatabaseReport:
    ok: bool
    database_name: str | None = None
    postgres_version: str | None = None
    public_table_count: int | None = None
    alembic_version: str | None = None
    tenants_total: int | None = None
    active_tenants_total: int | None = None
    sampled_tenant: DatabaseTenantReport | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class ApiSmokeReport:
    ok: bool
    health_status_code: int | None = None
    health_payload: dict[str, Any] | None = None
    auth_status_code: int | None = None
    protected_status_code: int | None = None
    protected_total: int | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class RestoreVerificationReport:
    generated_at: str
    overall_ok: bool
    database: DatabaseReport
    api: ApiSmokeReport | None = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valida um ambiente restaurado de DR/staging checando banco, Alembic, "
            "tenant amostral e smoke HTTP da API."
        )
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("RESTORE_CHECK_DATABASE_URL"),
        help="DSN asyncpg do banco restaurado. Tambem aceita RESTORE_CHECK_DATABASE_URL.",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("RESTORE_CHECK_API_URL"),
        help="Base URL da API restaurada. Ex.: http://127.0.0.1:18000",
    )
    parser.add_argument(
        "--tenant-slug",
        default=os.getenv("RESTORE_CHECK_TENANT_SLUG"),
        help="Slug de tenant para smoke funcional e amostragem no banco.",
    )
    parser.add_argument(
        "--tenant-api-key",
        default=os.getenv("RESTORE_CHECK_TENANT_API_KEY"),
        help="API key do tenant para validar POST /auth/token no ambiente restaurado.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.getenv("RESTORE_CHECK_TIMEOUT_SECONDS", "10")),
        help="Timeout por operacao HTTP e banco.",
    )
    return parser


async def _fetch_scalar(connection, sql: str, params: dict[str, Any] | None = None) -> Any:
    result = await connection.execute(text(sql), params or {})
    return result.scalar_one_or_none()


async def _fetch_first_mapping(
    connection,
    sql: str,
    params: dict[str, Any] | None = None,
) -> RowMapping | None:
    result = await connection.execute(text(sql), params or {})
    mapping = result.mappings().first()
    return mapping


async def collect_database_report(
    *,
    database_url: str,
    timeout_seconds: float,
    tenant_slug: str | None,
) -> DatabaseReport:
    report = DatabaseReport(ok=False)
    engine = create_async_engine(database_url, pool_pre_ping=True)

    try:
        async with engine.connect() as connection:
            report.database_name = await _fetch_scalar(connection, "select current_database()")
            report.postgres_version = await _fetch_scalar(connection, "select version()")
            report.public_table_count = int(
                await _fetch_scalar(
                    connection,
                    """
                    select count(*)
                    from information_schema.tables
                    where table_schema = 'public'
                    """,
                )
                or 0
            )
            report.alembic_version = await _fetch_scalar(
                connection,
                "select version_num from alembic_version limit 1",
            )
            report.tenants_total = int(await _fetch_scalar(connection, "select count(*) from tenants") or 0)
            report.active_tenants_total = int(
                await _fetch_scalar(
                    connection,
                    "select count(*) from tenants where is_active is true",
                )
                or 0
            )

            if tenant_slug:
                sampled_tenant_row = await _fetch_first_mapping(
                    connection,
                    "select id, is_active from tenants where slug = :slug limit 1",
                    {"slug": tenant_slug},
                )
                tenant_report = DatabaseTenantReport(slug=tenant_slug)
                if sampled_tenant_row is None:
                    report.errors.append(f"tenant_slug_not_found:{tenant_slug}")
                else:
                    tenant_id = str(sampled_tenant_row["id"])
                    tenant_report.tenant_id = tenant_id
                    tenant_report.is_active = bool(sampled_tenant_row["is_active"])
                    tenant_report.integration_present = bool(
                        await _fetch_scalar(
                            connection,
                            "select count(*) from tenant_integrations where tenant_id = :tenant_id",
                            {"tenant_id": tenant_id},
                        )
                    )
                    tenant_report.leads_count = int(
                        await _fetch_scalar(
                            connection,
                            "select count(*) from leads where tenant_id = :tenant_id",
                            {"tenant_id": tenant_id},
                        )
                        or 0
                    )
                    tenant_report.content_posts_count = int(
                        await _fetch_scalar(
                            connection,
                            "select count(*) from content_posts where tenant_id = :tenant_id",
                            {"tenant_id": tenant_id},
                        )
                        or 0
                    )
                report.sampled_tenant = tenant_report

        report.ok = not report.errors
    except Exception as exc:
        report.errors.append(str(exc))
        report.ok = False
    finally:
        await engine.dispose()

    return report


async def collect_api_report(
    *,
    api_url: str,
    timeout_seconds: float,
    tenant_slug: str | None,
    tenant_api_key: str | None,
) -> ApiSmokeReport:
    report = ApiSmokeReport(ok=False)

    async with httpx.AsyncClient(base_url=api_url.rstrip("/"), timeout=timeout_seconds) as client:
        try:
            health_response = await client.get("/health")
            report.health_status_code = health_response.status_code
            if health_response.headers.get("content-type", "").startswith("application/json"):
                report.health_payload = health_response.json()
            if health_response.status_code != 200:
                report.errors.append(f"health_failed:{health_response.status_code}")
        except Exception as exc:
            report.errors.append(f"health_error:{exc}")
            return report

        if tenant_slug and tenant_api_key:
            try:
                auth_response = await client.post(
                    "/auth/token",
                    data={"username": tenant_slug, "password": tenant_api_key},
                )
                report.auth_status_code = auth_response.status_code
                if auth_response.status_code != 200:
                    report.errors.append(f"tenant_auth_failed:{auth_response.status_code}")
                else:
                    payload = auth_response.json()
                    access_token = payload.get("access_token")
                    protected_response = await client.get(
                        "/leads",
                        params={"page": 1, "page_size": 1},
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    report.protected_status_code = protected_response.status_code
                    if protected_response.status_code != 200:
                        report.errors.append(
                            f"tenant_smoke_failed:{protected_response.status_code}"
                        )
                    else:
                        protected_payload = protected_response.json()
                        total_value = protected_payload.get("total")
                        if isinstance(total_value, int):
                            report.protected_total = total_value
            except Exception as exc:
                report.errors.append(f"tenant_auth_error:{exc}")

    report.ok = not report.errors
    return report


async def _run(args: argparse.Namespace) -> int:
    if not args.database_url:
        raise SystemExit("database_url ausente. Use --database-url ou RESTORE_CHECK_DATABASE_URL.")

    database_report = await collect_database_report(
        database_url=args.database_url,
        timeout_seconds=args.timeout_seconds,
        tenant_slug=args.tenant_slug,
    )
    api_report: ApiSmokeReport | None = None
    if args.api_url:
        api_report = await collect_api_report(
            api_url=args.api_url,
            timeout_seconds=args.timeout_seconds,
            tenant_slug=args.tenant_slug,
            tenant_api_key=args.tenant_api_key,
        )

    overall_ok = database_report.ok and (api_report.ok if api_report is not None else True)
    report = RestoreVerificationReport(
        generated_at=datetime.now(UTC).isoformat(),
        overall_ok=overall_ok,
        database=database_report,
        api=api_report,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if overall_ok else 1


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()