# Feature: LinkedIn Engagement Scanner
## Escopo para GitHub Copilot — Content Hub / Prospector

---

## OBJETIVO DA FEATURE

Antes de publicar um post próprio no LinkedIn, o usuário aciona o scanner dentro do Content Hub. O sistema busca posts relevantes do nicho e posts recentes de decisores do ICP, analisa cada um com LLM e gera sugestões de comentário calibradas com a voz do usuário.

O usuário comenta manualmente nos posts indicados, aquece o algoritmo do LinkedIn e aumenta o alcance orgânico do próprio post publicado em seguida.

**Regra absoluta:** nenhum comentário é postado automaticamente. Tudo passa pela revisão e ação manual do usuário.

---

## POSIÇÃO NO SISTEMA

- Módulo: Content Hub (já implementado)
- Rota frontend: `/content/engagement`
- Acesso: sidebar do Content Hub, abaixo de "Calendário Editorial"
- Contexto: o usuário seleciona o post que vai publicar em seguida (opcional) antes de acionar o scanner

---

## BANCO DE DADOS

### 3 tabelas novas

```sql
-- Sessão de garimpagem (agrupa uma rodada completa)
CREATE TABLE content_engagement_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  linked_post_id UUID REFERENCES content_posts(id), -- post que será publicado em seguida (opcional)
  status VARCHAR(20) DEFAULT 'running'
    CHECK (status IN ('running', 'completed', 'partial', 'failed')),
  references_found INTEGER DEFAULT 0,   -- posts de alto engajamento encontrados
  icp_posts_found INTEGER DEFAULT 0,    -- posts de ICP encontrados
  comments_generated INTEGER DEFAULT 0,
  comments_posted INTEGER DEFAULT 0,
  scan_source VARCHAR(20) DEFAULT 'apify'
    CHECK (scan_source IN ('linkedin_api', 'apify', 'manual')),
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Posts garimpados (referências de alto engajamento + posts de ICP)
CREATE TABLE content_engagement_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  session_id UUID NOT NULL REFERENCES content_engagement_sessions(id),
  post_type VARCHAR(20) NOT NULL CHECK (post_type IN ('reference', 'icp')),
    -- reference: post de alto engajamento do nicho (para aprender e salvar)
    -- icp: post recente de decisor do ICP (para comentar)
  author_name VARCHAR(150),
  author_title VARCHAR(200),
  author_company VARCHAR(150),
  author_linkedin_urn VARCHAR(100),
  author_profile_url VARCHAR(500),
  post_url VARCHAR(500),
  post_text TEXT NOT NULL,
  post_published_at TIMESTAMPTZ,
  likes INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  engagement_score INTEGER,             -- fórmula: comentários*3 + likes + compartilhamentos*2
  -- Análise LLM (preenchida após scan)
  hook_type VARCHAR(30),                -- loop_open|contrarian|identification|shortcut|benefit|data
  pillar VARCHAR(20),                   -- authority|case|vision
  why_it_performed TEXT,                -- por que esse post gerou engajamento
  what_to_replicate TEXT,               -- o que replicar nos próprios posts
  -- Controle
  is_saved BOOLEAN DEFAULT FALSE,       -- salvo como referência permanente
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comentários sugeridos para posts de ICP
CREATE TABLE content_engagement_comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  engagement_post_id UUID NOT NULL REFERENCES content_engagement_posts(id),
  session_id UUID NOT NULL REFERENCES content_engagement_sessions(id),
  comment_text TEXT NOT NULL,
  variation INTEGER NOT NULL DEFAULT 1,  -- 1 ou 2 (duas opções por post)
  status VARCHAR(20) DEFAULT 'pending'
    CHECK (status IN ('pending', 'selected', 'posted', 'discarded')),
  posted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## ESTRUTURA DE ARQUIVOS

```
api/routes/content/
└── engagement.py              # Todos os endpoints do scanner

workers/content/
├── engagement_scan.py         # Task Celery principal (orquestra o scan completo)
├── apify_linkedin_scanner.py  # Garimpagem via Apify (fonte primária)
└── linkedin_api_scanner.py    # Garimpagem via LinkedIn API (fonte secundária)

