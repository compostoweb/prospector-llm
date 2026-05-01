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
    # Content Hub — verifica articles agendados — a cada minuto
    "content-check-scheduled-articles": {
        "task": "workers.content.check_scheduled_articles",
        "schedule": crontab(minute="*"),
        "options": {"queue": "content"},
    },
    # Content Hub — lembretes de newsletter — diariamente 12h UTC (~09h BR)
    "content-newsletter-reminders": {
        "task": "workers.content.send_newsletter_reminders",
        "schedule": crontab(hour="12", minute="0"),
        "options": {"queue": "content"},
    },
    # Polling de batches Anthropic em andamento — a cada 5 minutos
    "poll-anthropic-batches": {
        "task": "workers.anthropic_batch.poll_anthropic_batches",
        "schedule": crontab(minute="*/5"),
    },
    # Fila de enriquecimento LinkedIn — processa um batch por hora
    "process-enrichment-queue": {
        "task": "workers.enrichment_queue.process_enrichment_queue",
        "schedule": crontab(minute="0"),  # topo de cada hora
        "options": {"queue": "enrich"},
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
    # Content Hub — refresh proativo de access_tokens LinkedIn — diariamente 03h UTC
    "content-refresh-linkedin-tokens": {
        "task": "workers.content.refresh_linkedin_tokens",
        "schedule": crontab(hour="3", minute="0"),
        "options": {"queue": "content"},
    },
    # Content Hub — purge semanal de posts soft-deleted >30d — domingo 04h UTC
    "content-purge-deleted-posts": {
        "task": "workers.content.purge_old_deleted_posts",
        "schedule": crontab(day_of_week="sunday", hour="4", minute="0"),
        "options": {"queue": "content"},
    },
    # Atualizar cache de parâmetros LinkedIn (LOCATION, INDUSTRY) — sábado 4h UTC
    "refresh-linkedin-search-params": {
        "task": "workers.linkedin_params_refresh.refresh_linkedin_search_params",
        "schedule": crontab(day_of_week="saturday", hour="4", minute="0"),
    },
}
