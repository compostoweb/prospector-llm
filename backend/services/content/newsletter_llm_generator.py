"""
services/content/newsletter_llm_generator.py

Geração e melhoria de edições da Newsletter "Operação Inteligente"
via LLM. Saída sempre em JSON estruturado para alimentar o renderer.

Acesso a LLM exclusivamente via LLMRegistry.
"""

from __future__ import annotations

import json
from typing import Any, cast

from integrations.llm import LLMMessage, LLMRegistry, LLMUsageContext
from services.content.newsletter_rules import (
    NEWSLETTER_DATA_BANK,
    NEWSLETTER_FORBIDDEN_WORDS,
    NEWSLETTER_NAME,
    NEWSLETTER_OPENING_TEMPLATES,
    NEWSLETTER_READ_TIME_MIN,
    NEWSLETTER_SECTION_SPECS,
    NEWSLETTER_SUBTITLE,
    NEWSLETTER_TARGET_WORDS,
    NEWSLETTER_TOOLS_BANK,
    NEWSLETTER_TUTORIAL_BANK,
    NEWSLETTER_VISION_THEMES,
    SECTION_MINI_TUTORIAL,
    SECTION_PERGUNTA,
    SECTION_RADAR,
    SECTION_TEMA_QUINZENA,
    SECTION_VISAO_OPINIAO,
    validate_full_newsletter,
)

_DEFAULT_AUTHOR_VOICE = (
    "Adriano Valadão, CEO da Composto Web. Análise aprofundada, primeira pessoa, "
    "linguagem direta, exemplos concretos de campo. Tom de conversa de 10 minutos "
    "com um CEO. Sem hype, sem clickbait, sem motivação vazia."
)


_SYSTEM_PROMPT = """\
Você é o copywriter editorial da newsletter "{newsletter_name}", assinada por {author_name}.

NEWSLETTER: {newsletter_name} — {newsletter_subtitle}
PUBLICAÇÃO: LinkedIn Newsletter (Pulse), quinzenal.
TEMPO DE LEITURA ALVO: {read_time} minutos.
COMPRIMENTO ALVO: {min_words} a {max_words} palavras NO TOTAL.

VOZ DO AUTOR:
{author_voice}

REGRAS INVIOLÁVEIS:
- Primeira pessoa sempre ("Já entrei em...", "O que vejo na prática...")
- Cada seção começa com situação CONCRETA, nunca definição abstrata
- Parágrafos de 3-5 linhas, com linha em branco entre blocos
- NUNCA usar travessão (—). Use vírgula, ponto ou dois pontos.
- Posição clara em Visão & Opinião — Adriano nunca fica em cima do muro.
- Mini Tutorial sempre com exemplo numérico ou concreto.
- Radar: ferramenta SEMPRE com limitação honesta. Link só de domínio confiável.
- Pergunta de fechamento: específica, conecta com o tema, convida à conversa.

PALAVRAS PROIBIDAS (incluindo variações):
{forbidden_words}

ESTRUTURA DAS 5 SEÇÕES:
① Tema da Quinzena (40% — ~500 palavras): análise aprofundada de 1 caso/padrão.
② Visão & Opinião (20% — ~200 palavras): ponto de vista direto sobre o mercado.
③ Mini Tutorial (20% — ~200 palavras): 3-5 passos práticos + exemplo + impacto.
④ Radar (10% — ~100 palavras): 🔧 ferramenta + 📊 número + 🔗 leitura (opcional).
⑤ Pergunta de Fechamento (10% — ~50 palavras): pergunta pessoal sobre operação.

SAÍDA: APENAS JSON VÁLIDO no formato exato:
{{
  "title": "string — título da edição (sem o prefixo 'Edição #X')",
  "subtitle": "string opcional",
  "opening_line": "string — 1 linha provocadora abaixo da data",
  "section_tema_quinzena": {{
    "heading": "string — título curto da seção",
    "body": "string — corpo em parágrafos separados por \\n\\n"
  }},
  "section_visao_opiniao": {{
    "heading": "string",
    "body": "string"
  }},
  "section_mini_tutorial": {{
    "heading": "string — título do tutorial",
    "steps": ["passo 1", "passo 2", "passo 3"],
    "example": "string — exemplo concreto com números",
    "impact": "string — frase final sobre o impacto"
  }},
  "section_radar": {{
    "tool": {{
      "name": "string",
      "what": "string — o que a ferramenta faz",
      "when": "string — quando usar",
      "limitation": "string — limitação honesta"
    }},
    "data": {{
      "fact": "string — dado/número",
      "source": "string — fonte (ex: McKinsey)",
      "context": "string — o que significa na prática"
    }},
    "reading": null
  }},
  "section_pergunta": {{
    "body": "string — pergunta pessoal + convite a responder"
  }}
}}

Sem markdown, sem comentários, sem texto extra. APENAS JSON.\
"""