services/content/
├── engagement_analyzer.py     # Análise LLM de posts (hook, pilar, por que performou)
└── comment_generator.py       # Geração LLM de comentários calibrados
```

---

## ENDPOINTS DA API

```
# Sessões
POST   /api/content/engagement/run
  Body: {
    linked_post_id?: string,       # post que será publicado depois (opcional)
    keywords?: string[],           # keywords customizadas (usa padrão se omitido)
    icp_filters?: {
      titles?: string[],           # filtros de cargo (usa padrão se omitido)
      sectors?: string[]           # filtros de setor (usa padrão se omitido)
    }
  }
  Response: { session_id: string, status: "running" }

GET    /api/content/engagement/sessions
  Query: ?page=1&limit=10
  Response: lista de sessões com totais

GET    /api/content/engagement/sessions/{id}
  Response: sessão com posts e comentários incluídos

# Posts garimpados
GET    /api/content/engagement/posts
  Query: ?session_id=&post_type=reference|icp&is_saved=true
  Response: lista de posts com análise LLM

POST   /api/content/engagement/posts
  Body: { post_url, post_text, author_name, author_title, post_type }
  # Adição manual de post pelo usuário

PATCH  /api/content/engagement/posts/{id}/save
  # Salvar post como referência permanente (is_saved = true)

DELETE /api/content/engagement/posts/{id}
  # Remover post da sessão

# Comentários
GET    /api/content/engagement/comments
  Query: ?session_id=&status=pending|selected|posted

PATCH  /api/content/engagement/comments/{id}/select
  # Marcar comentário como selecionado para usar

PATCH  /api/content/engagement/comments/{id}/posted
  # Confirmar que o comentário foi postado manualmente

PATCH  /api/content/engagement/comments/{id}/discard
  # Descartar sugestão

POST   /api/content/engagement/comments/{id}/regenerate
  # Regenerar comentário com nova sugestão LLM
```

---

## TASK CELERY — ORQUESTRAÇÃO DO SCAN

```python
# workers/content/engagement_scan.py

# ─── KEYWORDS POR VERTICAL ────────────────────────────────────────────────────
# Cobertura das 6 verticais da Composto Web:
# Automação · Integração · IA · Cloud/DevOps · Telefonia · Software sob Medida
# + CRM/Growth e Gestão Operacional geral

ENGAGEMENT_KEYWORDS = [

    # AUTOMAÇÃO DE PROCESSOS
    "automação de processos empresa",
    "processo manual retrabalho",
    "gargalo operacional crescimento",
    "RPA robô processo",
    "eliminar tarefa manual equipe",
    "operação que não escala",

    # INTEGRAÇÃO DE SISTEMAS
    "integração de sistemas ERP",
    "sistemas desconectados operação",
    "dado defasado decisão",
    "ERP CRM não integrado",
    "fechamento mensal manual planilha",
    "redigitação dado entre sistemas",

    # IA APLICADA AO NEGÓCIO
    "IA empresas resultado prático",
    "inteligência artificial operação",
    "agente IA atendimento empresa",
    "ChatGPT empresa dado seguro",
    "modelo IA negócio aplicado",
    "IA privada dado confidencial",

    # CLOUD E INFRAESTRUTURA
    "cloud migração empresa",
    "infraestrutura TI custo",
    "modernização tecnológica empresa",
    "LGPD conformidade sistema",
    "segurança dados empresa",
    "DevOps entrega contínua",

    # TELEFONIA E COMUNICAÇÃO
    "PABX IP nuvem empresa",
    "telefonia integrada CRM",
    "custo telefonia empresa redução",
    "atendimento telefônico rastreável",

    # SOFTWARE SOB MEDIDA
    "software personalizado empresa",
    "sistema próprio versus SaaS",
    "propriedade intelectual software",
    "lock-in fornecedor tecnologia",
    "SaaS custo escala empresa",
    "ativo digital empresa",

    # CRM E CRESCIMENTO COMERCIAL
    "CRM implementação resultado",
    "Pipedrive vendas processo",
    "pipeline comercial estruturado",
    "funil vendas dados",
    "aquisição clientes rastreável",
    "tracking marketing vendas",

    # GESTÃO E OPERAÇÃO GERAL
    "escalar empresa sem contratar",
    "crescimento operacional tecnologia",
    "dado tempo real decisão gestão",
    "tecnologia parceiro estratégico",
    "operação cresceu processo não acompanhou",
    "tecnologia resolve problema negócio",
]

# ─── CARGOS ICP ───────────────────────────────────────────────────────────────
# Decisores com autonomia de R$20k+ e dor operacional real
# Cobre todas as verticais e setores atendidos pela Composto Web

