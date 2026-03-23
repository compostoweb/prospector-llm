"""
services/ai_composer.py

Gera mensagens personalizadas para cada step da cadência.
Totalmente agnóstico ao provedor — usa LLMRegistry com o provider/modelo
configurado na cadência.
"""

from __future__ import annotations

import json
import structlog
from integrations.llm import LLMMessage, LLMRegistry, LLMResponse
from models.cadence import Cadence
from models.lead import Lead

logger = structlog.get_logger()

COMPOSER_SYSTEM_PROMPT = """
Você é um especialista em prospecção B2B consultiva.
Sua tarefa é escrever mensagens de outreach personalizadas, diretas e humanas.

Regras:
- NUNCA pareça um robô ou template genérico
- Máximo 3 parágrafos curtos
- Mencione algo específico sobre a empresa ou o lead (use o contexto fornecido)
- Tom: profissional mas conversacional — como se fossem colegas de setor
- Para LinkedIn: mais informal, curto (máximo 150 palavras)
- Para Email: pode ser um pouco mais formal, mas ainda direto (máximo 200 palavras)
- NUNCA use frases como "espero que esteja bem" ou "gostaria de apresentar"
- Retorne APENAS o texto da mensagem, sem assunto, sem saudação extra
""".strip()


class AIComposer:

    def __init__(self, registry: LLMRegistry) -> None:
        self._registry = registry

    async def compose(
        self,
        lead: Lead,
        channel: str,               # "linkedin_connect" | "linkedin_dm" | "email"
        step_number: int,
        context: dict,              # vindo de context_fetcher
        cadence: Cadence,
    ) -> str:
        """
        Gera uma mensagem personalizada para o lead/canal/step.
        Usa o provider e modelo configurados na cadência.
        """
        user_prompt = _build_user_prompt(lead, channel, step_number, context)

        messages = [
            LLMMessage(role="system", content=COMPOSER_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        response: LLMResponse = await self._registry.complete(
            messages=messages,
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=cadence.llm_temperature,
            max_tokens=cadence.llm_max_tokens,
        )

        logger.info(
            "ai_composer.composed",
            lead_id=str(lead.id),
            channel=channel,
            step=step_number,
            provider=response.provider,
            model=response.model,
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
        )

        return response.text.strip()


def _build_user_prompt(
    lead: Lead,
    channel: str,
    step: int,
    context: dict,
) -> str:
    site_summary = context.get("site_summary", "Não disponível")
    linkedin_post = context.get("recent_linkedin_post", "Não disponível")
    news = context.get("company_news", "Nenhuma notícia recente")

    return f"""
Escreva uma mensagem de outreach para:

Canal: {channel}
Step: {step} (1 = primeiro contato, 2+ = follow-up)
Nome do lead: {lead.name}
Empresa: {lead.company or "Não informado"}
Cargo/segmento: {lead.segment or "Não informado"}
LinkedIn: {lead.linkedin_url or "Não disponível"}

Contexto sobre a empresa:
{site_summary}

Post recente do lead no LinkedIn:
{linkedin_post}

Notícias recentes da empresa:
{news}

Escreva a mensagem agora:
""".strip()
