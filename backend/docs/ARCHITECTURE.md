# Arquitetura técnica — Prospector

## Visão geral

```
┌─────────────────────────────────────────────────────────────────┐
│                      FONTES EXTERNAS                             │
│  Apify Maps │ Apify LinkedIn │ Unipile webhook │ Gmail webhook   │
└──────┬───────────┬──────────────────┬──────────────┬────────────┘
       │           │                  │              │
       ▼           ▼                  ▼              ▼
┌─────────────┐ ┌───────────┐ ┌──────────────┐ ┌──────────────┐
│capture_worker│ │enrich_    │ │FastAPI        │ │FastAPI        │
│(Celery)      │ │worker     │ │POST /webhooks │ │POST /webhooks │
└──────┬───────┘ └─────┬─────┘ └──────┬────────┘ └──────┬────────┘
       │               │              │                  │
       └───────────────┴──────────────┴──────────────────┘
                               │
              ┌────────────────▼─────────────────┐
              │         PostgreSQL + RLS           │
              │  leads · cadences · cadence_steps  │
              │  interactions · tenants            │
              └────────────────┬─────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   cadence_worker     │  ← Beat tick/min
                    └──────────┬──────────┘
                               │ enfileira
                    ┌──────────▼──────────┐
                    │   dispatch_worker    │
                    └──────┬──────┬───────┘
                           │      │
              ┌────────────▼┐    ┌▼────────────┐
              │ ai_composer  │    │  voice.py    │
              │              │    │ (Speechify)  │
              └──────┬───────┘    └┬────────────┘
                     │             │
              ┌──────▼─────────────▼──┐
              │      LLMRegistry       │
              │  (integrations/llm/)   │
              └──────┬──────┬─────────┘
                     │      │
            ┌────────▼┐    ┌▼──────────┐
            │  OpenAI  │    │  Gemini   │
            │ Provider │    │ Provider  │
            └────────┬─┘    └┬──────────┘
                     │       │
            ┌────────▼───────▼──────────┐
            │    Unipile API             │
            │  LinkedIn · Gmail          │
            └────────────┬──────────────┘
                         │ resposta
              ┌──────────▼──────────┐
              │   reply_parser       │  ← LLMRegistry (settings globais)
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  Pipedrive API       │
              └─────────────────────┘
```

---

## Camada LLM

### Estrutura

```
integrations/llm/
├── __init__.py          # exports limpos do módulo
├── base.py              # LLMProvider (ABC), LLMMessage, LLMResponse, ModelInfo
├── openai_provider.py   # OpenAIProvider — gpt-4o, gpt-4o-mini, gpt-4.1, etc.
├── gemini_provider.py   # GeminiProvider — gemini-2.5-flash, gemini-2.5-pro, etc.
└── registry.py          # LLMRegistry — agrega providers, cache Redis, resolve completions
```

### Responsabilidades do LLMRegistry

- Instancia providers conforme keys disponíveis em settings
- Expõe `complete()` único para todo o sistema
- Agrega `list_models()` de todos os providers com cache Redis 1h
- Levanta `ValueError` claro se o provider não estiver configurado

### Seleção de modelo por cadência

Cada `Cadence` tem 4 campos LLM:

```
llm_provider     "openai" | "gemini"
llm_model        ex: "gpt-4o-mini" | "gemini-2.5-flash"
llm_temperature  0.0 – 1.0
llm_max_tokens   64 – 8192
```

Isso permite cadências paralelas com modelos diferentes:
- Cadência de volume → `gemini-2.5-flash-lite` ($0.10/MTok in)
- Cadência de alto valor → `gpt-4o` ou `gemini-2.5-pro`
- Reply parser e classificações inbound → configuração efetiva do tenant por escopo

### Modelos disponíveis (março 2026)

| Provider | Modelo | Input $/MTok | Output $/MTok | Uso recomendado |
|---|---|---|---|---|
| openai | gpt-4o-mini | $0.15 | $0.60 | Composer equilibrado |
| openai | gpt-4o | $2.50 | $10.00 | Composer alto valor |
| openai | gpt-4.1-nano | $0.10 | $0.40 | Volume máximo |
| openai | gpt-4.1-mini | $0.40 | $1.60 | Equilíbrio |
| openai | gpt-4.1 | $2.00 | $8.00 | Alto valor |
| gemini | gemini-2.5-flash-lite | $0.10 | $0.40 | Volume máximo |
| gemini | gemini-2.5-flash | $0.30 | $2.50 | Padrão recomendado |
| gemini | gemini-2.5-pro | $1.25 | $10.00 | Alto valor |

> Lista sempre atualizada via `GET /llm/models` (busca direto das APIs + cache 1h)

### Endpoints LLM

```
GET  /llm/providers          lista providers configurados
GET  /llm/models             todos os modelos (cache Redis 1h)
GET  /llm/models/{provider}  filtra por provider
POST /llm/test               testa um modelo com prompt simples
```

---

## Multi-tenancy

### Modelo de dados

Toda tabela tem `tenant_id UUID NOT NULL FK → tenants.id`.

