import asyncio
from uuid import UUID
from fastapi import HTTPException
from api.routes.llm import TestRequest, test_model
from core.config import settings
from core.redis_client import redis_client
from integrations.llm.registry import LLMRegistry

async def main():
    registry = LLMRegistry(settings=settings, redis=redis_client)
    try:
        await test_model(
            body=TestRequest(
                provider='anthropic',
                model='claude-sonnet-4-6',
                prompt='Responda com uma frase curta em portugues.',
            ),
            tenant_id=UUID('00000000-0000-0000-0000-000000000001'),
            _user={'sub': 'debug'} ,
            registry=registry,
        )
    except HTTPException as exc:
        print('status', exc.status_code)
        print('detail', exc.detail)

asyncio.run(main())
