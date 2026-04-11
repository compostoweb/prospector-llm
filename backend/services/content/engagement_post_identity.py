from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse, urlunparse

_WHITESPACE_RE = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def normalize_post_url(post_url: str | None) -> str | None:
    if not post_url:
        return None

    value = post_url.strip()
    if not value:
        return None

    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return value.rstrip("/")

    normalized_path = parsed.path.rstrip("/") or parsed.path or "/"
    cleaned = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=normalized_path,
        params="",
        query="",
        fragment="",
    )
    return urlunparse(cleaned)


def normalize_post_text(post_text: str | None) -> str:
    if not post_text:
        return ""

    value = _URL_RE.sub(" ", post_text.strip().lower())
    return _WHITESPACE_RE.sub(" ", value).strip()


def build_post_identity(
    *,
    post_url: str | None,
    post_text: str | None,
    author_name: str | None = None,
) -> tuple[str | None, str | None]:
    canonical_post_url = normalize_post_url(post_url)
    if canonical_post_url:
        return canonical_post_url, f"url:{canonical_post_url}"

    normalized_text = normalize_post_text(post_text)
    normalized_author = _WHITESPACE_RE.sub(" ", (author_name or "").strip().lower())
    if not normalized_text:
        return None, None

    digest = hashlib.sha1(f"{normalized_author}|{normalized_text}".encode()).hexdigest()
    return None, f"text:{digest}"


def merge_post_sources(existing_sources: list[str] | None, new_source: str) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for source in [*(existing_sources or []), new_source]:
        normalized = source.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)

    return merged


def choose_primary_post_source(existing_source: str, new_source: str) -> str:
    priority = {
        "linkedin_api": 4,
        "apify": 3,
        "google": 2,
        "manual": 1,
    }
    existing_score = priority.get(existing_source, 0)
    new_score = priority.get(new_source, 0)
    return new_source if new_score > existing_score else existing_source
