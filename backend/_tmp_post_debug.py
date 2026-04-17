import asyncio
import uuid
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.content_post import ContentPost
from models.content_linkedin_account import ContentLinkedInAccount
POST_ID = uuid.UUID("8b4f3055-ee84-4571-912c-05144b80f518")
async def main():
    async with AsyncSessionLocal() as db:
        post = (await db.execute(select(ContentPost).where(ContentPost.id == POST_ID))).scalar_one_or_none()
        print("POST", post is not None)
        if post is None:
            return
        print(post.status, post.publish_date, post.tenant_id)
        account = (await db.execute(select(ContentLinkedInAccount).where(ContentLinkedInAccount.tenant_id == post.tenant_id, ContentLinkedInAccount.is_active.is_(True)))).scalar_one_or_none()
        print("ACCOUNT", account is not None)
        if account is not None:
            print(account.person_urn, account.display_name)
asyncio.run(main())
