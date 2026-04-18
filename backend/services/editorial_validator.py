from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)
_UNICODE_DASH_RE = re.compile(r"[\u2012\u2013\u2014\u2015]")
_ASCII_DASH_RE = re.compile(r"(?<=\S)\s-\s(?=\S)")

_COMMON_BANNED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("opening_ola", r"\bolá\b", 'Nunca usar "Olá".'),
    (
        "direct_intro",
        r"\b(meu nome e|meu nome é|trabalho na|trabalho com|somos da|sou da|sou o fundador|sou a fundadora)\b",
        "Evite apresentacao direta no inicio da mensagem.",
    ),
    (
        "generic_sales_cliche",
        r"\b(gostaria de apresentar|nossa solu[cç][aã]o|parceria estrat[eé]gica|estamos ajudando empresas como a sua)\b",
        "Evite cliches comerciais e frases massificadas.",
    ),
    (
        "generic_promise",
        r"\b(reduz(a|ir) custos|aument(e|ar) efici[eê]ncia|maior efici[eê]ncia|inova[cç][aã]o|otimiza[cç][aã]o|gest[aã]o inteligente|impacto nos seus lucros)\b",
        "Evite promessas genericas e linguagem vazia.",
    ),
    (
        "generic_followup",
        r"\b(s[oó] passando|voltando ao assunto|retomando o assunto|follow-up|retomando o e-mail|voltando ao email)\b",
        "Follow-up deve trazer angulo novo, sem formula pronta.",
    ),
)

_HIGH_FRICTION_CTA_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "meeting_cta",
        r"\b(agendar uma call|podemos agendar|tem 15 minutos|tem 20 minutos|tem 30 minutos|call r[aá]pida|reuni[aã]o breve|bate papo r[aá]pido)\b",
    ),
)

_EMAIL_SUBJECT_BANNED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "generic_subject",
        r"\b(uma ideia para|proposta|oportunidade|parceria|apresenta[cç][aã]o)\b",
        "Assunto de email precisa evitar cliches comerciais.",
    ),
)

_CONNECT_PITCH_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "connect_pitch",
        r"\b(produto|servi[cç]o|solu[cç][aã]o|parceria|oportunidade)\b",
        "Convite de conexao deve ser puro networking, sem pitch.",
    ),
)

_OPENING_STEPS = {
    "linkedin_connect",
    "linkedin_dm_first",
    "linkedin_dm_post_connect",
    "email_first",
    "linkedin_inmail",
}

_STEP_WORD_LIMITS: dict[str, int] = {
    "linkedin_dm_first": 120,
    "linkedin_dm_post_connect": 120,
    "linkedin_dm_post_connect_voice": 80,
    "linkedin_dm_voice": 100,
    "linkedin_dm_followup": 100,
    "linkedin_dm_breakup": 80,
    "email_first": 150,
    "email_followup": 120,
    "email_breakup": 100,
    "linkedin_inmail": 200,
}

_STEP_CHAR_LIMITS: dict[str, int] = {
    "linkedin_connect": 170,
    "linkedin_post_comment": 280,
}

_LINKEDIN_OPENING_QUESTION_STEPS = {
    "linkedin_dm_first",
    "linkedin_dm_post_connect",
    "linkedin_dm_followup",
    "linkedin_inmail",
}

