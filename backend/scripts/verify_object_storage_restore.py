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
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import settings
from integrations.s3_client import S3Client


@dataclass(frozen=True)
class AssetSource:
    name: str
    table_name: str
    column_name: str
    created_at_column: str = "created_at"
    parser: str = "plain"


@dataclass
class AssetCheckRecord:
    record_id: str
    tenant_id: str | None
    storage_key: str | None
    status: str
    content_length: int | None = None
    error: str | None = None


@dataclass
class AssetCheckSummary:
    name: str
    total_references: int
    checked: int
    existing: int
    missing: int
    parse_errors: int
    records: list[AssetCheckRecord] = field(default_factory=list)


@dataclass
class StorageVerificationReport:
    generated_at: str
    overall_ok: bool
    tenant_slug: str | None
    bucket: str
    summaries: list[AssetCheckSummary]


ASSET_SOURCES: tuple[AssetSource, ...] = (
    AssetSource(name="audio_files", table_name="audio_files", column_name="s3_key"),
    AssetSource(name="content_post_images", table_name="content_posts", column_name="image_s3_key"),
    AssetSource(name="content_post_videos", table_name="content_posts", column_name="video_s3_key"),
    AssetSource(
        name="content_gallery_images",
        table_name="content_gallery_images",
        column_name="image_s3_key",
    ),
    AssetSource(
        name="content_articles",
        table_name="content_articles",
        column_name="thumbnail_s3_key",
    ),
    AssetSource(
        name="content_newsletters",
        table_name="content_newsletters",
        column_name="cover_image_s3_key",
    ),
    AssetSource(
        name="content_lead_magnets",
        table_name="content_lead_magnets",
        column_name="file_url",
        parser="file_url",
    ),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verifica se referencias criticas do banco apontam para objetos existentes "
            "no bucket restaurado de S3/MinIO."
        )
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("RESTORE_CHECK_DATABASE_URL"),
        help="DSN asyncpg do banco restaurado. Tambem aceita RESTORE_CHECK_DATABASE_URL.",
    )
    parser.add_argument(
        "--tenant-slug",
        default=os.getenv("RESTORE_CHECK_TENANT_SLUG"),
        help="Slug opcional para limitar a verificacao a um tenant.",
    )
    parser.add_argument(
        "--limit-per-asset",
        type=int,
        default=int(os.getenv("RESTORE_CHECK_STORAGE_LIMIT", "25")),
        help="Quantidade maxima de referencias checadas por tipo de asset.",
    )
    return parser


def _extract_storage_key_from_file_url(file_url: str | None) -> str | None:
    normalized = (file_url or "").strip()
    if not normalized:
        return None

    if normalized.startswith(("lm-pdfs/", "lm-images/", "audio/", "branding/", "content/")):
        return normalized

    parsed = urlsplit(normalized)
    path = (parsed.path or "").lstrip("/")

    if "files/" in path:
        extracted = path.split("files/", 1)[1]
        return extracted or None

    bucket_marker = f"{settings.S3_BUCKET}/"
    if bucket_marker in path:
        extracted = path.split(bucket_marker, 1)[1]
        return extracted or None

    return None


async def _resolve_tenant_id(connection, tenant_slug: str | None) -> str | None:
    if not tenant_slug:
        return None
    result = await connection.execute(
        text("select id::text from tenants where slug = :slug limit 1"),
        {"slug": tenant_slug},
    )
    return result.scalar_one_or_none()


async def _count_references(connection, source: AssetSource, tenant_id: str | None) -> int:
    tenant_sql = " and tenant_id = :tenant_id" if tenant_id else ""
    result = await connection.execute(
        text(
            f"""
            select count(*)
            from {source.table_name}
            where {source.column_name} is not null
              and nullif(trim({source.column_name}), '') is not null
              {tenant_sql}
            """
        ),
        {"tenant_id": tenant_id} if tenant_id else {},
    )
    return int(result.scalar_one() or 0)


