"""
services/content/lm_calculator.py

Lógica de cálculo da calculadora pública de ROI.
"""

from __future__ import annotations

from dataclasses import dataclass

from schemas.content_inbound import (
    CalculatorCompanySegment,
    CalculatorCompanySize,
    CalculatorProcessAreaSpan,
    CalculatorProcessType,
    CalculatorRole,
)

ROLE_HOURLY_COSTS: dict[CalculatorRole, float] = {
    "ceo": 250.0,
    "cfo": 200.0,
    "gerente": 120.0,
    "analista": 65.0,
    "operacional": 35.0,
}

PROCESS_INVESTMENT_RANGES: dict[CalculatorProcessType, tuple[float, float]] = {
    "financeiro": (12000.0, 30000.0),
    "juridico": (18000.0, 42000.0),
    "operacional": (15000.0, 36000.0),
    "atendimento": (10000.0, 26000.0),
    "rh": (12000.0, 28000.0),
}

SEGMENT_COMPLEXITY_FACTORS: dict[CalculatorCompanySegment, float] = {
    "clinicas": 0.07,
    "industria": 0.12,
    "advocacia": 0.08,
    "contabilidade": 0.06,
    "varejo": 0.05,
    "servicos": 0.04,
}

COMPANY_SIZE_FACTORS: dict[CalculatorCompanySize, float] = {
    "pequena": 0.00,
    "media": 0.08,
    "grande": 0.16,
}

PROCESS_AREA_FACTORS: dict[CalculatorProcessAreaSpan, float] = {
    "1": 0.00,
    "2-3": 0.08,
    "4+": 0.16,
}

SEGMENT_LABELS: dict[CalculatorCompanySegment, str] = {
    "clinicas": "clínicas",
    "industria": "indústrias",
    "advocacia": "advocacia",
    "contabilidade": "contabilidade",
    "varejo": "varejo",
    "servicos": "serviços",
}


@dataclass(slots=True)
class CalculatorComputation:
    custo_hora_sugerido: float
    custo_mensal: float
    custo_retrabalho: float
    custo_total_mensal: float
    custo_anual: float
    investimento_estimado_min: float
    investimento_estimado_max: float
    roi_estimado: float
    payback_meses: float
    mensagem_resultado: str


def get_calculator_config() -> tuple[
    dict[CalculatorRole, float],
    dict[CalculatorProcessType, tuple[float, float]],
]:
    return ROLE_HOURLY_COSTS, PROCESS_INVESTMENT_RANGES


def calculate_roi(
    *,
    pessoas: int,
    horas_semana: float,
    custo_hora: float | None,
    cargo: CalculatorRole,
    retrabalho_pct: float,
    tipo_processo: CalculatorProcessType,
    company_segment: CalculatorCompanySegment | None = None,
    company_size: CalculatorCompanySize | None = None,
    process_area_span: CalculatorProcessAreaSpan | None = None,
) -> CalculatorComputation:
    suggested_hourly_cost = custo_hora or ROLE_HOURLY_COSTS[cargo]

    custo_mensal = round(pessoas * horas_semana * 4.33 * suggested_hourly_cost, 2)
    custo_retrabalho = round(custo_mensal * (retrabalho_pct / 100.0) * 1.5, 2)
    custo_total_mensal = round(custo_mensal + custo_retrabalho, 2)
    custo_anual = round(custo_total_mensal * 12, 2)

    base_min, base_max = PROCESS_INVESTMENT_RANGES[tipo_processo]
    complexity_factor = 1.0
    complexity_factor += min(retrabalho_pct, 50.0) / 100.0
    complexity_factor += max(pessoas - 1, 0) * 0.05
    complexity_factor += max(horas_semana - 10.0, 0.0) * 0.01
    if company_segment is not None:
        complexity_factor += SEGMENT_COMPLEXITY_FACTORS[company_segment]
    if company_size is not None:
        complexity_factor += COMPANY_SIZE_FACTORS[company_size]
    if process_area_span is not None:
        complexity_factor += PROCESS_AREA_FACTORS[process_area_span]

    investimento_estimado_min = round(base_min * complexity_factor, 2)
    investimento_estimado_max = round(base_max * complexity_factor, 2)
    investimento_referencia = round(
        (investimento_estimado_min + investimento_estimado_max) / 2.0,
        2,
    )

    roi_estimado = 0.0
    if investimento_referencia > 0:
        roi_estimado = round(
            ((custo_anual - investimento_referencia) / investimento_referencia) * 100.0,
            2,
        )

    payback_meses = 0.0
    if custo_total_mensal > 0:
        payback_meses = round(investimento_referencia / custo_total_mensal, 1)

    return CalculatorComputation(
        custo_hora_sugerido=round(suggested_hourly_cost, 2),
        custo_mensal=custo_mensal,
        custo_retrabalho=custo_retrabalho,
        custo_total_mensal=custo_total_mensal,
        custo_anual=custo_anual,
        investimento_estimado_min=investimento_estimado_min,
        investimento_estimado_max=investimento_estimado_max,
        roi_estimado=roi_estimado,
        payback_meses=payback_meses,
        mensagem_resultado=build_result_message(
            custo_anual=custo_anual,
            roi_estimado=roi_estimado,
            payback_meses=payback_meses,
            company_segment=company_segment,
        ),
    )


def build_result_message(
    *,
    custo_anual: float,
    roi_estimado: float,
    payback_meses: float,
    company_segment: CalculatorCompanySegment | None = None,
) -> str:
    def format_decimal(value: float) -> str:
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

    custo_anual_label = (
        f"R$ {custo_anual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    roi_estimado_label = format_decimal(roi_estimado)
    payback_label = format_decimal(payback_meses)
    context_sentence_prefix = ""
    if company_segment is not None:
        context_sentence_prefix = f"No contexto de {SEGMENT_LABELS[company_segment]}, "

    if roi_estimado > 200:
        return (
            f"Seu processo manual está custando {custo_anual_label}/ano. "
            + context_sentence_prefix
            + f"a automação sob medida pode gerar um retorno estimado de {roi_estimado_label}% em 12 meses. "
            + "Esse número justifica uma conversa."
        )
    if roi_estimado >= 100:
        return (
            f"Seu processo está custando {custo_anual_label}/ano. "
            + context_sentence_prefix
            + f"a automação certa paga o investimento em {payback_label} meses."
        )
    return (
        f"Seu processo custa {custo_anual_label}/ano. "
        + context_sentence_prefix
        + f"com os parâmetros informados, a automação tem retorno em {payback_label} meses."
    )
