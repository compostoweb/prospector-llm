# Security Baseline

Ultima atualizacao: 2026-05-01

## Objetivos

- Reduzir risco de vazamento de dados, abuso de sessao e uploads mascarados.
- Garantir isolamento por tenant e rastreabilidade suficiente para investigacao.
- Elevar protecoes de borda sem quebrar a operacao atual.

## Controles Ja Implementados

### Autenticacao e Sessao

- Rate limiting Redis em `/auth/token`, Google OAuth e fluxos principais da extensao.
- Login web com `grant_code` single-use em vez de JWT longo na URL.
- WebSocket com ticket curto single-use.
- Extensao com validacao runtime dos contratos criticos, allowlist de API base URL e validacao explicita do callback OAuth esperado.

### Tenant Isolation

- Banco reconciliado ate `alembic_version = 099`.
- Auditoria de RLS criada para falhar em CI se novas tabelas multi-tenant ficarem sem policy.
- Confirmacao operacional atual: `TENANT_TABLES = 49`, `MISSING_RLS = 0`.
- Revisao de queries sensiveis reforcada em services de cadence, warmup, sandbox, batch Anthropic e voyager sync com filtro explicito por tenant.

### Auditoria e CI

- Trilha leve de auditoria ativa para eventos de auth, acoes administrativas e upload/delete de media do Content Hub.
- Workflows de CI, auditoria RLS, dependency audit e secret scanning versionados no repositório.

### Logs e Dados Sensiveis

- Redaction global de tokens, segredos, cookies e query params sensiveis.
- Sanitizacao de filenames em rotas publicas e respostas de arquivo.

### Uploads e Arquivos

- Politica de magic bytes e normalizacao aplicada para audio, TTS e uploads do Content Hub, incluindo posts, imagens standalone, articles, newsletters, landing pages, carousel e lead magnets PDF.
- Objetos privados relevantes servidos por presigned URL com TTL controlado.
- CORS restrito no backend e CSP aplicada no frontend.

## Controles Que Ainda Faltam

- Revisao continua de novas queries com filtro explicito por `tenant_id`.
- Acoplar os scripts de restore verification e object storage verification ao runner operacional diario.
- Revisao final de exposicao operacional de Flower, Redis e Postgres.

## Regras Operacionais

- Nunca registrar segredos, tokens ou credenciais em documentos versionados.
- Nunca confiar apenas em `content_type` informado pelo cliente para uploads.
- Nunca depender apenas de RLS implícita quando um filtro explicito por tenant for viavel.
- Nunca abrir acesso publico para buckets/prefixos privados.

## Validacoes Recomendadas

- Testar replay e expiracao de grants e tickets.
- Rodar auditoria RLS e testes cross-tenant em CI.
- Executar `backend/scripts/verify_restore_target.py` e `backend/scripts/verify_object_storage_restore.py` em drills de DR.
- Executar build/test do frontend e da extensao em toda alteracao relevante.
- Rodar `pip-audit`, `npm audit` e secret scanning em pipeline dedicado.