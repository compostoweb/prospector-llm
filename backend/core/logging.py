"""
core/logging.py

Configuração centralizada do structlog.

Responsabilidades:
  - Configurar structlog com processadores adequados ao ambiente
  - Dev (DEBUG=True):  saída legível no console (ConsoleRenderer)
  - Prod (DEBUG=False): saída JSON estruturado (JSONRenderer) para coleta de logs
  - Exportar configure_logging() para ser chamado no startup da API e dos workers

Uso:
    from core.logging import configure_logging
    configure_logging()  # chamar uma vez no startup
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import structlog

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "token",
    "secret",
    "secret_key",
    "password",
    "cookie",
    "set_cookie",
    "x_api_key",
    "client_secret",
}
_SENSITIVE_QUERY_PARAMS = {
    "token",
    "access_token",
    "refresh_token",
    "grant_code",
    "ticket",
    "code",
    "state",
    "api_key",
    "signature",
}


def _normalize_log_key(key: str) -> str:
    return key.lower().replace("-", "_").replace(" ", "_")


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_log_key(key)
    return normalized in _SENSITIVE_KEYS or normalized.endswith(
        ("_token", "_secret", "_password", "_api_key")
    )


def _redact_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.query:
        return value

    sanitized_params = []
    changed = False
    for query_key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
        if _normalize_log_key(query_key) in _SENSITIVE_QUERY_PARAMS:
            sanitized_params.append((query_key, _REDACTED))
            changed = True
        else:
            sanitized_params.append((query_key, query_value))

    if not changed:
        return value

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(sanitized_params, doseq=True),
            parsed.fragment,
        )
    )


def _redact_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return _REDACTED

    if isinstance(value, dict):
        return {nested_key: _redact_value(str(nested_key), nested_value) for nested_key, nested_value in value.items()}

    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]

    if isinstance(value, tuple):
        return tuple(_redact_value(key, item) for item in value)

    if isinstance(value, str) and _normalize_log_key(key) in {
        "url",
        "request_url",
        "callback_url",
        "authorization_url",
    }:
        return _redact_url(value)

    return value


def redact_sensitive_processor(
    _: Any,
    __: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    return {
        event_key: _redact_value(event_key, event_value)
        for event_key, event_value in event_dict.items()
    }


def configure_logging() -> None:
    """
    Configura structlog e o logging padrão do Python.
    Deve ser chamada uma única vez no startup da aplicação.
    """
    # Import tardio para garantir que settings já está carregado
    from core.config import settings

    renderer: structlog.types.Processor
    if settings.DEBUG:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        redact_sensitive_processor,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redireciona o logging padrão do Python (uvicorn, sqlalchemy, etc.) para structlog
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )

    # Silencia bibliotecas de terceiros muito verbosas mesmo em modo DEBUG
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
