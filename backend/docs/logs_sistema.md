Segue logs dos workers gerais, parece que tem erro mesmo:

 
 -------------- celery@a8c26f5529a3 v5.6.3 (recovery)
--- ***** ----- 
-- ******* ---- Linux-5.15.0-116-generic-x86_64-with-glibc2.41 2026-04-12 19:38:39
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         prospector:0x7f6b8aa98110
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

[2026-04-12 19:38:42,208: WARNING/ForkPoolWorker-4] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:38:42,269: WARNING/ForkPoolWorker-3] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:38:42,295: WARNING/ForkPoolWorker-4] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:38:42,303: WARNING/ForkPoolWorker-1] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:38:42,320: WARNING/ForkPoolWorker-4] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:38:42,328: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:38:42,342: WARNING/ForkPoolWorker-3] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:38:42,346: WARNING/ForkPoolWorker-4] 2026-04-12 19:38:42 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:38:42,362: WARNING/ForkPoolWorker-3] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:38:42,380: WARNING/ForkPoolWorker-1] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:38:42,382: WARNING/ForkPoolWorker-3] 2026-04-12 19:38:42 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:38:42,403: WARNING/ForkPoolWorker-1] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:38:42,424: WARNING/ForkPoolWorker-1] 2026-04-12 19:38:42 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:38:42,428: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:38:42,457: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:42 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:38:42,479: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:42 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:38:53,806: WARNING/ForkPoolWorker-3] 2026-04-12 19:38:53 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:38:54,799: WARNING/ForkPoolWorker-1] 2026-04-12 19:38:54 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:38:54,837: WARNING/ForkPoolWorker-4] 2026-04-12 19:38:54 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:38:56,124: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:56 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=e07127a0-fb32-4877-be78-c212c1a23fb7 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=ti_saude playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=51 tokens_in=2526 tokens_out=147
[2026-04-12 19:38:56,359: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:56 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=d15fc91a-db13-4730-b6b6-025323730050
[2026-04-12 19:38:56,635: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:56 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:38:56,685: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:56 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:38:56,698: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:56 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:38:56,703: WARNING/ForkPoolWorker-2] 2026-04-12 19:38:56 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:02,294: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:02 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=a1f06d2b-d94e-402a-a334-3777a3c89f1e matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=45 tokens_in=2510 tokens_out=147
[2026-04-12 19:39:02,496: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:02 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-12 19:39:02,995: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:02 [info     ] cadence_tick.done              dispatched=11 skipped=0 tenants=1
[2026-04-12 19:39:03,208: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:03 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:03,279: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:03 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:03,303: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:03 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:03,309: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:03 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:05,594: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:05 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:06,788: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:06 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:07,492: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:07 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:13,093: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:13 [info     ] ai_composer.compose_email      copy_method=AIRE few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=99fa5e1f-d887-4624-ab82-882766f2125d matched_role=None model=gpt-4.1-2025-04-14 playbook_role=None playbook_sector=None provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2162 tokens_out=133
[2026-04-12 19:39:13,321: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:13 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2867e1d6-e06c-4780-acf5-ec5a6cd2524a
[2026-04-12 19:39:14,841: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:14 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:15,042: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:15 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:15,109: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:15 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:15,132: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:15 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:15,138: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:15 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:15,386: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:15 [error    ] dispatch.error                 error='RetryError[<Future at 0x7f6b81c8b620 state=finished raised RateLimitError>]' step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-12 19:39:15,674: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:15 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:15,741: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:15 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:15,766: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:15 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:15,770: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:15 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:16,880: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:16 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=f04ab743-8dbe-4c0c-90f1-c5eee87104fc matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=39 tokens_in=2512 tokens_out=148
[2026-04-12 19:39:17,078: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:17 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=103abec0-a24c-41d7-b249-ad748519ee03
[2026-04-12 19:39:17,337: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:17 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:17,413: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:17 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:17,438: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:17 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:17,444: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:17 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:17,969: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:17 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=62c7322e-ce5e-4000-94a1-b59c65f9c937 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=36 tokens_in=2515 tokens_out=122
[2026-04-12 19:39:18,160: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:18 [error    ] dispatch.error                 error='RetryError[<Future at 0x7f6b81bc4800 state=finished raised RateLimitError>]' step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-12 19:39:18,205: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:18 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=49ebe07b-6bea-4ac9-9b70-3e0873ca3329
[2026-04-12 19:39:18,457: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:18 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:18,490: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:18 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:18,521: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:18 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:18,536: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:18 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:18,542: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:18 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:18,546: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:18 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:18,561: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:18 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:18,567: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:18 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:21,866: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:21 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=industria:diretor_industrial:email:first generation_mode=llm lead_id=7a3bcf26-c36b-4139-ab2b-bca9cc3d9c33 matched_role=diretor_industrial model=gpt-4.1-2025-04-14 playbook_role=diretor_industrial playbook_sector=industria provider=openai step=1 step_key=email_first subject_len=39 tokens_in=2479 tokens_out=133
[2026-04-12 19:39:22,035: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:22 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=836023a8-28c2-4805-855a-33c297ad7005
[2026-04-12 19:39:22,272: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:22 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:22,331: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:22 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:22,351: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:22 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:22,357: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:22 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:28,560: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:28 [info     ] ai_composer.compose_email      copy_method=AIRE few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=99fa5e1f-d887-4624-ab82-882766f2125d matched_role=None model=gpt-4.1-2025-04-14 playbook_role=None playbook_sector=None provider=openai step=1 step_key=email_first subject_len=47 tokens_in=2162 tokens_out=131
[2026-04-12 19:39:28,783: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:28 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2867e1d6-e06c-4780-acf5-ec5a6cd2524a
[2026-04-12 19:39:29,012: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:29 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:29,071: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:29 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:29,092: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:29 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:29,098: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:29 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:30,061: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:30 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:30,359: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:30 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:32,362: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:32 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=agencia:ceo_agencia:email:first generation_mode=llm lead_id=3f652e53-78be-48a4-8d95-ec09147c6d41 matched_role=ceo_agencia model=gpt-4.1-2025-04-14 playbook_role=ceo_agencia playbook_sector=agencia provider=openai step=1 step_key=email_first subject_len=43 tokens_in=2485 tokens_out=160
[2026-04-12 19:39:32,615: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:32 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2e16ca2d-ec24-417e-b5fe-8399932ebe71
[2026-04-12 19:39:32,894: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:32 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:32,985: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:32 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:33,011: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:33 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:33,020: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:33 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:33,964: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:33 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:35,594: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:35 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=agencia:ceo_agencia:email:first generation_mode=llm lead_id=3f652e53-78be-48a4-8d95-ec09147c6d41 matched_role=ceo_agencia model=gpt-4.1-2025-04-14 playbook_role=ceo_agencia playbook_sector=agencia provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2485 tokens_out=124
[2026-04-12 19:39:35,774: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:35 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2e16ca2d-ec24-417e-b5fe-8399932ebe71
[2026-04-12 19:39:36,030: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:36 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:36,105: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:36 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:36,133: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:36 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:36,139: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:36 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:38,256: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:38 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=e07127a0-fb32-4877-be78-c212c1a23fb7 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=ti_saude playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=48 tokens_in=2526 tokens_out=131
[2026-04-12 19:39:38,474: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:38 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=d15fc91a-db13-4730-b6b6-025323730050
[2026-04-12 19:39:38,736: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:38 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:38,804: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:38 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:38,826: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:38 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:38,834: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:38 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:40,866: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:40 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:43,035: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:43 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:44,793: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:44 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:45,127: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:45 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=62c7322e-ce5e-4000-94a1-b59c65f9c937 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=48 tokens_in=2515 tokens_out=110
[2026-04-12 19:39:45,328: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:45 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=49ebe07b-6bea-4ac9-9b70-3e0873ca3329
[2026-04-12 19:39:45,538: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:45 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:45,608: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:45 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:45,628: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:45 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:45,633: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:45 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:50,607: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:50 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:53,608: WARNING/ForkPoolWorker-2] 2026-04-12 19:39:53 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:57,367: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:57 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:57,522: WARNING/ForkPoolWorker-4] 2026-04-12 19:39:57 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:57,645: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:57 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=689e175c-50aa-40c9-bd0d-63e0fedb4d40 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=41 tokens_in=2511 tokens_out=134
[2026-04-12 19:39:57,898: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:57 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=86bd0508-eb97-4dcb-8897-242f2cbfb3db
[2026-04-12 19:39:58,129: ERROR/ForkPoolWorker-1] Task exception was never retrieved
future: <Task finished name='Task-65' coro=<AsyncClient.aclose() done, defined at /venv/lib/python3.12/site-packages/httpx/_client.py:1978> exception=RuntimeError('Event loop is closed')>
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/httpx/_client.py", line 1985, in aclose
    await self._transport.aclose()
  File "/venv/lib/python3.12/site-packages/httpx/_transports/default.py", line 406, in aclose
    await self._pool.aclose()
  File "/venv/lib/python3.12/site-packages/httpcore/_async/connection_pool.py", line 353, in aclose
    await self._close_connections(closing_connections)
  File "/venv/lib/python3.12/site-packages/httpcore/_async/connection_pool.py", line 345, in _close_connections
    await connection.aclose()
  File "/venv/lib/python3.12/site-packages/httpcore/_async/connection.py", line 173, in aclose
    await self._connection.aclose()
  File "/venv/lib/python3.12/site-packages/httpcore/_async/http11.py", line 258, in aclose
    await self._network_stream.aclose()
  File "/venv/lib/python3.12/site-packages/httpcore/_backends/anyio.py", line 53, in aclose
    await self._stream.aclose()
  File "/venv/lib/python3.12/site-packages/anyio/streams/tls.py", line 236, in aclose
    await self.transport_stream.aclose()
  File "/venv/lib/python3.12/site-packages/anyio/_backends/_asyncio.py", line 1344, in aclose
    self._transport.close()
  File "/usr/local/lib/python3.12/asyncio/selector_events.py", line 1213, in close
    super().close()
  File "/usr/local/lib/python3.12/asyncio/selector_events.py", line 875, in close
    self._loop.call_soon(self._call_connection_lost, None)
  File "/usr/local/lib/python3.12/asyncio/base_events.py", line 799, in call_soon
    self._check_closed()
  File "/usr/local/lib/python3.12/asyncio/base_events.py", line 545, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
[2026-04-12 19:39:58,197: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:58 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:58,261: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:58 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:58,280: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:58 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:58,286: WARNING/ForkPoolWorker-1] 2026-04-12 19:39:58 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:39:59,358: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:59 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=f04ab743-8dbe-4c0c-90f1-c5eee87104fc matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=46 tokens_in=2512 tokens_out=160
[2026-04-12 19:39:59,547: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:59 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=103abec0-a24c-41d7-b249-ad748519ee03
[2026-04-12 19:39:59,768: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:59 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:39:59,823: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:59 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:39:59,841: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:59 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:39:59,846: WARNING/ForkPoolWorker-3] 2026-04-12 19:39:59 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:00,584: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:00 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=ti:ceo_cto_ti:email:first generation_mode=llm lead_id=677bef5e-5648-4ca5-b321-87a8d4e6ba8e matched_role=ceo_cto_ti model=gpt-4.1-2025-04-14 playbook_role=ceo_cto_ti playbook_sector=ti provider=openai step=1 step_key=email_first subject_len=46 tokens_in=2515 tokens_out=118
[2026-04-12 19:40:00,770: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:00 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=71be3033-145b-434b-a8d6-8752b8fd4ccf
[2026-04-12 19:40:00,940: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:00 [info     ] anthropic_batch_worker.poll_done ended=0 polled=0 processed_leads=0
[2026-04-12 19:40:01,493: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:01 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:01,580: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:01 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:01,606: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:01 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:01,614: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:01 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:08,203: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:08 [error    ] dispatch.error                 error='RetryError[<Future at 0x7f6b80e9dd90 state=finished raised RateLimitError>]' step_id=1bf3cc1c-9663-4e33-a344-f23c3a544833
[2026-04-12 19:40:08,315: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:08 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:09,781: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:09 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:09,838: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:09 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:09,857: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:09 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:09,864: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:09 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:10,740: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:10 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:13,433: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:13 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:14,826: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:14 [info     ] ai_composer.compose_email      copy_method=AIRE few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=99fa5e1f-d887-4624-ab82-882766f2125d matched_role=None model=gpt-4.1-2025-04-14 playbook_role=None playbook_sector=None provider=openai step=1 step_key=email_first subject_len=47 tokens_in=2162 tokens_out=157
[2026-04-12 19:40:15,048: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:15 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2867e1d6-e06c-4780-acf5-ec5a6cd2524a
[2026-04-12 19:40:15,570: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:15 [info     ] cadence_tick.done              dispatched=11 skipped=0 tenants=1
[2026-04-12 19:40:15,764: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:15 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:15,826: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:15 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:15,847: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:15 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:15,853: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:15 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:16,603: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:16 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=agencia:ceo_agencia:email:first generation_mode=llm lead_id=3f652e53-78be-48a4-8d95-ec09147c6d41 matched_role=ceo_agencia model=gpt-4.1-2025-04-14 playbook_role=ceo_agencia playbook_sector=agencia provider=openai step=1 step_key=email_first subject_len=45 tokens_in=2485 tokens_out=128
[2026-04-12 19:40:16,780: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:16 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2e16ca2d-ec24-417e-b5fe-8399932ebe71
[2026-04-12 19:40:17,054: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:17 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:17,124: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:17 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:17,139: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:17 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:17,145: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:17 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:22,547: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:22 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:23,529: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:23 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=62c7322e-ce5e-4000-94a1-b59c65f9c937 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2515 tokens_out=158
[2026-04-12 19:40:23,725: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:23 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=49ebe07b-6bea-4ac9-9b70-3e0873ca3329
[2026-04-12 19:40:23,964: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:23 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:24,010: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:24 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:24,026: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:24 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:24,033: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:24 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:26,068: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:26 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:29,730: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:29 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=industria:diretor_industrial:email:first generation_mode=llm lead_id=7a3bcf26-c36b-4139-ab2b-bca9cc3d9c33 matched_role=diretor_industrial model=gpt-4.1-2025-04-14 playbook_role=diretor_industrial playbook_sector=industria provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2479 tokens_out=125
[2026-04-12 19:40:29,959: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:29 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=836023a8-28c2-4805-855a-33c297ad7005
[2026-04-12 19:40:30,216: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:30 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:30,298: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:30 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:30,320: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:30 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:30,327: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:30 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:31,569: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:31 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=e07127a0-fb32-4877-be78-c212c1a23fb7 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=ti_saude playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2526 tokens_out=122
[2026-04-12 19:40:31,790: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:31 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=d15fc91a-db13-4730-b6b6-025323730050
[2026-04-12 19:40:32,042: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:32 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:32,101: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:32 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:32,125: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:32 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:32,131: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:32 [debug    ] openai.complete                json_mode=False model=gpt-4.1
 
 -------------- celery@5c7ad2c6c2b5 v5.6.3 (recovery)
--- ***** ----- 
-- ******* ---- Linux-5.15.0-116-generic-x86_64-with-glibc2.41 2026-04-12 19:40:32
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         prospector:0x7f2eebd0e030
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

[2026-04-12 19:40:34,463: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:34 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=6ed0b0f7-d9b4-4c51-a13d-45229a21a009 matched_role=None model=gpt-4.1-2025-04-14 playbook_role=ceo_fintech playbook_sector=seguros provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2338 tokens_out=148
[2026-04-12 19:40:34,694: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:34 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-12 19:40:35,006: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:35 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:35,089: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:35 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:35,118: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:35 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:35,124: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:35 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:36,048: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:36,054: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:36,083: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:36,099: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:36,143: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:36,147: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:36,169: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:36,176: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:36,178: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:36,193: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:36,194: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:36 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:36,202: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:36 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:36,203: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:36,222: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:36 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:36,224: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:36 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:36,244: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:36 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:48,720: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:48 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:48,725: WARNING/ForkPoolWorker-1] 2026-04-12 19:40:48 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:48,739: WARNING/ForkPoolWorker-4] 2026-04-12 19:40:48 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:48,832: WARNING/ForkPoolWorker-2] 2026-04-12 19:40:48 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:40:50,561: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:50 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=689e175c-50aa-40c9-bd0d-63e0fedb4d40 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=36 tokens_in=2511 tokens_out=132
[2026-04-12 19:40:50,759: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:50 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=86bd0508-eb97-4dcb-8897-242f2cbfb3db
[2026-04-12 19:40:51,061: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:51 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:40:51,137: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:51 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:40:51,158: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:51 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:40:51,163: WARNING/ForkPoolWorker-3] 2026-04-12 19:40:51 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:01,375: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:01 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:01,478: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:01 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:01,597: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:01 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:01,855: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:01 [info     ] ai_composer.compose_email      copy_method=AIRE few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=99fa5e1f-d887-4624-ab82-882766f2125d matched_role=None model=gpt-4.1-2025-04-14 playbook_role=None playbook_sector=None provider=openai step=1 step_key=email_first subject_len=56 tokens_in=2162 tokens_out=127
[2026-04-12 19:41:02,049: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:02 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2867e1d6-e06c-4780-acf5-ec5a6cd2524a
[2026-04-12 19:41:02,620: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:02 [info     ] cadence_tick.done              dispatched=11 skipped=0 tenants=1
[2026-04-12 19:41:02,856: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:02 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:02,934: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:02 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:02,958: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:02 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:02,963: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:02 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:07,338: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:07 [error    ] dispatch.error                 error='RetryError[<Future at 0x7f2ee4895850 state=finished raised RateLimitError>]' step_id=103abec0-a24c-41d7-b249-ad748519ee03
[2026-04-12 19:41:08,333: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:08 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=ti:ceo_cto_ti:email:first generation_mode=llm lead_id=677bef5e-5648-4ca5-b321-87a8d4e6ba8e matched_role=ceo_cto_ti model=gpt-4.1-2025-04-14 playbook_role=ceo_cto_ti playbook_sector=ti provider=openai step=1 step_key=email_first subject_len=48 tokens_in=2515 tokens_out=123
[2026-04-12 19:41:08,541: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:08 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=1bf3cc1c-9663-4e33-a344-f23c3a544833
[2026-04-12 19:41:08,839: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:08 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:08,894: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:08 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:08,916: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:08 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:08,921: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:08 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:09,291: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:09 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:09,342: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:09 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:09,363: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:09 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:09,369: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:09 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:12,318: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:12 [error    ] dispatch.error                 error='RetryError[<Future at 0x7f2ee4894f80 state=finished raised RateLimitError>]' step_id=d15fc91a-db13-4730-b6b6-025323730050
[2026-04-12 19:41:12,650: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:12 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:12,721: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:12 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:12,745: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:12 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:12,751: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:12 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:13,782: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:13 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:16,252: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:16 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=agencia:ceo_agencia:email:first generation_mode=llm lead_id=3f652e53-78be-48a4-8d95-ec09147c6d41 matched_role=ceo_agencia model=gpt-4.1-2025-04-14 playbook_role=ceo_agencia playbook_sector=agencia provider=openai step=1 step_key=email_first subject_len=52 tokens_in=2485 tokens_out=128
[2026-04-12 19:41:16,465: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:16 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=2e16ca2d-ec24-417e-b5fe-8399932ebe71
[2026-04-12 19:41:16,716: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:16 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:16,775: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:16 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:16,796: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:16 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:16,801: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:16 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:19,776: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:19 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=62c7322e-ce5e-4000-94a1-b59c65f9c937 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2515 tokens_out=162
[2026-04-12 19:41:20,005: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:20 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=49ebe07b-6bea-4ac9-9b70-3e0873ca3329
[2026-04-12 19:41:20,335: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:20 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:20,393: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:20 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:20,417: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:20 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:20,423: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:20 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:20,709: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:20 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:22,492: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:22 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=a1f06d2b-d94e-402a-a334-3777a3c89f1e matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=41 tokens_in=2510 tokens_out=130
[2026-04-12 19:41:22,705: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:22 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-12 19:41:22,982: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:22 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:23,050: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:23 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:23,069: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:23 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:23,077: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:23 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:25,556: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:25 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:27,040: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:27 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=6ed0b0f7-d9b4-4c51-a13d-45229a21a009 matched_role=None model=gpt-4.1-2025-04-14 playbook_role=ceo_fintech playbook_sector=seguros provider=openai step=1 step_key=email_first subject_len=44 tokens_in=2338 tokens_out=120
[2026-04-12 19:41:27,253: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:27 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-12 19:41:27,523: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:27 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:27,597: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:27 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:27,621: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:27 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:27,627: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:27 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:28,329: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:28 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:30,020: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:30 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=industria:diretor_industrial:email:first generation_mode=llm lead_id=7a3bcf26-c36b-4139-ab2b-bca9cc3d9c33 matched_role=diretor_industrial model=gpt-4.1-2025-04-14 playbook_role=diretor_industrial playbook_sector=industria provider=openai step=1 step_key=email_first subject_len=35 tokens_in=2479 tokens_out=128
[2026-04-12 19:41:30,093: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:30 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=ti:ceo_cto_ti:email:first generation_mode=llm lead_id=677bef5e-5648-4ca5-b321-87a8d4e6ba8e matched_role=ceo_cto_ti model=gpt-4.1-2025-04-14 playbook_role=ceo_cto_ti playbook_sector=ti provider=openai step=1 step_key=email_first subject_len=44 tokens_in=2515 tokens_out=116
[2026-04-12 19:41:30,282: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:30 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=836023a8-28c2-4805-855a-33c297ad7005
[2026-04-12 19:41:30,303: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:30 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=71be3033-145b-434b-a8d6-8752b8fd4ccf
[2026-04-12 19:41:30,592: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:30 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:30,613: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:30 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:30,683: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:30 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:30,693: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:30 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:30,714: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:30 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:30,719: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:30 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:30,719: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:30 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:30,725: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:30 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:32,176: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:32 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:32,874: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:32 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=f04ab743-8dbe-4c0c-90f1-c5eee87104fc matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=42 tokens_in=2512 tokens_out=143
[2026-04-12 19:41:33,064: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:33 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=103abec0-a24c-41d7-b249-ad748519ee03
[2026-04-12 19:41:33,320: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:33 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:33,394: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:33 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:33,424: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:33 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:33,430: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:33 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:39,396: WARNING/ForkPoolWorker-3] 2026-04-12 19:41:39 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:41,490: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:41 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:43,127: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:43 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=6ed0b0f7-d9b4-4c51-a13d-45229a21a009 matched_role=None model=gpt-4.1-2025-04-14 playbook_role=ceo_fintech playbook_sector=seguros provider=openai step=1 step_key=email_first subject_len=54 tokens_in=2338 tokens_out=121
[2026-04-12 19:41:43,338: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:43 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-12 19:41:43,552: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:43 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:43,617: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:43 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:43,644: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:43 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:43,651: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:43 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:44,866: WARNING/ForkPoolWorker-2] 2026-04-12 19:41:44 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:45,185: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:45 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:47,409: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:47 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=ti:ceo_cto_ti:email:first generation_mode=llm lead_id=677bef5e-5648-4ca5-b321-87a8d4e6ba8e matched_role=ceo_cto_ti model=gpt-4.1-2025-04-14 playbook_role=ceo_cto_ti playbook_sector=ti provider=openai step=1 step_key=email_first subject_len=44 tokens_in=2515 tokens_out=126
[2026-04-12 19:41:47,608: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:47 [error    ] dispatch.error                 error="Client error '401 Unauthorized' for url 'https://api36.unipile.com:16621/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401" step_id=1bf3cc1c-9663-4e33-a344-f23c3a544833
[2026-04-12 19:41:47,877: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:47 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 19:41:47,955: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:47 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 19:41:47,981: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:47 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 19:41:47,986: WARNING/ForkPoolWorker-4] 2026-04-12 19:41:47 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 19:41:50,225: WARNING/ForkPoolWorker-1] 2026-04-12 19:41:50 [info     ] ai_composer.compose_email      copy_method=AIRE few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=99fa5e1f-d887-4624-ab82-882766f2125d matched_role=None model=gpt-4.1-2025-04-14 playbook_role=None playbook_sector=None provider=openai step=1 step_key=email_first subject_len=43 tokens_in=2162 tokens_out=134
 
 -------------- celery@eb561b6f35ca v5.6.3 (recovery)
--- ***** ----- 
-- ******* ---- Linux-5.15.0-116-generic-x86_64-with-glibc2.41 2026-04-12 21:58:22
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         prospector:0x7fa624551b20
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

[2026-04-12 21:58:25,200: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:25,238: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:25,251: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:25,257: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:25,280: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:25,304: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:25,311: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:25,325: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:25,331: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:25 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:25,342: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:25,344: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:25 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:25,357: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:25,358: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:25,374: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:25 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:25,382: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:25 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:25,406: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:25 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:27,681: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:27 [debug    ] llm.usage_recorded             estimated_cost_usd=0.005692 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2465
[2026-04-12 21:58:27,682: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:27 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=6ed0b0f7-d9b4-4c51-a13d-45229a21a009 matched_role=None model=gpt-4.1-2025-04-14 playbook_role=ceo_fintech playbook_sector=seguros provider=openai step=1 step_key=email_first subject_len=43 tokens_in=2338 tokens_out=127
[2026-04-12 21:58:27,889: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:27 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-12 21:58:27,981: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:27 [debug    ] llm.usage_recorded             estimated_cost_usd=0.0055 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2309
[2026-04-12 21:58:27,981: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:27 [info     ] ai_composer.compose_email      copy_method=AIRE few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=99fa5e1f-d887-4624-ab82-882766f2125d matched_role=None model=gpt-4.1-2025-04-14 playbook_role=None playbook_sector=None provider=openai step=1 step_key=email_first subject_len=47 tokens_in=2162 tokens_out=147
[2026-04-12 21:58:28,047: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:28 [debug    ] llm.usage_recorded             estimated_cost_usd=0.005934 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2601
[2026-04-12 21:58:28,048: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:28 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=industria:diretor_industrial:email:first generation_mode=llm lead_id=7a3bcf26-c36b-4139-ab2b-bca9cc3d9c33 matched_role=diretor_industrial model=gpt-4.1-2025-04-14 playbook_role=diretor_industrial playbook_sector=industria provider=openai step=1 step_key=email_first subject_len=45 tokens_in=2479 tokens_out=122
[2026-04-12 21:58:28,213: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:28 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=2867e1d6-e06c-4780-acf5-ec5a6cd2524a
[2026-04-12 21:58:28,245: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:28 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=836023a8-28c2-4805-855a-33c297ad7005
[2026-04-12 21:58:28,313: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:28,409: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:28,424: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:28,429: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:28 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:28,529: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:28,589: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:28,595: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:28,623: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:28,629: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:28 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:28,671: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:28,697: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:28 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:28,705: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:28 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:38,836: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:38 [debug    ] llm.usage_recorded             estimated_cost_usd=0.006422 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2689
[2026-04-12 21:58:38,837: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:38 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=62c7322e-ce5e-4000-94a1-b59c65f9c937 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=51 tokens_in=2515 tokens_out=174
[2026-04-12 21:58:39,047: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:39 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=49ebe07b-6bea-4ac9-9b70-3e0873ca3329
[2026-04-12 21:58:39,348: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:39 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:39,409: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:39 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:39,430: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:39 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:39,435: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:39 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:40,218: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:40 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:41,043: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:41 [debug    ] llm.usage_recorded             estimated_cost_usd=0.006066 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2622
[2026-04-12 21:58:41,044: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:41 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=agencia:ceo_agencia:email:first generation_mode=llm lead_id=3f652e53-78be-48a4-8d95-ec09147c6d41 matched_role=ceo_agencia model=gpt-4.1-2025-04-14 playbook_role=ceo_agencia playbook_sector=agencia provider=openai step=1 step_key=email_first subject_len=45 tokens_in=2485 tokens_out=137
[2026-04-12 21:58:41,251: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:41 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=2e16ca2d-ec24-417e-b5fe-8399932ebe71
[2026-04-12 21:58:41,496: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:41 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:41,562: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:41 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:41,585: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:41 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:41,590: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:41 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:41,660: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:41 [debug    ] llm.usage_recorded             estimated_cost_usd=0.006312 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2673
[2026-04-12 21:58:41,661: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:41 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=f04ab743-8dbe-4c0c-90f1-c5eee87104fc matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=46 tokens_in=2512 tokens_out=161
[2026-04-12 21:58:41,873: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:41 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=103abec0-a24c-41d7-b249-ad748519ee03
[2026-04-12 21:58:42,090: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:42 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:42,148: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:42 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:42,168: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:42 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:42,174: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:42 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:51,129: WARNING/ForkPoolWorker-4] 2026-04-12 21:58:51 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:52,711: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:52 [debug    ] llm.usage_recorded             estimated_cost_usd=0.006116 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2659
[2026-04-12 21:58:52,712: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:52 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=e07127a0-fb32-4877-be78-c212c1a23fb7 matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=ti_saude playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=46 tokens_in=2526 tokens_out=133
[2026-04-12 21:58:52,883: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:52 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=d15fc91a-db13-4730-b6b6-025323730050
[2026-04-12 21:58:53,139: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:53 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:53,214: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:53 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:53,232: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:53 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:53,238: WARNING/ForkPoolWorker-1] 2026-04-12 21:58:53 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:53,343: WARNING/ForkPoolWorker-2] 2026-04-12 21:58:53 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:53,883: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:53 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:58:56,085: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:56 [debug    ] llm.usage_recorded             estimated_cost_usd=0.006356 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2677
[2026-04-12 21:58:56,085: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:56 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=a1f06d2b-d94e-402a-a334-3777a3c89f1e matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=53 tokens_in=2510 tokens_out=167
[2026-04-12 21:58:56,302: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:56 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-12 21:58:56,332: ERROR/ForkPoolWorker-3] Task workers.dispatch.dispatch_step[2950f473-20d2-456b-94fc-777e349791b0] raised unexpected: RuntimeError("HTTPStatusError: Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400")
Traceback (most recent call last):
  File "/app/workers/dispatch.py", line 475, in _dispatch_async
    _r = await unipile_client.send_email(
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/integrations/unipile_client.py", line 297, in send_email
    response.raise_for_status()
  File "/venv/lib/python3.12/site-packages/httpx/_models.py", line 829, in raise_for_status
    raise HTTPStatusError(message, request=request, response=self)
httpx.HTTPStatusError: Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400

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
  File "/app/workers/dispatch.py", line 648, in _dispatch_async
    raise task.retry(exc=RuntimeError(f"{type(exc).__name__}: {exc}"))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 769, in retry
    raise_with_context(exc)
  File "/venv/lib/python3.12/site-packages/celery/utils/serialization.py", line 273, in raise_with_context
    raise exc from exc_info[1]
RuntimeError: HTTPStatusError: Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400
[2026-04-12 21:58:56,567: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:56 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-12 21:58:56,627: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:56 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-12 21:58:56,639: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:56 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-12 21:58:56,645: WARNING/ForkPoolWorker-3] 2026-04-12 21:58:56 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:59:03,819: WARNING/ForkPoolWorker-4] 2026-04-12 21:59:03 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:59:05,828: WARNING/ForkPoolWorker-1] 2026-04-12 21:59:05 [debug    ] llm.usage_recorded             estimated_cost_usd=0.006156 model=gpt-4.1-2025-04-14 module=cadence provider=openai task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=2652
[2026-04-12 21:59:05,829: WARNING/ForkPoolWorker-1] 2026-04-12 21:59:05 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=a1f06d2b-d94e-402a-a334-3777a3c89f1e matched_role=diretor_clinica model=gpt-4.1-2025-04-14 playbook_role=diretor_clinica playbook_sector=saude provider=openai step=1 step_key=email_first subject_len=51 tokens_in=2510 tokens_out=142
[2026-04-12 21:59:06,015: WARNING/ForkPoolWorker-1] 2026-04-12 21:59:06 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-12 21:59:06,027: WARNING/ForkPoolWorker-2] 2026-04-12 21:59:06 [debug    ] openai.complete                json_mode=False model=gpt-4.1
[2026-04-12 21:59:06,287: WARNING/ForkPoolWorker-1] 2026-04-12 21:59:06 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 00:40:29,572: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:29 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:33,573: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:33 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:33,979: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:33 [debug    ] llm.usage_recorded             estimated_cost_usd=0.004741 model=claude-haiku-4-5-20251001 module=cadence provider=anthropic task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=3537
[2026-04-13 00:40:33,980: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:33 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=a1f06d2b-d94e-402a-a334-3777a3c89f1e matched_role=diretor_clinica model=claude-haiku-4-5-20251001 playbook_role=diretor_clinica playbook_sector=saude provider=anthropic step=1 step_key=email_first subject_len=48 tokens_in=3236 tokens_out=301
[2026-04-13 00:40:34,155: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:34 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-13 00:40:34,441: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:34 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 00:40:34,514: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:34 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 00:40:34,534: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:34 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 00:40:34,539: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:34 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:36,271: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:36 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:36,319: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:36 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:36,544: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:36 [debug    ] llm.usage_recorded             estimated_cost_usd=0.003976 model=claude-haiku-4-5-20251001 module=cadence provider=anthropic task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=3196
[2026-04-13 00:40:36,545: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:36 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=False few_shot_key=None generation_mode=llm lead_id=6ed0b0f7-d9b4-4c51-a13d-45229a21a009 matched_role=None model=claude-haiku-4-5-20251001 playbook_role=ceo_fintech playbook_sector=seguros provider=anthropic step=1 step_key=email_first subject_len=54 tokens_in=3001 tokens_out=195
[2026-04-13 00:40:36,721: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:36 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=22e5e6f9-a04c-4a5e-a161-6ca3052a4faf
[2026-04-13 00:40:36,988: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:36 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 00:40:37,046: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:37 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 00:40:37,060: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:37 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 00:40:37,065: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:37 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:40,157: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:40 [debug    ] llm.usage_recorded             estimated_cost_usd=0.004419 model=claude-haiku-4-5-20251001 module=cadence provider=anthropic task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=3475
[2026-04-13 00:40:40,157: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:40 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=689e175c-50aa-40c9-bd0d-63e0fedb4d40 matched_role=diretor_clinica model=claude-haiku-4-5-20251001 playbook_role=diretor_clinica playbook_sector=saude provider=anthropic step=1 step_key=email_first subject_len=47 tokens_in=3239 tokens_out=236
[2026-04-13 00:40:40,333: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:40 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=86bd0508-eb97-4dcb-8897-242f2cbfb3db
[2026-04-13 00:40:40,586: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:40 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 00:40:40,672: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:40 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 00:40:40,702: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:40 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 00:40:40,706: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:40 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:44,145: WARNING/ForkPoolWorker-1] 2026-04-13 00:40:44 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:44,581: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:44 [debug    ] llm.usage_recorded             estimated_cost_usd=0.004576 model=claude-haiku-4-5-20251001 module=cadence provider=anthropic task_type=compose_email tenant_id=c00948b6-76d7-4d9c-8cd5-ba90663af6ac total_tokens=3504
[2026-04-13 00:40:44,582: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:44 [info     ] ai_composer.compose_email      copy_method=DIS few_shot_applied=True few_shot_key=saude:diretor_clinica:email:first generation_mode=llm lead_id=a1f06d2b-d94e-402a-a334-3777a3c89f1e matched_role=diretor_clinica model=claude-haiku-4-5-20251001 playbook_role=diretor_clinica playbook_sector=saude provider=anthropic step=1 step_key=email_first subject_len=43 tokens_in=3236 tokens_out=268
[2026-04-13 00:40:44,759: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:44 [error    ] dispatch.error                 error="Client error '400 Bad Request' for url 'https://api38.unipile.com:16847/api/v1/emails'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400" step_id=40d4703b-d65d-45ba-b07e-aaf04422f140
[2026-04-13 00:40:45,019: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:45 [info     ] llm.registry.provider_loaded   provider=openai
[2026-04-13 00:40:45,092: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:45 [info     ] llm.registry.provider_loaded   provider=gemini
[2026-04-13 00:40:45,117: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:45 [info     ] llm.registry.provider_loaded   provider=anthropic
[2026-04-13 00:40:45,123: WARNING/ForkPoolWorker-4] 2026-04-13 00:40:45 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:47,314: WARNING/ForkPoolWorker-3] 2026-04-13 00:40:47 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:47,722: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:47 [debug    ] anthropic.complete             json_mode=False model=claude-haiku-4-5-20251001
[2026-04-13 00:40:49,119: WARNI

==================
Log do worker content:

 
 -------------- celery@08bd6892c2ad v5.6.3 (recovery)
--- ***** ----- 
-- ******* ---- Linux-5.15.0-116-generic-x86_64-with-glibc2.41 2026-04-12 21:58:21
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         prospector:0x7f673b269460
- ** ---------- .> transport:   redis://default:**@chatwoot_redis_prospector_llm:6379/0
- ** ---------- .> results:     redis://default:**@chatwoot_redis_prospector_llm:6379/1
- *** --- * --- .> concurrency: 2 (prefork)
-- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
--- ***** ----- 
 -------------- [queues]
                .> content          exchange=prospector(direct) key=content
                .> content-engagement exchange=prospector(direct) key=content-engagement

[2026-04-12 21:59:00,368: WARNING/ForkPoolWorker-2] 2026-04-12 21:59:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T21:59:00.039923+00:00 dispatched=0
[2026-04-12 22:00:00,144: WARNING/ForkPoolWorker-2] 2026-04-12 22:00:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:00:00.042703+00:00 dispatched=0
[2026-04-12 22:01:00,139: WARNING/ForkPoolWorker-2] 2026-04-12 22:01:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:01:00.022633+00:00 dispatched=0
[2026-04-12 22:02:00,124: WARNING/ForkPoolWorker-2] 2026-04-12 22:02:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:02:00.018101+00:00 dispatched=0
[2026-04-12 22:03:00,094: WARNING/ForkPoolWorker-2] 2026-04-12 22:03:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:03:00.012447+00:00 dispatched=0
[2026-04-12 22:04:00,101: WARNING/ForkPoolWorker-2] 2026-04-12 22:04:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:04:00.016198+00:00 dispatched=0
[2026-04-12 22:05:00,141: WARNING/ForkPoolWorker-2] 2026-04-12 22:05:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:05:00.025938+00:00 dispatched=0
[2026-04-12 22:06:00,124: WARNING/ForkPoolWorker-2] 2026-04-12 22:06:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:06:00.022201+00:00 dispatched=0
[2026-04-12 22:07:00,138: WARNING/ForkPoolWorker-2] 2026-04-12 22:07:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:07:00.007689+00:00 dispatched=0
[2026-04-12 22:08:00,107: WARNING/ForkPoolWorker-2] 2026-04-12 22:08:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:08:00.017241+00:00 dispatched=0
[2026-04-12 22:09:00,123: WARNING/ForkPoolWorker-2] 2026-04-12 22:09:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:09:00.008024+00:00 dispatched=0
[2026-04-12 22:10:00,136: WARNING/ForkPoolWorker-2] 2026-04-12 22:10:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:10:00.022090+00:00 dispatched=0
[2026-04-12 22:11:00,113: WARNING/ForkPoolWorker-2] 2026-04-12 22:11:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:11:00.012434+00:00 dispatched=0
[2026-04-12 22:12:00,091: WARNING/ForkPoolWorker-2] 2026-04-12 22:12:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:12:00.017114+00:00 dispatched=0
[2026-04-12 22:13:00,124: WARNING/ForkPoolWorker-2] 2026-04-12 22:13:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:13:00.010307+00:00 dispatched=0
[2026-04-12 22:14:00,148: WARNING/ForkPoolWorker-2] 2026-04-12 22:14:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:14:00.023205+00:00 dispatched=0
[2026-04-12 22:15:00,113: WARNING/ForkPoolWorker-2] 2026-04-12 22:15:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:15:00.015763+00:00 dispatched=0
[2026-04-12 22:16:00,096: WARNING/ForkPoolWorker-2] 2026-04-12 22:16:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:16:00.014814+00:00 dispatched=0
[2026-04-12 22:17:00,100: WARNING/ForkPoolWorker-2] 2026-04-12 22:17:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:17:00.011327+00:00 dispatched=0
[2026-04-12 22:18:00,135: WARNING/ForkPoolWorker-2] 2026-04-12 22:18:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:18:00.016478+00:00 dispatched=0
[2026-04-12 22:19:00,126: WARNING/ForkPoolWorker-2] 2026-04-12 22:19:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:19:00.020851+00:00 dispatched=0
[2026-04-12 22:20:00,139: WARNING/ForkPoolWorker-2] 2026-04-12 22:20:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:20:00.026459+00:00 dispatched=0
[2026-04-12 22:21:00,126: WARNING/ForkPoolWorker-2] 2026-04-12 22:21:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:21:00.018469+00:00 dispatched=0
[2026-04-12 22:22:00,148: WARNING/ForkPoolWorker-2] 2026-04-12 22:22:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:22:00.020546+00:00 dispatched=0
[2026-04-12 22:23:00,136: WARNING/ForkPoolWorker-2] 2026-04-12 22:23:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:23:00.017508+00:00 dispatched=0
[2026-04-12 22:24:00,132: WARNING/ForkPoolWorker-2] 2026-04-12 22:24:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:24:00.014794+00:00 dispatched=0
[2026-04-12 22:25:00,129: WARNING/ForkPoolWorker-2] 2026-04-12 22:25:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:25:00.012643+00:00 dispatched=0
[2026-04-12 22:26:00,123: WARNING/ForkPoolWorker-2] 2026-04-12 22:26:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:26:00.014810+00:00 dispatched=0
[2026-04-12 22:27:00,097: WARNING/ForkPoolWorker-2] 2026-04-12 22:27:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:27:00.009333+00:00 dispatched=0
[2026-04-12 22:28:00,147: WARNING/ForkPoolWorker-2] 2026-04-12 22:28:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:28:00.027737+00:00 dispatched=0
[2026-04-12 22:29:00,099: WARNING/ForkPoolWorker-2] 2026-04-12 22:29:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:29:00.011206+00:00 dispatched=0
[2026-04-12 22:30:00,158: WARNING/ForkPoolWorker-2] 2026-04-12 22:30:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:30:00.031389+00:00 dispatched=0
[2026-04-12 22:31:00,096: WARNING/ForkPoolWorker-2] 2026-04-12 22:31:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:31:00.018730+00:00 dispatched=0
[2026-04-12 22:32:00,112: WARNING/ForkPoolWorker-2] 2026-04-12 22:32:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:32:00.014773+00:00 dispatched=0
[2026-04-12 22:33:00,111: WARNING/ForkPoolWorker-2] 2026-04-12 22:33:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:33:00.012288+00:00 dispatched=0
[2026-04-12 22:34:00,107: WARNING/ForkPoolWorker-2] 2026-04-12 22:34:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:34:00.009623+00:00 dispatched=0
[2026-04-12 22:35:00,118: WARNING/ForkPoolWorker-2] 2026-04-12 22:35:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:35:00.015592+00:00 dispatched=0
[2026-04-12 22:36:00,119: WARNING/ForkPoolWorker-2] 2026-04-12 22:36:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:36:00.020749+00:00 dispatched=0
[2026-04-12 22:37:00,141: WARNING/ForkPoolWorker-2] 2026-04-12 22:37:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:37:00.012134+00:00 dispatched=0
[2026-04-12 22:38:00,121: WARNING/ForkPoolWorker-2] 2026-04-12 22:38:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:38:00.029559+00:00 dispatched=0
[2026-04-12 22:39:00,107: WARNING/ForkPoolWorker-2] 2026-04-12 22:39:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:39:00.014356+00:00 dispatched=0
[2026-04-12 22:40:00,138: WARNING/ForkPoolWorker-2] 2026-04-12 22:40:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:40:00.032287+00:00 dispatched=0
[2026-04-12 22:41:00,109: WARNING/ForkPoolWorker-2] 2026-04-12 22:41:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:41:00.014254+00:00 dispatched=0
[2026-04-12 22:42:00,118: WARNING/ForkPoolWorker-2] 2026-04-12 22:42:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:42:00.014415+00:00 dispatched=0
[2026-04-12 22:43:00,115: WARNING/ForkPoolWorker-2] 2026-04-12 22:43:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:43:00.013392+00:00 dispatched=0
[2026-04-12 22:44:00,097: WARNING/ForkPoolWorker-2] 2026-04-12 22:44:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:44:00.018178+00:00 dispatched=0
[2026-04-12 22:45:00,138: WARNING/ForkPoolWorker-2] 2026-04-12 22:45:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:45:00.025270+00:00 dispatched=0
[2026-04-12 22:46:00,120: WARNING/ForkPoolWorker-2] 2026-04-12 22:46:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:46:00.016907+00:00 dispatched=0
[2026-04-12 22:47:00,109: WARNING/ForkPoolWorker-2] 2026-04-12 22:47:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:47:00.017365+00:00 dispatched=0
[2026-04-12 22:48:00,132: WARNING/ForkPoolWorker-2] 2026-04-12 22:48:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:48:00.013226+00:00 dispatched=0
[2026-04-12 22:49:00,130: WARNING/ForkPoolWorker-2] 2026-04-12 22:49:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:49:00.023660+00:00 dispatched=0
[2026-04-12 22:50:00,142: WARNING/ForkPoolWorker-2] 2026-04-12 22:50:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:50:00.021610+00:00 dispatched=0
[2026-04-12 22:51:00,132: WARNING/ForkPoolWorker-2] 2026-04-12 22:51:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:51:00.023069+00:00 dispatched=0
[2026-04-12 22:52:00,113: WARNING/ForkPoolWorker-2] 2026-04-12 22:52:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:52:00.012371+00:00 dispatched=0
[2026-04-12 22:53:00,125: WARNING/ForkPoolWorker-2] 2026-04-12 22:53:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:53:00.021973+00:00 dispatched=0
[2026-04-12 22:54:00,142: WARNING/ForkPoolWorker-2] 2026-04-12 22:54:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:54:00.020971+00:00 dispatched=0
[2026-04-12 22:55:00,101: WARNING/ForkPoolWorker-2] 2026-04-12 22:55:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:55:00.020899+00:00 dispatched=0
[2026-04-12 22:56:00,148: WARNING/ForkPoolWorker-2] 2026-04-12 22:56:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:56:00.015927+00:00 dispatched=0
[2026-04-12 22:57:00,097: WARNING/ForkPoolWorker-2] 2026-04-12 22:57:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:57:00.017816+00:00 dispatched=0
[2026-04-12 22:58:00,105: WARNING/ForkPoolWorker-2] 2026-04-12 22:58:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:58:00.013821+00:00 dispatched=0
[2026-04-12 22:59:00,124: WARNING/ForkPoolWorker-2] 2026-04-12 22:59:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T22:59:00.014721+00:00 dispatched=0
[2026-04-12 23:00:00,140: WARNING/ForkPoolWorker-2] 2026-04-12 23:00:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:00:00.022916+00:00 dispatched=0
[2026-04-12 23:01:00,117: WARNING/ForkPoolWorker-2] 2026-04-12 23:01:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:01:00.016110+00:00 dispatched=0
[2026-04-12 23:02:00,130: WARNING/ForkPoolWorker-2] 2026-04-12 23:02:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:02:00.011513+00:00 dispatched=0
[2026-04-12 23:03:00,103: WARNING/ForkPoolWorker-2] 2026-04-12 23:03:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:03:00.019972+00:00 dispatched=0
[2026-04-12 23:04:00,119: WARNING/ForkPoolWorker-2] 2026-04-12 23:04:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:04:00.017203+00:00 dispatched=0
[2026-04-12 23:05:00,102: WARNING/ForkPoolWorker-2] 2026-04-12 23:05:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:05:00.024792+00:00 dispatched=0
[2026-04-12 23:06:00,091: WARNING/ForkPoolWorker-2] 2026-04-12 23:06:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:06:00.011095+00:00 dispatched=0
[2026-04-12 23:07:00,104: WARNING/ForkPoolWorker-2] 2026-04-12 23:07:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:07:00.023123+00:00 dispatched=0
[2026-04-12 23:08:00,096: WARNING/ForkPoolWorker-2] 2026-04-12 23:08:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:08:00.011873+00:00 dispatched=0
[2026-04-12 23:09:00,131: WARNING/ForkPoolWorker-2] 2026-04-12 23:09:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:09:00.014253+00:00 dispatched=0
[2026-04-12 23:10:00,108: WARNING/ForkPoolWorker-2] 2026-04-12 23:10:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:10:00.013400+00:00 dispatched=0
[2026-04-12 23:11:00,136: WARNING/ForkPoolWorker-2] 2026-04-12 23:11:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:11:00.019920+00:00 dispatched=0
[2026-04-12 23:12:00,108: WARNING/ForkPoolWorker-2] 2026-04-12 23:12:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:12:00.014940+00:00 dispatched=0
[2026-04-12 23:13:00,158: WARNING/ForkPoolWorker-2] 2026-04-12 23:13:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:13:00.020467+00:00 dispatched=0
[2026-04-12 23:14:00,099: WARNING/ForkPoolWorker-2] 2026-04-12 23:14:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:14:00.010355+00:00 dispatched=0
[2026-04-12 23:15:00,117: WARNING/ForkPoolWorker-2] 2026-04-12 23:15:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:15:00.026923+00:00 dispatched=0
[2026-04-12 23:16:00,106: WARNING/ForkPoolWorker-2] 2026-04-12 23:16:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:16:00.011870+00:00 dispatched=0
[2026-04-12 23:17:00,115: WARNING/ForkPoolWorker-2] 2026-04-12 23:17:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:17:00.017541+00:00 dispatched=0
[2026-04-12 23:18:00,110: WARNING/ForkPoolWorker-2] 2026-04-12 23:18:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:18:00.011780+00:00 dispatched=0
[2026-04-12 23:19:00,119: WARNING/ForkPoolWorker-2] 2026-04-12 23:19:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:19:00.015540+00:00 dispatched=0
[2026-04-12 23:20:00,127: WARNING/ForkPoolWorker-2] 2026-04-12 23:20:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:20:00.021050+00:00 dispatched=0
[2026-04-12 23:21:00,093: WARNING/ForkPoolWorker-2] 2026-04-12 23:21:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:21:00.009739+00:00 dispatched=0
[2026-04-12 23:22:00,154: WARNING/ForkPoolWorker-2] 2026-04-12 23:22:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:22:00.019393+00:00 dispatched=0
[2026-04-12 23:23:00,121: WARNING/ForkPoolWorker-2] 2026-04-12 23:23:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:23:00.012419+00:00 dispatched=0
[2026-04-12 23:24:00,106: WARNING/ForkPoolWorker-2] 2026-04-12 23:24:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:24:00.010168+00:00 dispatched=0
[2026-04-12 23:25:00,133: WARNING/ForkPoolWorker-2] 2026-04-12 23:25:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:25:00.028230+00:00 dispatched=0
[2026-04-12 23:26:00,145: WARNING/ForkPoolWorker-2] 2026-04-12 23:26:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:26:00.017390+00:00 dispatched=0
[2026-04-12 23:27:00,124: WARNING/ForkPoolWorker-2] 2026-04-12 23:27:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:27:00.019496+00:00 dispatched=0
[2026-04-12 23:28:00,131: WARNING/ForkPoolWorker-2] 2026-04-12 23:28:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:28:00.012608+00:00 dispatched=0
[2026-04-12 23:29:00,126: WARNING/ForkPoolWorker-2] 2026-04-12 23:29:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:29:00.018747+00:00 dispatched=0
[2026-04-12 23:30:00,125: WARNING/ForkPoolWorker-2] 2026-04-12 23:30:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:30:00.029611+00:00 dispatched=0
[2026-04-12 23:31:00,119: WARNING/ForkPoolWorker-2] 2026-04-12 23:31:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:31:00.013760+00:00 dispatched=0
[2026-04-12 23:32:00,131: WARNING/ForkPoolWorker-2] 2026-04-12 23:32:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:32:00.021284+00:00 dispatched=0
[2026-04-12 23:33:00,129: WARNING/ForkPoolWorker-2] 2026-04-12 23:33:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:33:00.023804+00:00 dispatched=0
[2026-04-12 23:34:00,130: WARNING/ForkPoolWorker-2] 2026-04-12 23:34:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:34:00.016307+00:00 dispatched=0
[2026-04-12 23:35:00,142: WARNING/ForkPoolWorker-2] 2026-04-12 23:35:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:35:00.021259+00:00 dispatched=0
[2026-04-12 23:36:00,097: WARNING/ForkPoolWorker-2] 2026-04-12 23:36:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:36:00.011713+00:00 dispatched=0
[2026-04-12 23:37:00,122: WARNING/ForkPoolWorker-2] 2026-04-12 23:37:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:37:00.019948+00:00 dispatched=0
[2026-04-12 23:38:00,148: WARNING/ForkPoolWorker-2] 2026-04-12 23:38:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:38:00.019455+00:00 dispatched=0
[2026-04-12 23:39:00,116: WARNING/ForkPoolWorker-2] 2026-04-12 23:39:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:39:00.008896+00:00 dispatched=0
[2026-04-12 23:40:00,144: WARNING/ForkPoolWorker-2] 2026-04-12 23:40:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:40:00.017160+00:00 dispatched=0
[2026-04-12 23:41:00,129: WARNING/ForkPoolWorker-2] 2026-04-12 23:41:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:41:00.022205+00:00 dispatched=0
[2026-04-12 23:42:00,115: WARNING/ForkPoolWorker-2] 2026-04-12 23:42:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:42:00.010163+00:00 dispatched=0
[2026-04-12 23:43:00,108: WARNING/ForkPoolWorker-2] 2026-04-12 23:43:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:43:00.025503+00:00 dispatched=0
[2026-04-12 23:44:00,109: WARNING/ForkPoolWorker-2] 2026-04-12 23:44:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:44:00.013798+00:00 dispatched=0
[2026-04-12 23:45:00,103: WARNING/ForkPoolWorker-2] 2026-04-12 23:45:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:45:00.023222+00:00 dispatched=0
[2026-04-12 23:46:00,115: WARNING/ForkPoolWorker-2] 2026-04-12 23:46:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:46:00.015615+00:00 dispatched=0
[2026-04-12 23:47:00,117: WARNING/ForkPoolWorker-2] 2026-04-12 23:47:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:47:00.012886+00:00 dispatched=0
[2026-04-12 23:48:00,116: WARNING/ForkPoolWorker-2] 2026-04-12 23:48:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:48:00.009345+00:00 dispatched=0
[2026-04-12 23:49:00,107: WARNING/ForkPoolWorker-2] 2026-04-12 23:49:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:49:00.014076+00:00 dispatched=0
[2026-04-12 23:50:00,133: WARNING/ForkPoolWorker-2] 2026-04-12 23:50:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:50:00.019513+00:00 dispatched=0
[2026-04-12 23:51:00,127: WARNING/ForkPoolWorker-2] 2026-04-12 23:51:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:51:00.012713+00:00 dispatched=0
[2026-04-12 23:52:00,097: WARNING/ForkPoolWorker-2] 2026-04-12 23:52:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:52:00.013650+00:00 dispatched=0
[2026-04-12 23:53:00,148: WARNING/ForkPoolWorker-2] 2026-04-12 23:53:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:53:00.019922+00:00 dispatched=0
[2026-04-12 23:54:00,093: WARNING/ForkPoolWorker-2] 2026-04-12 23:54:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:54:00.013492+00:00 dispatched=0
[2026-04-12 23:55:00,136: WARNING/ForkPoolWorker-2] 2026-04-12 23:55:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:55:00.013100+00:00 dispatched=0
[2026-04-12 23:56:00,115: WARNING/ForkPoolWorker-2] 2026-04-12 23:56:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:56:00.018829+00:00 dispatched=0
[2026-04-12 23:57:00,139: WARNING/ForkPoolWorker-2] 2026-04-12 23:57:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:57:00.018736+00:00 dispatched=0
[2026-04-12 23:58:00,106: WARNING/ForkPoolWorker-2] 2026-04-12 23:58:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:58:00.020837+00:00 dispatched=0
[2026-04-12 23:59:00,095: WARNING/ForkPoolWorker-2] 2026-04-12 23:59:00 [info     ] content.check_scheduled.done   checked_at=2026-04-12T23:59:00.009191+00:00 dispatched=0
[2026-04-13 00:00:00,140: WARNING/ForkPoolWorker-2] 2026-04-13 00:00:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:00:00.026078+00:00 dispatched=0
[2026-04-13 00:01:00,133: WARNING/ForkPoolWorker-2] 2026-04-13 00:01:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:01:00.015986+00:00 dispatched=0
[2026-04-13 00:02:00,080: WARNING/ForkPoolWorker-2] 2026-04-13 00:02:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:02:00.012483+00:00 dispatched=0
[2026-04-13 00:03:00,123: WARNING/ForkPoolWorker-2] 2026-04-13 00:03:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:03:00.008864+00:00 dispatched=0
[2026-04-13 00:04:00,126: WARNING/ForkPoolWorker-2] 2026-04-13 00:04:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:04:00.013103+00:00 dispatched=0
[2026-04-13 00:05:00,165: WARNING/ForkPoolWorker-2] 2026-04-13 00:05:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:05:00.018330+00:00 dispatched=0
[2026-04-13 00:06:00,134: WARNING/ForkPoolWorker-2] 2026-04-13 00:06:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:06:00.015454+00:00 dispatched=0
[2026-04-13 00:07:00,131: WARNING/ForkPoolWorker-2] 2026-04-13 00:07:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:07:00.013985+00:00 dispatched=0
[2026-04-13 00:08:00,096: WARNING/ForkPoolWorker-2] 2026-04-13 00:08:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:08:00.012954+00:00 dispatched=0
[2026-04-13 00:09:00,128: WARNING/ForkPoolWorker-2] 2026-04-13 00:09:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:09:00.012007+00:00 dispatched=0
[2026-04-13 00:10:00,119: WARNING/ForkPoolWorker-2] 2026-04-13 00:10:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:10:00.011369+00:00 dispatched=0
[2026-04-13 00:11:00,110: WARNING/ForkPoolWorker-2] 2026-04-13 00:11:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:11:00.018531+00:00 dispatched=0
[2026-04-13 00:12:00,127: WARNING/ForkPoolWorker-2] 2026-04-13 00:12:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:12:00.014079+00:00 dispatched=0
[2026-04-13 00:13:00,109: WARNING/ForkPoolWorker-2] 2026-04-13 00:13:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:13:00.010132+00:00 dispatched=0
[2026-04-13 00:14:00,127: WARNING/ForkPoolWorker-2] 2026-04-13 00:14:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:14:00.014493+00:00 dispatched=0
[2026-04-13 00:15:00,119: WARNING/ForkPoolWorker-2] 2026-04-13 00:15:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:15:00.017889+00:00 dispatched=0
[2026-04-13 00:16:00,128: WARNING/ForkPoolWorker-2] 2026-04-13 00:16:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:16:00.014969+00:00 dispatched=0
[2026-04-13 00:17:00,144: WARNING/ForkPoolWorker-2] 2026-04-13 00:17:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:17:00.014590+00:00 dispatched=0
[2026-04-13 00:18:00,122: WARNING/ForkPoolWorker-2] 2026-04-13 00:18:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:18:00.016954+00:00 dispatched=0
[2026-04-13 00:19:00,106: WARNING/ForkPoolWorker-2] 2026-04-13 00:19:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:19:00.017034+00:00 dispatched=0
[2026-04-13 00:20:00,113: WARNING/ForkPoolWorker-2] 2026-04-13 00:20:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:20:00.017669+00:00 dispatched=0
[2026-04-13 00:21:00,107: WARNING/ForkPoolWorker-2] 2026-04-13 00:21:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:21:00.011781+00:00 dispatched=0
[2026-04-13 00:22:00,120: WARNING/ForkPoolWorker-2] 2026-04-13 00:22:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:22:00.021161+00:00 dispatched=0
[2026-04-13 00:23:00,117: WARNING/ForkPoolWorker-2] 2026-04-13 00:23:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:23:00.010833+00:00 dispatched=0
[2026-04-13 00:24:00,118: WARNING/ForkPoolWorker-2] 2026-04-13 00:24:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:24:00.013266+00:00 dispatched=0
[2026-04-13 00:25:00,140: WARNING/ForkPoolWorker-2] 2026-04-13 00:25:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:25:00.023098+00:00 dispatched=0
[2026-04-13 00:26:00,113: WARNING/ForkPoolWorker-2] 2026-04-13 00:26:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:26:00.011929+00:00 dispatched=0
[2026-04-13 00:27:00,108: WARNING/ForkPoolWorker-2] 2026-04-13 00:27:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:27:00.014657+00:00 dispatched=0
[2026-04-13 00:28:00,137: WARNING/ForkPoolWorker-2] 2026-04-13 00:28:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:28:00.013390+00:00 dispatched=0
[2026-04-13 00:29:00,111: WARNING/ForkPoolWorker-2] 2026-04-13 00:29:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:29:00.008861+00:00 dispatched=0
[2026-04-13 00:30:00,147: WARNING/ForkPoolWorker-2] 2026-04-13 00:30:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:30:00.038664+00:00 dispatched=0
[2026-04-13 00:31:00,105: WARNING/ForkPoolWorker-2] 2026-04-13 00:31:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:31:00.016581+00:00 dispatched=0
[2026-04-13 00:32:00,106: WARNING/ForkPoolWorker-2] 2026-04-13 00:32:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:32:00.016607+00:00 dispatched=0
[2026-04-13 00:33:00,120: WARNING/ForkPoolWorker-2] 2026-04-13 00:33:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:33:00.016527+00:00 dispatched=0
[2026-04-13 00:34:00,112: WARNING/ForkPoolWorker-2] 2026-04-13 00:34:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:34:00.020357+00:00 dispatched=0
[2026-04-13 00:35:00,132: WARNING/ForkPoolWorker-2] 2026-04-13 00:35:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:35:00.014511+00:00 dispatched=0
[2026-04-13 00:36:00,124: WARNING/ForkPoolWorker-2] 2026-04-13 00:36:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:36:00.015615+00:00 dispatched=0
[2026-04-13 00:37:00,111: WARNING/ForkPoolWorker-2] 2026-04-13 00:37:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:37:00.015479+00:00 dispatched=0
[2026-04-13 00:38:00,097: WARNING/ForkPoolWorker-2] 2026-04-13 00:38:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:38:00.009616+00:00 dispatched=0
[2026-04-13 00:39:00,106: WARNING/ForkPoolWorker-2] 2026-04-13 00:39:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:39:00.017855+00:00 dispatched=0
[2026-04-13 00:40:00,131: WARNING/ForkPoolWorker-2] 2026-04-13 00:40:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:40:00.018668+00:00 dispatched=0
[2026-04-13 00:41:00,092: WARNING/ForkPoolWorker-2] 2026-04-13 00:41:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:41:00.015370+00:00 dispatched=0
[2026-04-13 00:42:00,155: WARNING/ForkPoolWorker-2] 2026-04-13 00:42:00 [info     ] content.check_scheduled.done   checked_at=2026-04-13T00:42:00.015419+00:00 dispatched=0

==================
Log do Beat

__    -    ... __   -        _
LocalTime -> 2026-04-12 21:58:21
Configuration ->
    . broker -> redis://default:**@chatwoot_redis_prospector_llm:6379/0
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler
    . db -> /tmp/celerybeat-schedule
    . logfile -> [stderr]@%WARNING
    . maxinterval -> 5.00 minutes (300s)
[2026-04-12 22:00:00,011: ERROR/MainProcess] Message Error: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
['  File "/venv/bin/celery", line 6, in <module>\n    sys.exit(main())\n', '  File "/venv/lib/python3.12/site-packages/celery/__main__.py", line 15, in main\n    sys.exit(_main())\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/celery.py", line 227, in main\n    return celery(auto_envvar_prefix="CELERY")\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1485, in __call__\n    return self.main(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1406, in main\n    rv = self.invoke(ctx)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1873, in invoke\n    return _process_result(sub_ctx.command.invoke(sub_ctx))\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1269, in invoke\n    return ctx.invoke(self.callback, **ctx.params)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 824, in invoke\n    return callback(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/decorators.py", line 34, in new_func\n    return f(get_current_context(), *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/base.py", line 158, in caller\n    return f(ctx, *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/beat.py", line 72, in beat\n    return beat().run()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 84, in run\n    self.start_scheduler()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 113, in start_scheduler\n    service.start()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 645, in start\n    interval = self.scheduler.tick()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 355, in tick\n    self.apply_entry(entry, producer=self.producer)\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 285, in apply_entry\n    exc, traceback.format_stack(), exc_info=True)\n']
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
TypeError: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 282, in apply_entry
    result = self.apply_async(entry, producer=producer, advance=False)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 412, in apply_async
    reraise(SchedulingError, SchedulingError(
  File "/venv/lib/python3.12/site-packages/celery/exceptions.py", line 109, in reraise
    raise value.with_traceback(tb)
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
celery.beat.SchedulingError: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
[2026-04-12 22:30:00,030: ERROR/MainProcess] Message Error: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
['  File "/venv/bin/celery", line 6, in <module>\n    sys.exit(main())\n', '  File "/venv/lib/python3.12/site-packages/celery/__main__.py", line 15, in main\n    sys.exit(_main())\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/celery.py", line 227, in main\n    return celery(auto_envvar_prefix="CELERY")\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1485, in __call__\n    return self.main(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1406, in main\n    rv = self.invoke(ctx)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1873, in invoke\n    return _process_result(sub_ctx.command.invoke(sub_ctx))\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1269, in invoke\n    return ctx.invoke(self.callback, **ctx.params)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 824, in invoke\n    return callback(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/decorators.py", line 34, in new_func\n    return f(get_current_context(), *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/base.py", line 158, in caller\n    return f(ctx, *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/beat.py", line 72, in beat\n    return beat().run()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 84, in run\n    self.start_scheduler()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 113, in start_scheduler\n    service.start()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 645, in start\n    interval = self.scheduler.tick()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 355, in tick\n    self.apply_entry(entry, producer=self.producer)\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 285, in apply_entry\n    exc, traceback.format_stack(), exc_info=True)\n']
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
TypeError: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 282, in apply_entry
    result = self.apply_async(entry, producer=producer, advance=False)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 412, in apply_async
    reraise(SchedulingError, SchedulingError(
  File "/venv/lib/python3.12/site-packages/celery/exceptions.py", line 109, in reraise
    raise value.with_traceback(tb)
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
celery.beat.SchedulingError: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
[2026-04-12 23:00:00,033: ERROR/MainProcess] Message Error: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
['  File "/venv/bin/celery", line 6, in <module>\n    sys.exit(main())\n', '  File "/venv/lib/python3.12/site-packages/celery/__main__.py", line 15, in main\n    sys.exit(_main())\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/celery.py", line 227, in main\n    return celery(auto_envvar_prefix="CELERY")\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1485, in __call__\n    return self.main(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1406, in main\n    rv = self.invoke(ctx)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1873, in invoke\n    return _process_result(sub_ctx.command.invoke(sub_ctx))\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1269, in invoke\n    return ctx.invoke(self.callback, **ctx.params)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 824, in invoke\n    return callback(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/decorators.py", line 34, in new_func\n    return f(get_current_context(), *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/base.py", line 158, in caller\n    return f(ctx, *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/beat.py", line 72, in beat\n    return beat().run()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 84, in run\n    self.start_scheduler()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 113, in start_scheduler\n    service.start()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 645, in start\n    interval = self.scheduler.tick()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 355, in tick\n    self.apply_entry(entry, producer=self.producer)\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 285, in apply_entry\n    exc, traceback.format_stack(), exc_info=True)\n']
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
TypeError: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 282, in apply_entry
    result = self.apply_async(entry, producer=producer, advance=False)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 412, in apply_async
    reraise(SchedulingError, SchedulingError(
  File "/venv/lib/python3.12/site-packages/celery/exceptions.py", line 109, in reraise
    raise value.with_traceback(tb)
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
celery.beat.SchedulingError: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
[2026-04-12 23:30:00,027: ERROR/MainProcess] Message Error: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
['  File "/venv/bin/celery", line 6, in <module>\n    sys.exit(main())\n', '  File "/venv/lib/python3.12/site-packages/celery/__main__.py", line 15, in main\n    sys.exit(_main())\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/celery.py", line 227, in main\n    return celery(auto_envvar_prefix="CELERY")\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1485, in __call__\n    return self.main(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1406, in main\n    rv = self.invoke(ctx)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1873, in invoke\n    return _process_result(sub_ctx.command.invoke(sub_ctx))\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1269, in invoke\n    return ctx.invoke(self.callback, **ctx.params)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 824, in invoke\n    return callback(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/decorators.py", line 34, in new_func\n    return f(get_current_context(), *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/base.py", line 158, in caller\n    return f(ctx, *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/beat.py", line 72, in beat\n    return beat().run()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 84, in run\n    self.start_scheduler()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 113, in start_scheduler\n    service.start()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 645, in start\n    interval = self.scheduler.tick()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 355, in tick\n    self.apply_entry(entry, producer=self.producer)\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 285, in apply_entry\n    exc, traceback.format_stack(), exc_info=True)\n']
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
TypeError: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 282, in apply_entry
    result = self.apply_async(entry, producer=producer, advance=False)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 412, in apply_async
    reraise(SchedulingError, SchedulingError(
  File "/venv/lib/python3.12/site-packages/celery/exceptions.py", line 109, in reraise
    raise value.with_traceback(tb)
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
celery.beat.SchedulingError: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
[2026-04-13 00:00:00,019: ERROR/MainProcess] Message Error: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
['  File "/venv/bin/celery", line 6, in <module>\n    sys.exit(main())\n', '  File "/venv/lib/python3.12/site-packages/celery/__main__.py", line 15, in main\n    sys.exit(_main())\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/celery.py", line 227, in main\n    return celery(auto_envvar_prefix="CELERY")\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1485, in __call__\n    return self.main(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1406, in main\n    rv = self.invoke(ctx)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1873, in invoke\n    return _process_result(sub_ctx.command.invoke(sub_ctx))\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1269, in invoke\n    return ctx.invoke(self.callback, **ctx.params)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 824, in invoke\n    return callback(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/decorators.py", line 34, in new_func\n    return f(get_current_context(), *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/base.py", line 158, in caller\n    return f(ctx, *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/beat.py", line 72, in beat\n    return beat().run()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 84, in run\n    self.start_scheduler()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 113, in start_scheduler\n    service.start()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 645, in start\n    interval = self.scheduler.tick()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 355, in tick\n    self.apply_entry(entry, producer=self.producer)\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 285, in apply_entry\n    exc, traceback.format_stack(), exc_info=True)\n']
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
TypeError: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 282, in apply_entry
    result = self.apply_async(entry, producer=producer, advance=False)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 412, in apply_async
    reraise(SchedulingError, SchedulingError(
  File "/venv/lib/python3.12/site-packages/celery/exceptions.py", line 109, in reraise
    raise value.with_traceback(tb)
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
celery.beat.SchedulingError: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
[2026-04-13 00:30:00,029: ERROR/MainProcess] Message Error: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'
['  File "/venv/bin/celery", line 6, in <module>\n    sys.exit(main())\n', '  File "/venv/lib/python3.12/site-packages/celery/__main__.py", line 15, in main\n    sys.exit(_main())\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/celery.py", line 227, in main\n    return celery(auto_envvar_prefix="CELERY")\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1485, in __call__\n    return self.main(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1406, in main\n    rv = self.invoke(ctx)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1873, in invoke\n    return _process_result(sub_ctx.command.invoke(sub_ctx))\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 1269, in invoke\n    return ctx.invoke(self.callback, **ctx.params)\n', '  File "/venv/lib/python3.12/site-packages/click/core.py", line 824, in invoke\n    return callback(*args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/click/decorators.py", line 34, in new_func\n    return f(get_current_context(), *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/base.py", line 158, in caller\n    return f(ctx, *args, **kwargs)\n', '  File "/venv/lib/python3.12/site-packages/celery/bin/beat.py", line 72, in beat\n    return beat().run()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 84, in run\n    self.start_scheduler()\n', '  File "/venv/lib/python3.12/site-packages/celery/apps/beat.py", line 113, in start_scheduler\n    service.start()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 645, in start\n    interval = self.scheduler.tick()\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 355, in tick\n    self.apply_entry(entry, producer=self.producer)\n', '  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 285, in apply_entry\n    exc, traceback.format_stack(), exc_info=True)\n']
Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
TypeError: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 282, in apply_entry
    result = self.apply_async(entry, producer=producer, advance=False)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 412, in apply_async
    reraise(SchedulingError, SchedulingError(
  File "/venv/lib/python3.12/site-packages/celery/exceptions.py", line 109, in reraise
    raise value.with_traceback(tb)
  File "/venv/lib/python3.12/site-packages/celery/beat.py", line 404, in apply_async
    return task.apply_async(entry_args, entry_kwargs,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/venv/lib/python3.12/site-packages/celery/app/task.py", line 592, in apply_async
    check_arguments(*(args or ()), **(kwargs or {}))
celery.beat.SchedulingError: Couldn't apply scheduled task enrich-pending: enrich_pending_batch() missing 1 required positional argument: 'tenant_id'


===============
Logs do backend

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started parent process [7]
INFO:     Started server process [9]
INFO:     Waiting for application startup.
INFO:     Started server process [10]
INFO:     Waiting for application startup.
{"url": "chatwoot_bd_prospector_llm:5432/prospector", "event": "database.connected", "level": "info", "timestamp": "2026-04-12T21:55:40.418584Z"}
{"url": "chatwoot_bd_prospector_llm:5432/prospector", "event": "database.connected", "level": "info", "timestamp": "2026-04-12T21:55:40.424050Z"}
{"env": "prod", "debug": false, "event": "api.startup", "level": "info", "timestamp": "2026-04-12T21:55:40.627374Z"}
INFO:     Application startup complete.
{"env": "prod", "debug": false, "event": "api.startup", "level": "info", "timestamp": "2026-04-12T21:55:40.644455Z"}
INFO:     Application startup complete.
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 14.13, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:55:44.600304Z"}
INFO:     127.0.0.1:59188 - "GET /health HTTP/1.1" 200 OK
INFO:     10.11.0.4:50156 - "WebSocket /ws/events?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiI1YjI5ZmViYi05M2ViLTQ5MjEtOTg3ZS0zZDEwY2MxMWRkNjMiLCJlbWFpbCI6ImFkcmlhbm9AY29tcG9zdG93ZWIuY29tLmJyIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJuYW1lIjoiQWRyaWFubyBWYWxhZFx1MDBlM28iLCJleHAiOjE3NzY1MjI2MzF9.G5zd-ZDHhrAyBEtQDr9r5rKpmb_c9Of3BcNgrBBgNa0" [accepted]
{"user_id": "5b29febb-93eb-4921-987e-3d10cc11dd63", "tenant_id": "", "event": "ws.connected", "level": "info", "timestamp": "2026-04-12T21:55:50.629066Z"}
INFO:     connection open
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 5.01, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:56:14.736796Z"}
INFO:     127.0.0.1:35360 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 12.5, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:56:44.875804Z"}
INFO:     127.0.0.1:47008 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 10.91, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:57:15.021615Z"}
INFO:     127.0.0.1:56020 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 10.45, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:57:45.144661Z"}
INFO:     127.0.0.1:43322 - "GET /health HTTP/1.1" 200 OK
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 5.61, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:58:15.247652Z"}
INFO:     127.0.0.1:38630 - "GET /health HTTP/1.1" 200 OK
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started parent process [6]
INFO:     Started server process [8]
INFO:     Waiting for application startup.
{"url": "chatwoot_bd_prospector_llm:5432/prospector", "event": "database.connected", "level": "info", "timestamp": "2026-04-12T21:58:27.700135Z"}
INFO:     Started server process [9]
INFO:     Waiting for application startup.
{"env": "prod", "debug": false, "event": "api.startup", "level": "info", "timestamp": "2026-04-12T21:58:27.950668Z"}
INFO:     Application startup complete.
{"url": "chatwoot_bd_prospector_llm:5432/prospector", "event": "database.connected", "level": "info", "timestamp": "2026-04-12T21:58:27.959738Z"}
INFO:     Application startup complete.
{"env": "prod", "debug": false, "event": "api.startup", "level": "info", "timestamp": "2026-04-12T21:58:28.183884Z"}
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 13.93, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:58:29.608266Z"}
INFO:     127.0.0.1:41128 - "GET /health HTTP/1.1" 200 OK
INFO:     Received SIGTERM, exiting.
INFO:     Terminated child process [9]
INFO:     Terminated child process [10]
INFO:     Waiting for child process [9]
INFO:     Shutting down
INFO:     Shutting down
INFO:     connection closed
INFO:     Waiting for background tasks to complete. (CTRL+C to force quit)
INFO:     Waiting for application shutdown.
{"event": "api.shutdown", "level": "info", "timestamp": "2026-04-12T21:58:33.365681Z"}
INFO:     Application shutdown complete.
INFO:     Finished server process [10]
INFO:     10.11.0.4:48458 - "WebSocket /ws/events?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiI1YjI5ZmViYi05M2ViLTQ5MjEtOTg3ZS0zZDEwY2MxMWRkNjMiLCJlbWFpbCI6ImFkcmlhbm9AY29tcG9zdG93ZWIuY29tLmJyIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJuYW1lIjoiQWRyaWFubyBWYWxhZFx1MDBlM28iLCJleHAiOjE3NzY1MjI2MzF9.G5zd-ZDHhrAyBEtQDr9r5rKpmb_c9Of3BcNgrBBgNa0" [accepted]
{"user_id": "5b29febb-93eb-4921-987e-3d10cc11dd63", "tenant_id": "", "event": "ws.connected", "level": "info", "timestamp": "2026-04-12T21:58:35.566870Z"}
INFO:     connection open
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 10.6, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:58:59.741203Z"}
INFO:     127.0.0.1:45380 - "GET /health HTTP/1.1" 200 OK
INFO:     connection closed
{"method": "OPTIONS", "path": "/analytics/recent-replies", "status": 200, "duration_ms": 1.31, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.874447Z"}
INFO:     10.11.0.4:50818 - "OPTIONS /analytics/recent-replies?limit=10 HTTP/1.1" 200 OK
{"method": "OPTIONS", "path": "/analytics/email/stats", "status": 200, "duration_ms": 2.09, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.875801Z"}
INFO:     10.11.0.4:50802 - "OPTIONS /analytics/email/stats?days=30 HTTP/1.1" 200 OK
{"method": "OPTIONS", "path": "/analytics/intents", "status": 200, "duration_ms": 3.07, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.877257Z"}
INFO:     10.11.0.4:50850 - "OPTIONS /analytics/intents?days=30 HTTP/1.1" 200 OK
{"method": "OPTIONS", "path": "/tasks/stats", "status": 200, "duration_ms": 3.08, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.878418Z"}
INFO:     10.11.0.4:50836 - "OPTIONS /tasks/stats HTTP/1.1" 200 OK
INFO:     10.11.0.4:50874 - "WebSocket /ws/events?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiI1YjI5ZmViYi05M2ViLTQ5MjEtOTg3ZS0zZDEwY2MxMWRkNjMiLCJlbWFpbCI6ImFkcmlhbm9AY29tcG9zdG93ZWIuY29tLmJyIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJuYW1lIjoiQWRyaWFubyBWYWxhZFx1MDBlM28iLCJleHAiOjE3NzY1MjI2MzF9.G5zd-ZDHhrAyBEtQDr9r5rKpmb_c9Of3BcNgrBBgNa0" [accepted]
{"user_id": "5b29febb-93eb-4921-987e-3d10cc11dd63", "tenant_id": "", "event": "ws.connected", "level": "info", "timestamp": "2026-04-12T21:59:15.882462Z"}
INFO:     connection open
{"method": "OPTIONS", "path": "/analytics/funnel", "status": 200, "duration_ms": 7.97, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.884764Z"}
INFO:     10.11.0.4:50828 - "OPTIONS /analytics/funnel HTTP/1.1" 200 OK
{"method": "OPTIONS", "path": "/analytics/dashboard", "status": 200, "duration_ms": 8.17, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.886131Z"}
INFO:     10.11.0.4:50854 - "OPTIONS /analytics/dashboard?days=30 HTTP/1.1" 200 OK
{"method": "OPTIONS", "path": "/analytics/performance", "status": 200, "duration_ms": 7.83, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.886959Z"}
INFO:     10.11.0.4:50864 - "OPTIONS /analytics/performance?days=30 HTTP/1.1" 200 OK
{"method": "OPTIONS", "path": "/analytics/channels", "status": 200, "duration_ms": 1.86, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:15.887604Z"}
INFO:     10.11.0.4:50868 - "OPTIONS /analytics/channels?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/intents", "status": 200, "duration_ms": 567.93, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.704197Z"}
INFO:     10.11.0.4:50854 - "GET /analytics/intents?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/recent-replies", "status": 200, "duration_ms": 583.92, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.720017Z"}
INFO:     10.11.0.4:50864 - "GET /analytics/recent-replies?limit=10 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/funnel", "status": 200, "duration_ms": 369.5, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.727239Z"}
INFO:     10.11.0.4:50802 - "GET /analytics/funnel HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/performance", "status": 200, "duration_ms": 402.97, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.760566Z"}
INFO:     10.11.0.4:50850 - "GET /analytics/performance?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/tasks/stats", "status": 200, "duration_ms": 614.84, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.763143Z"}
INFO:     10.11.0.4:50828 - "GET /tasks/stats HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/email/stats", "status": 200, "duration_ms": 640.75, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.764105Z"}
INFO:     10.11.0.4:50868 - "GET /analytics/email/stats?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/channels", "status": 200, "duration_ms": 415.15, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.772990Z"}
INFO:     10.11.0.4:50818 - "GET /analytics/channels?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/dashboard", "status": 200, "duration_ms": 446.15, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:16.803604Z"}
INFO:     10.11.0.4:50836 - "GET /analytics/dashboard?days=30 HTTP/1.1" 200 OK
INFO:     connection closed
{"method": "GET", "path": "/analytics/channels", "status": 200, "duration_ms": 226.71, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.120382Z"}
INFO:     10.11.0.4:50818 - "GET /analytics/channels?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/recent-replies", "status": 200, "duration_ms": 232.73, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.133549Z"}
INFO:     10.11.0.4:50868 - "GET /analytics/recent-replies?limit=10 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/performance", "status": 200, "duration_ms": 229.7, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.134184Z"}
INFO:     10.11.0.4:50850 - "GET /analytics/performance?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/funnel", "status": 200, "duration_ms": 230.77, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.135086Z"}
INFO:     10.11.0.4:50828 - "GET /analytics/funnel HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/dashboard", "status": 200, "duration_ms": 267.41, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.152057Z"}
INFO:     10.11.0.4:50836 - "GET /analytics/dashboard?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/tasks/stats", "status": 200, "duration_ms": 246.76, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.157552Z"}
INFO:     10.11.0.4:50854 - "GET /tasks/stats HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/intents", "status": 200, "duration_ms": 258.24, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.162856Z"}
INFO:     10.11.0.4:50802 - "GET /analytics/intents?days=30 HTTP/1.1" 200 OK
{"method": "GET", "path": "/analytics/email/stats", "status": 200, "duration_ms": 258.22, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:19.168897Z"}
INFO:     10.11.0.4:50864 - "GET /analytics/email/stats?days=30 HTTP/1.1" 200 OK
INFO:     10.11.0.4:50882 - "WebSocket /ws/events?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiI1YjI5ZmViYi05M2ViLTQ5MjEtOTg3ZS0zZDEwY2MxMWRkNjMiLCJlbWFpbCI6ImFkcmlhbm9AY29tcG9zdG93ZWIuY29tLmJyIiwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJuYW1lIjoiQWRyaWFubyBWYWxhZFx1MDBlM28iLCJleHAiOjE3NzY1MjI2MzF9.G5zd-ZDHhrAyBEtQDr9r5rKpmb_c9Of3BcNgrBBgNa0" [accepted]
{"user_id": "5b29febb-93eb-4921-987e-3d10cc11dd63", "tenant_id": "", "event": "ws.connected", "level": "info", "timestamp": "2026-04-12T21:59:19.377109Z"}
INFO:     connection open
{"method": "OPTIONS", "path": "/inbox/conversations", "status": 200, "duration_ms": 0.32, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:28.760374Z"}
INFO:     10.11.0.4:38388 - "OPTIONS /inbox/conversations?limit=50&filter=all HTTP/1.1" 200 OK
HTTP Request: GET https://api38.unipile.com:16847/api/v1/chats?account_id=_WQ6XQnDR2ukuUaKCr6p0g&limit=100 "HTTP/1.1 200 OK"
{"method": "GET", "path": "/health", "status": 200, "duration_ms": 7.09, "event": "http.request", "level": "info", "timestamp": "2026-04-12T21:59:29.856304Z"}
INFO:     127.0.0.1:57470 - "GET /health HTTP/1.1" 200 OK
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAxZGFoBOXNtv7QlRnjeYzHODfiBMm-AigI?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAC091h4BdgCkorQ-K76S0T_Aocb1AysR1YQ?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAADu7RtgBHxSNmX6jlEiu6lxnUumF0kU6rUY?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAADuTdlMBIKtvH3BrJaekAB9gj2vKxNxAF6g?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAAeA54B1tjEl44e4wvUgbCHloCzhOdh8rg?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAADBiiGYB8Yj03yFnnxpEETSmtnPPAlhmBO4?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAZgBfEBWniZ8X4xSYckj5zBR9TE_qLsxnM?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAACvg4lUBcpNI8hNn_HTtaxYk4BN3Zfc-ipc?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAACbBEhcBTOzdLJll71sej1H3D_kavqEUFZc?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAEPaNWYB5XkRrNRQCZ6Nm3sitXci7v4_N5E?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAABiSzmYBLph98_crLauguVU9f-fyNYDEeJc?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAADtp4vkBZT-cLiYC4s90asgFzMufUObFaw0?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAXma7MBC7PMEaD4shItbC3zA-uIJ1f5SLM?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAESZxSoBTP-eaLxjVFGG2y2IEIiT_ZvF-2c?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAvH3DEBEgqixJRN-aBezgomMYzrvdljq2I?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAES3vY0BAWO0piIUXOxfA8GO3eU5zA61AMg?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAArRT0oBFIJx4zWk4iHS6QEx2XfJPtebsjg?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAA7g7qwBUL3luwVZcMKI98sdOe7MyVAd4G4?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAam5QIBCSxCLZilu7Av32-8-pwM32Q9C0w?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAC--2AEBIRCuFk00SRJ_v0nK4qRUixvjph8?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAA2tn4QBwX8y76Ct6-qXJSwht4ZloE54OYQ?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAa54rwBToOjImP-2GtJV51znt72tEpZmk8?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAOKq8EB6XgRYRgvQJg-b603Y8QSuFNeWOo?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAABZlA2QB8THFlhevnqopL1Nu92y9SdhKePw?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAADe1Ev8BK7nIznk4ovt6PHSFSh31KGs1wHM?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAABosZvQBPoG4mpLfljY8w6qx2lE043qtvKk?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAACdH2f4B5Mxt-gn0aPfgREhk1m6wAaJ63SM?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAA9Mh4cBkUyAX4X2EJ4JWg-nSNTyC6WfSwk?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAoKXVEBMo0R95pprIyMUsaAwUmYqx47Sfg?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAABzwl4kBcjOyDaxJqQ_G6UybVGaDNGleBQc?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAFdNBc8B1rm1GnL8454XgfVhkg-sjMTXdQ0?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAAAOwMEBIbQJI76zRr3w7jNbMR2NIxV59kk?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAABbg5ABH7vjye8UrXBV4r2hzHt40zokl08?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAE62o7MBmDODkLhjLsETVO_aOrJ9IraOVuA?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
{"user_id": "5b29febb-93eb-4921-987e-3d10cc11dd63", "event": "ws.disconnected", "level": "info", "timestamp": "2026-04-12T21:59:35.571360Z"}
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAEGG2N0B44BP2ShnUwGK1tBPrUVonhZZ4BE?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAB0wd3QBlaiZ85t5PUw7PrlPxbgp4GWJKz4?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAARY1IsB-EdnA_Q5Psp_bseICU1JbYmLLBw?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAACmiqwUBkBTfXz1dmYIC--ApxI8K3nTHqg8?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAAA93WokBBj8zvWWxEMZ-12i3PD5dgRHY1b4?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"
HTTP Request: GET https://api38.unipile.com:16847/api/v1/users/ACoAADN--MIB0D5NL9Xqf3d2ayE1ceu0s52cNgc?account_id=_WQ6XQnDR2ukuUaKCr6p0g "HTTP/1.1 200 OK"