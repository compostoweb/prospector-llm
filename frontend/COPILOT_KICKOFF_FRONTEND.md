# PROMPT DE KICKOFF — frontend/ do Prospector
# Cole no GitHub Copilot Chat ao abrir a pasta frontend/ no VS Code.
# O Copilot também lê .github/copilot-instructions.md automaticamente.
# Siga este documento sem exceções — não sugira stack alternativa.

---

Você está me ajudando a criar o **frontend/** do Prospector, sistema de
prospecção B2B da Composto Web. Este é um monorepo:

```
prospector/
├── backend/    FastAPI + Celery + PostgreSQL (já funcional)
└── frontend/   ← estamos aqui (criando do zero)
```

O backend já existe e está 100% funcional. Nunca sugira mover lógica de
negócio para o frontend nem criar rotas Next.js que dupliquem o backend.

---

## Contexto do backend (já implementado)

### Auth — Google OAuth via FastAPI

O backend tem login com Google OAuth2 implementado diretamente no FastAPI.
O fluxo é:

```
1. Frontend redireciona → GET /auth/google/login
2. Backend redireciona → Google OAuth consent screen
3. Google redireciona → GET /auth/google/callback (backend)
4. Backend valida, cria/atualiza usuário, gera JWT próprio
5. Backend redireciona → frontend com JWT em query param ou cookie
```

Endpoints relevantes no backend:
```
GET  /auth/google/login      → inicia o fluxo OAuth, redireciona para Google
GET  /auth/google/callback   → Google chama este após autorizar
POST /auth/refresh           → renova o JWT com refresh token
GET  /auth/me                → retorna dados do usuário logado
POST /auth/logout            → invalida o refresh token
```

O JWT retornado pelo backend contém:
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "email": "user@empresa.com",
  "name": "Nome do Usuário",
  "picture": "https://lh3.googleusercontent.com/...",
  "exp": 1234567890
}
```

### LLM Multi-provider
Cada cadência tem `llm_provider` (openai|gemini) e `llm_model` configuráveis.
Endpoints:
```
GET  /llm/providers          → providers configurados
GET  /llm/models             → modelos disponíveis (cache 1h)
GET  /llm/models/{provider}  → filtra por provider
POST /llm/test               → testa um modelo
```

---

## Stack do frontend — não negociável

| Camada | Tecnologia | Versão |
|---|---|---|
| Framework | Next.js App Router | 15 |
| Runtime | React | 19 |
| Linguagem | TypeScript strict | 5 |
| Estilos | Tailwind CSS | v4 |
| Componentes | shadcn/ui + Radix UI | latest |
| Data fetching | TanStack Query | v5 |
| State global UI | Zustand | v5 |
| HTTP client | ky + openapi-fetch | latest |
| Auth | NextAuth | v5 (beta) |
| Tema light/dark | next-themes | latest |
| Gráficos | Recharts | v2 |
| Ícones | lucide-react | latest |
| Animações | Framer Motion | v11 |
| Env type-safe | @t3-oss/env-nextjs | latest |
| Linting | ESLint + Prettier | — |
| Testes unit | Vitest + Testing Library | — |
| Testes E2E | Playwright | — |

**Nunca usar:** `axios`, `swr`, `useState` para dados remotos,
`process.env.` direto, cores Tailwind hardcoded, `any` no TypeScript,
imports com `../../`.

---

## Dois ambientes

| | Dev | Prod |
|---|---|---|
| Env file | `.env.local` | Vercel env vars |
| Frontend | `http://localhost:3000` | `https://app.seudominio.com.br` |
| Backend API | `http://localhost:8000` | `https://api.seudominio.com.br` |
| WebSocket | `ws://localhost:8000/ws/events` | `wss://api.seudominio.com.br/ws/events` |
| Google OAuth callback | `http://localhost:8000/auth/google/callback` | `https://api.seudominio.com.br/auth/google/callback` |

> O callback do Google aponta para o **backend**, não para o Next.js.
> O Next.js não precisa de `GOOGLE_CLIENT_ID` nem `GOOGLE_CLIENT_SECRET`.

---

## Estrutura de pastas

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                    # Root layout — providers globais
│   │   ├── page.tsx                      # Redireciona → /dashboard
│   │   ├── (auth)/
│   │   │   └── login/
│   │   │       └── page.tsx             # Página de login com botão Google
│   │   └── (app)/                       # Layout protegido (sidebar + topbar)
│   │       ├── layout.tsx
│   │       ├── dashboard/page.tsx
│   │       ├── leads/
│   │       │   ├── page.tsx
│   │       │   └── [id]/page.tsx
│   │       ├── cadencias/
│   │       │   ├── page.tsx
│   │       │   └── [id]/page.tsx
│   │       └── configuracoes/
│   │           ├── llm/page.tsx
│   │           └── integracoes/page.tsx
│   │
│   ├── components/
│   │   ├── ui/                          # shadcn/ui — não editar manualmente
│   │   ├── layout/
│   │   │   ├── sidebar.tsx
│   │   │   ├── topbar.tsx
│   │   │   └── theme-toggle.tsx
│   │   ├── auth/
│   │   │   └── google-sign-in-button.tsx
│   │   ├── leads/
│   │   │   ├── lead-table.tsx
│   │   │   ├── lead-card.tsx
│   │   │   ├── lead-timeline.tsx
│   │   │   └── lead-score.tsx
│   │   ├── cadencias/
│   │   │   ├── cadence-form.tsx
│   │   │   ├── cadence-steps.tsx
│   │   │   └── llm-config-form.tsx
│   │   ├── dashboard/
│   │   │   ├── stat-card.tsx
│   │   │   ├── channel-chart.tsx
│   │   │   └── recent-replies.tsx
│   │   └── shared/
│   │       ├── badge-intent.tsx
│   │       ├── badge-channel.tsx
│   │       └── empty-state.tsx
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts               # ky instance + openapi-fetch tipado
│   │   │   ├── schema.d.ts             # gerado por openapi-typescript (não editar)
│   │   │   └── hooks/
│   │   │       ├── use-leads.ts
│   │   │       ├── use-cadences.ts
│   │   │       ├── use-llm-models.ts
│   │   │       └── use-analytics.ts
│   │   ├── auth/
│   │   │   └── config.ts              # NextAuth config — Google delegando ao backend
│   │   ├── ws/
│   │   │   └── use-events.ts          # WebSocket hook
│   │   └── utils.ts
│   │
│   ├── store/
│   │   ├── ui-store.ts
│   │   └── notifications-store.ts
│   │
│   ├── styles/
│   │   ├── globals.css
│   │   └── design-system.css          # Tokens CSS light/dark do Prospector
│   │
│   └── env.ts                         # @t3-oss/env-nextjs
│
├── public/
├── .github/copilot-instructions.md
├── .env.example
├── .env.local                         # Dev — não commitar
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── vitest.config.ts
├── playwright.config.ts
└── package.json
```

---

## Fluxo de autenticação — detalhe completo

O NextAuth v5 é configurado no modo **Custom Backend** — ele não faz
OAuth diretamente, apenas gerencia a sessão no lado Next.js após o
backend concluir o fluxo com o Google.

### Fluxo completo

```
1. Usuário clica "Entrar com Google" → frontend
2. Frontend redireciona para: GET {NEXT_PUBLIC_API_URL}/auth/google/login
3. Backend redireciona para Google consent screen
4. Usuário autoriza no Google
5. Google chama: GET {NEXT_PUBLIC_API_URL}/auth/google/callback
6. Backend valida, cria sessão, gera access_token + refresh_token (JWT)
7. Backend redireciona para:
   {NEXT_PUBLIC_APP_URL}/auth/callback?token={access_token}&refresh={refresh_token}
8. Next.js captura o token na rota /auth/callback
9. NextAuth cria sessão interna com os dados do JWT do backend
10. Usuário é redirecionado para /dashboard
```

### Implementação do NextAuth (`src/lib/auth/config.ts`)

Usar `CredentialsProvider` com um provider customizado que aceita o token
já validado pelo backend — não usa Google Provider do NextAuth diretamente:

```typescript
import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import { jwtDecode } from "jwt-decode"

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      id: "backend-google",
      name: "Google via Backend",
      credentials: {
        access_token: { type: "text" },
        refresh_token: { type: "text" },
      },
      async authorize({ access_token, refresh_token }) {
        // Valida o token com o backend
        const res = await fetch(`${process.env.API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${access_token}` },
        })
        if (!res.ok) return null

        const user = await res.json()
        return {
          id: user.id,
          name: user.name,
          email: user.email,
          image: user.picture,
          tenant_id: user.tenant_id,
          access_token,
          refresh_token,
        }
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.tenant_id = user.tenant_id
        token.access_token = user.access_token
        token.refresh_token = user.refresh_token
      }
      return token
    },
    session({ session, token }) {
      session.user.tenant_id = token.tenant_id as string
      session.accessToken = token.access_token as string
      return session
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: { strategy: "jwt" },
})
```

### Rota de callback (`src/app/auth/callback/route.ts`)

Rota de API Next.js que captura o token vindo do backend e cria a sessão NextAuth:

```typescript
// app/auth/callback/route.ts
import { signIn } from "@/lib/auth/config"
import { redirect } from "next/navigation"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const token = searchParams.get("token")
  const refresh = searchParams.get("refresh")

  if (!token) redirect("/login?error=no_token")

  await signIn("backend-google", {
    access_token: token,
    refresh_token: refresh ?? "",
    redirect: false,
  })

  redirect("/dashboard")
}
```

### Botão "Entrar com Google" (`src/components/auth/google-sign-in-button.tsx`)

```typescript
"use client"
import { env } from "@/env"

export function GoogleSignInButton() {
  const handleLogin = () => {
    // Redireciona direto para o backend iniciar o fluxo OAuth
    window.location.href = `${env.NEXT_PUBLIC_API_URL}/auth/google/login`
  }

  return (
    <button onClick={handleLogin}>
      {/* ícone Google SVG + "Entrar com Google" */}
    </button>
  )
}
```

---

## Sprint 1 — Fundação (20 arquivos em ordem)

Implemente um arquivo por vez, completo e funcional.
Sem `// TODO`, sem stubs, sem código comentado.
Após cada arquivo: mostre o código completo e indique o próximo.