_USER_PROMPT_TEMPLATE = """\
Escreva a edição #{edition_number} da newsletter.

TEMA CENTRAL (seção ①): {theme_central}

TEMA DE VISÃO & OPINIÃO (seção ②): {vision_topic}

MINI TUTORIAL (seção ③): {tutorial_topic}

RADAR — FERRAMENTA (seção ④): {radar_tool}
{radar_tool_details}

RADAR — DADO (seção ④): {radar_data_fact}
Fonte: {radar_data_source} | Contexto: {radar_data_context}

EXEMPLOS DE ABERTURA (escolha o tom mais apropriado, não copie literalmente):
{opening_templates}

Lembre: retorne APENAS o JSON estruturado, sem markdown.\
"""


_IMPROVE_SYSTEM_PROMPT = """\
Você é o editor da newsletter "{newsletter_name}".
Sua tarefa é reescrever UMA seção específica da edição seguindo a instrução do autor.

VOZ:
{author_voice}

REGRAS:
- Primeira pessoa, situação concreta, parágrafos curtos.
- NUNCA usar travessão (—).
- Palavras proibidas: {forbidden_words}
- Mantenha a voz e tom do autor.
- Comprimento alvo da seção: {min_words}-{max_words} palavras.

RETORNE APENAS o JSON da seção (mesmo formato da seção original) — sem markdown,
sem prefácio, sem explicações.\
"""


_IMPROVE_USER_PROMPT_TEMPLATE = """\
SEÇÃO: {section_label}
INSTRUÇÃO: {instruction}

CONTEÚDO ATUAL (JSON):
{current_json}

Retorne APENAS o JSON reescrito da seção.\
"""


def _format_forbidden_words() -> str:
    return ", ".join(NEWSLETTER_FORBIDDEN_WORDS)


def _format_opening_templates() -> str:
    return "\n".join(
        f"- ({t['kind']}) {t['template']}" for t in NEWSLETTER_OPENING_TEMPLATES
    )


def _build_usage_context(
    *,
    tenant_id: str,
    task_type: str,
    model: str,
) -> LLMUsageContext:
    return LLMUsageContext(
        tenant_id=tenant_id,
        module="content_hub",
        task_type=task_type,
        feature="newsletter",
        metadata={"model_requested": model},
    )


def _safe_json_parse(content: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return cast(dict[str, Any], payload)
    return None


# ── API publica ──────────────────────────────────────────────────────


async def generate_newsletter_draft(
    *,
    edition_number: int,
    theme_central: str,
    vision_topic: str,
    tutorial_topic: str,
    radar_tool: dict[str, str] | str,
    radar_data: dict[str, str],
    registry: LLMRegistry,
    tenant_id: str,
    provider: str,
    model: str,
    temperature: float = 0.6,
    max_tokens: int = 4096,
    author_name: str = "Adriano Valadão",
    author_voice: str | None = None,
) -> dict[str, Any]:
    """
    Gera o rascunho completo de uma edição em JSON estruturado.

    Returns:
      payload dict com chaves: title, subtitle, opening_line,
      section_tema_quinzena, section_visao_opiniao, section_mini_tutorial,
      section_radar, section_pergunta. Inclui também 'violations' (list[str]).
    """
    voice = author_voice or _DEFAULT_AUTHOR_VOICE

    if isinstance(radar_tool, dict):
        tool_name = radar_tool.get("name") or ""
        tool_details = (
            f"O que faz: {radar_tool.get('what', '')}. "
            f"Quando usar: {radar_tool.get('when', '')}. "
            f"Limitação: {radar_tool.get('limitation', '')}."
        )
    else:
        tool_name = str(radar_tool)
        # Buscar no banco
        match = next(
            (t for t in NEWSLETTER_TOOLS_BANK if t["name"].lower() == tool_name.lower()),
            None,
        )
        if match:
            tool_details = (
                f"O que faz: {match['what']}. Quando usar: {match['when']}. "
                f"Limitação: {match['limitation']}."
            )
        else:
            tool_details = "(autor decide o que faz, quando usar e limitação)"

    system_prompt = _SYSTEM_PROMPT.format(
        newsletter_name=NEWSLETTER_NAME,
        newsletter_subtitle=NEWSLETTER_SUBTITLE,
        author_name=author_name,
        author_voice=voice,
        read_time=NEWSLETTER_READ_TIME_MIN,
        min_words=NEWSLETTER_TARGET_WORDS[0],
        max_words=NEWSLETTER_TARGET_WORDS[1],
        forbidden_words=_format_forbidden_words(),
    )

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        edition_number=edition_number,
        theme_central=theme_central,
        vision_topic=vision_topic,
        tutorial_topic=tutorial_topic,
        radar_tool=tool_name,
        radar_tool_details=tool_details,
        radar_data_fact=radar_data.get("fact", ""),
        radar_data_source=radar_data.get("source", ""),
        radar_data_context=radar_data.get("context", ""),
        opening_templates=_format_opening_templates(),
    )

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    response = await registry.complete(
        messages=messages,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
        usage_context=_build_usage_context(
            tenant_id=tenant_id,
            task_type="generate_newsletter_draft",
            model=model,
        ),
    )

    payload = _safe_json_parse(response.text) or {}
    violations = validate_full_newsletter(payload)
    payload["violations"] = violations
    return payload


