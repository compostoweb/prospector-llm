"""
services/content/engagement_analyzer.py

Analise LLM de posts do LinkedIn para o Engagement Scanner.

Dois analisadores:
  1. analyze_reference_post    — posts de alto engajamento (hook, pilar, por que performou)
  2. analyze_icp_post_relevance — posts de ICP (relevancia para comentar + angulo sugerido)

Modelo e provider recebidos dinamicamente via configuracao efetiva do tenant.
"""

from __future__ import annotations

import json
import re

import structlog

from integrations.llm import LLMMessage
from integrations.llm.registry import LLMRegistry
from services.llm_config import ResolvedLLMConfig

logger = structlog.get_logger()

# ── Prompts ────────────────────────────────────────────────────────────────────

_ANALYZE_POST_SYSTEM = """
Voce e um especialista em marketing de conteudo para LinkedIn.
Analise posts que geraram alto engajamento e extraia insights estruturados.
Retorne APENAS JSON valido, sem texto adicional, sem markdown, sem blocos de codigo.
""".strip()

_ANALYZE_POST_USER = """
Analise este post do LinkedIn e retorne um JSON com:
{{
  "hook_type": "loop_open|contrarian|identification|shortcut|benefit|data",
  "pillar": "authority|case|vision",
  "why_it_performed": "por que esse post gerou alto engajamento (1-2 frases diretas)",
  "what_to_replicate": "o que pode ser replicado em outros posts (1-2 frases diretas)"
}}

Definicoes dos tipos de hook:
- loop_open: abre enigma que so fecha no post
- contrarian: desafia o senso comum
- identification: descreve a dor com precisao — leitor pensa "e isso!"
- shortcut: promessa de rota mais curta para algo
- benefit: entrega o valor logo de cara
- data: ancora o post em dado concreto ou numero

Pilares:
- authority: demonstra expertise e conhecimento tecnico
- case: apresenta resultado real ou historia de transformacao
- vision: propoe perspectiva de futuro ou tendencia

POST:
{post_text}

Retorne APENAS o JSON valido.
""".strip()

_ICP_RELEVANCE_SYSTEM = """
Voce e um especialista em engenharia de solucoes e automacao empresarial.
Avalie se vale a pena comentar em posts de decisores do LinkedIn.
Retorne APENAS JSON valido, sem texto adicional.
""".strip()

_ICP_RELEVANCE_USER = """
Este post foi publicado por {author_name} ({author_title} em {author_company}).
Avalie se o post e relevante para que um especialista em engenharia de solucoes
e automacao faca um comentario tecnico que agregue valor a discussao.

POST:
{post_text}

Retorne JSON:
{{
  "is_relevant": true|false,
  "relevance_reason": "por que e ou nao relevante para comentar (1 frase)",
  "comment_angle": "angulo sugerido para o comentario (1 frase) — apenas se is_relevant = true, senao string vazia"
}}

Retorne APENAS o JSON valido.
""".strip()


# ── Funcoes publicas ────────────────────────────────────────────────────────────


async def analyze_reference_post(
    post_text: str,
    registry: LLMRegistry,
    llm_config: ResolvedLLMConfig,
) -> dict:
    """
    Analisa post de referencia e retorna hook_type, pillar, why_it_performed,
    what_to_replicate.

    Em caso de falha de parse, retorna dict com valores None.
    """
    messages = [
        LLMMessage(role="system", content=_ANALYZE_POST_SYSTEM),
        LLMMessage(
            role="user",
            content=_ANALYZE_POST_USER.format(post_text=post_text[:3000]),
        ),
    ]

    try:
        response = await registry.complete(
            messages=messages,
            provider=llm_config.provider,
            model=llm_config.model,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
        return _parse_json_response(response.text, _default_reference_analysis())
    except Exception as exc:
        logger.warning(
            "engagement_analyzer.reference_analysis_failed",
            error=str(exc),
        )
        return _default_reference_analysis()


async def analyze_icp_post_relevance(
    post_text: str,
    author_name: str,
    author_title: str,
    author_company: str,
    registry: LLMRegistry,
    llm_config: ResolvedLLMConfig,
) -> dict:
    """
    Avalia relevancia de post de ICP para comentar.

    Retorna: {is_relevant, relevance_reason, comment_angle}
    """
    messages = [
        LLMMessage(role="system", content=_ICP_RELEVANCE_SYSTEM),
        LLMMessage(
            role="user",
            content=_ICP_RELEVANCE_USER.format(
                author_name=author_name or "Autor",
                author_title=author_title or "Profissional",
                author_company=author_company or "Empresa",
                post_text=post_text[:2000],
            ),
        ),
    ]

    try:
        response = await registry.complete(
            messages=messages,
            provider=llm_config.provider,
            model=llm_config.model,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
        result = _parse_json_response(response.text, _default_icp_relevance())
        # Garante tipo correto para is_relevant
        if isinstance(result.get("is_relevant"), str):
            result["is_relevant"] = result["is_relevant"].lower() == "true"
        return result
    except Exception as exc:
        logger.warning(
            "engagement_analyzer.icp_relevance_failed",
            error=str(exc),
        )
        return _default_icp_relevance()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _parse_json_response(content: str, default: dict) -> dict:
    """Faz parse do JSON retornado pelo LLM com fallback para o default."""
    # Remove markdown code blocks se presentes
    cleaned = re.sub(r"```(?:json)?\s*", "", content).strip()
    cleaned = cleaned.replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("engagement_analyzer.json_parse_failed", raw_content=content[:200])
        return default


def _default_reference_analysis() -> dict:
    return {
        "hook_type": None,
        "pillar": None,
        "why_it_performed": None,
        "what_to_replicate": None,
    }


def _default_icp_relevance() -> dict:
    return {
        "is_relevant": False,
        "relevance_reason": "Nao foi possivel analisar o post",
        "comment_angle": "",
    }