---

### 1. `package.json`

Scripts obrigatórios:
- `dev` → `next dev --turbo`
- `build` → `next build`
- `lint` → `next lint && tsc --noEmit`
- `test` → `vitest run`
- `test:e2e` → `playwright test`
- `generate:api` → `openapi-typescript http://localhost:8000/openapi.json -o src/lib/api/schema.d.ts`
- `format` → `prettier --write .`

Dependências obrigatórias da stack listada acima, mais:
- `jwt-decode` — decodificar JWT do backend no client
- `@auth/core` — NextAuth v5 core

---

### 2. `tsconfig.json`

- `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`
- Path alias `@/*` → `./src/*`
- Target ES2022, module bundler
- Include: `src/**/*`, `next.config.ts`

---

### 3. `next.config.ts`

- `reactStrictMode: true`
- `experimental.typedRoutes: true`
- Configurar `rewrites` para que `/api/backend/*` faça proxy para o backend
  em dev (evita CORS): `{ source: "/api/backend/:path*", destination: "http://localhost:8000/:path*" }`
- Headers de segurança em prod (X-Frame-Options, X-Content-Type-Options)
- `images.remotePatterns` incluindo `lh3.googleusercontent.com` (fotos do Google)

---

### 4. `src/env.ts`

Validar com `@t3-oss/env-nextjs`:

**Client (NEXT_PUBLIC_):**
- `NEXT_PUBLIC_API_URL` — URL do backend (ex: `http://localhost:8000`)
- `NEXT_PUBLIC_WS_URL` — WebSocket (ex: `ws://localhost:8000/ws/events`)
- `NEXT_PUBLIC_APP_URL` — URL do próprio frontend (ex: `http://localhost:3000`)

**Server:**
- `NEXTAUTH_SECRET` — min 32 chars
- `NEXTAUTH_URL` — URL do frontend
- `API_URL` — URL do backend para uso server-side (sem NEXT_PUBLIC_)
- `NODE_ENV` — enum development|production|test

---

### 5. `.env.example`

```bash
# Backend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/events
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Server-side (sem NEXT_PUBLIC — não exposto ao browser)
API_URL=http://localhost:8000

# Auth
NEXTAUTH_SECRET=gere-com-openssl-rand-base64-32
NEXTAUTH_URL=http://localhost:3000

# Não precisamos de GOOGLE_CLIENT_ID aqui
# O Google OAuth é gerenciado 100% pelo backend FastAPI
```

---

### 6. `tailwind.config.ts`

- Content: `src/**/*.{ts,tsx}`
- Dark mode via `class`
- Extend: fonte `DM Sans` como `sans`
- Sem cores customizadas — cores via tokens CSS do design-system