async def _load_reference_rows(
    connection,
    source: AssetSource,
    tenant_id: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    tenant_sql = " and tenant_id = :tenant_id" if tenant_id else ""
    result = await connection.execute(
        text(
            f"""
            select id::text as record_id,
                   tenant_id::text as tenant_id,
                   {source.column_name} as raw_value
            from {source.table_name}
            where {source.column_name} is not null
              and nullif(trim({source.column_name}), '') is not null
              {tenant_sql}
            order by {source.created_at_column} desc nulls last
            limit :limit_value
            """
        ),
        {
            "limit_value": limit,
            **({"tenant_id": tenant_id} if tenant_id else {}),
        },
    )
    return [dict(row) for row in result.mappings().all()]


def _normalize_key(source: AssetSource, raw_value: str | None) -> str | None:
    if source.parser == "file_url":
        return _extract_storage_key_from_file_url(raw_value)
    normalized = (raw_value or "").strip()
    return normalized or None


async def _collect_summary(
    connection,
    s3_client: S3Client,
    source: AssetSource,
    tenant_id: str | None,
    limit_per_asset: int,
) -> AssetCheckSummary:
    total_references = await _count_references(connection, source, tenant_id)
    rows = await _load_reference_rows(connection, source, tenant_id, limit_per_asset)

    records: list[AssetCheckRecord] = []
    existing = 0
    missing = 0
    parse_errors = 0

    for row in rows:
        storage_key = _normalize_key(source, row.get("raw_value"))
        if not storage_key:
            parse_errors += 1
            records.append(
                AssetCheckRecord(
                    record_id=str(row.get("record_id")),
                    tenant_id=row.get("tenant_id"),
                    storage_key=None,
                    status="parse_error",
                    error="storage_key_unresolved",
                )
            )
            continue

        metadata = s3_client.head_object(storage_key)
        if metadata is None:
            missing += 1
            records.append(
                AssetCheckRecord(
                    record_id=str(row.get("record_id")),
                    tenant_id=row.get("tenant_id"),
                    storage_key=storage_key,
                    status="missing",
                )
            )
            continue

        existing += 1
        content_length = metadata.get("ContentLength")
        records.append(
            AssetCheckRecord(
                record_id=str(row.get("record_id")),
                tenant_id=row.get("tenant_id"),
                storage_key=storage_key,
                status="ok",
                content_length=int(content_length) if isinstance(content_length, int) else None,
            )
        )

    return AssetCheckSummary(
        name=source.name,
        total_references=total_references,
        checked=len(rows),
        existing=existing,
        missing=missing,
        parse_errors=parse_errors,
        records=records,
    )


async def _run(args: argparse.Namespace) -> int:
    if not args.database_url:
        raise SystemExit("database_url ausente. Use --database-url ou RESTORE_CHECK_DATABASE_URL.")

    engine = create_async_engine(args.database_url, pool_pre_ping=True)
    s3_client = S3Client()

    try:
        async with engine.connect() as connection:
            tenant_id = await _resolve_tenant_id(connection, args.tenant_slug)
            if args.tenant_slug and tenant_id is None:
                raise SystemExit(f"tenant_slug_not_found:{args.tenant_slug}")

            summaries = [
                await _collect_summary(
                    connection,
                    s3_client,
                    source,
                    tenant_id,
                    args.limit_per_asset,
                )
                for source in ASSET_SOURCES
            ]
    finally:
        await engine.dispose()

    overall_ok = all(summary.missing == 0 and summary.parse_errors == 0 for summary in summaries)
    report = StorageVerificationReport(
        generated_at=datetime.now(UTC).isoformat(),
        overall_ok=overall_ok,
        tenant_slug=args.tenant_slug,
        bucket=settings.S3_BUCKET,
        summaries=summaries,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if overall_ok else 1


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()