_BREAKUP_OPEN_DOOR_PATTERNS = re.compile(
    r"\b(por ora|quando fizer sentido|fico a disposi[cç][aã]o|porta aberta|retomamos)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EditorialIssue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class EditorialValidationResult:
    step_key: str
    subject: str | None
    body: str
    issues: tuple[EditorialIssue, ...]
    body_word_count: int
    body_char_count: int
    subject_word_count: int
    subject_char_count: int

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def hard_failure_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


def validate_editorial_output(
    step_key: str,
    text: str,
    *,
    subject: str | None = None,
) -> EditorialValidationResult:
    body = (text or "").strip()
    subject_text = (subject or "").strip()
    body_lower = body.lower()
    subject_lower = subject_text.lower()
    issues: list[EditorialIssue] = []

    def add_issue(code: str, severity: str, message: str) -> None:
        issues.append(EditorialIssue(code=code, severity=severity, message=message))

    for code, pattern, message in _COMMON_BANNED_PATTERNS:
        if re.search(pattern, body_lower, re.IGNORECASE):
            add_issue(code, "error", message)

    for code, pattern in _HIGH_FRICTION_CTA_PATTERNS:
        if re.search(pattern, body_lower, re.IGNORECASE):
            add_issue(code, "error", "CTA de alto atrito nao e permitido neste stage.")

    if _UNICODE_DASH_RE.search(body) or _ASCII_DASH_RE.search(body):
        add_issue("dash_punctuation", "error", "Nao use travessao como pontuacao.")

    if step_key in _OPENING_STEPS and _starts_with_company_intro(body_lower):
        add_issue(
            "company_intro_first_sentence",
            "error",
            "A primeira frase deve abrir pelo lead, empresa ou problema, nao por apresentacao da Composto Web.",
        )

    char_limit = _STEP_CHAR_LIMITS.get(step_key)
    if char_limit is not None and len(body) > char_limit:
        add_issue(
            "body_too_long",
            "error",
            f"Texto excede o limite de {char_limit} caracteres para {step_key}.",
        )

    body_word_count = _count_words(body)
    word_limit = _STEP_WORD_LIMITS.get(step_key)
    if word_limit is not None and body_word_count > word_limit:
        add_issue(
            "body_too_long",
            "error",
            f"Texto excede o limite de {word_limit} palavras para {step_key}.",
        )

    if step_key == "linkedin_post_comment" and _sentence_count(body) > 2:
        add_issue(
            "too_many_sentences",
            "warning",
            "Comentario em post deve caber em ate 2 frases curtas.",
        )

    if step_key == "linkedin_connect":
        for code, pattern, message in _CONNECT_PITCH_PATTERNS:
            if re.search(pattern, body_lower, re.IGNORECASE):
                add_issue(code, "error", message)
        if _sentence_count(body) > 2:
            add_issue(
                "too_many_sentences",
                "warning",
                "Convite de conexao deve usar 1 ou 2 frases curtas.",
            )

    if step_key in _LINKEDIN_OPENING_QUESTION_STEPS and "?" not in body:
        add_issue(
            "missing_low_friction_question",
            "warning",
            "Este stage costuma performar melhor com pergunta leve no CTA.",
        )

    if step_key in {
        "linkedin_dm_breakup",
        "email_breakup",
    } and not _BREAKUP_OPEN_DOOR_PATTERNS.search(body_lower):
        add_issue(
            "missing_open_door",
            "warning",
            "Breakup deve sinalizar encerramento elegante com porta aberta.",
        )

    subject_word_count = _count_words(subject_text)
    subject_char_count = len(subject_text)
    if step_key.startswith("email_"):
        if subject_word_count > 8:
            add_issue(
                "subject_too_long",
                "error",
                "Assunto de email deve ter no maximo 8 palavras.",
            )
        for code, pattern, message in _EMAIL_SUBJECT_BANNED_PATTERNS:
            if re.search(pattern, subject_lower, re.IGNORECASE):
                add_issue(code, "error", message)

    if step_key == "linkedin_inmail" and subject_char_count > 60:
        add_issue(
            "subject_too_long",
            "error",
            "Assunto de InMail deve ter no maximo 60 caracteres.",
        )

    return EditorialValidationResult(
        step_key=step_key,
        subject=subject or None,
        body=body,
        issues=tuple(issues),
        body_word_count=body_word_count,
        body_char_count=len(body),
        subject_word_count=subject_word_count,
        subject_char_count=subject_char_count,
    )


def serialize_editorial_validation(result: EditorialValidationResult) -> dict[str, Any]:
    return {
        "step_key": result.step_key,
        "ok": result.ok,
        "hard_failures": result.hard_failure_count,
        "warnings": result.warning_count,
        "metrics": {
            "body_words": result.body_word_count,
            "body_chars": result.body_char_count,
            "subject_words": result.subject_word_count,
            "subject_chars": result.subject_char_count,
        },
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
            }
            for issue in result.issues
        ],
    }


def _count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _sentence_count(text: str) -> int:
    return len([part for part in re.split(r"[.!?]+", text) if part.strip()])


def _starts_with_company_intro(text: str) -> bool:
    first_sentence = re.split(r"[.!?\n]", text, maxsplit=1)[0].strip()
    return bool(
        re.search(
            r"^(na composto|aqui na composto|na composto web|somos a composto|trabalho com|trabalho na|meu nome e|meu nome é)",
            first_sentence,
            re.IGNORECASE,
        )
    )
