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

from typing import TypedDict

from integrations.llm import LLMMessage, LLMRegistry
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
    "loop_open": "Abre enigma ou promessa que só se resolve lendo o post inteiro.",
    "contrarian": "Desafia o senso comum — começa afirmando o contrário do óbvio.",
    "identification": "Descreve a dor exata do leitor para ele pensar 'é isso!'",
    "shortcut": "Promete uma rota mais curta para um resultado desejado.",
    "benefit": "Entrega o principal benefício ou aprendizado já na primeira linha.",
    "data": "Ancora o post em dado concreto que surpreende.",
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
- Comprimento ideal: {ideal_min} a {ideal_max} caracteres (máx LinkedIn: {max_chars})
- Hashtags: 3 a 5 no final, nunca no meio do texto

PALAVRAS PROIBIDAS (nunca usar):
inovação, otimização, gestão inteligente, reduza custos, faz sentido?,
transformação digital, solução robusta, de forma eficiente, travessão

CTA: pergunta leve ou reflexão. Nunca pedido de reunião direto.

TIPOS DE GANCHO (hook):
- loop_open: abre enigma que só fecha no post
- contrarian: desafia o senso comum
- identification: descreve a dor com precisão para o leitor pensar "é isso!"
- shortcut: promessa de rota mais curta
- benefit: entrega o valor logo de cara
- data: ancora o post em dado concreto

ESTRUTURA ESPERADA:
[Linha 1: GANCHO — curta, direta, para o scroll]
[Linha 2: desenvolve a tensão]

[CORPO em blocos de 1-3 linhas com linha em branco entre eles]
[Coisas CONCRETAS, nunca abstratas]

[FECHAMENTO — 1-2 linhas com conclusão ou aprendizado]

[CTA — pergunta leve]
#hashtag1 #hashtag2 #hashtag3
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

Lembre-se: retorne APENAS o texto do post, sem nenhuma explicação adicional.\
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
- Palavras proibidas: inovação, otimização, gestão inteligente, reduza custos,
  faz sentido?, transformação digital, solução robusta, de forma eficiente, travessão

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
    for i, ref in enumerate(references[:5], start=1):
        examples += _FEW_SHOT_EXAMPLE_TEMPLATE.format(
            index=i,
            hook_type=ref.get("hook_type") or "—",
            pillar=ref.get("pillar") or "—",
            body=ref.get("body", ""),
        )
    return _FEW_SHOT_BLOCK_TEMPLATE.format(examples=examples)


def _render_system_prompt(
    author_name: str,
    author_voice: str,
    references: list[ReferenceExample],
) -> str:
    few_shot_block = _build_few_shot_block(references)
    return _SYSTEM_PROMPT_TEMPLATE.format(
        author_name=author_name,
        author_voice=author_voice,
        ideal_min=IDEAL_MIN_CHARS,
        ideal_max=IDEAL_MAX_CHARS,
        max_chars=LINKEDIN_MAX_CHARS,
        few_shot_block=few_shot_block,
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
    provider: str,
    model: str,
    temperature: float,
    max_tokens: int = 1024,
) -> list[GeneratedVariation]:
    """
    Gera N variações de post para LinkedIn sobre um dado tema.

    Retorna lista de dicts com:
      - text: str
      - character_count: int
      - hook_type_used: str
      - violations: list[str]
    """
    resolved_hook = hook_type or "benefit"
    system_prompt = _render_system_prompt(author_name, author_voice, references)
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        theme=theme,
        pillar_label=pillar,
        pillar_description=PILLAR_CONTEXT.get(pillar, pillar),
        hook_label=resolved_hook,
        hook_description=HOOK_CONTEXT.get(resolved_hook, resolved_hook),
    )

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    results: list[GeneratedVariation] = []
    for _ in range(variations):
        response = await registry.complete(
            messages=messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.text.strip()
        results.append(
            {
                "text": text,
                "character_count": count_characters(text),
                "hook_type_used": resolved_hook,
                "violations": validate_post(text),
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
    )
    return response.text.strip()
