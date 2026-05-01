"""
tests/test_content_rules.py

Cobre as regras de validação de posts (Phase A — sync skill 05).
- FORBIDDEN_WORDS expandido (variações de "inovação", CTAs comerciais).
- IDEAL_RANGES_BY_HOOK + recommend_range.
- validate_post() com hook opcional gera aviso fora do range.
"""

from __future__ import annotations

import pytest

from services.content.rules import (
    FORBIDDEN_WORDS,
    IDEAL_MAX_CHARS,
    IDEAL_MIN_CHARS,
    IDEAL_RANGES_BY_HOOK,
    LINKEDIN_MAX_CHARS,
    recommend_range,
    validate_post,
)

# ── FORBIDDEN_WORDS ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "term",
    [
        "inovação",
        "inovador",
        "inovar",
        "otimização",
        "aumente eficiência",
        "impacto nos seus lucros",
        "Entre em contato",
        "Agende uma reunião",
        "Tem 15 minutos?",
        "Clique no link",
    ],
)
def test_forbidden_words_includes_new_terms(term: str) -> None:
    assert term in FORBIDDEN_WORDS


def test_validate_post_detects_new_cta_terms() -> None:
    text = "Texto qualquer.\n\nAgende uma reunião comigo amanhã."
    violations = validate_post(text)
    assert any("Agende uma reunião" in v for v in violations)


def test_validate_post_detects_inovador_variation() -> None:
    text = "Somos um time inovador resolvendo problemas reais."
    violations = validate_post(text)
    assert any("inovador" in v for v in violations)


def test_validate_post_clean_text_returns_empty() -> None:
    text = (
        "Trabalhei 22 anos em TI antes de fundar a Composto Web.\n\n"
        "Aprendi uma coisa: método vale mais que ferramenta.\n\n"
        "Qual a sua experiência com isso?\n\n#linkedin #b2b #ti"
    )
    assert validate_post(text) == []


# ── Tamanho máximo LinkedIn ───────────────────────────────────────────


def test_validate_post_flags_above_max() -> None:
    text = "a" * (LINKEDIN_MAX_CHARS + 50)
    violations = validate_post(text)
    assert any("excede o limite" in v for v in violations)


# ── recommend_range ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "hook,expected",
    [
        ("short_reflection", (150, 400)),
        ("contrast_direct", (300, 600)),
        ("contrarian", (600, 900)),
        ("identification", (600, 900)),
        ("loop_open", (900, 1500)),
        ("data_isolated", (900, 1500)),
        ("shortcut", (900, 1500)),
        ("personal_story", (800, 1500)),
        ("dm_offer", (400, 900)),
    ],
)
def test_recommend_range_known_hooks(
    hook: str, expected: tuple[int, int]
) -> None:
    assert recommend_range(hook) == expected
    assert IDEAL_RANGES_BY_HOOK[hook] == expected


def test_recommend_range_unknown_hook_returns_default() -> None:
    assert recommend_range(None) == (IDEAL_MIN_CHARS, IDEAL_MAX_CHARS)
    assert recommend_range("not_a_hook") == (IDEAL_MIN_CHARS, IDEAL_MAX_CHARS)


def test_recommend_range_legacy_aliases() -> None:
    # benefit / data são aliases legados — devem mapear para faixa de autoridade.
    assert recommend_range("benefit") == (900, 1500)
    assert recommend_range("data") == (900, 1500)


# ── validate_post com hook ────────────────────────────────────────────


def test_validate_post_warns_when_below_hook_range() -> None:
    text = "a" * 100  # bem abaixo de 150 (short_reflection)
    violations = validate_post(text, hook_type="short_reflection")
    assert any("Aviso" in v and "short_reflection" in v for v in violations)


def test_validate_post_warns_when_above_hook_range() -> None:
    text = "a" * 700  # acima de 600 (contrast_direct)
    violations = validate_post(text, hook_type="contrast_direct")
    assert any("Aviso" in v and "contrast_direct" in v for v in violations)


def test_validate_post_no_warning_when_within_hook_range() -> None:
    text = "a" * 1000  # dentro de 900-1500 (loop_open)
    violations = validate_post(text, hook_type="loop_open")
    # Nenhuma violation de range; texto não tem palavras proibidas
    assert violations == []


def test_validate_post_no_warning_when_hook_omitted() -> None:
    text = "a" * 100
    # Sem hook: não há warning de range (texto curto e sem palavras proibidas)
    assert validate_post(text) == []
