from services.content.apify_linkedin_scanner import (
    _build_icp_query_batches,
    _expand_icp_sectors,
    _expand_icp_titles,
    _headline_matches_icp,
    _is_career_milestone_post,
    _is_job_posting,
    _matches_any_sector,
    _matches_reference_keywords,
)


def test_job_posting_detector_ignores_hashtag_vaga_in_thought_leadership_post() -> None:
    text = """
    Há empresas que não precisam apenas de um CFO.
    Precisam de um executivo capaz de colocar clareza onde hoje existe pressão.
    #CFO #AltaGestao #Vaga #Financas
    """

    assert _is_job_posting(text) is False


def test_career_milestone_detector_rejects_promotion_post() -> None:
    text = """
    Hoje compartilho com muita satisfação um novo passo na minha trajetória profissional:
    fui promovido para Especialista de Laboratório – Gestão da Automação.
    Sou grato pela confiança depositada em mim.
    """

    assert _is_career_milestone_post(text) is True


def test_reference_keyword_match_requires_meaningful_overlap() -> None:
    assert (
        _matches_reference_keywords(
            "A automação de processos na área financeira deixou de ser tendência.",
            ["automacao de processos"],
        )
        is True
    )
    assert (
        _matches_reference_keywords(
            "Hoje quase meia noite, o que estão a fazer? Por aqui… código!",
            ["automacao de processos"],
        )
        is False
    )


def test_headline_matches_icp_is_accent_insensitive() -> None:
    assert (
        _headline_matches_icp(
            "CFO | Diretor Financeiro | Estruturo finanças",
            {"diretor", "cfo"},
        )
        is True
    )


def test_sector_match_is_accent_insensitive() -> None:
    text = "Controller | Finanças | Controladoria | A automação de processos na área financeira"

    assert _matches_any_sector(text, {"financas", "financeiro"}) is True


def test_expand_icp_titles_adds_finance_aliases() -> None:
    titles = _expand_icp_titles(["diretor", "CFO"], ["finanças"])

    assert "Diretor Financeiro" in titles
    assert "Finance Director" in titles
    assert "Controller" in titles


def test_expand_icp_titles_adds_technology_aliases() -> None:
    titles = _expand_icp_titles(["diretor", "CTO"], ["tecnologia", "software"])

    assert "Diretor de TI" in titles
    assert "Diretor de Tecnologia" in titles
    assert "Head of Technology" in titles


def test_expand_icp_titles_adds_operations_aliases() -> None:
    titles = _expand_icp_titles(["gerente", "coo"], ["operações", "logística"])

    assert "Gerente de Operações" in titles
    assert "Operations Manager" in titles
    assert "Diretor de Operações" in titles


def test_expand_icp_sectors_adds_family_terms_for_technology() -> None:
    sectors = _expand_icp_sectors(["tecnologia"])

    assert "software" in sectors
    assert "infraestrutura" in sectors
    assert "dados" in sectors


def test_build_icp_query_batches_includes_keyword_and_fallback_batches() -> None:
    batches = _build_icp_query_batches(
        icp_titles=["CFO", "Diretor Financeiro"],
        icp_sectors=["finanças", "controladoria"],
        topic_keywords=["automacao de processos"],
        posted_limit="week",
    )

    assert len(batches) >= 3
    assert any(batch["required_keywords"] for batch in batches)
    assert any(batch["require_sector_match"] is False for batch in batches)
