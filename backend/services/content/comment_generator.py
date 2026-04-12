"""
services/content/comment_generator.py

Gerador LLM de comentarios para posts de ICP no LinkedIn Engagement Scanner.

Regras obrigatorias (definidas no escopo):
  - Max 4 linhas
  - Nunca mencionar Composto Web
  - Nunca comecar com "Otimo post!" ou variantes
  - Terminar com pergunta
  - Sem em-dash (—): usar virgula ou dois-pontos
  - Palavras proibidas: inovacao, otimizacao, gestao inteligente, faz sentido?
  - Gerar 2 variacoes distintas por post
  - NUNCA postar automaticamente — so sugere

Modelo recebido dinamicamente via configuracao efetiva do tenant.
"""

from __future__ import annotations

import json
import re
from typing import cast

import structlog

from integrations.llm import LLMMessage, LLMUsageContext
from integrations.llm.registry import LLMRegistry
from services.llm_config import ResolvedLLMConfig

logger = structlog.get_logger()

CommentPayload = dict[str, str]

# ── Prompts ────────────────────────────────────────────────────────────────────

_COMMENT_SYSTEM = """
Voce e um especialista em engenharia de solucoes e automacao empresarial no Brasil.
Escreve comentarios estrategicos no LinkedIn para construir relacionamentos com decisores.

REGRAS ABSOLUTAS:
1. Maximo 4 linhas de texto
2. NUNCA mencionar a empresa pelo nome
3. NUNCA comecar com elogios genericos ("Otimo post!", "Que insight!", "Excelente!")
4. SEMPRE terminar com uma pergunta genuina e especifica
5. NENHUM em-dash (—): use virgula ou dois-pontos em vez disso
6. NUNCA usar estas palavras: inovacao, otimizacao, gestao inteligente, faz sentido?
7. Tom: tecnico, direto, coloquial inteligente — sem corporativismo

Retorne APENAS JSON valido, sem markdown, sem texto adicional.
""".strip()

_COMMENT_USER = """
Autor: {author_name} ({author_title} em {author_company})
Angulo sugerido para comentario: {comment_angle}
Estilo de escrita do comentarista: {author_voice}

POST DO LINKEDIN:
{post_text}

Gere 2 variacoes de comentario para este post.
Cada comentario deve:
- Ter no maximo 4 linhas
- Ser distinto em angulo ou abordagem da outra variacao
- Terminar com pergunta especifica sobre o conteudo do post
- Acrescentar perspectiva tecnica real (nao elogio vazio)
- Ser escrito em portugues brasileiro informal-profissional

Retorne EXATAMENTE este JSON (somente o JSON, nada mais):
{{
  "comment_1": "texto do primeiro comentario",
  "comment_2": "texto do segundo comentario"
}}
""".strip()


# ── Funcao publica ─────────────────────────────────────────────────────────────


async def generate_comments_for_post(
    post_text: str,
    author_name: str,
    author_title: str,
    author_company: str,
    comment_angle: str,
    author_voice: str,
    registry: LLMRegistry,
    llm_config: ResolvedLLMConfig,
    tenant_id: str,
    post_id: str | None = None,
) -> tuple[str, str]:
    """
    Gera dois comentarios LLM para um post de ICP.

    Retorna (comment_1, comment_2).
    Em caso de falha, retorna strings de fallback.
    Tenta ate 2 vezes antes de retornar fallback.
    """
    messages = [
        LLMMessage(role="system", content=_COMMENT_SYSTEM),
        LLMMessage(
            role="user",
            content=_COMMENT_USER.format(
                author_name=author_name or "Autor",
                author_title=author_title or "Profissional",
                author_company=author_company or "Empresa",
                comment_angle=comment_angle or "Adicionar perspectiva tecnica relevante",
                author_voice=author_voice or "direto, tecnico e coloquial",
                post_text=post_text[:2000],
            ),
        ),
    ]

    for attempt in range(1, 3):
        try:
            response = await registry.complete(
                messages=messages,
                provider=llm_config.provider,
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                usage_context=LLMUsageContext(
                    tenant_id=tenant_id,
                    module="content_engagement",
                    task_type="generate_comments",
                    feature="linkedin",
                    entity_type="engagement_post",
                    entity_id=post_id,
                ),
            )
            parsed = _parse_comment_json(response.text)
            if parsed:
                c1 = _sanitize_comment(parsed.get("comment_1", ""))
                c2 = _sanitize_comment(parsed.get("comment_2", ""))
                if c1 and c2:
                    return c1, c2
        except Exception as exc:
            logger.warning(
                "comment_generator.attempt_failed",
                attempt=attempt,
                error=str(exc),
            )

    logger.error(
        "comment_generator.all_attempts_failed",
        author_name=author_name,
    )
    fallback = _fallback_comment(author_name)
    return fallback, fallback


# ── Helpers ────────────────────────────────────────────────────────────────────


def _parse_comment_json(content: str) -> CommentPayload | None:
    """Faz parse do JSON retornado pelo LLM com fallback None."""
    cleaned = re.sub(r"```(?:json)?\s*", "", content).strip()
    cleaned = cleaned.replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            return None
        payload = cast(dict[str, object], data)
        if (
            isinstance(payload.get("comment_1"), str)
            and isinstance(payload.get("comment_2"), str)
        ):
            return {
                "comment_1": str(payload["comment_1"]),
                "comment_2": str(payload["comment_2"]),
            }
    except (json.JSONDecodeError, ValueError):
        pass
    logger.warning("comment_generator.json_parse_failed", raw_content=content[:200])
    return None


def _sanitize_comment(text: str) -> str:
    """
    Remove em-dashes e problemas pontuais no texto gerado.
    Nao altera o conteudo semantico.
    """
    if not text:
        return ""
    # Substituir em-dash por virgula + espaco
    text = text.replace("—", ",").replace("–", ",")
    return text.strip()


def _fallback_comment(author_name: str) -> str:
    name_part = author_name.split()[0] if author_name else "vc"
    return (
        f"Perspectiva interessante, {name_part}. "
        "Na pratica, qual o maior bloqueio que voce enfrenta na implementacao?"
    )
