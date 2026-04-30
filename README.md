# Prospector — Sistema de Prospecção B2B

Sistema automatizado de prospecção B2B com cadência multicanal (LinkedIn + Email),
personalização por IA, detecção de resposta e integração com Pipedrive.

Desenvolvido para a **Composto Web Empreendimentos Ltda** — arquitetura
multi-tenant preparada para SaaS.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn |
| Workers | Celery + Redis |
| Banco | PostgreSQL + SQLAlchemy async + Alembic |
| LLM — OpenAI | openai SDK >= 1.55 |
| LLM — Gemini | google-genai SDK >= 1.0 (GA) |
| Voz | Speechify API (SIMBA) |
| Canais | Unipile API (LinkedIn + Gmail) |
| Captação | Apify (Google Maps + LinkedIn) |
| CRM | Pipedrive API |
| Email finder | Cascata: Unipile → Prospeo → Hunter → Apollo → OSINT |
| Contexto | Jina AI + Firecrawl + Tavily |
| Monitor | Flower |

---

## Ambientes

| Ambiente | Banco | Redis | Docker Compose |
|---|---|---|---|
| **dev** | PostgreSQL remoto (Neon/Supabase) | container local | `docker-compose.dev.yml` |
| **prod** | PostgreSQL remoto | container no VPS | `docker-compose.prod.yml` |

> Não há container PostgreSQL em nenhum ambiente — banco sempre remoto.

---

## LLM Multi-Provider

O sistema suporta **OpenAI e Google Gemini simultaneamente**.
A escolha de provider e modelo é feita **por cadência**:

```json
{
  "name": "Prospecção volume",
  "llm": {
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "temperature": 0.7,
    "max_tokens": 512
  }
}
```

Modelos disponíveis em tempo real: `GET /llm/models`

Ver guia completo em [`docs/LLM.md`](docs/LLM.md)

---

## Estrutura do projeto

```
prospector/
├── api/
│   ├── main.py                  # FastAPI app factory
│   ├── dependencies.py          # DB session, auth, LLMRegistry, tenant
│   ├── routes/
│   │   ├── llm.py               # GET /llm/models, POST /llm/test
│   │   ├── leads.py
│   │   ├── cadences.py
│   │   ├── capture.py
│   │   ├── channels.py
│   │   └── analytics.py
│   └── webhooks/
│       ├── unipile.py           # message.received / invitation.accepted
│       └── pipedrive.py
│
├── integrations/
│   ├── llm/                     # Camada LLM multi-provider
│   │   ├── __init__.py          # exports: LLMMessage, LLMRegistry, etc.
│   │   ├── base.py              # LLMProvider (ABC), LLMMessage, LLMResponse
│   │   ├── openai_provider.py   # GPT-4o, GPT-4o-mini, GPT-4.1, etc.
│   │   ├── gemini_provider.py   # Gemini 2.5 Flash, Pro, Flash-Lite, etc.
│   │   └── registry.py          # LLMRegistry — agrega providers, cache Redis
│   ├── unipile.py
│   ├── apify.py
│   ├── pipedrive.py
│   ├── prospeo.py / hunter.py / apollo.py / zerobounce.py
│   ├── jina.py / firecrawl.py / tavily.py
│   └── speechify.py
│
├── workers/
│   ├── celery_app.py
│   ├── capture.py               # Apify Maps + LinkedIn
│   ├── enrich.py                # Email finder + scoring
│   ├── cadence.py               # Motor de cadência (tick/min)
│   └── dispatch.py              # Envio LinkedIn/Gmail + voice notes
│
├── services/
│   ├── ai_composer.py           # Usa LLMRegistry — provider por cadência
│   ├── reply_parser.py          # Usa LLMRegistry — settings globais
│   ├── email_finder.py          # Cascata de email finder
│   ├── email_classifier.py      # Corporativo vs pessoal
│   ├── voice.py                 # Speechify MP3
│   ├── context_fetcher.py       # Jina + Firecrawl + Tavily
│   └── scoring.py               # Score 0–100
│
├── models/
│   ├── base.py                  # Base + TenantMixin
│   ├── tenant.py
│   ├── lead.py
│   ├── cadence.py               # Inclui llm_provider, llm_model, llm_temperature, llm_max_tokens
│   ├── interaction.py
│   └── opportunity.py
│
├── schemas/
│   ├── cadence.py               # LLMConfigSchema + CadenceCreateRequest
│   ├── lead.py
│   └── analytics.py
│
├── core/
│   ├── config.py                # Settings (OPENAI_API_KEY, GEMINI_API_KEY, etc.)
│   ├── database.py
│   ├── redis_client.py
│   ├── security.py
│   └── logging.py
│
├── scheduler/beats.py
├── alembic/
├── tests/
├── docs/
│   ├── ARCHITECTURE.md          # Arquitetura técnica + diagrama
│   ├── LLM.md                   # Guia multi-provider (OpenAI + Gemini)
│   ├── ENVIRONMENTS.md          # Dev local + produção
│   └── SKILLS.md                # O que saber + sprints de desenvolvimento
│
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.worker
│
├── .env.example                 # Template com todas as variáveis
├── .env.dev                     # Dev (não commitar)
├── .env.prod                    # Prod (não commitar)
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── pyproject.toml
└── .github/copilot-instructions.md
```

