-------------- celery@341f0003a10e v5.6.3 (recovery)
--- ***** ----- 
-- ******* ---- Linux-5.15.0-116-generic-x86_64-with-glibc2.41 2026-04-13 03:12:03
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         prospector:0x7f7166ac8110
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

[2026-04-13 03:12:06,347: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:06 [info     ] anthropic_batch_worker.poll_done ended=0 polled=0 processed_leads=0
[2026-04-13 03:12:06,721: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:06 [info     ] cadence_tick.done              dispatched=11 skipped=0 tenants=1
[2026-04-13 03:12:06,770: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:06 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:06,812: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:06 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:06,824: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:06 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:06,840: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:06 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:06,974: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:06 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:06,985: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:06 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:07,046: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:07 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:07,070: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:07 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:07,070: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:07 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:07,094: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:07 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:07,096: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:07 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:07,117: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:07 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:07,986: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:07 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:08,058: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:08 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:08,067: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:08 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:08,077: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:08 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:08,089: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:08 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:08,337: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:08 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:08,347: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:08 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:09,301: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:09 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:10,244: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:10 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:10,391: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:10 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DVb3dS9t6K6QcJFDW'}" step_id=71be3033-145b-434b-a8d6-8752b8fd4ccf
[2026-04-13 03:12:10,414: ERROR/ForkPoolWorker-2] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f715e0cc9b0>>
Traceback (most recent call last):
  File "/app/workers/dispatch.py", line 437, in _dispatch_inner
    subject, message_text = await composer.compose_email(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/services/ai_composer.py", line 478, in compose_email
    response: LLMResponse = await self._registry.complete(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/registry.py", line 96, in complete
    response = await llm.complete(
               ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 193, in async_wrapped
    return await copy(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 112, in __call__
    do = await self.iter(retry_state=retry_state)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 413, in exc_check
    raise retry_exc.reraise()
          ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 184, in reraise
    raise self.last_attempt.result()
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 449, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 401, in __get_result
    raise self._exception
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 116, in __call__
    result = await fn(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/anthropic_provider.py", line 172, in complete
    response: Message = await self._client.messages.create(**kwargs)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/resources/messages/messages.py", line 2443, in create
    return await self._post(
           ^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1996, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1781, in request
    raise self._make_status_error_from_response(err.response) from None
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DVb3dS9t6K6QcJFDW'}

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
  File "/app/workers/dispatch.py", line 95, in _dispatch_async
    return await _dispatch_inner(step_id, tenant_id, tid, sid, task, lock_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 713, in _dispatch_inner
    raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 790, in retry
    raise ret
celery.exceptions.Retry: Retry in 60s: RuntimeError("BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DVb3dS9t6K6QcJFDW'}")

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
[2026-04-13 03:12:10,489: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:10 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:10,504: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:10 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:10,648: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:10 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DWhGisuSAZN8VuGPp'}" step_id=d15fc91a-db13-4730-b6b6-025323730050
[2026-04-13 03:12:10,654: ERROR/ForkPoolWorker-4] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f715e0b96d0>>
Traceback (most recent call last):
  File "/app/workers/dispatch.py", line 437, in _dispatch_inner
    subject, message_text = await composer.compose_email(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/services/ai_composer.py", line 478, in compose_email
    response: LLMResponse = await self._registry.complete(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/registry.py", line 96, in complete
    response = await llm.complete(
               ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 193, in async_wrapped
    return await copy(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 112, in __call__
    do = await self.iter(retry_state=retry_state)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 413, in exc_check
    raise retry_exc.reraise()
          ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 184, in reraise
    raise self.last_attempt.result()
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 449, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 401, in __get_result
    raise self._exception
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 116, in __call__
    result = await fn(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/anthropic_provider.py", line 172, in complete
    response: Message = await self._client.messages.create(**kwargs)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/resources/messages/messages.py", line 2443, in create
    return await self._post(
           ^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1996, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1781, in request
    raise self._make_status_error_from_response(err.response) from None
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DWhGisuSAZN8VuGPp'}

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
  File "/app/workers/dispatch.py", line 95, in _dispatch_async
    return await _dispatch_inner(step_id, tenant_id, tid, sid, task, lock_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 713, in _dispatch_inner
    raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 790, in retry
    raise ret
celery.exceptions.Retry: Retry in 60s: RuntimeError("BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DWhGisuSAZN8VuGPp'}")

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
[2026-04-13 03:12:10,699: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:10 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DWpU42U4ievQZQbpx'}" step_id=1bf3cc1c-9663-4e33-a344-f23c3a544833
[2026-04-13 03:12:10,780: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:10 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:10,876: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:10 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:10,905: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:10 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:10,911: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:10 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:10,967: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:10 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:10,990: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:10 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:11,049: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:11 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:11,078: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:11 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:11,078: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:11 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:11,090: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:11 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:11,100: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:11 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:11,123: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:11 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:11,452: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:11 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:11,688: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:11 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DayVeXRYqgHFyDbwb'}" step_id=86bd0508-eb97-4dcb-8897-242f2cbfb3db
[2026-04-13 03:12:11,951: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:11 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 03:12:11,999: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:11 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 03:12:12,015: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:12 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 03:12:12,021: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:12 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:12,119: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:12 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:12,355: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:12 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:12,639: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:12 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:13,222: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:13 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:14,360: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:14 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:14,511: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:14 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DoCTFZB87jLjZYMxs'}" step_id=103abec0-a24c-41d7-b249-ad748519ee03
[2026-04-13 03:12:14,517: ERROR/ForkPoolWorker-2] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f715d6259a0>>
Traceback (most recent call last):
  File "/app/workers/dispatch.py", line 437, in _dispatch_inner
    subject, message_text = await composer.compose_email(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/services/ai_composer.py", line 478, in compose_email
    response: LLMResponse = await self._registry.complete(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/registry.py", line 96, in complete
    response = await llm.complete(
               ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 193, in async_wrapped
    return await copy(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 112, in __call__
    do = await self.iter(retry_state=retry_state)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 413, in exc_check
    raise retry_exc.reraise()
          ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 184, in reraise
    raise self.last_attempt.result()
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 449, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 401, in __get_result
    raise self._exception
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 116, in __call__
    result = await fn(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/anthropic_provider.py", line 172, in complete
    response: Message = await self._client.messages.create(**kwargs)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/resources/messages/messages.py", line 2443, in create
    return await self._post(
           ^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1996, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1781, in request
    raise self._make_status_error_from_response(err.response) from None
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DoCTFZB87jLjZYMxs'}

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
  File "/app/workers/dispatch.py", line 95, in _dispatch_async
    return await _dispatch_inner(step_id, tenant_id, tid, sid, task, lock_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 713, in _dispatch_inner
    raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 790, in retry
    raise ret
celery.exceptions.Retry: Retry in 60s: RuntimeError("BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13DoCTFZB87jLjZYMxs'}")

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
[2026-04-13 03:12:14,547: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:14 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:14,699: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:14 [warning  ] dispatch.circuit_breaker_open  failure_count=5 step_id=2e16ca2d-ec24-417e-b5fe-8399932ebe71 tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac
[2026-04-13 03:12:14,730: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:14 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13Dp2pACdTgnrG34f2K'}" step_id=2867e1d6-e06c-4780-acf5-ec5a6cd2524a
[2026-04-13 03:12:14,737: ERROR/ForkPoolWorker-4] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f715dff1d60>>
Traceback (most recent call last):
  File "/app/workers/dispatch.py", line 437, in _dispatch_inner
    subject, message_text = await composer.compose_email(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/services/ai_composer.py", line 478, in compose_email
    response: LLMResponse = await self._registry.complete(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/registry.py", line 96, in complete
    response = await llm.complete(
               ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 193, in async_wrapped
    return await copy(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 112, in __call__
    do = await self.iter(retry_state=retry_state)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 413, in exc_check
    raise retry_exc.reraise()
          ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 184, in reraise
    raise self.last_attempt.result()
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 449, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 401, in __get_result
    raise self._exception
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 116, in __call__
    result = await fn(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/anthropic_provider.py", line 172, in complete
    response: Message = await self._client.messages.create(**kwargs)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/resources/messages/messages.py", line 2443, in create
    return await self._post(
           ^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1996, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1781, in request
    raise self._make_status_error_from_response(err.response) from None
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13Dp2pACdTgnrG34f2K'}

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
  File "/app/workers/dispatch.py", line 95, in _dispatch_async
    return await _dispatch_inner(step_id, tenant_id, tid, sid, task, lock_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 713, in _dispatch_inner
    raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 790, in retry
    raise ret
celery.exceptions.Retry: Retry in 60s: RuntimeError("BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13Dp2pACdTgnrG34f2K'}")

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
[2026-04-13 03:12:14,791: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:14 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:14,844: WARNING/ForkPoolWorker-2] 2026-04-13 03:12:14 [warning  ] dispatch.circuit_breaker_open  failure_count=6 step_id=49ebe07b-6bea-4ac9-9b70-3e0873ca3329 tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac
[2026-04-13 03:12:14,942: WARNING/ForkPoolWorker-4] 2026-04-13 03:12:14 [warning  ] dispatch.circuit_breaker_open  failure_count=6 step_id=836023a8-28c2-4805-855a-33c297ad7005 tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac
[2026-04-13 03:12:14,949: WARNING/ForkPoolWorker-1] 2026-04-13 03:12:14 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13Dq3aa1Y1qQs2yfTgj'}" step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-13 03:12:15,399: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:15 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 03:12:15,545: WARNING/ForkPoolWorker-3] 2026-04-13 03:12:15 [error    ] dispatch.error                 error="Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13Dsd7BuuSYrsfW9sz5'}" step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-13 03:12:15,552: ERROR/ForkPoolWorker-3] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f715d6324e0>>
Traceback (most recent call last):
  File "/app/workers/dispatch.py", line 437, in _dispatch_inner
    subject, message_text = await composer.compose_email(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/services/ai_composer.py", line 478, in compose_email
    response: LLMResponse = await self._registry.complete(
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/registry.py", line 96, in complete
    response = await llm.complete(
               ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 193, in async_wrapped
    return await copy(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 112, in __call__
    do = await self.iter(retry_state=retry_state)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 157, in iter
    result = await action(retry_state)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/_utils.py", line 111, in inner
    return call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 413, in exc_check
    raise retry_exc.reraise()
          ^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/tenacity/__init__.py", line 184, in reraise
    raise self.last_attempt.result()
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 449, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/concurrent/futures/_base.py", line 401, in __get_result
    raise self._exception
  File "/venv/lib/python3.12/site-packages/tenacity/asyncio/__init__.py", line 116, in __call__
    result = await fn(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/llm/anthropic_provider.py", line 172, in complete
    response: Message = await self._client.messages.create(**kwargs)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/resources/messages/messages.py", line 2443, in create
    return await self._post(
           ^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1996, in post
    return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/anthropic/_base_client.py", line 1781, in request
    raise self._make_status_error_from_response(err.response) from None
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13Dsd7BuuSYrsfW9sz5'}

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
  File "/app/workers/dispatch.py", line 95, in _dispatch_async
    return await _dispatch_inner(step_id, tenant_id, tid, sid, task, lock_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 713, in _dispatch_inner
    raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 790, in retry
    raise ret
celery.exceptions.Retry: Retry in 60s: RuntimeError("BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_011Ca13Dsd7BuuSYrsfW9sz5'}")

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
