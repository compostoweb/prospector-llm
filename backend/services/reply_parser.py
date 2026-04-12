"""
services/reply_parser.py

Classifica a intenção de uma resposta recebida (inbound).
Usa o provider/modelo efetivo resolvido para o tenant no ponto de chamada.
"""

from __future__ import annotations

import json

import structlog

from integrations.llm import LLMMessage, LLMRegistry, LLMResponse, LLMUsageContext

logger = structlog.get_logger()

PARSER_SYSTEM_PROMPT = """
Você é um analisador de respostas de prospecção B2B.
Sua tarefa é classificar a intenção de uma mensagem recebida de um prospect.

Classifique em exatamente uma das categorias:
- INTEREST: demonstra interesse, quer saber mais, pede reunião ou orçamento
- OBJECTION: tem dúvidas, preço alto, timing ruim, mas não descartou
- NOT_INTERESTED: descartou explicitamente, pediu para não contactar mais
- OUT_OF_OFFICE: resposta automática de férias/ausência
- NEUTRAL: resposta que não se encaixa nas anteriores (pergunta genérica, "ok", etc.)

Retorne APENAS JSON no formato:
{
  "intent": "INTEREST" | "OBJECTION" | "NOT_INTERESTED" | "OUT_OF_OFFICE" | "NEUTRAL",
  "confidence": 0.0 a 1.0,
  "summary": "resumo em 1 frase do que o lead disse",
  "out_of_office_return_date": "YYYY-MM-DD ou null"
}
""".strip()


class ReplyParser:
    def __init__(
        self,
        registry: LLMRegistry,
        provider: str,
        model: str,
    ) -> None:
        self._registry = registry
        self._provider = provider
        self._model = model

    async def classify(
        self,
        reply_text: str,
        lead_name: str,
        *,
        tenant_id: str,
        lead_id: str | None = None,
        channel: str | None = None,
    ) -> dict:
        """
        Retorna dict com: intent, confidence, summary, out_of_office_return_date.
        """
        messages = [
            LLMMessage(role="system", content=PARSER_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=f"Lead: {lead_name}\n\nMensagem recebida:\n{reply_text}",
            ),
        ]

        response: LLMResponse = await self._registry.complete(
            messages=messages,
            provider=self._provider,
            model=self._model,
            temperature=0.1,  # baixa temperatura para classificação determinística
            max_tokens=256,
            json_mode=True,
            usage_context=LLMUsageContext(
                tenant_id=tenant_id,
                module="inbox",
                task_type="reply_classification",
                feature=channel,
                entity_type="lead",
                entity_id=lead_id,
            ),
        )

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error("reply_parser.json_error", raw=response.text)
            result = {
                "intent": "NEUTRAL",
                "confidence": 0.0,
                "summary": "Erro ao classificar resposta",
                "out_of_office_return_date": None,
            }

        logger.info(
            "reply_parser.classified",
            lead=lead_name,
            intent=result.get("intent"),
            confidence=result.get("confidence"),
            provider=response.provider,
            model=response.model,
        )

        return result
