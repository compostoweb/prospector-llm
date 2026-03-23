"""
api/routes/llm.py

Endpoints para gerenciamento e seleção de modelos LLM.

GET  /llm/models          — lista todos os modelos de todos os providers configurados
GET  /llm/models/{provider} — filtra por provider
POST /llm/test            — testa um modelo com uma mensagem simples
GET  /llm/providers       — lista providers disponíveis (configurados)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import get_llm_registry
from integrations.llm import LLMMessage, LLMRegistry, ModelInfo

router = APIRouter(prefix="/llm", tags=["LLM"])


# ── Schemas de resposta ──────────────────────────────────────────────

class ModelResponse(BaseModel):
    id: str
    name: str
    provider: str
    context_window: int
    supports_json_mode: bool
    price_input_per_mtok: float
    price_output_per_mtok: float

    @classmethod
    def from_model_info(cls, m: ModelInfo) -> "ModelResponse":
        return cls(
            id=m.id,
            name=m.name,
            provider=m.provider,
            context_window=m.context_window,
            supports_json_mode=m.supports_json_mode,
            price_input_per_mtok=m.price_input_per_mtok,
            price_output_per_mtok=m.price_output_per_mtok,
        )


class ModelsListResponse(BaseModel):
    providers: list[str]
    total: int
    models: list[ModelResponse]


class TestRequest(BaseModel):
    provider: str
    model: str
    prompt: str = "Olá! Responda em 1 frase: qual é a capital do Brasil?"
    temperature: float = 0.5
    max_tokens: int = 100


class TestResponse(BaseModel):
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    ok: bool


# ── Rotas ────────────────────────────────────────────────────────────

@router.get("/providers", summary="Lista provedores configurados")
async def get_providers(
    registry: LLMRegistry = Depends(get_llm_registry),
) -> dict:
    return {"providers": registry.available_providers()}


@router.get(
    "/models",
    response_model=ModelsListResponse,
    summary="Lista todos os modelos de chat disponíveis (todos os providers)",
)
async def get_all_models(
    force_refresh: bool = Query(False, description="Força atualização ignorando cache"),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> ModelsListResponse:
    """
    Retorna a lista agregada de modelos de todos os providers configurados.
    Os modelos são cacheados por 1h no Redis — use force_refresh=true para forçar.
    """
    models = await registry.list_all_models(force_refresh=force_refresh)
    return ModelsListResponse(
        providers=registry.available_providers(),
        total=len(models),
        models=[ModelResponse.from_model_info(m) for m in models],
    )


@router.get(
    "/models/{provider}",
    response_model=ModelsListResponse,
    summary="Lista modelos de um provider específico",
)
async def get_models_by_provider(
    provider: str,
    registry: LLMRegistry = Depends(get_llm_registry),
) -> ModelsListResponse:
    if provider not in registry.available_providers():
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider}' não encontrado. Disponíveis: {registry.available_providers()}",
        )
    models = await registry.list_models_by_provider(provider)
    return ModelsListResponse(
        providers=[provider],
        total=len(models),
        models=[ModelResponse.from_model_info(m) for m in models],
    )


@router.post(
    "/test",
    response_model=TestResponse,
    summary="Testa um modelo com uma mensagem simples",
)
async def test_model(
    body: TestRequest,
    registry: LLMRegistry = Depends(get_llm_registry),
) -> TestResponse:
    """
    Endpoint de diagnóstico — envia uma mensagem simples para verificar
    se o provider e modelo estão funcionando corretamente.
    """
    try:
        response = await registry.complete(
            messages=[LLMMessage(role="user", content=body.prompt)],
            provider=body.provider,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
        return TestResponse(
            text=response.text,
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            ok=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro no provider: {exc}")
