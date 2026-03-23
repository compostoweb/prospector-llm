# Skills necessárias para o desenvolvimento

Guia de conhecimentos, referências e ordem de desenvolvimento para tocar
o projeto com autonomia no VS Code + GitHub Copilot.

---

## Nível 1 — Fundação (obrigatório antes de começar)

### Python 3.12+
- Type hints em funções, classes e variáveis (`str | None`, `list[UUID]`)
- Async/await e event loop
- Pydantic v2 — validators, model_validator, field_validator
- Context managers (`async with`, `async for`)
- ABCs e herança — base.py da camada LLM usa `ABC` e `@abstractmethod`

### FastAPI
- Rotas com path/query/body params
- Dependency injection via `Depends()`
- Background tasks
- Schemas Pydantic v2 para request/response

### SQLAlchemy async
- Mapped columns e relacionamentos
- Queries com `select()`, `where()`, `join()`
- `AsyncSession` e transações
- Alembic para migrations — `--autogenerate`, `upgrade`, `downgrade`

---

## Nível 2 — Backend distribuído

### Celery + Redis
- Tasks com `@celery_app.task(bind=True, max_retries=3, queue="nome")`
- Filas dedicadas: `capture | enrich | cadence | dispatch`
- Celery Beat para agendamentos com crontab
- Monitorar jobs no Flower (localhost:5555)

### Redis
- Rate limiting: `INCR` + `EXPIRE` por canal/tenant/dia
- Cache com `SET`/`GET`/`EXPIRE` (ex: modelos LLM e contexto de lead)
- Chaves hierárquicas: `ratelimit:{tenant_id}:{channel}:{date}`

### Docker + Docker Compose
- Dev: volumes montados (hot reload), banco sempre remoto, sem postgres local
- Prod: imagens builadas, Redis com persistência, sem volumes de código

---

## Nível 3 — Camada LLM Multi-Provider

Este é o ponto mais específico do projeto — entender bem antes de codificar.

### Padrão Provider/Registry

O sistema usa o padrão Strategy + Registry para abstrair os provedores:

```python
# Nunca instanciar providers diretamente nos services
# Sempre via LLMRegistry injetado pelo Depends()
registry: LLMRegistry = Depends(get_llm_registry)
response = await registry.complete(messages=..., provider=..., model=...)
```

### OpenAI SDK (openai >= 1.55)
- `AsyncOpenAI` para async
- `client.chat.completions.create()` com `response_format={"type":"json_object"}`
- `client.models.list()` para listar modelos disponíveis
- Filtrar modelos de chat pelos prefixos: `gpt-4`, `gpt-3.5`, `o1`, `o3`, `o4`

### Google Gemini SDK (google-genai >= 1.0.0)
- **Não usar** `google-generativeai` — EOL novembro/2025
- `genai.Client(api_key=...)` para Gemini Developer API
- `client.aio.models.generate_content()` para async
- System prompt via `GenerateContentConfig(system_instruction=...)`
- JSON mode via `config.response_mime_type = "application/json"`
- `client.models.list()` para listar modelos disponíveis

### Configuração por cadência
- Cada cadência tem `llm_provider`, `llm_model`, `llm_temperature`, `llm_max_tokens`
- `LLMConfigSchema` valida que o modelo pertence ao provider
- Permite cadências com custos diferentes (volume vs. alto valor)

### Endpoints LLM
```
GET  /llm/providers       → providers ativos
GET  /llm/models          → todos os modelos (cache 1h)
GET  /llm/models/openai   → só OpenAI
GET  /llm/models/gemini   → só Gemini
POST /llm/test            → diagnóstico de provider + modelo
```

---

## Nível 4 — Integrações e Webhooks

### httpx async
- Cliente reutilizável por integração (classe com `httpx.AsyncClient`)
- Headers de autenticação por provider
- Retry com `tenacity` nos providers LLM e Unipile

### Webhooks Unipile
- `POST /webhooks/unipile` recebe `message.received` e `invitation.accepted`
- Validar assinatura HMAC com `UNIPILE_WEBHOOK_SECRET`
- Responder 200 imediatamente, processar em background

### OAuth2 Gmail via Unipile
- Unipile gerencia o token OAuth2 do Gmail
- Envio via `POST /emails` na Unipile API

---

## Nível 5 — Domínio do projeto

### Multi-tenancy com RLS
- `SET LOCAL app.current_tenant_id` em cada session
- RLS garante isolamento no banco
- `tenant_id` obrigatório em todos os models e queries

### Email finder cascata
- Ordem: Unipile → Prospeo → Hunter → Apollo → OSINT
- Classificar: corporativo (domínio próprio) vs. pessoal (gmail, hotmail, etc.)
- Por padrão: só usar email corporativo