ICP_TITLES = [

    # C-LEVEL GERAL
    "CEO",
    "CFO",
    "COO",
    "CTO",
    "Diretor Executivo",
    "Sócio Diretor",
    "Fundador",
    "Co-fundador",

    # OPERAÇÕES E TI
    "Diretor de Operações",
    "Gerente de Operações",
    "Diretor de TI",
    "Gerente de TI",
    "Head de TI",
    "Gerente de Infraestrutura",
    "Diretor de Tecnologia",
    "VP de Tecnologia",
    "VP de Operações",

    # FINANCEIRO E CONTÁBIL
    "Diretor Financeiro",
    "Gerente Financeiro",
    "Controller",
    "CFO",
    "Sócio Contador",
    "Diretor de Controladoria",

    # COMERCIAL E MARKETING
    "Diretor Comercial",
    "Gerente Comercial",
    "Diretor de Vendas",
    "Head de Vendas",
    "CMO",
    "Diretor de Marketing",
    "Head de Growth",

    # INDUSTRIAL E LOGÍSTICA
    "Diretor Industrial",
    "Gerente Industrial",
    "Diretor de Logística",
    "Gerente de Supply Chain",
    "Gerente de Planejamento",
    "Gerente de PCP",

    # JURÍDICO
    "Sócio Advogado",
    "Diretor Jurídico",
    "General Counsel",
    "Sócio de Escritório",

    # SAÚDE
    "Diretor de Clínica",
    "Administrador Hospitalar",
    "Gerente Administrativo",
    "Sócio Clínica",
]

# ─── SETORES ICP ──────────────────────────────────────────────────────────────
# 13 setores cobertos no playbook da Composto Web

ICP_SECTORS = [
    # Prioritários
    "Financeiro",
    "Contabilidade",
    "Jurídico",
    "Advocacia",
    "Saúde",
    "Clínica",
    # Secundários
    "Indústria",
    "Logística",
    "Varejo",
    "E-commerce",
    "Tecnologia",
    "Software",
    "Imobiliário",
    "Construtora",
    "Agência",
    "RH",
    "Agroindustrial",
]

@celery_app.task(name="content.run_engagement_scan", bind=True, max_retries=2)
async def run_engagement_scan(self, session_id: str, tenant_id: str):
    """
    Orquestra o scan completo em 4 etapas:

    ETAPA 1 — Garimpagem de posts de referência (alto engajamento):
      - Busca posts via Apify LinkedIn Search por ENGAGEMENT_KEYWORDS
      - Filtra posts com engagement_score > 50 (comentários*3 + likes + shares*2)
      - Coleta até 15 posts de referência por sessão

    ETAPA 2 — Garimpagem de posts de ICP:
      - Busca perfis do LinkedIn por ICP_TITLES + ICP_SECTORS via Apify
      - Coleta posts publicados nas últimas 48-72 horas desses perfis
      - Filtra por relevância: posts que mencionam gestão, operação, tecnologia, processo
      - Coleta até 10 posts de ICP por sessão

    ETAPA 3 — Análise LLM:
      - Para cada post de referência: analisa hook_type, pillar, why_it_performed, what_to_replicate
      - Para cada post de ICP: analisa relevância e prepara contexto para geração de comentário

    ETAPA 4 — Geração de comentários:
      - Para cada post de ICP (máx 10): gera 2 opções de comentário
      - Salva em content_engagement_comments com status 'pending'

    Ao final: atualiza session com totais e status 'completed'
    Em caso de falha parcial: status 'partial' com erro registrado
    """
```

---

## SERVICE — APIFY LINKEDIN SCANNER

```python
# workers/content/apify_linkedin_scanner.py

class ApifyLinkedInScanner:
    """
    Usa o Apify LinkedIn Scraper já configurado no Prospector.
    Actor: apify/linkedin-scraper (já em uso no módulo de prospecção)

    Dois tipos de busca:
    1. search_posts_by_keywords: busca posts por palavras-chave
    2. get_profile_recent_posts: pega posts recentes de perfis específicos
    """

    APIFY_ACTOR_SEARCH = "apify/linkedin-scraper"

    async def search_posts_by_keywords(
        self,
        keywords: list[str],
        max_results: int = 20,
        min_engagement_score: int = 30,
    ) -> list[dict]:
        """
        Dispara actor Apify para buscar posts por keyword.
        Retorna lista de posts com: text, author, likes, comments, shares, url, published_at
        Filtra por engagement_score >= min_engagement_score
        """

    async def get_icp_recent_posts(
        self,
        icp_titles: list[str],
        icp_sectors: list[str],
        days_back: int = 3,
        max_results: int = 15,
    ) -> list[dict]:
        """
        Busca perfis do ICP e coleta posts recentes.
        1. Busca perfis com título em icp_titles e setor em icp_sectors
        2. Para cada perfil encontrado, coleta posts dos últimos days_back dias
        3. Retorna posts com contexto do autor (nome, cargo, empresa)
        """

    @staticmethod
    def calculate_engagement_score(likes: int, comments: int, shares: int) -> int:
        return (comments * 3) + likes + (shares * 2)
