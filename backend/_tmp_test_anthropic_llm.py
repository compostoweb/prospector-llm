import asyncio
from core.config import settings
from core.redis_client import redis_client
from integrations.llm.registry import LLMRegistry
from integrations.llm import LLMMessage

async def main():
    registry = LLMRegistry(settings=settings, redis=redis_client)
    print('providers', registry.available_providers())
    models = await registry.list_models_by_provider('anthropic')
    print('anthropic_models', len(models))
    print('first_model', models[0].id if models else 'none')
    response = await registry.complete(
        messages=[LLMMessage(role='user', content='Responda com uma frase curta em portugues.')],
        provider='anthropic',
        model='claude-sonnet-4-6',
        max_tokens=80,
        temperature=0.2,
    )
    print('ok', response.model, response.text)

asyncio.run(main())