_SECTION_KEY_MAP = {
    SECTION_TEMA_QUINZENA: "section_tema_quinzena",
    SECTION_VISAO_OPINIAO: "section_visao_opiniao",
    SECTION_MINI_TUTORIAL: "section_mini_tutorial",
    SECTION_RADAR: "section_radar",
    SECTION_PERGUNTA: "section_pergunta",
}


async def improve_newsletter_section(
    *,
    section_id: str,
    current_payload: dict[str, Any],
    instruction: str,
    registry: LLMRegistry,
    tenant_id: str,
    provider: str,
    model: str,
    temperature: float = 0.5,
    max_tokens: int = 2048,
    author_voice: str | None = None,
) -> dict[str, Any]:
    """
    Reescreve UMA seção específica conforme instrução.

    Returns:
      novo conteúdo da seção (mesmo shape de section_<id> no payload).
    """
    if section_id not in _SECTION_KEY_MAP:
        raise ValueError(f"Seção desconhecida: {section_id}")

    spec = NEWSLETTER_SECTION_SPECS[section_id]
    voice = author_voice or _DEFAULT_AUTHOR_VOICE

    system_prompt = _IMPROVE_SYSTEM_PROMPT.format(
        newsletter_name=NEWSLETTER_NAME,
        author_voice=voice,
        forbidden_words=_format_forbidden_words(),
        min_words=spec["target_words"][0],
        max_words=spec["target_words"][1],
    )

    user_prompt = _IMPROVE_USER_PROMPT_TEMPLATE.format(
        section_label=spec["label"],
        instruction=instruction,
        current_json=json.dumps(current_payload, ensure_ascii=False, indent=2),
    )

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    response = await registry.complete(
        messages=messages,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
        usage_context=_build_usage_context(
            tenant_id=tenant_id,
            task_type=f"improve_newsletter_{section_id}",
            model=model,
        ),
    )

    parsed = _safe_json_parse(response.text)
    if parsed is None:
        raise ValueError("LLM não retornou JSON válido para a seção.")
    return parsed


def get_banks_payload() -> dict[str, Any]:
    """
    Retorna todos os bancos de referencia para popular dropdowns no frontend.
    """
    from services.content.newsletter_rules import (
        NEWSLETTER_PLANNED_EDITIONS,
        NEWSLETTER_PUBLISHED_HISTORY,
        NEWSLETTER_THEMES_CENTRAL,
    )

    return {
        "themes_central": NEWSLETTER_THEMES_CENTRAL,
        "vision_themes": NEWSLETTER_VISION_THEMES,
        "tutorials": NEWSLETTER_TUTORIAL_BANK,
        "tools": NEWSLETTER_TOOLS_BANK,
        "data_points": NEWSLETTER_DATA_BANK,
        "opening_templates": NEWSLETTER_OPENING_TEMPLATES,
        "published_history": NEWSLETTER_PUBLISHED_HISTORY,
        "planned_editions": NEWSLETTER_PLANNED_EDITIONS,
    }
