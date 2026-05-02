from __future__ import annotations

import re
from pathlib import Path

_AUDIO_EXTENSIONS_BY_CONTENT_TYPE = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/mp4": ".m4a",
}
_IMAGE_EXTENSIONS_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}
_VIDEO_EXTENSIONS_BY_CONTENT_TYPE = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}
_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_download_filename(filename: str, *, fallback: str) -> str:
    candidate = Path(filename or "").name.strip()
    if not candidate:
        candidate = fallback

    candidate = candidate.replace("\r", "_").replace("\n", "_")
    candidate = _SAFE_FILENAME_CHARS.sub("_", candidate)
    candidate = candidate.strip("._") or fallback
    return candidate[:180]


def detect_audio_content_type(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"ID3":
        return "audio/mpeg"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "audio/mpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if len(data) >= 4 and data[:4] == b"OggS":
        return "audio/ogg"
    if len(data) >= 4 and data[:4] == b"\x1A\x45\xDF\xA3":
        return "audio/webm"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "audio/mp4"
    return None


def detect_image_content_type(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"\xFF\xD8\xFF":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 6 and data[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"

    sniff = data[:512].lstrip()
    if sniff.startswith(b"<svg") or (sniff.startswith(b"<?xml") and b"<svg" in sniff):
        return "image/svg+xml"
    return None


def detect_video_content_type(data: bytes) -> str | None:
    if len(data) >= 12 and data[4:8] == b"ftyp":
        major_brand = data[8:12]
        if major_brand == b"qt  ":
            return "video/quicktime"
        return "video/mp4"
    return None


def detect_pdf_content_type(data: bytes) -> str | None:
    if len(data) >= 5 and data[:5] == b"%PDF-":
        return "application/pdf"
    return None


def pick_audio_extension(*, content_type: str, original_filename: str | None = None) -> str:
    normalized_content_type = content_type.split(";", 1)[0].strip().lower()
    mapped = _AUDIO_EXTENSIONS_BY_CONTENT_TYPE.get(normalized_content_type)
    if mapped:
        return mapped

    if original_filename and "." in original_filename:
        suffix = Path(original_filename).suffix.lower()
        if suffix:
            return suffix[:10]

    return ".bin"


def pick_image_extension(*, content_type: str, original_filename: str | None = None) -> str:
    normalized_content_type = content_type.split(";", 1)[0].strip().lower()
    mapped = _IMAGE_EXTENSIONS_BY_CONTENT_TYPE.get(normalized_content_type)
    if mapped:
        return mapped

    if original_filename and "." in original_filename:
        suffix = Path(original_filename).suffix.lower()
        if suffix:
            return suffix[:10]

    return ".bin"


def pick_video_extension(*, content_type: str, original_filename: str | None = None) -> str:
    normalized_content_type = content_type.split(";", 1)[0].strip().lower()
    mapped = _VIDEO_EXTENSIONS_BY_CONTENT_TYPE.get(normalized_content_type)
    if mapped:
        return mapped

    if original_filename and "." in original_filename:
        suffix = Path(original_filename).suffix.lower()
        if suffix:
            return suffix[:10]

    return ".bin"