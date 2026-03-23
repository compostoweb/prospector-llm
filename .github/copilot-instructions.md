# GitHub Copilot — Instruções do projeto Prospector

## O que é este projeto

Sistema de prospecção B2B automatizado da Composto Web.
Canais ativos: LinkedIn (connect + DM texto + DM voz) + Email via Google Workspace.
Arquitetura multi-tenant preparada para SaaS.
Backend 100% Python nativo — sem n8n, sem ferramentas no-code.

---

## Stack obrigatória — nunca sugerir alternativas

| Componente | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn |
| Workers / Filas | Celery + Redis |
| Banco | PostgreSQL + SQLAlchemy async + asyncpg |
| Migrations | Alembic |
| Validação | Pydantic v2 |
| HTTP client | httpx (async) — NUNCA requests |
| LLM OpenAI | openai SDK oficial >= 1.55 |
| LLM Gemini | google-genai >= 1.0.0 — NUNCA google-generativeai (EOL nov/2025) |
| Canais | Unipile API (LinkedIn + Gmail) |
| Logs | structlog — NUNCA print() |
| Python | 3.12+ com type hints obrigatórios |

---

## Dois ambientes — regras de configuração

### Dev local
- Arquivo: `.env.dev`
- Banco: PostgreSQL **remoto** (Neon ou Supabase) — nunca container local
- Redis: container local na porta 6379
- Carregar com: `ENV=dev` → lê `.env.dev`

### Produção
- Arquivo: `.env.prod`
- Banco: mesmo cluster remoto, database `prospector_prod`
- Redis: container no VPS
- Carregar com: `ENV=prod` → lê `.env.prod`

### Como o código detecta o ambiente

```python
# core/config.py
ENV = os.getenv("ENV", "dev")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=f".env.{ENV}")
```

### NUNCA fazer
- Nunca container de PostgreSQL local no dev
- Nunca hardcodar DATABASE_URL — sempre via settings
- Nunca commitar `.env.dev` ou `.env.prod`

---

## Camada LLM — regras obrigatórias

### Localização

```
integrations/llm/
├── __init__.py          # exports: LLMMessage, LLMProvider, LLMResponse, ModelInfo, LLMRegistry
├── base.py              # abstrações base — nunca instanciar diretamente
├── openai_provider.py   # implementação OpenAI
├── gemini_provider.py   # implementação Gemini (google-genai SDK)
└── registry.py          # LLMRegistry — único ponto de acesso para todo o sistema
```

### Regra de ouro — nunca importar SDK diretamente nos services

```python
# ERRADO — nunca fazer isso em services/ ou workers/
from openai import AsyncOpenAI
from google import genai

# CORRETO — sempre via registry injetado via Depends()
from integrations.llm import LLMRegistry, LLMMessage

response = await registry.complete(
    messages=messages,
    provider=cadence.llm_provider,
    model=cadence.llm_model,
    temperature=cadence.llm_temperature,
    max_tokens=cadence.llm_max_tokens,
)
```

### Providers disponíveis

| Provider | Key necessária | SDK |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | openai >= 1.55 |
| `gemini` | `GEMINI_API_KEY` | google-genai >= 1.0.0 |

### SDK Gemini — usar google-genai, NUNCA google-generativeai

```python
# CORRETO — SDK GA (disponível desde maio/2025)
from google import genai
from google.genai import types
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ERRADO — descontinuado em novembro/2025, sem novos recursos
import google.generativeai as genai   # ← NUNCA USAR
```

### Configuração LLM por cadência

Cada cadência tem 4 campos LLM:

```python
cadence.llm_provider     # "openai" | "gemini"
cadence.llm_model        # ex: "gpt-4o-mini" | "gemini-2.5-flash"
cadence.llm_temperature  # 0.0–1.0
cadence.llm_max_tokens   # 64–8192
```

Ao criar cadência via API, o campo `llm` é validado pelo `LLMConfigSchema`
que garante que o modelo pertence ao provider selecionado.

### Reply parser usa settings globais (não cadência)

```python
# O lead saiu da cadência antes de responder — usa config do sistema
REPLY_PARSER_PROVIDER=openai
REPLY_PARSER_MODEL=gpt-4o-mini
```

### Listagem dinâmica de modelos

```
GET /llm/providers              → providers configurados
GET /llm/models                 → todos os modelos (cache Redis 1h)
GET /llm/models/openai          → só OpenAI
GET /llm/models/gemini          → só Gemini
POST /llm/test                  → testa provider + modelo com prompt simples
```

### Adicionar novo provider no futuro

1. Criar `integrations/llm/novo_provider.py` implementando `LLMProvider`
2. Registrar em `registry.py` se a key estiver em settings
3. Adicionar key em `.env.example` e `core/config.py`
O restante do sistema não muda.

### Recomendações de modelo por caso de uso

| Caso de uso | Provider | Modelo | Custo |
|---|---|---|---|
| Composer volume alto | gemini | gemini-2.5-flash-lite | $0.10/$0.40 MTok |
| Composer equilibrado | openai | gpt-4o-mini | $0.15/$0.60 MTok |
| Composer alto valor | gemini | gemini-2.5-pro | $1.25/$10 MTok |
| Composer alto valor alt. | openai | gpt-4o | $2.50/$10 MTok |
| Reply parser | openai | gpt-4o-mini | JSON mode confiável |
| Reply parser fallback | gemini | gemini-2.5-flash | JSON mode nativo |

---

## Estrutura de arquivos — onde cada coisa fica

