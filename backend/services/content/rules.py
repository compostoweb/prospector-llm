"""
services/content/rules.py

Regras de validação para posts do Content Hub.

Caracteres: LinkedIn aceita até 3.000; faixa ideal 900–1.500.
Palavras proibidas: termos banais de marketing B2B.
"""

from __future__ import annotations

# ── Limites de caracteres ─────────────────────────────────────────────

LINKEDIN_MAX_CHARS: int = 3000
IDEAL_MIN_CHARS: int = 900
IDEAL_MAX_CHARS: int = 1500

# ── Palavras/expressões proibidas ─────────────────────────────────────

FORBIDDEN_WORDS: list[str] = [
    "inovação",
    "otimização",
    "gestão inteligente",
    "reduza custos",
    "faz sentido?",
    "transformação digital",
    "solução robusta",
    "de forma eficiente",
    "travessão",
]


def count_characters(text: str) -> int:
    """Retorna a contagem de caracteres do texto."""
    return len(text)


def validate_post(text: str) -> list[str]:
    """
    Valida um texto de post e retorna lista de violações (string vazia = sem problemas).

    Regras verificadas:
    - Tamanho máximo do LinkedIn (3.000 chars)
    - Palavras/expressões proibidas
    """
    violations: list[str] = []
    char_count = count_characters(text)

    if char_count > LINKEDIN_MAX_CHARS:
        violations.append(
            f"Post excede o limite do LinkedIn: {char_count} de {LINKEDIN_MAX_CHARS} caracteres."
        )

    lower_text = text.lower()
    for word in FORBIDDEN_WORDS:
        if word.lower() in lower_text:
            violations.append(f"Palavra/expressão proibida encontrada: '{word}'.")

    return violations