---

### 7. `src/styles/design-system.css`

Arquivo completo com todos os tokens CSS do Prospector para light e dark mode:

```css
/* Tokens light (padrão) */
:root, [data-theme="light"] {
  --font-sans: 'DM Sans', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Backgrounds */
  --bg-page:      #F5F4F0;
  --bg-surface:   #FFFFFF;
  --bg-overlay:   #F1F0EC;
  --bg-sunken:    #ECEAE4;

  /* Texto */
  --text-primary:   #1A1A18;
  --text-secondary: #5C5B56;
  --text-tertiary:  #9B9A94;
  --text-disabled:  #C4C2BB;
  --text-invert:    #FFFFFF;

  /* Bordas */
  --border-default: rgba(26,26,24,0.10);
  --border-subtle:  rgba(26,26,24,0.06);
  --border-strong:  rgba(26,26,24,0.20);

  /* Acento */
  --accent:           #0F5C8A;
  --accent-hover:     #0A4A70;
  --accent-subtle:    #E8F3FA;
  --accent-subtle-fg: #0C4E76;
  --accent-border:    #A8CFEA;

  /* Semânticos */
  --success:           #1A8C5C;
  --success-subtle:    #E6F5EE;
  --success-subtle-fg: #165E3E;
  --warning:           #946600;
  --warning-subtle:    #FDF3DC;
  --warning-subtle-fg: #7A5500;
  --danger:            #C13535;
  --danger-subtle:     #FDEAEA;
  --danger-subtle-fg:  #9E2B2B;
  --info:              #2B68B0;
  --info-subtle:       #EBF2FB;
  --info-subtle-fg:    #215490;
  --neutral:           #5C5B56;
  --neutral-subtle:    #F1F0EC;
  --neutral-subtle-fg: #3E3D39;

  /* Sombras */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.04);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.09), 0 0 0 0.5px rgba(0,0,0,0.05);

  /* Layout */
  --radius-sm:   4px;
  --radius-md:   8px;
  --radius-lg:   10px;
  --radius-xl:   14px;
  --radius-full: 9999px;
}

/* Tokens dark */
[data-theme="dark"] {
  --bg-page:      #111110;
  --bg-surface:   #1C1C1A;
  --bg-overlay:   #242422;
  --bg-sunken:    #0D0D0C;
  --text-primary:   #EEEEE8;
  --text-secondary: #9B9A94;
  --text-tertiary:  #6B6A65;
  --text-disabled:  #3E3D39;
  --text-invert:    #111110;
  --border-default: rgba(255,255,255,0.08);
  --border-subtle:  rgba(255,255,255,0.04);
  --border-strong:  rgba(255,255,255,0.16);
  --accent:           #4BA3D4;
  --accent-hover:     #63B3E0;
  --accent-subtle:    #0F2C3D;
  --accent-subtle-fg: #7EC4E8;
  --accent-border:    #1E4D68;
  --success:           #3DBD80;
  --success-subtle:    #0D2A1C;
  --success-subtle-fg: #6DD4A3;
  --warning:           #F0B429;
  --warning-subtle:    #271D08;
  --warning-subtle-fg: #F5CA62;
  --danger:            #EF5050;
  --danger-subtle:     #2A0F0F;
  --danger-subtle-fg:  #F48080;
  --info:              #5B9DD4;
  --info-subtle:       #0D1F33;
  --info-subtle-fg:    #89BCE6;
  --neutral:           #9B9A94;
  --neutral-subtle:    #242422;
  --neutral-subtle-fg: #C4C2BB;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.5), 0 0 0 0.5px rgba(255,255,255,0.04);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.6), 0 0 0 0.5px rgba(255,255,255,0.05);
}
```

---

### 8. `src/styles/globals.css`

- `@import "./design-system.css"` como primeira linha
- Tailwind directives: `@tailwind base; @tailwind components; @tailwind utilities`
- `body`: `font-family: var(--font-sans)`, `background-color: var(--bg-page)`, `color: var(--text-primary)`
- `::selection`: background `var(--accent)`, color branco
- Scrollbar customizada: thin, track transparente, thumb `var(--border-strong)`
- Transição suave de tema: `transition: background-color 200ms, color 200ms` no body

---

### 9. `src/lib/utils.ts`

Implementar todas estas funções com types corretos:

