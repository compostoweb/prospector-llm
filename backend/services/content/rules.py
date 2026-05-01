"""
services/content/rules.py

Regras de validação para posts do Content Hub.

Caracteres: LinkedIn aceita até 3.000; faixa ideal 900–1.500 (default).
Cada hook tem seu range ideal (skill 05-conteudo-linkedin).
Palavras proibidas: termos banais de marketing B2B + CTAs comerciais diretos.
"""

from __future__ import annotations

# ── Limites de caracteres ─────────────────────────────────────────────

LINKEDIN_MAX_CHARS: int = 3000
IDEAL_MIN_CHARS: int = 900
IDEAL_MAX_CHARS: int = 1500

# Range ideal por tipo de gancho (transcrito da skill 05-conteudo-linkedin).
# Quando o hook é desconhecido ou ausente, usar (IDEAL_MIN_CHARS, IDEAL_MAX_CHARS).
IDEAL_RANGES_BY_HOOK: dict[str, tuple[int, int]] = {
    "short_reflection": (150, 400),
    "contrast_direct": (300, 600),
    "contrarian": (600, 900),
    "identification": (600, 900),
    "loop_open": (900, 1500),
    "data_isolated": (900, 1500),
    "shortcut": (900, 1500),
    "personal_story": (800, 1500),
    "dm_offer": (400, 900),
    # Hooks legados — alias para retrocompat
    "benefit": (900, 1500),  # alias de loop_open
    "data": (900, 1500),     # alias de data_isolated
}

# ── Palavras/expressões proibidas ─────────────────────────────────────

FORBIDDEN_WORDS: list[str] = [
    # Termos vazios de marketing B2B
    "inovação",
    "inovador",
    "inovar",
    "otimização",
    "gestão inteligente",
    "reduza custos",
    "aumente eficiência",
    "impacto nos seus lucros",
    "faz sentido?",
    "transformação digital",
    "solução robusta",
    "de forma eficiente",
    "travessão",
    # CTAs comerciais diretos (proibidos pela skill)
    "Entre em contato",
    "Agende uma reunião",
    "Tem 15 minutos?",
    "Clique no link",
]


def count_characters(text: str) -> int:
    """Retorna a contagem de caracteres do texto."""
    return len(text)


def recommend_range(hook_type: str | None) -> tuple[int, int]:
    """
    Retorna o range ideal de caracteres para o hook informado.
    Se hook desconhecido ou ausente, retorna o default global.
    """
    if hook_type and hook_type in IDEAL_RANGES_BY_HOOK:
        return IDEAL_RANGES_BY_HOOK[hook_type]
    return (IDEAL_MIN_CHARS, IDEAL_MAX_CHARS)


def validate_post(text: str, hook_type: str | None = None) -> list[str]:
    """
    Valida um texto de post e retorna lista de violações.

    Regras verificadas:
    - Tamanho máximo do LinkedIn (3.000 chars) — violation
    - Palavras/expressões proibidas — violation
    - Range ideal por hook (quando informado) — warning prefixado com "Aviso:"
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

    if hook_type:
        ideal_min, ideal_max = recommend_range(hook_type)
        if char_count < ideal_min or char_count > ideal_max:
            violations.append(
                f"Aviso: comprimento {char_count} fora do range ideal "
                f"para o gancho '{hook_type}' ({ideal_min}-{ideal_max} chars)."
            )

    return violations
