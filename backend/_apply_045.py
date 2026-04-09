"""Script para aplicar migration 045 via asyncpg direto."""

import asyncio

import asyncpg

URL = "postgresql://postgres:e094b9cd2bb7c02356db@easypanel.compostoweb.com.br:7342/prospector"


async def main() -> None:
    conn = await asyncpg.connect(URL, timeout=15)
    try:
        rows = await conn.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'content_posts'
            AND column_name IN ('image_filename', 'image_size_bytes')
        """,
            timeout=10,
        )
        existing = [r["column_name"] for r in rows]
        print("Colunas existentes:", existing)

        if "image_filename" not in existing:
            await conn.execute(
                "ALTER TABLE content_posts ADD COLUMN image_filename VARCHAR(500)",
                timeout=30,
            )
            print("Adicionado: image_filename")
        else:
            print("image_filename ja existe")

        if "image_size_bytes" not in existing:
            await conn.execute(
                "ALTER TABLE content_posts ADD COLUMN image_size_bytes INTEGER",
                timeout=30,
            )
            print("Adicionado: image_size_bytes")
        else:
            print("image_size_bytes ja existe")

        await conn.execute("UPDATE alembic_version SET version_num = '045'", timeout=10)
        print("alembic_version -> 045")
        print("Migration 045 aplicada com sucesso.")
    finally:
        await asyncio.wait_for(conn.close(), timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
