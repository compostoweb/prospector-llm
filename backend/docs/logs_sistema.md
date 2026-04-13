LOGS Workers Gerais


          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('836023a8-28c2-4805-855a-33c297ad7005'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)

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
[2026-04-13 02:38:56,576: ERROR/ForkPoolWorker-3] Task workers.dispatch.dispatch_step[2ecd0125-a776-4265-b2d1-78ddda8db0e1] raised unexpected: ProgrammingError("(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist")
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedColumnError: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 585, in trace_task
    R = retval = fun(*args, **kwargs)
                 ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 858, in __protected_call__
    return self.run(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 79, in dispatch_step
    return asyncio.run(_dispatch_async(step_id, tenant_id, self))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
  File "/app/workers/dispatch.py", line 117, in _dispatch_inner
    step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2351, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 306, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
           ^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('836023a8-28c2-4805-855a-33c297ad7005'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)
[2026-04-13 02:38:56,716: ERROR/ForkPoolWorker-3] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f12ea90e5d0>>
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedColumnError: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

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
  File "/app/workers/dispatch.py", line 117, in _dispatch_inner
    step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2351, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 306, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
           ^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('d15fc91a-db13-4730-b6b6-025323730050'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)

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
[2026-04-13 02:38:56,743: WARNING/ForkPoolWorker-4] 2026-04-13 02:38:56 [error    ] cadence_tick.tenant_error      error="(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist\n[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id \nFROM cadence_steps \nWHERE cadence_steps.tenant_id = $1::UUID AND cadence_steps.status = $2::cadence_step_status AND cadence_steps.scheduled_at <= $3::TIMESTAMP WITH TIME ZONE ORDER BY cadence_steps.scheduled_at ASC \n LIMIT $4::INTEGER]\n[parameters: (UUID('c00948b6-76d7-4d9c-8cd5-ba90663af6ac'), 'PENDING', datetime.datetime(2026, 4, 13, 2, 38, 56, 740291, tzinfo=datetime.timezone.utc), 200)]\n(Background on this error at: https://sqlalche.me/e/20/f405)" tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac
[2026-04-13 02:38:56,744: WARNING/ForkPoolWorker-4] 2026-04-13 02:38:56 [info     ] cadence_tick.done              dispatched=0 skipped=0 tenants=1
[2026-04-13 02:38:56,749: ERROR/ForkPoolWorker-3] Task workers.dispatch.dispatch_step[5901a15e-6d5a-4e88-9b66-a85dd17153c1] raised unexpected: ProgrammingError("(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist")
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedColumnError: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 585, in trace_task
    R = retval = fun(*args, **kwargs)
                 ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 858, in __protected_call__
    return self.run(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 79, in dispatch_step
    return asyncio.run(_dispatch_async(step_id, tenant_id, self))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
  File "/app/workers/dispatch.py", line 117, in _dispatch_inner
    step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2351, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 306, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
           ^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('d15fc91a-db13-4730-b6b6-025323730050'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)
[2026-04-13 02:38:56,791: WARNING/ForkPoolWorker-3] 2026-04-13 02:38:56 [info     ] dispatch.lock_exists           step_id=1bf3cc1c-9663-4e33-a344-f23c3a544833
[2026-04-13 02:38:57,164: ERROR/ForkPoolWorker-4] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f12e968fa70>>
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedColumnError: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

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
  File "/app/workers/dispatch.py", line 117, in _dispatch_inner
    step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2351, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 306, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
           ^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('103abec0-a24c-41d7-b249-ad748519ee03'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)

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
[2026-04-13 02:38:57,207: ERROR/ForkPoolWorker-4] Task workers.dispatch.dispatch_step[6685c463-0405-4116-a0c1-395d4e9ac5a5] raised unexpected: ProgrammingError("(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist")
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedColumnError: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 585, in trace_task
    R = retval = fun(*args, **kwargs)
                 ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 858, in __protected_call__
    return self.run(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 79, in dispatch_step
    return asyncio.run(_dispatch_async(step_id, tenant_id, self))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
  File "/app/workers/dispatch.py", line 117, in _dispatch_inner
    step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2351, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 306, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
           ^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('103abec0-a24c-41d7-b249-ad748519ee03'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)
[2026-04-13 02:38:57,402: ERROR/ForkPoolWorker-2] Exception closing connection <AdaptedConnection <asyncpg.connection.Connection object at 0x7f12e86a07d0>>
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedColumnError: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

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
  File "/app/workers/dispatch.py", line 117, in _dispatch_inner
    step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2351, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 306, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
           ^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('86bd0508-eb97-4dcb-8897-242f2cbfb3db'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)

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
[2026-04-13 02:38:57,442: ERROR/ForkPoolWorker-2] Task workers.dispatch.dispatch_step[9e06160e-2061-4d11-918f-605be6d10457] raised unexpected: ProgrammingError("(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist")
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 526, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 773, in _prepare
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 638, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 657, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/asyncpg/connection.py", line 443, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg/protocol/protocol.pyx", line 165, in prepare
asyncpg.exceptions.UndefinedColumnError: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 585, in trace_task
    R = retval = fun(*args, **kwargs)
                 ^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/trace.py", line 858, in __protected_call__
    return self.run(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/workers/dispatch.py", line 79, in dispatch_step
    return asyncio.run(_dispatch_async(step_id, tenant_id, self))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
  File "/app/workers/dispatch.py", line 117, in _dispatch_inner
    step_result = await db.execute(select(CadenceStep).where(CadenceStep.id == sid))
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 201, in greenlet_spawn
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2351, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/orm/context.py", line 306, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1419, in execute
    return meth(
           ^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 585, in execute
    self._adapt_connection.await_(
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 563, in _prepare_and_execute
    self._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 513, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "/venv/lib/python3.12/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py", line 797, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist
[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id 
FROM cadence_steps 
WHERE cadence_steps.id = $1::UUID]
[parameters: (UUID('86bd0508-eb97-4dcb-8897-242f2cbfb3db'),)]
(Background on this error at: https://sqlalche.me/e/20/f405)
[2026-04-13 02:38:57,475: WARNING/ForkPoolWorker-4] 2026-04-13 02:38:57 [error    ] cadence_tick.tenant_error      error="(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column cadence_steps.composed_text does not exist\n[SQL: SELECT cadence_steps.id, cadence_steps.cadence_id, cadence_steps.lead_id, cadence_steps.channel, cadence_steps.step_number, cadence_steps.day_offset, cadence_steps.use_voice, cadence_steps.audio_file_id, cadence_steps.status, cadence_steps.scheduled_at, cadence_steps.sent_at, cadence_steps.subject_used, cadence_steps.composed_text, cadence_steps.composed_subject, cadence_steps.tenant_id \nFROM cadence_steps \nWHERE cadence_steps.tenant_id = $1::UUID AND cadence_steps.status = $2::cadence_step_status AND cadence_steps.scheduled_at <= $3::TIMESTAMP WITH TIME ZONE ORDER BY cadence_steps.scheduled_at ASC \n LIMIT $4::INTEGER]\n[parameters: (UUID('c00948b6-76d7-4d9c-8cd5-ba90663af6ac'), 'PENDING', datetime.datetime(2026, 4, 13, 2, 38, 57, 471788, tzinfo=datetime.timezone.utc), 200)]\n(Background on this error at: https://sqlalche.me/e/20/f405)" tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac
[2026-04-13 02:38:57,475: WARNING/ForkPoolWorker-4] 2026-04-13 02:38:57 [info     ] cadence_tick.done              dispatched=0 skipped=0 tenants=1

=================================
Logs Workers Content:

 -------------- celery@ab32b9bedaf8 v5.6.3 (recovery)
--- ***** ----- 
-- ******* ---- Linux-5.15.0-116-generic-x86_64-with-glibc2.41 2026-04-13 02:35:52
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         prospector:0x7f7315ff5af0
- ** ---------- .> transport:   redis://default:**@chatwoot_redis_prospector_llm:6379/0
- ** ---------- .> results:     redis://default:**@chatwoot_redis_prospector_llm:6379/1
- *** --- * --- .> concurrency: 2 (prefork)
-- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
--- ***** ----- 
 -------------- [queues]
                .> content          exchange=prospector(direct) key=content
                .> content-engagement exchange=prospector(direct) key=content-engagement

[2026-04-13 02:36:00,333: WARNING/ForkPoolWorker-2] 2026-04-13 02:36:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T02:36:00.037745+00:00 dispatched=0
[2026-04-13 02:37:00,149: WARNING/ForkPoolWorker-2] 2026-04-13 02:37:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T02:37:00.018643+00:00 dispatched=0
[2026-04-13 02:38:00,102: WARNING/ForkPoolWorker-2] 2026-04-13 02:38:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T02:38:00.014871+00:00 dispatched=0
[2026-04-13 02:39:00,149: WARNING/ForkPoolWorker-2] 2026-04-13 02:39:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T02:39:00.030408+00:00 dispatched=0
[2026-04-13 02:40:00,112: WARNING/ForkPoolWorker-2] 2026-04-13 02:40:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T02:40:00.020448+00:00 dispatched=0

===============================
Logs Beat:

celery beat v5.6.3 (recovery) is starting.
__    -    ... __   -        _
LocalTime -> 2026-04-13 02:35:52
Configuration ->
    . broker -> redis://default:**@chatwoot_redis_prospector_llm:6379/0
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler
    . db -> /tmp/celerybeat-schedule
    . logfile -> [stderr]@%WARNING
    . maxinterval -> 5.00 minutes (300s)

==========================
Logs backend:

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started parent process [6]
INFO:     Started server process [8]
INFO:     Waiting for application startup.
INFO:     Started server process [9]
INFO:     Waiting for application startup.
{"url": "chatwoot_bd_prospector_llm:5432/prospector", "event": "database.connected", "level": "info", "timestamp": "2026-04-13T02:35:58.007707Z"}
{"url": "chatwoot_bd_prospector_llm:5432/prospector", "event": "database.connected", "level": "info", "timestamp": "2026-04-13T02:35:58.012902Z"}
{"env": "prod", "debug": false, "event": "api.startup", "level": "info", "timestamp": "2026-04-13T02:35:58.185233Z"}
INFO:     Application startup complete.
{"env": "prod", "debug": false, "event": "api.startup", "level": "info", "timestamp": "2026-04-13T02:35:58.192823Z"}
INFO:     Application startup complete.
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 13.08, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:35:58.380151Z"}
INFO:     127.0.0.1:37552 - "GET /health HTTP/1.1" 200 OK
INFO:     10.11.0.4:35162 - "WebSocket /ws/events?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiI1YjI5ZmViYi05M2ViLTQ5MjEtOTg3ZS0zZDEwY2MxMWRkNjMiLCJlbWFpbCI6ImFkcmlhbm9AY29tcG9zdG93ZWIuY29tLmJyIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJuYW1lIjoiQWRyaWFubyBWYWxhZFx1MDBlM28iLCJleHAiOjE3NzY1MjI2MzF9.G5zd-ZDHhrAyBEtQDr9r5rKpmb_c9Of3BcNgrBBgNa0" [accepted]
{"user_id": "5b29febb-93eb-4921-987e-3d10cc11dd63", "tenant_id": "", "event": "ws.connected", "level": "info", "timestamp": "2026-04-13T02:36:03.973101Z"}
INFO:     connection open
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 15.25, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:36:28.527533Z"}
INFO:     127.0.0.1:59004 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 4.29, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:36:58.659384Z"}
INFO:     127.0.0.1:33894 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 14.98, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:37:28.795876Z"}
INFO:     127.0.0.1:40266 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 5.18, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:37:58.891084Z"}
INFO:     127.0.0.1:33074 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 6.21, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:38:28.987322Z"}
INFO:     127.0.0.1:34750 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 10.78, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:38:59.140674Z"}
INFO:     127.0.0.1:47042 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 8.94, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:39:29.250960Z"}
INFO:     127.0.0.1:48814 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 13.46, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:39:59.376692Z"}
INFO:     127.0.0.1:35704 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 9.3, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:40:29.495314Z"}
INFO:     127.0.0.1:33830 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 10.75, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:40:59.606110Z"}
INFO:     127.0.0.1:58978 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 5.91, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:41:29.722198Z"}
INFO:     127.0.0.1:54698 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 10.63, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:41:59.834344Z"}
INFO:     127.0.0.1:32920 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 8.66, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:42:29.943532Z"}
INFO:     127.0.0.1:36520 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 5.62, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:43:00.051473Z"}
INFO:     127.0.0.1:54556 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 9.57, "event": "http.request", "level": "info", "timestamp": "2026-04-13T02:43:30.176251Z"}
INFO:     127.0.0.1:40772 - "GET /health HTTP/1.1" 200 OK