```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// Merge de classes Tailwind
export function cn(...inputs: ClassValue[]): string

// Data relativa: "agora", "há 3 min", "há 2h", "há 3 dias", "12 jan"
export function formatRelativeTime(date: Date | string): string

// Score → classe CSS de cor semântica
export function scoreVariant(score: number): "success" | "warning" | "danger"
// 0-40 = danger, 41-70 = warning, 71-100 = success

// Truncar string
export function truncate(str: string, max: number): string

// Canal → label legível
export function channelLabel(channel: string): string
// "linkedin_dm" → "LinkedIn DM", "linkedin_connect" → "LinkedIn Connect"

// Intent → { label, variant }
export function intentConfig(intent: string): {
  label: string
  variant: "success" | "warning" | "danger" | "neutral" | "info"
}
// interest→success, objection→warning, not_interested→danger,
// neutral→neutral, out_of_office→info

// Slug para URL
export function slugify(str: string): string

// Formatar moeda BRL
export function formatBRL(value: number): string
```

---

### 10. `src/lib/auth/config.ts`

Implementar exatamente o NextAuth config descrito na seção
"Fluxo de autenticação" acima. Incluir também:

- Type augmentation do NextAuth para adicionar `tenant_id` e `accessToken`
  à interface `Session` e `JWT`:
  ```typescript
  declare module "next-auth" {
    interface Session {
      accessToken: string
      user: DefaultSession["user"] & { tenant_id: string }
    }
  }
  declare module "next-auth/jwt" {
    interface JWT {
      tenant_id: string
      access_token: string
      refresh_token: string
    }
  }
  ```

- Callback `jwt` que tenta refresh automático quando o access_token expirar:
  - Decodificar o JWT com `jwt-decode` para verificar `exp`
  - Se expirado, chamar `POST /auth/refresh` com o refresh_token
  - Atualizar o token com o novo access_token

---

### 11. `src/app/auth/callback/route.ts`

Implementar a rota de API Next.js que recebe o redirect do backend com
o token, conforme descrito na seção "Fluxo de autenticação".

Tratar casos de erro:
- `token` ausente → redirect `/login?error=no_token`
- signIn falhou → redirect `/login?error=auth_failed`
- Sucesso → redirect `/dashboard`

---

### 12. `src/env.ts`

Implementar a validação com `@t3-oss/env-nextjs` conforme spec do item 4.
O build deve falhar com mensagem clara se qualquer variável obrigatória
estiver faltando.

---

### 13. `src/lib/api/client.ts`

Client HTTP tipado. Deve:
- Importar tipos de `./schema` (gerado pelo openapi-typescript)
- Criar `api` com `openapi-fetch` para uso em Client Components e Server Actions
- O client injeta `Authorization: Bearer {accessToken}` automaticamente
  lendo a sessão do NextAuth
- Criar `serverApi` para uso em Server Components (lê token do servidor)
- Tratar 401: limpar sessão e redirecionar para `/login`
- Exportar: `export { api, serverApi }`

---

### 14. `src/lib/api/hooks/use-llm-models.ts`

TanStack Query hooks para a camada LLM:

```typescript
// Lista modelos disponíveis — staleTime 1h (igual ao cache Redis)
export function useLLMModels(): {
  models: ModelInfo[]
  providers: string[]
  byProvider: Record<string, ModelInfo[]>
  isLoading: boolean
}

// Providers configurados no backend
export function useLLMProviders(): { providers: string[]; isLoading: boolean }

// Mutation para testar um modelo
export function useTestModel(): {
  mutate: (params: TestModelParams) => void
  result: TestModelResult | null
  isPending: boolean
}
```

Stale time de `60 * 60 * 1000` (1h) para evitar chamadas repetidas.

---

### 15. `src/store/ui-store.ts`

Zustand store:
```typescript
interface UIStore {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (v: boolean) => void

  activeFilters: {
    status: string[]
    intent: string[]
    channel: string[]
    segment: string | null
  }
  setFilter: <K extends keyof ActiveFilters>(key: K, value: ActiveFilters[K]) => void
  clearFilters: () => void

  selectedLeadId: string | null
  setSelectedLead: (id: string | null) => void
}
```

Persistir `sidebarCollapsed` no localStorage com `zustand/middleware/persist`.

---

### 16. `src/store/notifications-store.ts`

