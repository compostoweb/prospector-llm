"""
api/routes/llm.py

Endpoints para gerenciamento e seleção de modelos LLM.

GET  /llm/models          — lista todos os modelos de todos os providers configurados
GET  /llm/models/{provider} — filtra por provider
POST /llm/test            — testa um modelo com uma mensagem simples
GET  /llm/providers       — lista providers disponíveis (configurados)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import get_effective_tenant_id, get_llm_registry
from core.security import UserPayload, get_current_user_payload
from integrations.llm import (
    LLMMessage,
    LLMNonRetryableError,
    LLMRegistry,
    LLMUsageContext,
    ModelInfo,
)

router = APIRouter(prefix="/llm", tags=["LLM"])


# ── Schemas de resposta ──────────────────────────────────────────────


class ModelResponse(BaseModel):
    id: str
    name: str
    provider: str
    context_window: int
    supports_json: bool
    input_cost_per_mtok: float
    output_cost_per_mtok: float
    pricing_tag: str  # "free" | "paid" | ""

    @classmethod
    def from_model_info(cls, m: ModelInfo) -> ModelResponse:
        return cls(
            id=m.id,
            name=m.name,
            provider=m.provider,
            context_window=m.context_window,
            supports_json=m.supports_json_mode,
            input_cost_per_mtok=m.price_input_per_mtok,
            output_cost_per_mtok=m.price_output_per_mtok,
            pricing_tag=m.pricing_tag,
        )


class ProviderResponse(BaseModel):
    provider: str
    configured: bool
    models_count: int


class TestRequest(BaseModel):
    provider: str
    model: str
    prompt: str = "Olá! Responda em 1 frase: qual é a capital do Brasil?"
    temperature: float = 0.5
    max_tokens: int = 100


class TestResponse(BaseModel):
    response: str
    provider: str
    model: str
    tokens_used: int
    latency_ms: float
    ok: bool


# ── Rotas ────────────────────────────────────────────────────────────


@router.get("/providers", summary="Lista provedores configurados")
async def get_providers(
    registry: LLMRegistry = Depends(get_llm_registry),
) -> list[ProviderResponse]:
    """Retorna lista de providers com status de configuração e contagem de modelos."""
    providers = registry.available_providers()
    result: list[ProviderResponse] = []
    for p in providers:
        models = await registry.list_models_by_provider(p)
        result.append(ProviderResponse(provider=p, configured=True, models_count=len(models)))
    return result


@router.get(
    "/models",
    response_model=list[ModelResponse],
    summary="Lista todos os modelos de chat disponíveis (todos os providers)",
)
async def get_all_models(
    force_refresh: bool = Query(False, description="Força atualização ignorando cache"),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> list[ModelResponse]:
    """
    Retorna a lista agregada de modelos de todos os providers configurados.
    Os modelos são cacheados por 1h no Redis — use force_refresh=true para forçar.
    """
    models = await registry.list_all_models(force_refresh=force_refresh)
    return [ModelResponse.from_model_info(m) for m in models]


@router.get(
    "/models/{provider}",
    response_model=list[ModelResponse],
    summary="Lista modelos de um provider específico",
)
async def get_models_by_provider(
    provider: str,
    registry: LLMRegistry = Depends(get_llm_registry),
) -> list[ModelResponse]:
    if provider not in registry.available_providers():
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider}' não encontrado. Disponíveis: {registry.available_providers()}",
        )
    models = await registry.list_models_by_provider(provider)
    return [ModelResponse.from_model_info(m) for m in models]


@router.post(
    "/test",
    response_model=TestResponse,
    summary="Testa um modelo com uma mensagem simples",
)
async def test_model(
    body: TestRequest,
    tenant_id: UUID = Depends(get_effective_tenant_id),
    _user: UserPayload = Depends(get_current_user_payload),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> TestResponse:
    """
    Endpoint de diagnóstico — envia uma mensagem simples para verificar
    se o provider e modelo estão funcionando corretamente.
    """
    import time

    try:
        t0 = time.monotonic()
        response = await registry.complete(
            messages=[LLMMessage(role="user", content=body.prompt)],
            provider=body.provider,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            usage_context=LLMUsageContext(
                tenant_id=str(tenant_id),
                module="llm_settings",
                task_type="test_model",
                feature=body.provider,
                metadata={"model": body.model},
            ),
        )
        latency = (time.monotonic() - t0) * 1000
        return TestResponse(
            response=response.text,
            provider=response.provider,
            model=response.model,
            tokens_used=response.input_tokens + response.output_tokens,
            latency_ms=round(latency, 1),
            ok=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LLMNonRetryableError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro no provider: {exc}")