```

---

## SERVICE — ANÁLISE LLM DE POSTS

```python
# services/content/engagement_analyzer.py

ANALYZE_POST_PROMPT = """
Analise este post do LinkedIn e retorne um JSON com:
{
  "hook_type": "loop_open|contrarian|identification|shortcut|benefit|data",
  "pillar": "authority|case|vision",
  "why_it_performed": "por que esse post gerou alto engajamento (1-2 frases diretas)",
  "what_to_replicate": "o que pode ser replicado em outros posts (1-2 frases diretas)"
}

Definições dos tipos de hook:
- loop_open: abre enigma que só fecha no post
- contrarian: desafia o senso comum
- identification: descreve a dor com precisão — leitor pensa "é isso!"
- shortcut: promessa de rota mais curta para algo
- benefit: entrega o valor logo de cara
- data: ancora o post em dado concreto ou número

POST:
{post_text}

Retorne APENAS o JSON válido, sem texto adicional.
"""

ICP_POST_RELEVANCE_PROMPT = """
Este post foi publicado por {author_name} ({author_title} em {author_company}).
Avalie se o post é relevante para que um especialista em engenharia de soluções e automação
faça um comentário técnico que agregue valor à discussão.

POST:
{post_text}

Retorne JSON:
{
  "is_relevant": true|false,
  "relevance_reason": "por que é ou não relevante para comentar (1 frase)",
  "comment_angle": "ângulo sugerido para o comentário (1 frase) — apenas se is_relevant = true"
}

Retorne APENAS o JSON válido.
"""
```

---

## SERVICE — GERAÇÃO DE COMENTÁRIOS

```python
# services/content/comment_generator.py

COMMENT_GENERATION_PROMPT = """
Você é um assistente de conteúdo para {author_name}, fundador da Composto Web,
especialista em engenharia de soluções com 22 anos de TI.

Gere 2 opções de comentário para o post abaixo.

REGRAS INVIOLÁVEIS:
- Máximo 4 linhas por comentário
- Nunca mencionar a Composto Web nem fazer pitch
- Tom: técnico mas acessível, perspectiva de quem já viu esse problema na prática
- Nunca começar com "Ótimo post!", "Excelente!", "Que conteúdo!" ou equivalente
- Terminar com pergunta ou provocação que convide resposta
- Sem travessão — usar vírgula ou dois pontos
- Palavras proibidas: inovação, otimização, gestão inteligente, faz sentido?

CONTEXTO DO AUTOR:
{author_voice}

ÂNGULO SUGERIDO PARA O COMENTÁRIO:
{comment_angle}

POST:
Autor: {icp_author_name} — {icp_author_title} ({icp_author_company})
Texto: {post_text}

Retorne JSON:
{
  "comment_1": "texto completo do primeiro comentário",
  "comment_2": "texto completo do segundo comentário"
}

Retorne APENAS o JSON válido.
"""

async def generate_comments_for_post(
    post: dict,
    author_name: str,
    author_voice: str,
    comment_angle: str,
    model: str = "gpt-4o",
) -> tuple[str, str]:
    """
    Gera 2 opções de comentário para um post de ICP.
    Retorna (comment_1, comment_2).
    Em caso de falha no parse do JSON, tenta novamente (max 2 tentativas).
    """
