"""
Batch fetch ALL LinkedIn search params (LOCATION + INDUSTRY) via keyword sweep.
The Unipile API returns max 100 items per call with no real pagination.
By searching each letter a-z (and some common prefixes), we collect all unique items.
"""

import asyncio
import os
import string

os.environ.setdefault("ENV", "dev")


async def batch_fetch():
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from core.config import settings
    from core.database import AsyncSessionLocal
    from integrations.unipile_client import unipile_client
    from models.linkedin_search_param import LinkedInSearchParam

    account_id = settings.UNIPILE_ACCOUNT_ID_LINKEDIN
    if not account_id:
        print("No UNIPILE_ACCOUNT_ID_LINKEDIN configured")
        return

    # Keywords: empty + a-z + common prefixes
    keywords = [""] + list(string.ascii_lowercase)
    keywords += ["são", "rio", "san", "new", "sul", "nor", "est", "oes"]

    for param_type in ["LOCATION", "INDUSTRY"]:
        seen: dict[str, str] = {}  # id -> title

        for i, kw in enumerate(keywords):
            try:
                r = await unipile_client._client.get(
                    "/linkedin/search/parameters",
                    params={"account_id": account_id, "type": param_type, "keywords": kw},
                )
                r.raise_for_status()
                data = r.json()
                items = data.get("items", [])
                new = 0
                for item in items:
                    iid = str(item.get("id", ""))
                    title = str(item.get("title", ""))
                    if iid and iid not in seen:
                        seen[iid] = title
                        new += 1
                print(
                    f"  [{param_type}] kw='{kw}': {len(items)} items, {new} new → total {len(seen)}"
                )
            except Exception as e:
                print(f"  [{param_type}] ERROR kw='{kw}': {e}")

            await asyncio.sleep(0.15)

        print(f"\n{param_type}: found {len(seen)} unique items. Persisting...")

        # Persist to DB in bulk batches of 500
        async with AsyncSessionLocal() as db:
            items_list = [
                {"param_type": param_type, "external_id": eid, "title": title}
                for eid, title in seen.items()
            ]
            batch_size = 500
            count = 0
            for i in range(0, len(items_list), batch_size):
                batch = items_list[i : i + batch_size]
                insert_stmt = pg_insert(LinkedInSearchParam).values(batch)
                stmt = insert_stmt.on_conflict_do_update(
                    constraint="uq_li_search_param_type_eid",
                    set_={"title": insert_stmt.excluded.title},
                )
                await db.execute(stmt)
                await db.commit()
                count += len(batch)
                print(f"  Committed {count}/{len(items_list)}...")
            print(f"  Persisted {count} {param_type} items to DB\n")

    # Final count
    from sqlalchemy import func, select

    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count()).select_from(LinkedInSearchParam))).scalar()
        loc = (
            await db.execute(
                select(func.count())
                .select_from(LinkedInSearchParam)
                .where(LinkedInSearchParam.param_type == "LOCATION")
            )
        ).scalar()
        ind = (
            await db.execute(
                select(func.count())
                .select_from(LinkedInSearchParam)
                .where(LinkedInSearchParam.param_type == "INDUSTRY")
            )
        ).scalar()
        print(f"DB totals: {total} total | LOCATION: {loc} | INDUSTRY: {ind}")


asyncio.run(batch_fetch())
