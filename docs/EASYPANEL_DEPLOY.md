# Deploy de Produção no EasyPanel

Este guia traduz a stack real do repositório para a configuração do EasyPanel.

Topologia recomendada em produção:

- frontend web: https://prospector.compostoweb.com.br
- api: https://api.prospector.compostoweb.com.br
- redis: serviço interno no EasyPanel
- postgres: remoto, fora do EasyPanel
- workers celery: serviços separados
- beat: serviço separado
- flower: opcional

## 1. Regra principal do backend no EasyPanel

Para qualquer serviço que use os Dockerfiles do backend, o build path correto é:

- `/backend`

O screenshot com build path `/` está incorreto para este repositório.

Motivo:

- os Dockerfiles usam `COPY pyproject.toml .`
- esse arquivo existe em `backend/pyproject.toml`
- se o contexto for `/`, o build quebra ou copia o diretório errado

## 2. Serviço API

Crie um app no EasyPanel para a API com estes valores:

### Source

- Provider: GitHub
- Owner: `compostoweb`
- Repository: `prospector-llm`
- Branch: `master`
- Build Path: `/backend`

### Build

- Tipo: Dockerfile
- Dockerfile path: `docker/Dockerfile.api`

### Runtime

- Internal port: `8000`
- Start command: deixar o padrão do Dockerfile ou definir explicitamente:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Healthcheck

- Path: `/health`
- Port: `8000`

### Domain

- domínio público recomendado: `api.prospector.compostoweb.com.br`

### Environment variables mínimas

Use como base o bloco de [docs/GOOGLE_OAUTH_SETUP.md](docs/GOOGLE_OAUTH_SETUP.md).

Mínimo necessário para subir a API:

```env
ENV=prod
DEBUG=false

DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/prospector_prod
REDIS_URL=redis://SEU_SERVICO_REDIS:6379/0
CELERY_BROKER_URL=redis://SEU_SERVICO_REDIS:6379/1
CELERY_RESULT_BACKEND=redis://SEU_SERVICO_REDIS:6379/2

SECRET_KEY=TROQUE_POR_UMA_CHAVE_LONGA_E_ALEATORIA
API_PUBLIC_URL=https://api.prospector.compostoweb.com.br
FRONTEND_URL=https://prospector.compostoweb.com.br
TRACKING_BASE_URL=https://api.prospector.compostoweb.com.br
ALLOWED_ORIGINS=["https://prospector.compostoweb.com.br","https://api.prospector.compostoweb.com.br"]

GOOGLE_CLIENT_ID=seu-client-id-prod.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret-prod
GOOGLE_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/google/callback
GOOGLE_EXTENSION_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/extension/google/callback

EXTENSION_LINKEDIN_CAPTURE_ENABLED=true
EXTENSION_CAPTURE_DAILY_LIMIT=250
EXTENSION_ALLOWED_IDS=SEU_EXTENSION_ID_PROD
```

## 3. Serviço Redis

Crie um serviço Redis gerenciado no próprio EasyPanel.

Configuração sugerida:

- Image: `redis:7-alpine`
- Command: `redis-server --appendonly yes`
- Volume persistente: habilitado
- Exposição pública: não

Depois substitua `SEU_SERVICO_REDIS` pelo hostname interno que o EasyPanel gerar para esse serviço.

Exemplo típico:

