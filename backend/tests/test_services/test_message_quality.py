from __future__ import annotations

from services.message_quality import normalize_generated_text


def test_normalize_generated_text_splits_final_question_into_own_paragraph() -> None:
    text = (
        "Em operacoes parecidas, a combinacao de confirmacao automatica com reagendamento inteligente "
        "costuma atacar essa perda silenciosa. Na Pro-Video, voces ja tratam confirmacao e remarcacao "
        "de forma ativa, ou isso ainda fica mais no fluxo manual?"
    )

    normalized = normalize_generated_text(text)

    assert normalized == (
        "Em operacoes parecidas, a combinacao de confirmacao automatica com reagendamento inteligente "
        "costuma atacar essa perda silenciosa.\n\n"
        "Na Pro-Video, voces ja tratam confirmacao e remarcacao de forma ativa, ou isso ainda fica mais no fluxo manual?"
    )


def test_normalize_generated_text_splits_final_open_door_sentence_into_own_paragraph() -> None:
    text = (
        "Adriano, imagino que esse tema nao esteja no topo da lista agora. "
        "Quando fizer sentido retomar esse assunto mais adiante, fico a disposicao por aqui."
    )

    normalized = normalize_generated_text(text)

    assert normalized == (
        "Adriano, imagino que esse tema nao esteja no topo da lista agora.\n\n"
        "Quando fizer sentido retomar esse assunto mais adiante, fico a disposicao por aqui."
    )