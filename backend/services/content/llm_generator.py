"""
services/content/llm_generator.py

Geração e melhoria de posts para LinkedIn via LLM.

Fluxo:
  1. Monta o system prompt com voz do autor e exemplos few-shot.
  2. Monta o user prompt com o tema, pilar, tipo de gancho e restrições.
  3. Chama registry.complete() N vezes para N variações.
  4. Valida cada variação com rules.validate_post().

Nunca importa AsyncOpenAI ou genai diretamente —
aceso exclusivamente via LLMRegistry injetado.
"""

from __future__ import annotations

import json
from typing import TypedDict, cast

from integrations.llm import LLMMessage, LLMRegistry, LLMUsageContext
from services.content.rules import (
    IDEAL_MAX_CHARS,
    IDEAL_MIN_CHARS,
    LINKEDIN_MAX_CHARS,
    count_characters,
    validate_post,
)


class ReferenceExample(TypedDict):
    body: str
    hook_type: str | None
    pillar: str | None


class GeneratedVariation(TypedDict):
    text: str
    character_count: int
    hook_type_used: str
    violations: list[str]


class LeadMagnetPromptContext(TypedDict, total=False):
    title: str
    description: str | None
    cta_text: str | None
    type: str
    distribution_type: str | None
    trigger_word: str | None

# ── Mapeamento de pilares ─────────────────────────────────────────────

PILLAR_CONTEXT: dict[str, str] = {
    "authority": (
        "Posicionamento como autoridade no setor. "
        "Compartilhe ponto de vista diferenciado, opinião contrária ao senso comum, "
        "ou aprendizado prático de alto impacto."
    ),
    "case": (
        "Estudo de caso real ou situação concreta. "
        "Conte uma história com começo, meio e fim. "
        "Mostre resultado mensurável quando possível."
    ),
    "vision": (
        "Visão de futuro ou tendência do setor. "
        "Inspire com perspectiva ousada mas fundamentada. "
        "Conecte com implicações práticas para o leitor."
    ),
}

HOOK_CONTEXT: dict[str, str] = {
    # Ganchos canônicos da skill 05-conteudo-linkedin (atualizada).
    "loop_open": (
        "Abre enigma ou promessa que só se resolve lendo o post inteiro. "
        "Use para casos com payoff em mid/late."
    ),
    "contrarian": (
        "Desafia o senso comum — começa afirmando o contrário do óbvio. "
        "Pede argumentação consistente para sustentar a posição."
    ),
    "identification": (
        "Descreve a dor exata do leitor para ele pensar 'é isso!' "
        "Linguagem específica do dia-a-dia do tomador de decisão."
    ),
    "contrast_direct": (
        "Estrutura A vs B em 2-4 linhas paralelas e curtas. "
        "Mediana de ER mais alta de todos os formatos. Texto enxuto, alto contraste."
    ),
    "data_isolated": (
        "Ancora o post em um dado concreto que surpreende, isolado na 1ª linha "
        "(ex.: '83% dos projetos de IA falham.'). Resto desenvolve por que."
    ),
    "short_reflection": (
        "Reflexão curta e direta (150-400 chars). Uma observação afiada, "
        "sem desenvolvimento longo. Mediana ER ~14%."
    ),
    "personal_story": (
        "Narrativa em 1ª pessoa contando experiência real. "
        "Picos de ER mais altos. Começo, meio, fim — e aprendizado."
    ),
    "shortcut": (
        "Promete uma rota mais curta para um resultado desejado. "
        "Use somente quando há método/passos concretos no corpo."
    ),
    "dm_offer": (
        "Oferta de material/diagnóstico via DM ou comentário, no máximo 1x/mês. "
        "Lead qualificado — exige post anterior de autoridade no mesmo tema."
    ),
    # Hooks legados — alias para retrocompat (não citar nos prompts)
    "benefit": "Entrega o principal benefício ou aprendizado já na primeira linha.",
    "data": "Ancora o post em dado concreto que surpreende.",
}

# Mapa hook → pilar default (skill 05). Usado quando hook_type ausente.
# A primeira opção da lista é a sugestão default para o pilar.
HOOK_DEFAULT_BY_PILLAR: dict[str, list[str]] = {
    "vision": ["contrarian", "contrast_direct", "short_reflection"],
    "authority": ["loop_open", "data_isolated", "shortcut"],
    "case": ["personal_story", "loop_open", "contrast_direct"],
}

