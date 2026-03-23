"""
scheduler/beats.py

Agendamentos Celery Beat do Prospector.

Cada task é referenciada como string (evita imports circulares com celery_app).
O dicionário CELERY_BEAT_SCHEDULE é importado em workers/celery_app.py.
"""

from __future__ import annotations

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE: dict = {
    # Tick da cadência — verifica e dispara steps a cada minuto
    "cadence-tick": {
        "task": "workers.cadence.tick",
        "schedule": crontab(minute="*"),
    },
    # Captura de leads via Google Maps (Apify) — 1x por dia às 8h
    "capture-maps-daily": {
        "task": "workers.capture.run_apify_maps",
        "schedule": crontab(hour="8", minute="0"),
    },
    # Captura de leads via LinkedIn (Apify) — 1x por dia às 9h
    "capture-linkedin-daily": {
        "task": "workers.capture.run_apify_linkedin",
        "schedule": crontab(hour="9", minute="0"),
    },
    # Enriquecimento de leads pendentes — a cada 30 minutos
    "enrich-pending": {
        "task": "workers.enrich.enrich_pending_batch",
        "schedule": crontab(minute="*/30"),
    },
}