---

## Setup rápido — dev

```bash
# 1. Clonar e configurar
git clone https://github.com/compostoweb/prospector.git
cd prospector
cp .env.example .env.dev
# Preencher .env.dev com as keys reais

# 2. Subir stack (sem banco — usa remoto)
docker compose -f docker-compose.dev.yml up -d

# 3. Migrations no banco remoto
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# 4. Acessar
# API docs:  http://localhost:8000/docs
# Flower:    http://localhost:5555
# LLM test:  POST http://localhost:8000/llm/test
```

---

## Setup — produção

```bash
git clone https://github.com/compostoweb/prospector.git /app/prospector
cd /app/prospector
cp .env.example .env.prod
# Preencher .env.prod

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## Comandos úteis

```bash
# Logs
docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml logs -f worker-general
docker compose -f docker-compose.dev.yml logs -f worker-content

# Dev local no Windows
npm run backend
npm run frontend
npm run worker:general
npm run worker:content
npm run extension
npm run extension:build

# Observacao
# No Windows local, o worker de engagement usa pool solo para evitar falha do Celery com prefork.

# Nova migration
docker compose -f docker-compose.dev.yml exec api \
  alembic revision --autogenerate -m "descricao"

# Aplicar migration
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# Testar LLM via curl
curl -X POST http://localhost:8000/llm/test \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"gemini-2.5-flash","prompt":"Olá!"}'

# Listar modelos disponíveis
curl http://localhost:8000/llm/models | python -m json.tool

# Rodar testes
docker compose -f docker-compose.dev.yml exec api pytest tests/ -v
```

---

## Custo mensal (MVP)

| Serviço | USD/mês |
|---|---|
| Unipile (LinkedIn + Gmail, 10 contas) | $55 |
| OpenAI (gpt-4o-mini composer + parser) | ~$5–10 |
| Gemini (opcional, por cadência) | ~$1–5 |
| Speechify TTS | ~$1 |
| Apify, Jina, Firecrawl, Tavily, ZeroBounce | $0 (free tiers) |
| Google Workspace, VPS | já pagos |
| **Total adicional** | **~$62–71/mês** |

---

## Docs

| Documento | Conteúdo |
|---|---|
| [`docs/LLM.md`](docs/LLM.md) | Guia completo multi-provider OpenAI + Gemini |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Arquitetura técnica, fluxos, modelos de dados |
| [`docs/ENVIRONMENTS.md`](docs/ENVIRONMENTS.md) | Dev local vs produção, setup, deploy |
| [`docs/EASYPANEL_DEPLOY.md`](docs/EASYPANEL_DEPLOY.md) | Configuração exata de deploy no EasyPanel para API, workers, Redis e frontend |
| [`docs/EXTENSAO_LINKEDIN_V1.md`](docs/EXTENSAO_LINKEDIN_V1.md) | Escopo, arquitetura e contratos da extensao LinkedIn V1 |
| [`docs/GOOGLE_OAUTH_SETUP.md`](docs/GOOGLE_OAUTH_SETUP.md) | Checklist exato de Google Console e variáveis de ambiente para web + extensão |
| [`docs/SKILLS.md`](docs/SKILLS.md) | Skills necessárias + ordem de desenvolvimento |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Instruções para o GitHub Copilot |
