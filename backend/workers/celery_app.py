"""
workers/celery_app.py

Instância e configuração central do Celery.

Responsabilidades:
  - Criar o app Celery com broker e backend de settings
    - Declarar as filas de processamento: capture, enrich, cadence, dispatch,
        content e content-engagement
  - Configurar serialização JSON e fuso UTC
  - Carregar o Beat schedule de scheduler/beats.py

Filas:
  capture  — captura de leads via Apify (Maps + LinkedIn)
  enrich   — enriquecimento de leads (email finder, contexto web)
  cadence  — tick da cadência, geração de mensagens
  dispatch — envio de mensagens via Unipile (LinkedIn + Email)
    content  — publicação e sincronizações gerais do Content Hub
    content-engagement — scanner de engajamento do Content Hub

Uso:
    celery -A workers.celery_app worker -Q dispatch -c 2
    celery -A workers.celery_app beat --loglevel=info --schedule /tmp/celerybeat-schedule
"""

from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from core.config import settings
from scheduler.beats import CELERY_BEAT_SCHEDULE

# ── Instância ─────────────────────────────────────────────────────────

celery_app = Celery(
    "prospector",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "workers.capture",
        "workers.enrich",
        "workers.cadence",
        "workers.dispatch",
        "workers.content",
        "workers.content_lm_sync",
        "workers.content_voyager",
        "workers.linkedin_poll",
        "workers.email_inbox_poll",
        "workers.warmup",
        "workers.connection_check",
        "workers.anthropic_batch",
        "workers.content_engagement",
    ],
)

# ── Filas e exchanges ─────────────────────────────────────────────────

default_exchange = Exchange("prospector", type="direct")

task_queues = (
    Queue("capture", default_exchange, routing_key="capture"),
    Queue("enrich", default_exchange, routing_key="enrich"),
    Queue("cadence", default_exchange, routing_key="cadence"),
    Queue("dispatch", default_exchange, routing_key="dispatch"),
    Queue("content", default_exchange, routing_key="content"),
    Queue("content-engagement", default_exchange, routing_key="content-engagement"),
)

# ── Configuração ──────────────────────────────────────────────────────

celery_app.conf.update(
    # Serialização
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Filas
    task_queues=task_queues,
    task_default_queue="dispatch",
    task_default_exchange="prospector",
    task_default_routing_key="dispatch",
    # Workers
    worker_prefetch_multiplier=1,  # não reservar tasks extras (fairness)
    task_acks_late=True,  # confirmar só após execução bem-sucedida
    task_reject_on_worker_lost=True,  # recolocar na fila se worker morrer
    # Resultados
    result_expires=3600,  # TTL de 1h para resultados
    # Beat schedule
    beat_schedule=CELERY_BEAT_SCHEDULE,
)
