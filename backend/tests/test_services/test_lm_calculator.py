from __future__ import annotations

from services.content.lm_calculator import calculate_roi


def test_calculate_roi_applies_context_factors_to_investment_and_message() -> None:
    base = calculate_roi(
        pessoas=3,
        horas_semana=12,
        custo_hora=120,
        cargo="gerente",
        retrabalho_pct=15,
        tipo_processo="financeiro",
    )

    segmented = calculate_roi(
        pessoas=3,
        horas_semana=12,
        custo_hora=120,
        cargo="gerente",
        retrabalho_pct=15,
        tipo_processo="financeiro",
        company_segment="industria",
        company_size="grande",
        process_area_span="4+",
    )

    assert segmented.investimento_estimado_min > base.investimento_estimado_min
    assert segmented.investimento_estimado_max > base.investimento_estimado_max
    assert "indústrias" in segmented.mensagem_resultado
