from services.content.publisher import _compose_linkedin_post_text


def test_compose_linkedin_post_text_appends_hashtags_after_body() -> None:
    result = _compose_linkedin_post_text(
        "CTA final do post.",
        "#gestao #processos #tecnologia",
    )

    assert result == "CTA final do post.\n\n#gestao #processos #tecnologia"


def test_compose_linkedin_post_text_removes_trailing_hashtag_block_from_body() -> None:
    result = _compose_linkedin_post_text(
        "CTA final do post. #gestao #processos",
        "#gestao #processos",
    )

    assert result == "CTA final do post.\n\n#gestao #processos"


def test_compose_linkedin_post_text_keeps_body_hashtags_when_field_is_empty() -> None:
    result = _compose_linkedin_post_text(
        "Linha de conteúdo\n#legitimo #no-corpo",
        None,
    )

    assert result == "Linha de conteúdo\n#legitimo #no-corpo"
