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

import logging

import structlog


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
