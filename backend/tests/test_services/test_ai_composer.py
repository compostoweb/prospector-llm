"""
tests/test_services/test_ai_composer.py

Testes unitários para services/ai_composer.py.
O LLMRegistry é mockado — nenhuma chamada real de API é feita.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from integrations.llm.base import LLMMessage, LLMResponse
from models.cadence import Cadence
from models.enums import LeadStatus
from models.lead import Lead
from services.ai_composer import COMPOSER_SYSTEM_PROMPT, AIComposer, prepare_composer_messages

pytestmark = pytest.mark.asyncio


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_registry(response_text: str = "Olá, vi que vocês trabalham com X...") -> MagicMock:
    """Retorna um LLMRegistry mockado que sempre responde com response_text."""
    registry = MagicMock()
    registry.complete = AsyncMock(
        return_value=LLMResponse(
            text=response_text,
            model="gpt-4o-mini",
            provider="openai",
            input_tokens=50,
            output_tokens=30,
        )
    )
    return registry


def _make_lead(
    tenant_id: uuid.UUID,
    *,
    company: str = "Tech Startup",
    website: str = "https://techstartup.com",
    linkedin_url: str = "https://linkedin.com/in/mariasouza",
    job_title: str | None = None,
    industry: str | None = None,
) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Maria Souza",
        company=company,
        website=website,
        linkedin_url=linkedin_url,
        job_title=job_title,
        industry=industry,
        status=LeadStatus.ENRICHED,
    )


def _make_cadence(tenant_id: uuid.UUID) -> Cadence:
    return Cadence(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Cadência Principal",
        is_active=True,
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_temperature=0.7,
        llm_max_tokens=512,
    )


# ── Testes ────────────────────────────────────────────────────────────

async def test_compose_returns_string():
    """compose() deve retornar uma string não-vazia."""
    tid = uuid.uuid4()
    registry = _make_registry("Mensagem personalizada para Maria.")
    composer = AIComposer(registry)

    result = await composer.compose(
        lead=_make_lead(tid),
        channel="linkedin_connect",
        step_number=1,
        context={"summary": "Empresa de tecnologia focada em SaaS"},
        cadence=_make_cadence(tid),
    )

    assert isinstance(result, str)
    assert len(result) > 0


async def test_compose_calls_registry_with_correct_provider():
    """compose() deve passar o provider e modelo da cadência para registry.complete()."""
    tid = uuid.uuid4()
    registry = _make_registry()
    composer = AIComposer(registry)
    cadence = _make_cadence(tid)
    cadence.llm_provider = "gemini"
    cadence.llm_model = "gemini-2.5-flash"
    cadence.llm_temperature = 0.3
    cadence.llm_max_tokens = 1024

    await composer.compose(
        lead=_make_lead(tid),
        channel="email",
        step_number=2,
        context={},
        cadence=cadence,
    )

    registry.complete.assert_called_once()
    call_kwargs = registry.complete.call_args.kwargs
    assert call_kwargs["provider"] == "gemini"
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["max_tokens"] == 1024


async def test_compose_includes_system_prompt():
    """compose() deve incluir o system prompt nas mensagens enviadas ao LLM."""
    tid = uuid.uuid4()
    registry = _make_registry()
    composer = AIComposer(registry)

    await composer.compose(
        lead=_make_lead(tid),
        channel="linkedin_dm",
        step_number=2,
        context={},
        cadence=_make_cadence(tid),
    )

    messages: list[LLMMessage] = registry.complete.call_args.kwargs["messages"]
    assert messages[0].role == "system"
    assert messages[0].content == COMPOSER_SYSTEM_PROMPT


async def test_compose_strips_whitespace():
    """compose() deve retornar o texto sem espaços/quebras extras nas bordas."""
    tid = uuid.uuid4()
    registry = _make_registry("  Mensagem com espaços extras  \n")
    composer = AIComposer(registry)

    result = await composer.compose(
        lead=_make_lead(tid),
        channel="email",
        step_number=1,
        context={},
        cadence=_make_cadence(tid),
    )

    assert result == "Mensagem com espaços extras"


async def test_compose_user_prompt_includes_lead_data():
    """O user prompt enviado ao LLM deve conter dados do lead."""
    tid = uuid.uuid4()
    registry = _make_registry()
    composer = AIComposer(registry)
    lead = _make_lead(tid)

    await composer.compose(
        lead=lead,
        channel="linkedin_connect",
        step_number=1,
        context={"summary": "Empresa inovadora no setor de IA"},
        cadence=_make_cadence(tid),
    )

    messages: list[LLMMessage] = registry.complete.call_args.kwargs["messages"]
    user_prompt = messages[1].content
    # O prompt deve mencionar o nome ou a empresa do lead
    assert "Maria Souza" in user_prompt or "Tech Startup" in user_prompt


async def test_prepare_composer_messages_returns_observability_metadata() -> None:
    """prepare_composer_messages() deve expor o contexto de composição usado."""
    tid = uuid.uuid4()
    lead = _make_lead(
        tid,
        company="Finance Labs",
        website="https://financelabs.com",
        job_title="CFO",
        industry="Financeiro e contabilidade",
    )

    messages, composition_context = prepare_composer_messages(
        lead=lead,
        channel="email",
        step_number=1,
        context={"site_summary": "Empresa com operação financeira distribuída."},
        cadence=_make_cadence(tid),
    )

    assert messages[0].content == COMPOSER_SYSTEM_PROMPT
    assert composition_context.generation_mode == "llm"
    assert composition_context.step_key == "email_first"
    assert composition_context.copy_method == "DIS"
    assert composition_context.playbook_sector == "financeiro"
    assert composition_context.playbook_role == "cfo"
    assert composition_context.few_shot_applied is True
    assert composition_context.few_shot_key == "financeiro:cfo:email:first"
    assert composition_context.few_shot_method == "DPO"
    assert composition_context.has_site_summary is True


async def test_compose_attaches_composition_context_to_response_raw():
    """compose() deve anexar o composition_context normalizado ao raw da resposta."""
    tid = uuid.uuid4()
    registry = _make_registry("Mensagem personalizada para CFO.")
    composer = AIComposer(registry)
    lead = _make_lead(
        tid,
        company="Finance Labs",
        website="https://financelabs.com",
        job_title="CFO",
        industry="Financeiro e contabilidade",
    )

    await composer.compose(
        lead=lead,
        channel="email",
        step_number=1,
        context={"site_summary": "Empresa com operação financeira distribuída."},
        cadence=_make_cadence(tid),
    )

    response = registry.complete.return_value
    composition_context = response.raw.get("composition_context")

    assert composition_context is not None
    assert composition_context["generation_mode"] == "llm"
    assert composition_context["step_key"] == "email_first"
    assert composition_context["playbook_sector"] == "financeiro"
    assert composition_context["playbook_role"] == "cfo"
    assert composition_context["few_shot_applied"] is True
    assert composition_context["few_shot_key"] == "financeiro:cfo:email:first"
    assert composition_context["has_site_summary"] is True