```sql
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON leads
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### Isolamento por request

```python
async def get_session(tenant_id: UUID) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tid"),
            {"tid": str(tenant_id)}
        )
        yield session
```

### Credenciais por tenant (TenantIntegration)

```python
class TenantIntegration(Base):
    tenant_id: UUID
    # Unipile
    unipile_linkedin_account_id: str
    unipile_gmail_account_id: str
    # Pipedrive (criptografado)
    pipedrive_api_token: str
    pipedrive_domain: str
    pipedrive_stage_interest: int
    pipedrive_stage_objection: int
    pipedrive_owner_id: int
    notify_email: str
    # Cadência
    allow_personal_email: bool = False
    limit_linkedin_connect: int = 20
    limit_linkedin_dm: int = 40
    limit_email: int = 300
```

---

## Modelos de dados

### Lead

```python
class Lead(Base, TenantMixin):
    id: UUID
    name: str
    company: str | None
    website: str | None
    linkedin_url: str | None
    linkedin_profile_id: str | None
    city: str | None
    segment: str | None
    source: LeadSource           # apify_maps | apify_linkedin | manual
    status: LeadStatus           # raw | enriched | in_cadence | converted | archived
    score: int                   # 0–100
    # Emails
    email_corporate: str | None
    email_corporate_source: str | None
    email_corporate_verified: bool
    email_personal: str | None
    email_personal_source: str | None
    phone: str | None
    enriched_at: datetime | None
    notes: str | None
```

### Cadence

```python
class Cadence(Base, TenantMixin):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    allow_personal_email: bool
    # LLM — selecionado por cadência
    llm_provider: str            # "openai" | "gemini"
    llm_model: str               # ex: "gpt-4o-mini"
    llm_temperature: float       # 0.0–1.0
    llm_max_tokens: int          # 64–8192
```

### CadenceStep

```python
class CadenceStep(Base, TenantMixin):
    id: UUID
    cadence_id: UUID
    lead_id: UUID
    channel: Channel             # linkedin_connect | linkedin_dm | email
    step_number: int
    day_offset: int
    use_voice: bool              # True = voice note MP3 (só linkedin_dm)
    status: StepStatus           # pending | sent | replied | skipped | failed
    scheduled_at: datetime
    sent_at: datetime | None
```

### Interaction

```python
class Interaction(Base, TenantMixin):
    id: UUID
    lead_id: UUID
    channel: Channel
    direction: str               # outbound | inbound
    content_text: str | None
    content_audio_url: str | None
    intent: Intent | None        # classificado pela IA (inbound)
    unipile_message_id: str | None
    opened: bool                 # para email
```

---

## Fluxo de cadência

### 1. Captação → enriquecimento
```
Apify → leads raw → enrich_worker:
  cascata email finder (Unipile → Prospeo → Hunter → Apollo → OSINT)
  → classifica corporativo/pessoal
  → scoring inicial
  → status = enriched
  → cria CadenceSteps com day_offset
```

### 2. Cadência tick (Beat a cada minuto)
```
SELECT steps WHERE scheduled_at <= now() AND status = pending
→ verifica rate limit Redis
→ dispatch_worker.dispatch_step.delay(step_id)
```

### 3. Dispatch
```
→ context_fetcher (Jina + Firecrawl + Tavily) → cache Redis 24h
→ ai_composer.compose() via LLMRegistry(cadence.llm_provider, cadence.llm_model)
→ se use_voice: voice.generate() → MP3 → unipile.send_voice_note()
→ senão: unipile.send_message() ou unipile.send_email()
→ salva Interaction outbound
→ step.status = sent
```

### 4. Resposta recebida
```
Unipile webhook → pause_cadence()
→ resolve_tenant_llm_config(tenant_id) → reply_parser.classify()
→ INTEREST/OBJECTION → pipedrive.create_deal() + notify_seller()
→ NOT_INTERESTED → archive_lead()
→ OUT_OF_OFFICE → reschedule_cadence(return_date)
→ NEUTRAL → notify_seller(priority=low)
```

---

## Rate limiting

```python
# Redis key: ratelimit:{tenant_id}:{channel}:{YYYY-MM-DD}  TTL: 86400s
CHANNEL_LIMITS = {
    Channel.LINKEDIN_CONNECT: 20,
    Channel.LINKEDIN_DM:      40,
    Channel.EMAIL:            300,
}
```

---

## Celery Beat schedule

```python
CELERY_BEAT_SCHEDULE = {
    "cadence-tick":             crontab(minute="*"),        # todo minuto
    "capture-maps-daily":       crontab(hour="8"),          # 08:00
    "capture-linkedin-daily":   crontab(hour="9"),          # 09:00
    "enrich-pending":           crontab(minute="*/30"),     # 30 em 30 min
}
```

---

## Custo mensal MVP

| Serviço | USD/mês |
|---|---|
| Unipile (10 contas) | $55 |
| OpenAI GPT-4o-mini (composer + parser) | ~$5–10 |
| Gemini (opcional, por cadência) | ~$1–5 |
| Speechify TTS | ~$1 |
| Apify, Jina, Firecrawl, Tavily, ZeroBounce | $0 (free tiers) |
| **Total** | **~$62–71** |