| O que escrever | Onde |
|---|---|
| Rotas REST | `api/routes/` |
| Webhooks recebidos | `api/webhooks/` |
| Tasks Celery | `workers/` |
| Lógica de negócio | `services/` |
| Clientes de API externos | `integrations/` |
| Abstração LLM | `integrations/llm/` |
| Models SQLAlchemy | `models/` |
| Schemas Pydantic | `schemas/` |
| Agendamentos Celery Beat | `scheduler/beats.py` |
| Settings / config | `core/config.py` |
| DB session | `core/database.py` |
| Redis helpers | `core/redis_client.py` |
| JWT + tenant | `core/security.py` |

---

## Multi-tenant — regras obrigatórias

Todo model deve ter `tenant_id: UUID` com FK para `tenants.id`.

```python
class TenantMixin:
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
```

PostgreSQL Row-Level Security (RLS) deve estar ativo em todas as tabelas.
A session injeta o tenant via `SET LOCAL app.current_tenant_id`.

Nunca fazer query sem filtrar por tenant_id — o RLS é garantia mas o código
deve ser explícito.

---

## Padrões de código obrigatórios

### Async em tudo

```python
# CORRETO
async def buscar_lead(lead_id: UUID, db: AsyncSession) -> Lead | None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()

# ERRADO
def buscar_lead(lead_id):
    return db.query(Lead).get(lead_id)
```

### Injeção via Depends()

```python
@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
    registry: LLMRegistry = Depends(get_llm_registry),
) -> LeadResponse:
    ...
```

### Celery tasks com fila dedicada

```python
@celery_app.task(bind=True, max_retries=3, queue="dispatch")
async def dispatch_step(self, step_id: str) -> dict:
    ...
# Filas: "capture" | "enrich" | "cadence" | "dispatch"
```

### Clientes externos como classe com httpx

```python
class UnipileClient:
    def __init__(self, settings: Settings):
        self._client = httpx.AsyncClient(
            base_url=settings.UNIPILE_BASE_URL,
            headers={"X-API-KEY": settings.UNIPILE_API_KEY},
            timeout=30.0,
        )
```

### Logs estruturados

```python
import structlog
logger = structlog.get_logger()

# CORRETO
logger.info("dispatch.sent", step_id=step_id, channel=channel, tenant_id=tenant_id)

# ERRADO
print(f"Enviado: {step_id}")
```

---

## Enums do sistema

```python
class Channel(str, Enum):
    LINKEDIN_CONNECT = "linkedin_connect"
    LINKEDIN_DM      = "linkedin_dm"
    EMAIL            = "email"

class LeadStatus(str, Enum):
    RAW        = "raw"
    ENRICHED   = "enriched"
    IN_CADENCE = "in_cadence"
    CONVERTED  = "converted"
    ARCHIVED   = "archived"

class StepStatus(str, Enum):
    PENDING  = "pending"
    SENT     = "sent"
    REPLIED  = "replied"
    SKIPPED  = "skipped"
    FAILED   = "failed"

class Intent(str, Enum):
    INTEREST       = "interest"
    OBJECTION      = "objection"
    NOT_INTERESTED = "not_interested"
    NEUTRAL        = "neutral"
    OUT_OF_OFFICE  = "out_of_office"

class EmailType(str, Enum):
    CORPORATE = "corporate"
    PERSONAL  = "personal"
    UNKNOWN   = "unknown"
```

---

## Integrações externas — referência rápida

| Integração | Base URL | Auth |
|---|---|---|
| Unipile | `https://api2.unipile.com:13246/api/v1` | `X-API-KEY` header |
| OpenAI | SDK oficial | `OPENAI_API_KEY` |
| Gemini | google-genai SDK | `GEMINI_API_KEY` |
| Apify | `https://api.apify.com/v2` | `Authorization: Bearer` |
| Speechify | `https://api.sws.speechify.com/v1` | `Authorization: Bearer` |
| Pipedrive | `https://{domain}.pipedrive.com/api/v2` | `api_token` query param |
| Prospeo | `https://api.prospeo.io/v1` | `X-KEY` header |
| Hunter | `https://api.hunter.io/v2` | `api_key` query param |
| Jina | `https://r.jina.ai/{url}` | `Authorization: Bearer` |
| Firecrawl | `https://api.firecrawl.dev/v1` | `Authorization: Bearer` |
| Tavily | `https://api.tavily.com` | `api_key` no body |
| ZeroBounce | `https://api.zerobounce.net/v2` | `api_key` query param |

---

## Rate limits por canal (por tenant/dia)

```python
CHANNEL_LIMITS = {
    Channel.LINKEDIN_CONNECT: 20,
    Channel.LINKEDIN_DM:      40,
    Channel.EMAIL:            300,
}
# Redis key: ratelimit:{tenant_id}:{channel}:{YYYY-MM-DD}  TTL: 86400s
```

---

## O que NUNCA fazer

- Nunca `requests` — sempre `httpx` async
- Nunca `Base.metadata.create_all()` — sempre Alembic
- Nunca hardcodar chaves de API — sempre `settings.NOME`
- Nunca lógica de negócio em routes — mover para `services/`
- Nunca `time.sleep()` — usar `await asyncio.sleep()`
- Nunca type hints faltando em funções públicas
- Nunca `print()` — usar `logger.debug/info/error()`
- Nunca container PostgreSQL local no dev
- Nunca misturar dados de tenants
- Nunca commitar `.env.dev` ou `.env.prod`
- Nunca `import google.generativeai` — usar `from google import genai`
- Nunca importar `AsyncOpenAI` ou `genai.Client` diretamente em services
- Nunca implementar WhatsApp, Instagram ou Telefone no MVP
