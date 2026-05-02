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

- Banco reconciliado ate `alembic_version = 098`.
- Auditoria de RLS criada para falhar em CI se novas tabelas multi-tenant ficarem sem policy.
- Confirmacao operacional atual: `TENANT_TABLES = 49`, `MISSING_RLS = 0`.

### Logs e Dados Sensiveis

- Redaction global de tokens, segredos, cookies e query params sensiveis.
- Sanitizacao de filenames em rotas publicas e respostas de arquivo.

### Uploads e Arquivos

- Politica de magic bytes e normalizacao aplicada para audio, TTS e uploads do Content Hub, incluindo posts, imagens standalone, articles, newsletters, landing pages, carousel e lead magnets PDF.
- Objetos privados relevantes servidos por presigned URL com TTL controlado.
- CORS restrito no backend e CSP aplicada no frontend.

## Controles Que Ainda Faltam

- Trilho de auditoria leve mais abrangente para eventos sensiveis e administrativos.
- Revisao continua de queries com filtro explicito por `tenant_id`.
- Workflows de CI com lint, typecheck, testes, auditoria RLS, dependency audit e secret scanning.
- Revisao final de exposicao operacional de Flower, Redis e Postgres.

## Regras Operacionais

- Nunca registrar segredos, tokens ou credenciais em documentos versionados.
- Nunca confiar apenas em `content_type` informado pelo cliente para uploads.
- Nunca depender apenas de RLS implícita quando um filtro explicito por tenant for viavel.
- Nunca abrir acesso publico para buckets/prefixos privados.

## Validacoes Recomendadas

- Testar replay e expiracao de grants e tickets.
- Rodar auditoria RLS e testes cross-tenant em CI.
- Executar build/test do frontend e da extensao em toda alteracao relevante.
- Rodar `pip-audit`, `npm audit` e secret scanning em pipeline dedicado.