# Range textual por gancho (espelha rules.IDEAL_RANGES_BY_HOOK; usado no prompt).
HOOK_LENGTH_HINTS: dict[str, str] = {
    "short_reflection": "150-400 chars (curto e afiado)",
    "contrast_direct": "300-600 chars (paralelos enxutos)",
    "contrarian": "600-900 chars (argumentação curta)",
    "identification": "600-900 chars (dor específica)",
    "loop_open": "900-1500 chars (autoridade/case)",
    "data_isolated": "900-1500 chars (autoridade/case)",
    "shortcut": "900-1500 chars (método em passos)",
    "personal_story": "800-1500 chars (narrativa)",
    "dm_offer": "400-900 chars (oferta direta)",
}

# ── Templates de prompt ───────────────────────────────────────────────

_SYSTEM_PROMPT_TEMPLATE = """\
Você é um especialista em criação de conteúdo para LinkedIn B2B.
Sua tarefa é escrever posts para {author_name}.

SOBRE O AUTOR:
{author_voice}

PÚBLICO-ALVO: CEOs, CFOs, COOs, CTOs de empresas com 100 a 1.000 funcionários.

REGRAS INVIOLÁVEIS DE FORMATO:
- Parágrafos curtos: máx 3 linhas
- Linha em branco entre cada bloco de texto
- 1 post = 1 ideia. Nunca duas ideias no mesmo post.
- Comprimento ajustado ao gancho (ver tabela abaixo). Máx LinkedIn: {max_chars}
- Hashtags: 3 a 5 no final, nunca no meio do texto

PALAVRAS PROIBIDAS (nunca usar — incluindo variações):
inovação, inovador, inovar, otimização, gestão inteligente, reduza custos,
aumente eficiência, impacto nos seus lucros, faz sentido?, transformação digital,
solução robusta, de forma eficiente, travessão.

CTAs PROIBIDOS (nunca usar):
"Entre em contato", "Agende uma reunião", "Tem 15 minutos?", "Clique no link".
CTA permitido: pergunta leve, reflexão ou convite à conversa nos comentários.

TIPOS DE GANCHO (hook) — 9 formatos canônicos:
- loop_open: abre enigma que só fecha no post (autoridade/case, 900-1500)
- contrarian: desafia o senso comum (vision, 600-900)
- identification: descreve a dor com precisão (600-900)
- contrast_direct: estrutura A vs B em paralelos curtos (vision, 300-600) — maior ER mediano
- data_isolated: dado isolado na 1ª linha que surpreende (authority, 900-1500)
- short_reflection: reflexão afiada (vision, 150-400)
- personal_story: narrativa em 1ª pessoa (case, 800-1500) — picos de ER
- shortcut: rota mais curta com método em passos (authority, 900-1500)
- dm_offer: oferta de DM/comentário (uso máx 1x/mês, exige autoridade prévia, 400-900)

QUAL GANCHO POR PILAR (default quando não especificado):
- vision   → contrarian | contrast_direct | short_reflection
- authority → loop_open | data_isolated | shortcut
- case     → personal_story | loop_open | contrast_direct

ESTRUTURA ESPERADA:
[Linha 1: GANCHO — curta, direta, para o scroll]
[Linha 2: desenvolve a tensão]

[CORPO em blocos de 1-3 linhas com linha em branco entre eles]
[Coisas CONCRETAS, nunca abstratas]

[FECHAMENTO — 1-2 linhas com conclusão ou aprendizado]

[CTA — pergunta leve sobre a operação/empresa do leitor]



#hashtag1 #hashtag2 #hashtag3

O QUE NÃO REPLICAR (estilos fora da voz do autor):
- Nada de tom religioso, espiritual ou motivacional vazio.
- Nada de "saí do CLT", jornada de empreendedor solo ou storytelling de coach.
- Nada de listas genéricas de ferramentas sem contexto de uso real.
- Nada de promessas exageradas ("3x mais resultado", "dobre seu faturamento").
- Nada de tom guru, "verdade que ninguém te conta", clickbait.
{few_shot_block}
Retorne APENAS o texto do post. Sem explicações, sem prefácio, sem aspas.\
"""

_FEW_SHOT_BLOCK_TEMPLATE = """\

EXEMPLOS DE REFERÊNCIA (posts de alto engajamento para calibrar estilo):
{examples}
---
"""

_FEW_SHOT_EXAMPLE_TEMPLATE = """\
--- EXEMPLO {index} ({hook_type} | {pillar}) ---
{body}
--- FIM DO EXEMPLO {index} ---
"""

_USER_PROMPT_TEMPLATE = """\
Escreva um post sobre o seguinte tema:

TEMA: {theme}
PILAR: {pillar_label} — {pillar_description}
TIPO DE GANCHO: {hook_label} — {hook_description}
OBJETIVO: {content_goal_label}

{goal_block}

Lembre-se: retorne APENAS o texto do post, sem nenhuma explicação adicional.\
"""

