# PROMPT DE KICKOFF — Prospector
# Cole no GitHub Copilot Chat (painel lateral do VS Code) para iniciar o desenvolvimento.
# Copilot já lê .github/copilot-instructions.md automaticamente — este prompt
# complementa com o contexto de onde estamos e o que fazer agora.

---

Você está me ajudando a desenvolver o **Prospector**, sistema de prospecção B2B
automatizado da Composto Web. Leia o arquivo `.github/copilot-instructions.md`
que já está no projeto — ele contém todas as regras obrigatórias de stack,
padrões de código e o que nunca fazer. Siga-o sem exceções.

## Contexto do projeto

Sistema que automatiza cadências de prospecção multicanal (LinkedIn + Email),
personaliza mensagens com IA (OpenAI e/ou Google Gemini por cadência),
detecta respostas automaticamente e cria deals no Pipedrive.

Arquitetura: FastAPI + Celery + Redis + PostgreSQL async + Docker Compose.
Multi-tenant com Row-Level Security no PostgreSQL.
Dois ambientes: `dev` (banco remoto, Redis remoto) e `prod` (tudo no VPS).

## O que já existe no projeto

Os seguintes arquivos já estão criados e **não devem ser reescritos**:

```
integrations/llm/__init__.py       # exports da camada LLM
integrations/llm/base.py           # LLMProvider (ABC), LLMMessage, LLMResponse, ModelInfo
integrations/llm/openai_provider.py
integrations/llm/gemini_provider.py
integrations/llm/registry.py       # LLMRegistry — singleton via Depends()
api/routes/llm.py                  # GET /llm/models, POST /llm/test
models/cadence.py                  # Cadence com campos llm_provider, llm_model, etc.
schemas/cadence.py                 # LLMConfigSchema + CadenceCreateRequest
services/ai_composer.py            # usa LLMRegistry
services/reply_parser.py           # usa LLMRegistry
```

## Sprint atual — Sprint 1: Fundação

Precisamos criar os seguintes arquivos **nesta ordem exata**. Para cada um,
implemente completo e funcional — sem stubs, sem `pass`, sem `TODO`.

---

### 1. `core/config.py`

Settings com pydantic-settings. Deve:
- Detectar `ENV` via `os.getenv("ENV", "dev")` e carregar `.env.{ENV}`
- Ter campos para: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `DEBUG`, `ENV`
- Ter campos LLM: `OPENAI_API_KEY`, `OPENAI_DEFAULT_MODEL`, `GEMINI_API_KEY`, `GEMINI_DEFAULT_MODEL`, `REPLY_PARSER_PROVIDER`, `REPLY_PARSER_MODEL`
- Ter campos de voz: `VOICE_PROVIDER`, `SPEECHIFY_API_KEY`, `SPEECHIFY_VOICE_ID`
- Ter campos Unipile: `UNIPILE_API_KEY`, `UNIPILE_BASE_URL`, `UNIPILE_ACCOUNT_ID_LINKEDIN`, `UNIPILE_ACCOUNT_ID_GMAIL`, `UNIPILE_WEBHOOK_SECRET`
- Ter campos Apify, email finder (Prospeo, Hunter, Apollo, ZeroBounce), contexto (Jina, Firecrawl, Tavily)
- Ter campos Pipedrive: `PIPEDRIVE_API_TOKEN`, `PIPEDRIVE_DOMAIN`, `PIPEDRIVE_STAGE_INTEREST`, `PIPEDRIVE_STAGE_OBJECTION`, `PIPEDRIVE_OWNER_ID`, `PIPEDRIVE_NOTIFY_EMAIL`
- Ter rate limits: `LIMIT_LINKEDIN_CONNECT=20`, `LIMIT_LINKEDIN_DM=40`, `LIMIT_EMAIL=300`
- Ter Celery: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- Exportar `settings = Settings()` como singleton

---

### 2. `core/database.py`

Engine async SQLAlchemy + session factory. Deve:
- Criar `AsyncEngine` com `DATABASE_URL` de settings
- Criar `AsyncSessionLocal` com `AsyncSession`
- Implementar `get_session(tenant_id: UUID)` como async generator que:
  - Abre `AsyncSession`
  - Executa `SET LOCAL app.current_tenant_id = :tid` antes de yield
  - Faz yield da session
  - Garante commit/rollback/close no finally
- Implementar `init_db()` async para verificar conexão no startup

---

### 3. `core/redis_client.py`

Cliente Redis + helpers de rate limiting. Deve:
- Criar instância global `redis_client` via `redis.asyncio.from_url(settings.REDIS_URL)`
- Implementar `async def check_and_increment(channel: str, tenant_id: UUID, limit: int) -> bool`:
  - Chave: `ratelimit:{tenant_id}:{channel}:{date.today()}`
  - Usa `INCR` + `EXPIRE 86400` no primeiro incremento
  - Retorna `True` se abaixo do limite, `False` se atingiu
- Implementar `async def get_cache(key: str) -> str | None`
- Implementar `async def set_cache(key: str, value: str, ttl: int) -> None`

---

### 4. `core/security.py`

JWT + extração de tenant. Deve:
- Usar `python-jose` com algoritmo HS256
- Implementar `create_access_token(data: dict, expires_delta: timedelta) -> str`
- Implementar `decode_token(token: str) -> dict`
- Implementar `get_current_tenant_id(token: str = Depends(oauth2_scheme)) -> UUID`
  que extrai `tenant_id` do payload do JWT