```env
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

## 4. Workers Celery

Cada worker é um app separado no EasyPanel usando o mesmo build do backend.

Configuração base para todos:

- Owner: `compostoweb`
- Repository: `prospector-llm`
- Branch: `master`
- Build Path: `/backend`
- Build type: Dockerfile
- Dockerfile path: `docker/Dockerfile.worker`

Use exatamente as mesmas environment variables da API.

### worker-capture

Start command:

```bash
celery -A workers.celery_app worker -Q capture -c 2 --loglevel=warning
```

### worker-dispatch

Start command:

```bash
celery -A workers.celery_app worker -Q dispatch -c 4 --loglevel=warning
```

### worker-cadence

Start command:

```bash
celery -A workers.celery_app worker -Q cadence -c 1 --loglevel=warning
```

### worker-enrich

Start command:

```bash
celery -A workers.celery_app worker -Q enrich -c 2 --loglevel=warning
```

### worker-content

Start command:

```bash
celery -A workers.celery_app worker -Q content -c 2 --loglevel=warning
```

### worker-content-engagement

Start command:

```bash
celery -A workers.celery_app worker -Q content-engagement -c 2 --loglevel=warning
```

## 5. Serviço Beat

Mesmo build do worker.

Start command:

```bash
celery -A workers.celery_app beat --loglevel=warning --schedule /tmp/celerybeat-schedule
```

Motivo:

- o Celery Beat usa um arquivo local de estado
- no container, a pasta /app pode nao ser gravavel para apagar/recriar esse arquivo
- usando /tmp/celerybeat-schedule, o beat consegue recriar o estado sem falhar por permissao

## 6. Serviço Flower

Opcional, mas útil para operação.

Mesmo build do worker.

### Runtime

- Internal port: `5555`

### Start command

```bash
celery -A workers.celery_app flower --port=5555 --basic_auth=${FLOWER_USER}:${FLOWER_PASSWORD}
```

### Variáveis extras

```env
FLOWER_USER=admin
FLOWER_PASSWORD=TROQUE_AQUI
```

### Domínio opcional

- `flower.prospector.compostoweb.com.br`

## 7. Frontend Next.js

O frontend não tem Dockerfile no repositório. No EasyPanel, a opção mais direta é subir como app Node com Nixpacks.

### Source

- Owner: `compostoweb`
- Repository: `prospector-llm`
- Branch: `master`
- Build Path: `/frontend`

### Build

- Tipo: Nixpacks

### Runtime

- Install command: `npm ci`
- Build command: `npm run build`
- Start command: `npm run start`
- Internal port: `3000`

### Domain

- domínio público recomendado: `prospector.compostoweb.com.br`

### Environment variables mínimas

```env
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://api.prospector.compostoweb.com.br
NEXT_PUBLIC_WS_URL=wss://api.prospector.compostoweb.com.br/ws/events
NEXT_PUBLIC_APP_URL=https://prospector.compostoweb.com.br
API_URL=https://api.prospector.compostoweb.com.br
NEXTAUTH_URL=https://prospector.compostoweb.com.br
NEXTAUTH_SECRET=gere-com-openssl-rand-base64-32
```

## 8. Ordem correta de subida

No primeiro deploy, suba nesta ordem:

1. Redis
2. API
3. Console da API: rodar `alembic upgrade head`
4. workers
5. beat
6. frontend
7. flower, se for usar

## 9. Migrations no EasyPanel

Depois que a API estiver de pé, execute dentro do container da API:

```bash
alembic upgrade head
```

Se o EasyPanel oferecer comando pós-deploy ou release command, você pode usar esse mesmo comando.

## 10. Checklist de produção

- `Build Path` da API e workers está em `/backend`
- `Dockerfile path` da API está em `docker/Dockerfile.api`
- `Dockerfile path` dos workers está em `docker/Dockerfile.worker`
- frontend está com `Build Path` em `/frontend`
- `DATABASE_URL` aponta para o banco remoto de produção
- `REDIS_URL`, `CELERY_BROKER_URL` e `CELERY_RESULT_BACKEND` apontam para o Redis interno do EasyPanel
- `API_PUBLIC_URL` e `FRONTEND_URL` usam os domínios reais
- redirects do Google usam o host da API
- `NEXT_PUBLIC_API_URL` do frontend aponta para a API pública
- `NEXTAUTH_URL` aponta para o domínio público do frontend

## 11. Erros mais prováveis no EasyPanel

### Build falha logo no começo

Causa comum:

- build path configurado como `/` em vez de `/backend`

### API sobe mas workers não conectam

Causa comum:

- `CELERY_BROKER_URL` ou `CELERY_RESULT_BACKEND` apontando para `localhost` em vez do serviço Redis do EasyPanel

### Login Google redireciona errado

Causa comum:

- `FRONTEND_URL`, `API_PUBLIC_URL`, `GOOGLE_REDIRECT_URI` ou `GOOGLE_EXTENSION_REDIRECT_URI` com host divergente do domínio real publicado

### Frontend sobe mas não fala com a API

Causa comum:

- `NEXT_PUBLIC_API_URL` ou `API_URL` ainda em localhost