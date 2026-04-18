from __future__ import annotations

from services.editorial_validator import validate_editorial_output


def test_validate_editorial_output_flags_email_subject_and_opening_issues() -> None:
    result = validate_editorial_output(
        "email_first",
        "Olá Maria, meu nome é Adriano e queria apresentar nossa solução.",
        subject="Uma ideia para apresentar uma oportunidade comercial urgente agora",
    )

    issue_codes = {issue.code for issue in result.issues}

    assert result.ok is False
    assert "opening_ola" in issue_codes
    assert "direct_intro" in issue_codes
    assert "generic_sales_cliche" in issue_codes
    assert "subject_too_long" in issue_codes
    assert "generic_subject" in issue_codes


def test_validate_editorial_output_flags_pitch_and_length_on_linkedin_connect() -> None:
    result = validate_editorial_output(
        "linkedin_connect",
        (
            "Oi Mariana, queria te apresentar nossa solução para automação comercial e marcar uma call rápida "
            "porque acredito que faz sentido para a operação de vocês ainda este mês, antes da próxima "
            "rodada de contratação e da revisão completa do fluxo comercial."
        ),
    )

    issue_codes = {issue.code for issue in result.issues}

    assert result.ok is False
    assert "connect_pitch" in issue_codes
    assert "meeting_cta" in issue_codes
    assert "body_too_long" in issue_codes


def test_validate_editorial_output_accepts_relational_linkedin_followup() -> None:
    result = validate_editorial_output(
        "linkedin_dm_followup",
        "Oi Mariana, vi um dado novo sobre inadimplencia no setor educacional. Voces ja conseguem prever onde o aluno esfria antes da rematricula?",
    )

    assert result.ok is True
    assert result.warning_count == 0


def test_validate_editorial_output_flags_unattributed_external_proof() -> None:
    result = validate_editorial_output(
        "linkedin_dm_followup",
        "Vi um estudo recente sobre acesso em saúde e pensei em te mandar um resumo. Isso entrou no radar de vocês?",
    )

    issue_codes = {issue.code for issue in result.issues}

    assert result.ok is False
    assert "unattributed_external_proof" in issue_codes