```

---

## FRONTEND — PÁGINA DE ENGAJAMENTO

### Rota: `/content/engagement`

### Layout da página

```
EngagementPage
├── PageHeader
│   ├── Título: "Engajamento Estratégico"
│   ├── Subtítulo: "Comente antes de publicar para aumentar o alcance"
│   └── RunScanButton
│       ├── Se sem sessão ativa: botão "Garimpar agora"
│       └── Se sessão ativa: spinner + "Buscando posts... (etapa X/4)"
│
├── LinkedPostSelector (opcional)
│   ├── Select: "Qual post você vai publicar depois?"
│   └── Lista posts com status 'approved' do calendário editorial
│
├── SessionSummaryBar (exibido após scan concluído)
│   ├── Badge: "X posts de referência encontrados"
│   ├── Badge: "X posts de ICP para comentar"
│   └── Badge: "X comentários sugeridos"
│
├── ReferencePostsSection
│   ├── Título: "Posts de Referência — aprenda com o que está funcionando"
│   └── Lista de PostReferenceCard
│       ├── Avatar + Nome + Cargo
│       ├── Texto resumido (primeiras 3 linhas + "ver mais")
│       ├── Métricas: 👍 X  💬 X  🔁 X  | Score: X
│       ├── HookBadge (tipo de gancho identificado)
│       ├── PillarBadge (pilar identificado)
│       ├── Accordion "Por que performou" (análise LLM)
│       ├── Accordion "O que replicar" (sugestão LLM)
│       ├── Botão "Salvar como referência" (is_saved = true)
│       └── Link "Ver no LinkedIn" (abre em nova aba)
│
└── ICPPostsSection
    ├── Título: "Posts de Decisores — comente nesses antes de publicar"
    └── Lista de ICPPostCard
        ├── Avatar + Nome + Cargo + Empresa
        ├── Texto resumido (primeiras 3 linhas + "ver mais")
        ├── Métricas: 👍 X  💬 X  🔁 X
        ├── CommentOptions
        │   ├── CommentCard (opção 1)
        │   │   ├── Texto completo do comentário
        │   │   ├── Botão "Copiar" (copia para clipboard)
        │   │   └── Botão "Regenerar" (nova sugestão LLM)
        │   └── CommentCard (opção 2)
        │       ├── Texto completo do comentário
        │       ├── Botão "Copiar" (copia para clipboard)
        │       └── Botão "Regenerar" (nova sugestão LLM)
        ├── Checkbox "Já comentei neste post" → PATCH /posted
        └── Link "Ver no LinkedIn" (abre em nova aba)
```

### Estados da página

```
Estado 1 — Sem sessão anterior:
  Empty state com ilustração e botão "Garimpar agora"
  Texto: "Comentar em posts relevantes 30 min antes de publicar aumenta o alcance orgânico."

Estado 2 — Scan em progresso:
  Skeleton loading + progress indicator com etapa atual
  "Buscando posts de referência... (1/4)"
  Polling via React Query a cada 3 segundos em GET /sessions/{id}

Estado 3 — Scan concluído:
  Exibe as duas seções (referências + ICP)
  SessionSummaryBar com totais

Estado 4 — Erro no scan:
  Toast de erro + botão "Tentar novamente"
  Log de erro visível para debug
```

---

## TYPES TYPESCRIPT

```typescript
// packages/shared/types/engagement.ts

export type EngagementPostType = 'reference' | 'icp'
export type CommentStatus = 'pending' | 'selected' | 'posted' | 'discarded'
export type SessionStatus = 'running' | 'completed' | 'partial' | 'failed'
export type HookType = 'loop_open' | 'contrarian' | 'identification' | 'shortcut' | 'benefit' | 'data'
export type PostPillar = 'authority' | 'case' | 'vision'

export interface EngagementSession {
  id: string
  tenantId: string
  linkedPostId?: string
  linkedPost?: { title: string; publishDate: string }
  status: SessionStatus
  referencesFound: number
  icpPostsFound: number
  commentsGenerated: number
  commentsPosted: number
  scanSource: 'linkedin_api' | 'apify' | 'manual'
  errorMessage?: string
  createdAt: string
  completedAt?: string
}

export interface EngagementPost {
  id: string
  tenantId: string
  sessionId: string
  postType: EngagementPostType
  authorName?: string
  authorTitle?: string
  authorCompany?: string
  authorLinkedinUrn?: string
  authorProfileUrl?: string
  postUrl?: string
  postText: string
  postPublishedAt?: string
  likes: number
  comments: number
  shares: number
  engagementScore?: number
  hookType?: HookType
  pillar?: PostPillar
  whyItPerformed?: string
  whatToReplicate?: string
  isSaved: boolean
  suggestedComments?: EngagementComment[]
  createdAt: string
}

export interface EngagementComment {
  id: string
  engagementPostId: string
  sessionId: string
  commentText: string
  variation: 1 | 2
  status: CommentStatus
  postedAt?: string
  createdAt: string
}