_MULTI_VARIATION_PROMPT_SUFFIX = """\

Gere EXATAMENTE {variations} variações distintas do mesmo tema.
Retorne APENAS JSON válido neste formato:
{{
    "variations": [
        "texto da variação 1",
        "texto da variação 2"
    ]
}}
Sem markdown, sem comentários, sem texto extra.\
"""

_IMPROVE_SYSTEM_PROMPT = """\
Você é um especialista em edição de conteúdo para LinkedIn B2B.
Sua tarefa é melhorar o post fornecido seguindo a instrução exata do autor.

SOBRE O AUTOR:
{author_voice}

REGRAS INVIOLÁVEIS:
- Mantenha a voz e o estilo do autor
- Parágrafos curtos (máx 3 linhas) com linha em branco entre blocos
- Comprimento ideal: {ideal_min} a {ideal_max} caracteres (máx: {max_chars})
- Palavras proibidas: inovação, inovador, inovar, otimização, gestão inteligente,
  reduza custos, aumente eficiência, impacto nos seus lucros, faz sentido?,
  transformação digital, solução robusta, de forma eficiente, travessão.
- CTAs proibidos: "Entre em contato", "Agende uma reunião", "Tem 15 minutos?",
  "Clique no link". Use pergunta leve ou convite à conversa.
- Não use tom religioso, motivacional vazio, "saí do CLT" ou listas genéricas.

Retorne APENAS o texto do post reescrito. Sem explicações, sem prefácio, sem aspas.\
"""

_IMPROVE_USER_PROMPT_TEMPLATE = """\
INSTRUÇÃO DE MELHORIA: {instruction}

POST ATUAL:
{body}

Retorne APENAS o texto do post melhorado.\
"""


# ── Helpers internos ──────────────────────────────────────────────────

def _build_few_shot_block(references: list[ReferenceExample]) -> str:
    """Monta bloco few-shot com posts de referência."""
    if not references:
        return ""
    examples = ""
    for i, ref in enumerate(references[:3], start=1):
        examples += _FEW_SHOT_EXAMPLE_TEMPLATE.format(
            index=i,
            hook_type=ref.get("hook_type") or "—",
            pillar=ref.get("pillar") or "—",
            body=(ref.get("body", "") or "")[:900],
        )
    return _FEW_SHOT_BLOCK_TEMPLATE.format(examples=examples)


def _build_usage_context(
    *,
    tenant_id: str,
    task_type: str,
    feature: str | None,
    model: str,
) -> LLMUsageContext:
    return LLMUsageContext(
        tenant_id=tenant_id,
        module="content_hub",
        task_type=task_type,
        feature=feature,
        metadata={"model_requested": model},
    )


def _parse_variations_json(content: str, expected_count: int) -> list[str] | None:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    payload_dict = cast(dict[str, object], payload)
    raw_variations = payload_dict.get("variations")
    if not isinstance(raw_variations, list):
        return None
    variation_items = cast(list[object], raw_variations)

    cleaned = [str(item).strip() for item in variation_items if str(item).strip()]
    if len(cleaned) < expected_count:
        return None
    return cleaned[:expected_count]


def _render_system_prompt(
    author_name: str,
    author_voice: str,
    references: list[ReferenceExample],
) -> str:
    few_shot_block = _build_few_shot_block(references)
    return _SYSTEM_PROMPT_TEMPLATE.format(
        author_name=author_name,
        author_voice=author_voice,
        max_chars=LINKEDIN_MAX_CHARS,
        few_shot_block=few_shot_block,
    )


def _build_goal_block(
    *,
    content_goal: str,
    lead_magnet_context: LeadMagnetPromptContext | None,
) -> tuple[str, str]:
    if content_goal != "lead_magnet_launch" or not lead_magnet_context:
        return (
            "Post editorial para reforçar autoridade e gerar conversa qualificada.",
            (
                "Desenvolva a ideia de forma nativa para LinkedIn. "
                "O foco principal é entregar valor e sustentar autoridade no tema."
            ),
        )

    distribution_type = lead_magnet_context.get("distribution_type") or "comment"
    trigger_word = lead_magnet_context.get("trigger_word") or "mapa"
    cta_text = lead_magnet_context.get("cta_text") or f"Comente '{trigger_word}'"

    distribution_instruction = {
        "comment": (
            f"Feche o post convidando a pessoa a comentar '{trigger_word}' para receber o material."
        ),
        "dm": (
            f"Feche o post convidando a pessoa a pedir '{trigger_word}' por direct."
        ),
        "link_bio": "Feche o post convidando a acessar o link da bio ou comentário fixado.",
    }.get(distribution_type, "Feche o post com um CTA claro e natural para receber o material.")

    return (
        "Lançamento de lead magnet com CTA nativo, sem parecer anúncio.",
        (
            f"LEAD MAGNET: {lead_magnet_context.get('title', '')}\n"
            f"TIPO: {lead_magnet_context.get('type', '')}\n"
            f"DESCRIÇÃO: {lead_magnet_context.get('description') or 'Não informada.'}\n"
            f"CTA BASE: {cta_text}\n"
            "REGRAS ADICIONAIS:\n"
            "- Construa tensão ou curiosidade antes do CTA.\n"
            "- Cite o lead magnet de forma concreta, sem tom publicitário.\n"
            "- Mostre o problema que o material ajuda a resolver.\n"
            f"- {distribution_instruction}\n"
            "- Evite parecer venda direta ou promessa exagerada."
        ),
    )


