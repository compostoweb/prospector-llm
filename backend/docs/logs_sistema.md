 -------------- celery@60324ac3700f v5.6.3 (recovery)
--- ***** ----- 
-- ******* ---- Linux-5.15.0-116-generic-x86_64-with-glibc2.41 2026-04-13 03:49:26
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         prospector:0x7eff41b354f0
- ** ---------- .> transport:   redis://default:**@chatwoot_redis_prospector_llm:6379/0
- ** ---------- .> results:     redis://default:**@chatwoot_redis_prospector_llm:6379/1
- *** --- * --- .> concurrency: 4 (prefork)
-- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
--- ***** ----- 
 -------------- [queues]
                .> cadence          exchange=prospector(direct) key=cadence
                .> capture          exchange=prospector(direct) key=capture
                .> dispatch         exchange=prospector(direct) key=dispatch
                .> enrich           exchange=prospector(direct) key=enrich

[2026-04-13 03:49:29,520: WARNING/ForkPoolWorker-1] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:49:29,523: WARNING/ForkPoolWorker-2] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:49:29,562: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:49:29,583: WARNING/ForkPoolWorker-4] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:49:29,609: WARNING/ForkPoolWorker-2] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:49:29,615: WARNING/ForkPoolWorker-1] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:49:29,635: WARNING/ForkPoolWorker-2] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:49:29,646: WARNING/ForkPoolWorker-1] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:49:29,649: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:49:29,665: WARNING/ForkPoolWorker-4] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:49:29,675: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:49:29,692: WARNING/ForkPoolWorker-2] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openrouter
[2026-04-13 03:49:29,692: WARNING/ForkPoolWorker-4] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:49:29,706: WARNING/ForkPoolWorker-1] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openrouter
[2026-04-13 03:49:29,717: WARNING/ForkPoolWorker-2] 2026-04-13 03:49:29 [debug    ] openrouter.complete            json_mode=False model=arcee-ai/trinity-large-preview:free
[2026-04-13 03:49:29,724: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openrouter
[2026-04-13 03:49:29,730: WARNING/ForkPoolWorker-1] 2026-04-13 03:49:29 [debug    ] openrouter.complete            json_mode=False model=arcee-ai/trinity-large-preview:free
[2026-04-13 03:49:29,732: WARNING/ForkPoolWorker-4] 2026-04-13 03:49:29 [info     ] llm.registry.provider_loaded   provider=openrouter
[2026-04-13 03:49:29,746: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:29 [debug    ] openrouter.complete            json_mode=False model=arcee-ai/trinity-large-preview:free
[2026-04-13 03:49:29,756: WARNING/ForkPoolWorker-4] 2026-04-13 03:49:29 [debug    ] openrouter.complete            json_mode=False model=arcee-ai/trinity-large-preview:free
[2026-04-13 03:49:53,628: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:53 [debug    ] llm.usage_recorded             estimated_cost_usd=0.0 model=arcee-ai/trinity-large-preview:free module=cadence provider=openrouter task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2734
[2026-04-13 03:49:53,630: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:53 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=6ed0b0f7-d9b4-4c51-a13d-45229a21a009 matched_role=None model=arcee-ai/trinity-large-preview:free playbook_role=ceo_fintech playbook_sector=seguros provider=openrouter step=1 step_key=email_first subject_len=37 tokens_in=2643 tokens_out=91
[2026-04-13 03:49:54,089: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:54 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-13 03:49:54,126: ERROR/ForkPoolWorker-3] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7eff3c35d6d0>>
Traceback (most recent call last):
  File "/app/workers/dispatch.py", line 530, in _dispatch_inner
    _r = await unipile_client.send_email(
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/unipile_client.py", line 297, in send_email
    response.raise_for_status()
  File "/venv/lib/python3.12/site-packages/httpx/_models.py", line 829, in raise_for_status
    raise HTTPStatusError(message, request=request, response=self)
httpx.HTTPStatusError: Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/lib/python3.12/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/asyncio/base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 96, in _dispatch_async
    return await _dispatch_inner(step_id, tenant_id, tid, sid, task, lock_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 726, in _dispatch_inner
    raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 790, in retry
    raise ret
celery.exceptions.Retry: Retry in 60s: RuntimeError("HTTPStatusError: Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400")

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/pool/base.py", line 375, in _close_connection
    self._dialect.do_close(connection)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 721, in do_close
    dbapi_connection.close()
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 903, in close
    self.await_(self._connection.close())
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 1513, in close
    await self._protocol.close(timeout)
  File "asyncpg/protocol/protocol.pyx", line 632, in close
asyncio.exceptions.CancelledError
[2026-04-13 03:49:54,407: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:54 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:49:54,459: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:54 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:49:54,473: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:54 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:49:54,498: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:54 [info     ] llm.registry.provider_loaded   provider=openrouter
[2026-04-13 03:49:54,503: WARNING/ForkPoolWorker-3] 2026-04-13 03:49:54 [debug    ] openrouter.complete            json_mode=False model=arcee-ai/trinity-large-preview:free