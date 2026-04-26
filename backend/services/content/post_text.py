from __future__ import annotations

import re

_HASHTAG_RE = re.compile(r"#[\w-]+", re.UNICODE)
_TRAILING_HASHTAG_BLOCK_RE = re.compile(
    r"\s+(?:#[\w-]+(?:\s+#[\w-]+)*)\s*$",
    re.UNICODE,
)


def normalize_hashtags(hashtags: str | None) -> str:
    """Normaliza hashtags para uma linha unica separada por espacos."""
    if not hashtags:
        return ""

    return " ".join(dict.fromkeys(_HASHTAG_RE.findall(hashtags)))


def compose_linkedin_post_text(body: str, hashtags: str | None) -> str:
    """Monta o texto final enviado ao LinkedIn com hashtags no fim."""
    normalized_body = body.strip()
    normalized_hashtags = normalize_hashtags(hashtags)

    if not normalized_hashtags:
        return normalized_body

    body_without_trailing_hashtags = _TRAILING_HASHTAG_BLOCK_RE.sub("", normalized_body).strip()
    if not body_without_trailing_hashtags:
        return normalized_hashtags

    return f"{body_without_trailing_hashtags}\n\n{normalized_hashtags}"