Zustand store para notificações WebSocket:
```typescript
interface Notification {
  id: string
  type: "interest" | "objection" | "neutral" | "connection_accepted" | "step_sent"
  leadName: string
  leadId: string
  company: string | null
  message: string
  timestamp: Date
  read: boolean
}

interface NotificationsStore {
  notifications: Notification[]
  unreadCount: number
  push: (n: Omit<Notification, "id" | "read">) => void
  markRead: (id: string) => void
  markAllRead: () => void
  dismiss: (id: string) => void
  clear: () => void
}
```

Limitar a 50 notificações (descartar as mais antigas).

---

### 17. `src/lib/ws/use-events.ts`

Hook WebSocket para eventos em tempo real:

- Conectar em `env.NEXT_PUBLIC_WS_URL` enviando o token JWT no primeiro
  frame após conectar: `ws.send(JSON.stringify({ type: "auth", token }))`
- Reconectar com backoff exponencial: 1s → 2s → 4s → 8s → 30s (máximo)
- Eventos tipados:
  ```typescript
  type WSEvent =
    | { type: "lead.replied"; lead_id: string; lead_name: string; company: string; intent: string }
    | { type: "step.sent"; step_id: string; lead_id: string; channel: string }
    | { type: "deal.created"; deal_id: number; lead_id: string }
    | { type: "invitation.accepted"; lead_id: string; lead_name: string }
    | { type: "ping" }
  ```
- Ao receber `lead.replied`: chamar `notificationsStore.push()` +
  invalidar query `["leads", lead_id]`
- Ao receber `invitation.accepted`: invalidar query `["leads", lead_id]`
- Exportar: `export function useEvents(): { connected: boolean; lastEvent: WSEvent | null }`

---

### 18. `src/app/layout.tsx`

Root layout:
- Importar fonte `DM Sans` do `next/font/google` (pesos 400 e 500)
- Aplicar variável CSS da fonte no `<html>`
- `suppressHydrationWarning` no `<html>` (next-themes precisa)
- Providers na ordem: `SessionProvider` → `ThemeProvider` → `QueryClientProvider`
- `ThemeProvider`: `attribute="data-theme"`, `defaultTheme="system"`, `enableSystem`
- Metadata: `title: "Prospector"`, `description: "Prospecção B2B automatizada"`
- Importar `globals.css`

---

### 19. `src/app/(auth)/login/page.tsx`

Página de login pública. Deve:
- Verificar se já há sessão → redirecionar para `/dashboard`
- Layout centralizado com card no meio, fundo `var(--bg-page)`
- Logo "Prospector" (dot azul + nome) no topo do card
- Subtítulo: "Prospecção B2B automatizada"
- `<GoogleSignInButton />` centralizado
- Mensagem de erro se `searchParams.error` estiver presente:
  - `no_token` → "Erro ao autenticar. Tente novamente."
  - `auth_failed` → "Falha na autenticação. Verifique sua conta."
- Link de privacidade no rodapé do card

---

### 20. `src/components/auth/google-sign-in-button.tsx`

Botão de login com Google. Deve:
- Ser `"use client"`
- Ao clicar: `window.location.href = \`${env.NEXT_PUBLIC_API_URL}/auth/google/login\``
- Estado de loading enquanto redireciona (evitar double-click)
- SVG do ícone do Google embutido (não usar imagem externa)
- Estilo: botão branco, borda `var(--border-default)`, sombra `var(--shadow-sm)`
- Hover: `var(--bg-overlay)`
- Texto: "Entrar com Google"
- Largura total (`w-full`)

---

## Regras de geração de código

1. TypeScript strict — sem `any`, sem `as unknown as`, sem `!`
2. Props tipadas com interface nomeada acima do componente
3. `@/` para todos os imports — nunca caminhos relativos com `../`
4. Server Components por padrão — `"use client"` só quando necessário
5. shadcn/ui para todos primitivos (Button, Input, Select, Badge, Card...)
6. Cores via tokens CSS (`var(--accent)`) — nunca `text-blue-500`
7. `cn()` para classes condicionais — nunca template literals com classes
8. Acessibilidade: `aria-label` em botões icon-only, `role` quando necessário
9. Sem comentários óbvios — comentar só o não-óbvio

---

## Como trabalharemos

Implemente **um arquivo por vez** na ordem acima.
Após cada arquivo:
- Mostre o código completo
- Liste pacotes extras se necessário
- Diga o nome do próximo arquivo

Comece pelo `package.json`.