export interface RunScanRequest {
  linkedPostId?: string
  keywords?: string[]
  icpFilters?: {
    titles?: string[]
    sectors?: string[]
  }
}
```

---

## INTEGRAÇÃO COM MÓDULO DE LEADS

Quando o usuário marcar um comentário como "Postado":

```python
# api/routes/content/engagement.py

async def on_comment_marked_posted(
    comment_id: str,
    tenant_id: str,
    db: AsyncSession
):
    """
    Após marcar comentário como postado:
    1. Busca o post de ICP correspondente
    2. Verifica se o autor do post já existe na base de leads (por linkedin_urn)
    3. Se existe: registra atividade na timeline do lead
    4. Se não existe: cria sugestão de novo lead com origem 'engagement_comment'
    """
    comment = await get_comment(comment_id, db)
    post = await get_engagement_post(comment.engagement_post_id, db)

    if not post.author_linkedin_urn:
        return

    existing_lead = await find_lead_by_linkedin_urn(
        post.author_linkedin_urn, tenant_id, db
    )

    if existing_lead:
        await create_lead_activity(
            lead_id=existing_lead.id,
            type="engagement_comment",
            description=f"Comentou no post de {post.author_name}",
            metadata={
                "post_url": post.post_url,
                "comment_text": comment.comment_text[:200],
            }
        )
    else:
        await create_lead_suggestion(
            linkedin_urn=post.author_linkedin_urn,
            name=post.author_name,
            title=post.author_title,
            company=post.author_company,
            origin="engagement_comment",
            tenant_id=tenant_id,
        )
```

---

## ORDEM DE IMPLEMENTAÇÃO

### Sprint 1 — Backend base (2-3 dias)
1. Migrations Alembic: 3 tabelas novas
2. Models SQLAlchemy com relacionamentos
3. Schemas Pydantic (request/response)
4. Endpoints CRUD básicos (sessions, posts, comments)

### Sprint 2 — Garimpagem via Apify (2-3 dias)
1. `ApifyLinkedInScanner` com `search_posts_by_keywords`
2. `ApifyLinkedInScanner` com `get_icp_recent_posts`
3. Task Celery `run_engagement_scan` (etapas 1 e 2)
4. Endpoint `POST /engagement/run` disparando a task

### Sprint 3 — Análise e geração LLM (2 dias)
1. `engagement_analyzer.py` com prompts de análise de post e relevância
2. `comment_generator.py` com prompt de geração de comentário
3. Task Celery (etapas 3 e 4) com análise + geração
4. Endpoint `POST /comments/{id}/regenerate`

### Sprint 4 — Frontend (3-4 dias)
1. Types TypeScript + React Query hooks
2. Componentes base: PostReferenceCard, ICPPostCard, CommentCard, SessionSummaryBar
3. Página `/content/engagement` com os 4 estados
4. Polling em tempo real durante o scan (React Query a cada 3s)
5. Integração com módulo de leads (on_comment_marked_posted)

---

## PROMPT COPILOT PARA INICIAR

```
Vou implementar a feature "LinkedIn Engagement Scanner" dentro do módulo Content Hub
do sistema Prospector.

Objetivo: buscar posts relevantes do nicho e de ICPs no LinkedIn, analisar com LLM
e gerar sugestões de comentário calibradas com a voz do usuário — para o usuário
comentar manualmente antes de publicar o próprio post e aumentar o alcance orgânico.

Stack: FastAPI + Celery + PostgreSQL + SQLAlchemy async + Alembic (backend)
Next.js 15 + TypeScript + Tailwind + shadcn/ui (frontend)
Apify (garimpagem LinkedIn) + OpenAI GPT-4o (análise e geração de comentários)
Multi-tenant obrigatório. Turborepo monorepo.

Regra absoluta: nenhum comentário é postado automaticamente.
Tudo passa pela revisão e ação manual do usuário.

Começando pelo Sprint 1: migrations Alembic e models SQLAlchemy para:
- content_engagement_sessions
- content_engagement_posts
- content_engagement_comments

Schema SQL de referência: [cole o bloco SQL deste documento]

Padrão do projeto: async SQLAlchemy, UUIDs como PKs, timestamps automáticos,
todas as queries filtradas por tenant_id.
```

---

*Composto Web | Prospector — Content Hub: LinkedIn Engagement Scanner*
*Feature incremental sobre o módulo Content Hub v2*
