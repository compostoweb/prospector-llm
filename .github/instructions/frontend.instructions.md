---
applyTo: "frontend/**"
---

# GitHub Copilot — Instruções do Prospector (frontend/)

## Contexto do monorepo

```
prospector/
├── backend/    FastAPI + Celery + PostgreSQL (já funcional)
└── frontend/   Next.js 15 — você está aqui
```

O backend está funcional. Nunca mova lógica de negócio para o frontend.
Nunca duplique rotas do backend em `app/api/` (exceto NextAuth).

---

## Auth — Google OAuth via backend (não via NextAuth diretamente)

O Google OAuth é gerenciado 100% pelo backend FastAPI.
O NextAuth no frontend só gerencia a sessão após o backend concluir o fluxo.

```
Usuário clica "Entrar com Google"
  → window.location.href = {API_URL}/auth/google/login   (backend inicia OAuth)
  → Google consent screen
  → Backend valida e gera JWT
  → Backend redireciona → /auth/callback?token=...&refresh=...  (frontend)
  → Next.js cria sessão NextAuth com o JWT do backend
  → Redireciona para /dashboard
```

O frontend **não tem** `GOOGLE_CLIENT_ID` nem `GOOGLE_CLIENT_SECRET`.
O Google OAuth callback aponta para o **backend**, nunca para o Next.js.

---

## Stack — nunca sugerir alternativas

| Camada        | Tecnologia                                         |
| ------------- | -------------------------------------------------- |
| Framework     | Next.js 15 App Router                              |
| UI            | React 19 + TypeScript 5 strict                     |
| Estilos       | Tailwind CSS v4 + design-system.css                |
| Componentes   | shadcn/ui + Radix UI                               |
| Data fetching | TanStack Query v5                                  |
| State UI      | Zustand v5 (persist para sidebar)                  |
| HTTP client   | ky + openapi-fetch (tipado pelo schema do backend) |
| Auth          | NextAuth v5 — CredentialsProvider customizado      |
| Tema          | next-themes (`attribute="data-theme"`)             |
| Gráficos      | Recharts                                           |
| Ícones        | lucide-react                                       |
| Animações     | Framer Motion v11                                  |
| Env           | @t3-oss/env-nextjs (build falha se var faltando)   |

---

## Regras obrigatórias

### Imports — sempre via @/

```typescript
// CORRETO
import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";

// ERRADO — nunca
import { api } from "../../lib/api/client";
```

### Variáveis de ambiente — sempre via env.ts

```typescript
// CORRETO
import { env } from "@/env";
const url = env.NEXT_PUBLIC_API_URL;

// ERRADO
const url = process.env.NEXT_PUBLIC_API_URL;
```

### Cores — sempre via tokens CSS do design-system

```typescript
// CORRETO — sintaxe Tailwind v4 (CSS variable shorthand)
className="bg-(--bg-surface) text-(--text-primary)"
style={{ color: "var(--accent)" }}

// ERRADO — sintaxe antiga (Tailwind v3), gera warnings no linter
className="bg-[var(--bg-surface)] text-[var(--text-primary)]"

// ERRADO — nunca hardcodar cores Tailwind padrão
className="bg-white text-gray-900 text-blue-600"
```

### Data fetching — TanStack Query, nunca useState

```typescript
// CORRETO
"use client"
function LeadTable({ initialData }: Props) {
  const { data } = useLeads({ initialData })
}

// ERRADO
"use client"
function LeadTable() {
  const [leads, setLeads] = useState([])
  useEffect(() => fetch(...).then(setLeads), [])
}
```

### API client — sempre tipado via openapi-fetch

```typescript
// CORRETO
import { api } from "@/lib/api/client";
const { data } = await api.GET("/leads/{id}", { params: { path: { id } } });

// ERRADO
const data = await ky.get(`/leads/${id}`).json();
const data = await fetch(`/api/leads/${id}`).then((r) => r.json());
```

### Server vs Client Components

```typescript
// Server Component (padrão) — busca dados no servidor
async function LeadsPage() {
  const { data } = await serverApi.GET("/leads")
  return <LeadTable initialData={data} />
}

// "use client" APENAS quando usar:
// - event handlers, useState, useEffect
// - hooks (useSession, useTheme, useRouter, etc.)
// - browser APIs (window, localStorage)
```

