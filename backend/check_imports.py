modules = [
    'models.enums',
    'models.cadence',
    'models.interaction',
    'schemas.cadence',
    'services.cadence_manager',
    'workers.dispatch',
    'api.routes.cadences',
    'api.routes.llm',
    'api.webhooks.unipile',
    'scheduler.beats',
]
ok = 0
fail = 0
for m in modules:
    try:
        __import__(m)
        ok += 1
    except Exception as e:
        print(f'FAIL: {m}: {e}')
        fail += 1
print(f'Result: {ok} OK, {fail} FAILED')