# ── Funções públicas ─────────────────────────────────────────────────

async def generate_post(
    *,
    theme: str,
    pillar: str,
    hook_type: str | None,
    author_name: str,
    author_voice: str,
    variations: int,
    references: list[ReferenceExample],
    registry: LLMRegistry,
    tenant_id: str,
    provider: str,
    model: str,
    temperature: float,
    max_tokens: int = 1024,
    content_goal: str = "editorial",
    lead_magnet_context: LeadMagnetPromptContext | None = None,
) -> list[GeneratedVariation]:
    """
    Gera N variações de post para LinkedIn sobre um dado tema.

    Retorna lista de dicts com:
      - text: str
      - character_count: int
      - hook_type_used: str
      - violations: list[str]
    """
    resolved_hook = hook_type or HOOK_DEFAULT_BY_PILLAR.get(pillar, ["loop_open"])[0]
    system_prompt = _render_system_prompt(author_name, author_voice, references)
    content_goal_label, goal_block = _build_goal_block(
        content_goal=content_goal,
        lead_magnet_context=lead_magnet_context,
    )
    hook_description = HOOK_CONTEXT.get(resolved_hook, resolved_hook)
    length_hint = HOOK_LENGTH_HINTS.get(resolved_hook)
    if length_hint:
        hook_description = f"{hook_description} | Comprimento esperado: {length_hint}."
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        theme=theme,
        pillar_label=pillar,
        pillar_description=PILLAR_CONTEXT.get(pillar, pillar),
        hook_label=resolved_hook,
        hook_description=hook_description,
        content_goal_label=content_goal_label,
        goal_block=goal_block,
    )

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    results: list[GeneratedVariation] = []
    if variations > 1:
        batched_messages = [
            messages[0],
            LLMMessage(
                role="user",
                content=user_prompt + "\n\n" + _MULTI_VARIATION_PROMPT_SUFFIX.format(variations=variations),
            ),
        ]
        response = await registry.complete(
            messages=batched_messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=min(max_tokens * variations, 1800),
            json_mode=True,
            usage_context=_build_usage_context(
                tenant_id=tenant_id,
                task_type="generate_post_batch",
                feature=content_goal,
                model=model,
            ),
        )
        parsed_variations = _parse_variations_json(response.text, variations)
        if parsed_variations:
            for text in parsed_variations:
                results.append(
                    {
                        "text": text,
                        "character_count": count_characters(text),
                        "hook_type_used": resolved_hook,
                        "violations": validate_post(text, hook_type=resolved_hook),
                    }
                )
            return results

    for _ in range(variations):
        response = await registry.complete(
            messages=messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            usage_context=_build_usage_context(
                tenant_id=tenant_id,
                task_type="generate_post",
                feature=content_goal,
                model=model,
            ),
        )
        text = response.text.strip()
        results.append(
            {
                "text": text,
                "character_count": count_characters(text),
                "hook_type_used": resolved_hook,
                "violations": validate_post(text, hook_type=resolved_hook),
            }
        )

    return results


async def improve_post(
    *,
    body: str,
    instruction: str,
    author_name: str,
    author_voice: str,
    registry: LLMRegistry,
    tenant_id: str,
    provider: str,
    model: str,
    temperature: float = 0.6,
    max_tokens: int = 1024,
) -> str:
    """
    Melhora um post existente com base em uma instrução específica.

    Retorna o texto melhorado (string pura).
    """
    system_prompt = _IMPROVE_SYSTEM_PROMPT.format(
        author_voice=author_voice,
        author_name=author_name,
        ideal_min=IDEAL_MIN_CHARS,
        ideal_max=IDEAL_MAX_CHARS,
        max_chars=LINKEDIN_MAX_CHARS,
    )
    user_prompt = _IMPROVE_USER_PROMPT_TEMPLATE.format(
        instruction=instruction,
        body=body,
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
        usage_context=_build_usage_context(
            tenant_id=tenant_id,
            task_type="improve_post",
            feature="editorial",
            model=model,
        ),
    )
    return response.text.strip()
