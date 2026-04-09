"""Script único para aplicar migration 044 via asyncpg."""

import asyncio
import sys

import asyncpg

URL = "postgresql://postgres:e094b9cd2bb7c02356db@easypanel.compostoweb.com.br:7342/prospector"


async def main() -> None:
    conn = await asyncpg.connect(URL, timeout=15)
    try:
        # Encerrar outras sessoes que possam segurar lock
        await conn.fetch(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
        """,
            timeout=10,
        )
        print("Sessoes encerradas.")

        rows = await conn.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'content_posts'
            AND column_name IN ('video_filename', 'video_size_bytes')
        """,
            timeout=10,
        )
        existing = [r["column_name"] for r in rows]
        print("Colunas existentes:", existing)

        if "video_filename" not in existing:
            await conn.execute(
                "ALTER TABLE content_posts ADD COLUMN video_filename VARCHAR(500)",
                timeout=30,
            )
            print("Adicionado: video_filename")
        else:
            print("video_filename ja existe")

        if "video_size_bytes" not in existing:
            await conn.execute(
                "ALTER TABLE content_posts ADD COLUMN video_size_bytes INTEGER",
                timeout=30,
            )
            print("Adicionado: video_size_bytes")
        else:
            print("video_size_bytes ja existe")

        await conn.execute("UPDATE alembic_version SET version_num = '044'", timeout=10)
        print("alembic_version -> 044")
        print("Migration 044 aplicada com sucesso.")
    finally:
        await asyncio.wait_for(conn.close(), timeout=5)


try:
    asyncio.run(main())
except Exception as exc:
    print(f"ERRO: {exc}", file=sys.stderr)
    sys.exit(1)
