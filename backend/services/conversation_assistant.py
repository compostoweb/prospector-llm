"""
services/conversation_assistant.py

Assistente de conversa para UniBox LinkedIn.
Gera sugestões de resposta com base no histórico do chat e dados do lead.
"""

from __future__ import annotations

import structlog

from integrations.llm import LLMMessage, LLMRegistry, LLMResponse
from core.config import settings

logger = structlog.get_logger()

_TONES = {
    "formal": "Profissional e respeitoso, linguagem corporativa sem ser engessada.",
    "casual": "Descontraído porém profissional, como conversa entre colegas de setor.",
    "objetiva": "Direto ao ponto, frases curtas, sem rodeios. Máxima clareza.",
    "consultiva": "Postura de consultor, questiona para entender, oferece perspectivas de valor.",
}

_SYSTEM_PROMPT = """
Você é um assistente de conversa para prospecção B2B via LinkedIn.
Sua tarefa é sugerir a próxima resposta para o operador de vendas.

REGRAS:
1. Analise o histórico de mensagens do chat para entender o contexto
2. Se houver dados do lead (empresa, cargo, setor), use para personalizar
3. Mantenha o tom solicitado pelo operador
4. Nunca sugira texto longo — LinkedIn é conversa, não email
5. Máximo 80 palavras
6. Retorne APENAS o texto da mensagem sugerida — sem explicações, sem aspas
7. NUNCA use travessões como pontuação
8. Não se apresente — o operador já está em conversa com o lead
""".strip()


class ConversationAssistant:
    """Gera sugestões de resposta para conversas LinkedIn via LLM."""

    def __init__(self, registry: LLMRegistry) -> None:
        self._registry = registry

    async def suggest_reply(
        self,
        chat_messages: list[dict],
        lead_data: dict | None = None,
        tone: str = "formal",
        provider: str | None = None,
        model: str | None = None,
    ) -> str:
        """
        Gera sugestão de resposta baseada no histórico do chat.

        Args:
            chat_messages: últimas N mensagens [{sender, text, is_own}]
            lead_data: dados do lead (nome, empresa, cargo, etc)
            tone: tom desejado (formal, casual, objetiva, consultiva)
            provider: provider LLM (default: settings global)
            model: modelo LLM (default: settings global)
        """
        tone_desc = _TONES.get(tone, _TONES["formal"])
        llm_provider = provider or settings.REPLY_PARSER_PROVIDER
        llm_model = model or settings.REPLY_PARSER_MODEL

        # Monta contexto do lead
        lead_context = ""
        if lead_data:
            parts = []
            if lead_data.get("name"):
                parts.append(f"Nome: {lead_data['name']}")
            if lead_data.get("company"):
                parts.append(f"Empresa: {lead_data['company']}")
            if lead_data.get("job_title"):
                parts.append(f"Cargo: {lead_data['job_title']}")
            if lead_data.get("segment"):
                parts.append(f"Segmento: {lead_data['segment']}")
            if lead_data.get("industry"):
                parts.append(f"Indústria: {lead_data['industry']}")
            lead_context = "\n".join(parts)

        # Monta histórico formatado
        history_lines = []
        for msg in chat_messages[-15:]:  # últimas 15 msgs
            sender = "EU" if msg.get("is_own") else msg.get("sender_name", "LEAD")
            history_lines.append(f"{sender}: {msg.get('text', '')}")
        history = "\n".join(history_lines)

        user_prompt = f"""TOM DESEJADO: {tone_desc}

DADOS DO LEAD:
{lead_context or "Não disponível"}

HISTÓRICO DO CHAT:
{history}

Sugira a próxima resposta mantendo o tom '{tone}':"""

        messages = [
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        response: LLMResponse = await self._registry.complete(
            messages=messages,
            provider=llm_provider,
            model=llm_model,
            temperature=0.7,
            max_tokens=256,
        )

        logger.info(
            "conversation_assistant.suggested",
            tone=tone,
            provider=response.provider,
            model=response.model,
        )

        return response.text.strip()