### Componentes — props tipadas explicitamente

```typescript
// CORRETO
interface Props {
  lead: Lead;
  onArchive: (id: string) => Promise<void>;
  className?: string;
}
export default function LeadCard({ lead, onArchive, className }: Props) {}

// ERRADO
export default function LeadCard(props: any) {}
```

---

## Estrutura de pastas

| O que criar               | Onde                           |
| ------------------------- | ------------------------------ |
| Páginas e layouts         | `src/app/`                     |
| Componentes reutilizáveis | `src/components/`              |
| shadcn/ui (auto-gerados)  | `src/components/ui/`           |
| Hooks TanStack Query      | `src/lib/api/hooks/`           |
| API client tipado         | `src/lib/api/client.ts`        |
| Tipos gerados do backend  | `src/lib/api/schema.d.ts`      |
| Auth NextAuth config      | `src/lib/auth/config.ts`       |
| WebSocket hook            | `src/lib/ws/use-events.ts`     |
| Utilitários               | `src/lib/utils.ts`             |
| Zustand stores            | `src/store/`                   |
| Tokens CSS                | `src/styles/design-system.css` |
| Env validation            | `src/env.ts`                   |

---

## Rotas

| Rota                         | Tipo      | Descrição                            |
| ---------------------------- | --------- | ------------------------------------ |
| `/login`                     | pública   | Botão "Entrar com Google"            |
| `/auth/callback`             | API route | Recebe token do backend, cria sessão |
| `/dashboard`                 | protegida | Métricas, respostas, notificações    |
| `/leads`                     | protegida | Lista com filtros                    |
| `/leads/[id]`                | protegida | Perfil, timeline, cadência, score    |
| `/cadencias`                 | protegida | Lista e criação                      |
| `/cadencias/[id]`            | protegida | Editor + config LLM                  |
| `/configuracoes/llm`         | protegida | Provider/modelo + teste              |
| `/configuracoes/integracoes` | protegida | Unipile, Pipedrive                   |

---

## Tipagem da API — manter sincronizada com o backend

```bash
# Sempre que o backend mudar contratos:
npm run generate:api
# Gera src/lib/api/schema.d.ts a partir do OpenAPI do backend
```

---

## Design system — tokens obrigatórios

```css
/* Backgrounds */
var(--bg-page)        /* fundo da página */
var(--bg-surface)     /* cards, painéis */
var(--bg-overlay)     /* hover, stat cards */
var(--bg-sunken)      /* recesso */

/* Texto */
var(--text-primary)
var(--text-secondary)
var(--text-tertiary)

/* Acento */
var(--accent)
var(--accent-subtle)
var(--accent-subtle-fg)

/* Semânticos */
var(--success) / var(--success-subtle) / var(--success-subtle-fg)
var(--warning) / var(--warning-subtle) / var(--warning-subtle-fg)
var(--danger)  / var(--danger-subtle)  / var(--danger-subtle-fg)
var(--info)    / var(--info-subtle)    / var(--info-subtle-fg)

/* Layout */
var(--radius-md)      /* 8px */
var(--radius-lg)      /* 10px */
var(--shadow-sm) / var(--shadow-md) / var(--shadow-lg)
var(--border-default) / var(--border-subtle)
```

---

## O que NUNCA fazer

- Nunca `axios` ou `swr`
- Nunca `useState` para dados remotos
- Nunca `process.env.` direto — sempre `env.` de `@/env`
- Nunca cores Tailwind hardcoded (`text-blue-500`, `bg-white`)
- Nunca `any` no TypeScript
- Nunca `!` non-null assertion sem comentário
- Nunca lógica de negócio no frontend
- Nunca `app/api/` routes (exceto `/auth/callback` e NextAuth handlers)
- Nunca imports relativos com `../`
- Nunca `GOOGLE_CLIENT_ID` ou `GOOGLE_CLIENT_SECRET` no frontend
- Nunca iniciar o fluxo OAuth diretamente do Next.js — sempre via `{API_URL}/auth/google/login`
