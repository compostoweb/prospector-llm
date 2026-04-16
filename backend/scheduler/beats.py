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
        "task": "workers.cadence.cadence_tick",
        "schedule": crontab(minute="*"),
    },
    # Captura de leads via Google Maps (Apify) — 1x por dia às 8h
    "capture-maps-daily": {
        "task": "workers.capture.run_apify_maps_daily",
        "schedule": crontab(hour="8", minute="0"),
    },
    # Captura de leads via LinkedIn (Apify) — 1x por dia às 9h
    "capture-linkedin-daily": {
        "task": "workers.capture.run_apify_linkedin_daily",
        "schedule": crontab(hour="9", minute="0"),
    },
    # Enriquecimento de leads pendentes — a cada 30 minutos
    "enrich-pending": {
        "task": "workers.enrich.enrich_pending_batch",
        "schedule": crontab(minute="*/30"),
    },
    # Verificação de conexões LinkedIn pendentes — a cada 15 minutos
    "check-connections": {
        "task": "workers.connection_check.check_pending_connections",
        "schedule": crontab(minute="*/15"),
    },
    # Warmup de e-mail — ciclo diário a cada 30 minutos (executa só se necessário)
    "warmup-tick": {
        "task": "workers.warmup.warmup_tick",
        "schedule": crontab(minute="*/30"),
    },
    # Polling de inbox LinkedIn para contas nativas — a cada minuto
    "linkedin-poll-tick": {
        "task": "workers.linkedin_poll.linkedin_poll_tick",
        "schedule": crontab(minute="*"),
    },
    # Polling de inbox de e-mail (Gmail OAuth + SMTP/IMAP) — a cada 5 minutos
    "email-inbox-poll": {
        "task": "workers.email_inbox_poll.email_inbox_poll_tick",
        "schedule": crontab(minute="*/5"),
    },
    # Content Hub — verifica posts agendados para publicar — a cada minuto
    "content-check-scheduled": {
        "task": "workers.content.check_scheduled_posts",
        "schedule": crontab(minute="*"),
    },
    # Polling de batches Anthropic em andamento — a cada 5 minutos
    "poll-anthropic-batches": {
        "task": "workers.anthropic_batch.poll_anthropic_batches",
        "schedule": crontab(minute="*/5"),
    },
    # Content Hub — sincronizacao Voyager Analytics — 3x/dia (08h, 14h, 20h)
    "content-voyager-sync-morning": {
        "task": "workers.content_voyager.sync_all_voyager",
        "schedule": crontab(hour="8", minute="0"),
    },
    "content-voyager-sync-afternoon": {
        "task": "workers.content_voyager.sync_all_voyager",
        "schedule": crontab(hour="14", minute="0"),
    },
    "content-voyager-sync-evening": {
        "task": "workers.content_voyager.sync_all_voyager",
        "schedule": crontab(hour="20", minute="0"),
    },
}
