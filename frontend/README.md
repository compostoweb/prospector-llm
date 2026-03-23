# frontend/

Frontend do Prospector. Parte do monorepo `prospector/`.

```
prospector/
├── backend/    FastAPI (já funcional)
└── frontend/   ← você está aqui
```

## Setup

```bash
# 1. Pré-requisito: backend rodando
cd ../backend
docker compose -f docker-compose.dev.yml up -d

# 2. Instalar dependências
cd ../frontend
npm install

# 3. Configurar variáveis
cp .env.example .env.local

# 4. Gerar tipos da API (backend precisa estar rodando)
npm run generate:api

# 5. Iniciar
npm run dev
# → http://localhost:3000
```

## Comandos

```bash
npm run dev           # Next.js com Turbopack
npm run build         # build de produção
npm run lint          # ESLint + tsc
npm run test          # Vitest
npm run test:e2e      # Playwright
npm run generate:api  # Gera src/lib/api/schema.d.ts do backend
npm run format        # Prettier
```

## Auth — Google OAuth

O login com Google é gerenciado pelo backend.
O frontend apenas redireciona para `{API_URL}/auth/google/login`
e recebe o JWT de volta em `/auth/callback?token=...`.

Não há `GOOGLE_CLIENT_ID` nem `GOOGLE_CLIENT_SECRET` no frontend.

## Docs

- [`COPILOT_KICKOFF_FRONTEND.md`](COPILOT_KICKOFF_FRONTEND.md) — kickoff para o Copilot Chat
- [`.github/copilot-instructions.md`](.github/copilot-instructions.md) — regras permanentes