### Cadência como máquina de estados
```
CadenceStep: pending → sent → replied | skipped | failed
Cadence (lead): in_cadence → pausada (resposta) | encerrada (NOT_INTERESTED)
```

---

## Ferramentas de desenvolvimento

### GitHub Copilot
- `.github/copilot-instructions.md` carregado automaticamente no VS Code
- Use Copilot Chat para perguntas de arquitetura
- Inline suggestions para código repetitivo: clients, schemas, tests

### VS Code Extensions (já configuradas em `.vscode/extensions.json`)
- `github.copilot` + `github.copilot-chat`
- `charliermarsh.ruff` — linter/formatter (roda no save)
- `ms-python.mypy-type-checker` — type checker
- `ms-azuretools.vscode-docker`
- `mtxr.sqltools` + driver PostgreSQL

### Ruff
```bash
ruff check .      # lint
ruff format .     # format
```

### Alembic (rodar dentro do container)
```bash
docker compose -f docker-compose.dev.yml exec api \
  alembic revision --autogenerate -m "add llm fields to cadences"

docker compose -f docker-compose.dev.yml exec api alembic upgrade head
```

---

## Referências rápidas

### SDKs e documentações
| SDK/Doc | URL |
|---|---|
| FastAPI | https://fastapi.tiangolo.com |
| SQLAlchemy async | https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html |
| Celery | https://docs.celeryq.dev |
| Pydantic v2 | https://docs.pydantic.dev/latest |
| Alembic | https://alembic.sqlalchemy.org |
| OpenAI Python SDK | https://github.com/openai/openai-python |
| Google Gen AI SDK | https://github.com/googleapis/python-genai |
| google-genai docs | https://googleapis.github.io/python-genai/ |

### APIs externas
| Serviço | URL |
|---|---|
| Unipile | https://developer.unipile.com |
| Gemini API | https://ai.google.dev/gemini-api/docs |
| OpenAI models | https://platform.openai.com/docs/models |
| Pipedrive | https://developers.pipedrive.com/docs/api/v1 |
| Apify | https://docs.apify.com/api/v2 |
| Speechify | https://docs.sws.speechify.com |
| Hunter | https://hunter.io/api-documentation |
| Prospeo | https://api.prospeo.io/docs |
| Jina AI Reader | https://jina.ai/reader |
| Firecrawl | https://docs.firecrawl.dev |
| Tavily | https://docs.tavily.com |

---

## Ordem sugerida de desenvolvimento (5 sprints)

### Sprint 1 — Fundação
1. `core/config.py` — Settings com `ENV=dev|prod`, OpenAI e Gemini keys
2. `core/database.py` — Engine async + RLS
3. `core/redis_client.py` — Cliente Redis + rate limit helpers
4. `models/` — Todos os models com tenant_id (incluindo `llm_*` em Cadence)
5. Migration inicial com Alembic
6. `api/main.py` — App FastAPI básico com `/health`

### Sprint 2 — Camada LLM
7. `integrations/llm/base.py` — ABCs (já criado)
8. `integrations/llm/openai_provider.py` — OpenAIProvider (já criado)
9. `integrations/llm/gemini_provider.py` — GeminiProvider (já criado)
10. `integrations/llm/registry.py` — LLMRegistry (já criado)
11. `api/routes/llm.py` — endpoints /llm/models, /llm/test (já criado)
12. `api/dependencies.py` — `get_llm_registry()` singleton
13. Testar: `POST /llm/test` com ambos os providers

### Sprint 3 — Enriquecimento
14. `integrations/unipile.py` — get_profile, send_message, send_voice_note
15. `services/email_finder.py` — cascata completa
16. `services/email_classifier.py` — corporativo vs pessoal
17. `workers/enrich.py` — pipeline de enriquecimento
18. `integrations/apify.py` + `workers/capture.py`

### Sprint 4 — Cadência e Dispatch
19. `services/context_fetcher.py` — Jina + Firecrawl + Tavily
20. `services/ai_composer.py` — usa LLMRegistry (já criado)
21. `services/voice.py` — Speechify MP3
22. `workers/dispatch.py` — envio por canal
23. `workers/cadence.py` — motor de cadência
24. `scheduler/beats.py`

### Sprint 5 — Resposta e CRM
25. `api/webhooks/unipile.py` — message.received + invitation.accepted
26. `services/reply_parser.py` — usa LLMRegistry (já criado)
27. `integrations/pipedrive.py` — deal + person + org + note + activity
28. `api/routes/` — CRUD de leads, cadências, analytics
29. Testes dos services críticos
