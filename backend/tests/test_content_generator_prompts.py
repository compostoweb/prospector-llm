"""
tests/test_content_generator_prompts.py

Verifica que o system prompt do gerador menciona os 9 ganchos canônicos
da skill 05-conteudo-linkedin (atualizada) e contém os blocos novos:
- Mapa hook→pilar
- Comprimentos por formato
- "O QUE NÃO REPLICAR"
"""

from __future__ import annotations

from services.content.llm_generator import (
    HOOK_CONTEXT,
    HOOK_DEFAULT_BY_PILLAR,
    HOOK_LENGTH_HINTS,
    _render_system_prompt,
)

CANONICAL_HOOKS = {
    "loop_open",
    "contrarian",
    "identification",
    "contrast_direct",
    "data_isolated",
    "short_reflection",
    "personal_story",
    "shortcut",
    "dm_offer",
}


def test_hook_context_has_all_9_canonical_hooks() -> None:
    for hook in CANONICAL_HOOKS:
        assert hook in HOOK_CONTEXT, f"HOOK_CONTEXT faltando: {hook}"


def test_hook_context_keeps_legacy_aliases() -> None:
    # benefit e data continuam para retrocompat com posts antigos.
    assert "benefit" in HOOK_CONTEXT
    assert "data" in HOOK_CONTEXT


def test_hook_default_by_pillar_covers_all_pillars() -> None:
    assert set(HOOK_DEFAULT_BY_PILLAR.keys()) == {"vision", "authority", "case"}
    for pillar, hooks in HOOK_DEFAULT_BY_PILLAR.items():
        assert hooks, f"pilar {pillar} sem hooks default"
        for h in hooks:
            assert h in CANONICAL_HOOKS


def test_hook_length_hints_cover_canonical_hooks() -> None:
    for hook in CANONICAL_HOOKS:
        assert hook in HOOK_LENGTH_HINTS, f"HOOK_LENGTH_HINTS faltando: {hook}"


def test_system_prompt_lists_all_9_hooks() -> None:
    prompt = _render_system_prompt(
        author_name="Adriano",
        author_voice="Voz fictícia para teste.",
        references=[],
    )
    for hook in CANONICAL_HOOKS:
        assert hook in prompt, f"system prompt não menciona {hook}"


def test_system_prompt_has_hook_pillar_map() -> None:
    prompt = _render_system_prompt(
        author_name="Adriano",
        author_voice="Voz fictícia.",
        references=[],
    )
    assert "QUAL GANCHO POR PILAR" in prompt
    # Blocos por pilar com hooks corretos
    assert "vision" in prompt and "authority" in prompt and "case" in prompt


def test_system_prompt_has_what_not_to_replicate_block() -> None:
    prompt = _render_system_prompt(
        author_name="Adriano",
        author_voice="Voz fictícia.",
        references=[],
    )
    assert "O QUE NÃO REPLICAR" in prompt
    assert "saí do CLT" in prompt or "religioso" in prompt


def test_system_prompt_has_new_forbidden_words() -> None:
    prompt = _render_system_prompt(
        author_name="Adriano",
        author_voice="Voz fictícia.",
        references=[],
    )
    assert "Agende uma reunião" in prompt
    assert "inovador" in prompt
    assert "Clique no link" in prompt


def test_system_prompt_no_unfilled_placeholders() -> None:
    prompt = _render_system_prompt(
        author_name="Adriano",
        author_voice="Voz fictícia.",
        references=[],
    )
    # Garantia de que removemos os placeholders ideal_min/ideal_max
    assert "{ideal_min}" not in prompt
    assert "{ideal_max}" not in prompt
    assert "{max_chars}" not in prompt
