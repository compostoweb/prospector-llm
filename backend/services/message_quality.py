from __future__ import annotations

import html
import re

_UNICODE_DASH_RE = re.compile(r"\s*[\u2012\u2013\u2014\u2015]\s*")
_ASCII_DASH_RE = re.compile(r"(?<=\S)\s-\s(?=\S)")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_OPENING_OLA_RE = re.compile(r"^(olá)(?=[\s,!.:;]|$)", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]", re.DOTALL)
_CTA_CLOSING_RE = re.compile(
    r"\b("
    r"quando fizer sentido|"
    r"se fizer sentido|"
    r"fico a disposi[cç][aã]o|"
    r"fico por aqui|"
    r"podemos continuar por aqui|"
    r"me avise|"
    r"vale explorar|"
    r"faz sentido retomar|"
    r"deixo a porta aberta"
    r")\b",
    re.IGNORECASE,
)


def normalize_generated_text(text: str) -> str:
    """Normaliza texto gerado pela IA preservando estrutura de parágrafos."""
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in normalized.split("\n")]
    normalized = "\n".join(lines)
    normalized = _MULTI_NEWLINE_RE.sub("\n\n", normalized)
    normalized = _UNICODE_DASH_RE.sub(", ", normalized)
    normalized = _ASCII_DASH_RE.sub(", ", normalized)
    normalized = re.sub(r"\s+([,.;!?])", r"\1", normalized)
    normalized = re.sub(r"([,.;!?])(\S)", r"\1 \2", normalized)
    normalized = _OPENING_OLA_RE.sub("Oi", normalized, count=1)
    normalized = _split_final_cta_into_paragraph(normalized)
    normalized = _MULTI_NEWLINE_RE.sub("\n\n", normalized)
    return normalized.strip()


def normalize_email_subject(subject: str) -> str:
    """Normaliza assunto mantendo saída em uma linha."""
    normalized = normalize_generated_text(subject)
    normalized = normalized.replace("\n", " ")
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def build_fallback_email_subject(company_or_name: str | None, step_number: int) -> str:
    """Gera fallback compatível com as skills internas de coldmail."""
    company = (company_or_name or "").strip()
    short_company = company if 0 < len(company.split()) <= 3 else ""

    if step_number <= 1:
        if short_company:
            return normalize_email_subject(f"{short_company}: processo manual ou automatizado?")
        return "Esse processo ainda e manual?"

    if short_company:
        return normalize_email_subject(f"{short_company}: novo angulo operacional")
    return "Novo angulo sobre esse processo"


def plain_text_email_to_html(text: str) -> str:
    """Converte email em texto puro para HTML preservando paragrafos."""
    normalized = normalize_generated_text(text)
    if not normalized:
        return "<p></p>"

    paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()]
    html_parts: list[str] = []
    for paragraph in paragraphs:
        lines = [html.escape(line.strip()) for line in paragraph.split("\n") if line.strip()]
        if not lines:
            continue
        html_parts.append(f"<p>{'<br />'.join(lines)}</p>")

    return "\n".join(html_parts) if html_parts else "<p></p>"


def _split_final_cta_into_paragraph(text: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return text

    last_paragraph = paragraphs[-1]
    sentences = _extract_sentences(last_paragraph)
    if len(sentences) < 2:
        return "\n\n".join(paragraphs)

    final_sentence = sentences[-1]
    if not _looks_like_final_cta(final_sentence):
        return "\n\n".join(paragraphs)

    paragraphs[-1] = " ".join(sentences[:-1]).strip()
    paragraphs.append(final_sentence)
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def _extract_sentences(paragraph: str) -> list[str]:
    matches = [match.group(0).strip() for match in _SENTENCE_RE.finditer(paragraph)]
    consumed = sum(len(match.group(0)) for match in _SENTENCE_RE.finditer(paragraph))
    remainder = paragraph[consumed:].strip()
    if remainder:
        matches.append(remainder)
    return [sentence for sentence in matches if sentence]


def _looks_like_final_cta(sentence: str) -> bool:
    normalized = sentence.strip()
    if not normalized:
        return False
    return normalized.endswith("?") or bool(_CTA_CLOSING_RE.search(normalized))
