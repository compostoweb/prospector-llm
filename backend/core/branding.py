from __future__ import annotations

from pathlib import Path

COMPOSTO_WEB_PRIMARY = "#1B2A4A"
COMPOSTO_WEB_SECONDARY = "#1E4B8F"
COMPOSTO_WEB_ACCENT = "#F5A623"
COMPOSTO_WEB_SURFACE = "#F4F6F9"
COMPOSTO_WEB_WHITE = "#FFFFFF"
COMPOSTO_WEB_TEXT = "#333333"

COMPOSTO_WEB_SITE_URL = "https://compostoweb.com.br"
COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_CID = "compostoweb-logo-primary-transparent"
COMPOSTO_WEB_LOGO_PRIMARY_WHITE_BG_CID = "compostoweb-logo-primary-white-bg"

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH = (
    _BACKEND_ROOT / "assets" / "branding" / "compostoweb-logo-primary-transparent.webp"
)
COMPOSTO_WEB_LOGO_PRIMARY_WHITE_BG_PATH = (
    _BACKEND_ROOT / "assets" / "branding" / "compostoweb-logo-primary-white-bg.webp"
)


def _load_branding_asset_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def load_composto_web_logo_primary_transparent_bytes() -> bytes | None:
    return _load_branding_asset_bytes(COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH)


def load_composto_web_logo_primary_white_bg_bytes() -> bytes | None:
    return _load_branding_asset_bytes(COMPOSTO_WEB_LOGO_PRIMARY_WHITE_BG_PATH)