- Usar `OAuth2PasswordBearer(tokenUrl="/auth/token")`

---

### 5. `core/logging.py`

Configuração do structlog. Deve:
- Configurar `structlog` com processadores: timestamp ISO, nível, JSON renderer em prod / console em dev
- Detectar `settings.DEBUG` para escolher o renderer
- Exportar `configure_logging()` para chamar no startup da API

---

### 6. `models/base.py`

Base declarativa e mixins. Deve:
- Criar `Base` com `DeclarativeBase`
- Criar `TenantMixin` com `tenant_id: Mapped[UUID]` FK para `tenants.id`, `nullable=False`, `index=True`
- Criar `TimestampMixin` com `created_at` e `updated_at` (default `utcnow`, onupdate)

---

### 7. `models/tenant.py`

Models Tenant e TenantIntegration. Deve:
- `Tenant`: id (UUID PK), name, slug, is_active, created_at
- `TenantIntegration`: tenant_id (FK+unique), todos os campos de integração:
  `unipile_linkedin_account_id`, `unipile_gmail_account_id`,
  `pipedrive_api_token`, `pipedrive_domain`, `pipedrive_stage_interest`,
  `pipedrive_stage_objection`, `pipedrive_owner_id`, `notify_email`,
  `notify_on_interest`, `notify_on_objection`, `allow_personal_email`,
  `limit_linkedin_connect`, `limit_linkedin_dm`, `limit_email`

---

### 8. `models/lead.py`

Model Lead. Deve ter todos os campos definidos na arquitetura:
- id, tenant_id, name, company, website, linkedin_url, linkedin_profile_id
- city, segment, source (Enum LeadSource), status (Enum LeadStatus), score
- email_corporate, email_corporate_source, email_corporate_verified
- email_personal, email_personal_source
- phone, enriched_at, notes, created_at, updated_at
- Enums `LeadSource` e `LeadStatus` no mesmo arquivo (ou em `models/enums.py`)

---

### 9. `models/interaction.py`

Model Interaction. Deve ter:
- id, tenant_id, lead_id (FK), channel (Enum Channel), direction ("outbound"|"inbound")
- content_text, content_audio_url, intent (Enum Intent, nullable)
- unipile_message_id, opened (bool, para email), created_at

---

### 10. `alembic/env.py`

Configurar Alembic para usar o `DATABASE_URL` de `core/config.settings`
e importar todos os models para autogenerate funcionar corretamente.
Configurar para rodar em modo async com `asyncpg`.

---

### 11. `api/dependencies.py`

Todas as dependências FastAPI. Deve:
- `get_session`: wrap de `core/database.get_session` para uso com `Depends()`
- `get_current_tenant_id`: extrai UUID do JWT
- `get_current_tenant`: busca `Tenant` no banco pelo tenant_id
- `get_llm_registry`: singleton `LLMRegistry` via `@lru_cache`
- `get_redis`: retorna `redis_client` global

---

### 12. `api/main.py`

FastAPI app factory. Deve:
- Criar `app = FastAPI(title="Prospector API", version="1.0.0")`
- Registrar todos os routers existentes: `api/routes/llm.py`
- Adicionar `GET /health` que verifica banco e Redis
- Chamar `configure_logging()` no startup
- Chamar `init_db()` no startup
- Configurar CORS com `settings.ALLOWED_ORIGINS`
- Adicionar middleware de logging de requests (método, path, status, duração)

---

### 13. `workers/celery_app.py`

Instância e configuração do Celery. Deve:
- Criar `celery_app = Celery("prospector")` com broker e backend de settings
- Configurar filas: `capture`, `enrich`, `cadence`, `dispatch`
- Configurar `task_serializer = "json"`, `result_serializer = "json"`
- Importar `scheduler/beats.py` para o Beat schedule

---

### 14. `scheduler/beats.py`

CELERY_BEAT_SCHEDULE com os 4 agendamentos:
- `cadence-tick`: `crontab(minute="*")` → `workers.cadence.tick`
- `capture-maps-daily`: `crontab(hour="8", minute="0")` → `workers.capture.run_apify_maps`
- `capture-linkedin-daily`: `crontab(hour="9", minute="0")` → `workers.capture.run_apify_linkedin`
- `enrich-pending`: `crontab(minute="*/30")` → `workers.enrich.enrich_pending_batch`

---

## Regras para geração de código

1. **Type hints obrigatórios** em todas as funções e métodos públicos
2. **Async em tudo** — nenhuma função de I/O síncrona
3. **structlog** para logs — nunca `print()`
4. **httpx** para HTTP — nunca `requests`
5. **Alembic** para migrations — nunca `create_all()`
6. Cada arquivo começa com docstring explicando o que é e responsabilidades
7. Imports organizados: stdlib → third-party → internal (ruff cuida disso)
8. Nenhum valor hardcoded — tudo via `settings`

## Como trabalharemos

Implemente um arquivo por vez, na ordem listada acima. Após cada arquivo:
- Mostre o código completo
- Aponte se alguma dependência precisa ser instalada além do `pyproject.toml`
- Indique o próximo arquivo da lista

Comece pelo `core/config.py`.
