# Backup, Disaster Recovery e Seguranca

Data de consolidacao: 2026-05-01

## Estado Atual Consolidado

### Itens ja implementados em producao
- Postgres primary com pgBackRest persistido no servico.
- Backup full existente no repositorio pgBackRest: `20260501-220228F`.
- WAL archiving ativo e validado no primary.
- Replica refeita do zero e operando como standby real por streaming replication.
- Slot fisico `prospector_replica_slot` criado e ativo.
- Redis com AOF habilitado (`appendonly yes`, `appendfsync everysec`).
- Restore drill isolado executado com sucesso a partir do backup + WAL, sem tocar no primary.
- Monitor operacional criado no host para archiving, replicacao e Redis AOF, com execucao via cron a cada 5 minutos.

### Artefatos operacionais criados no host
- Restore drill:
  - `/root/prospector-restore-drill/data`
  - `/root/prospector-restore-drill/pgbackrest/pgbackrest.conf`
  - `/root/prospector-restore-drill/restore.log`
- Monitor de saude DR:
  - `/root/prospector-alerts/check_dr_health.py`
  - `/root/prospector-alerts/alert.env`
  - `/root/prospector-alerts/state.json`
  - `/var/log/prospector-dr-alert.log`
- Cron instalado:
  - `*/5 * * * * /root/prospector-alerts/check_dr_health.py >> /var/log/prospector-dr-alert.log 2>&1`

### Resultado do restore drill isolado
- Restore do backup base concluido com sucesso via pgBackRest.
- Startup do banco restaurado validado em container temporario e porta isolada.
- Recovery completou ate o ultimo WAL disponivel e promoveu para nova timeline.
- Validacoes observadas no drill:
  - banco `prospector`
  - PostgreSQL `17.9`
  - `pg_is_in_recovery() = false` ao final
  - `55` tabelas publicas encontradas
  - `alembic_version = 096` no momento do drill isolado

### Estado atual confirmado apos reconciliacao de seguranca
- Banco principal reconciliado ate `alembic_version = 099`.
- Auditoria direta confirmou `TENANT_TABLES = 49` e `MISSING_RLS = 0`.
- Auditoria automatica de RLS adicionada ao repositório para falhar em CI se surgir nova tabela multi-tenant sem policy.
- Hardening de autenticacao e sessao implementado no codigo:
  - rate limiting Redis em fluxos de auth/OAuth/extensao
  - `grant_code` curto no login web, sem JWT longo em query string
  - ticket curto single-use para WebSocket
  - extensao endurecida com allowlist da API, validacao de callback e validacao runtime de payloads criticos
- Hardening de borda publica implementado parcialmente no codigo:
  - CORS restrito no backend
  - CSP ativa no frontend
  - redaction global de tokens/secrets em logs
  - sanitizacao de filenames e presigned URLs para arquivos privados relevantes
  - validacao por magic bytes para audio, TTS e uploads restantes relevantes do Content Hub
- Trilha leve de auditoria implementada para auth, acoes administrativas e upload/delete de media do Content Hub.
- Workflows de CI e seguranca adicionados para backend, frontend, extensao, auditoria RLS, dependency audit e secret scanning.

## Status por Fase

### Phase 1 — Definicao de Arquitetura DR
Status: majoritariamente concluida.

Concluido:
- acesso operacional, topologia alvo e metas de RPO/RTO foram definidos e usados para a implantacao premium
- este documento consolidado registra a arquitetura, os artefatos operacionais e os runbooks essenciais ja exercitados

Concluido adicionalmente:
- documentacao operacional separada criada em `docs/BACKUP_DR.md`, `docs/SECURITY.md` e `docs/INCIDENT_RESPONSE.md`

### Phase 2 — PostgreSQL PITR e Standby
Status: majoritariamente concluida.

Concluido:
- pgBackRest implantado e persistido no servico
- WAL archiving continuo ativo
- standby real por streaming replication pronto para promocao manual
- slot fisico ativo
- restore drill isolado executado com sucesso
- monitor operacional para archiving, replicacao e Redis AOF ativo via cron

Pendente:
- automatizar verificacao diaria de restore em ambiente temporario/staging
- versionar runbooks operacionais detalhados fora deste consolidado

### Phase 3 — Redis, Celery e MinIO/S3
Status: parcial.

Concluido:
- Redis com AOF habilitado em producao
- uso de presigned URLs para objetos privados relevantes no backend

Pendente:
- runbook versionado de perda de Redis
- estrategia operacional de mirror/versionamento/backup de MinIO/S3
- restore validado de prefixos criticos do bucket

### Phase 4 — Hardening de Autenticacao e Sessoes
Status: majoritariamente concluida.

Concluido:
- rate limiting Redis em `/auth/token`, Google OAuth e fluxos principais da extensao
- troca de JWT web em URL por `grant_code` single-use
- troca de JWT longo em WebSocket por ticket curto single-use
 - extensao endurecida com allowlist de hosts da API em producao
 - validacao explicita de callback/origin esperado no fluxo OAuth da extensao
 - validacao runtime de schema antes de persistir/enviar payloads criticos da extensao
 - reducao de persistencia de sessao/token da extensao onde antes recaia em storage persistente

Pendente:
- revisar periodicamente a allowlist de extensao e os limites de rate limit conforme uso real

### Phase 5 — Tenant Isolation, Logs e Dados Sensiveis
Status: majoritariamente concluida.

Concluido:
- auditoria automatica de RLS criada
- migrations 097 e 098 reconciliaram cobertura de RLS/policies
- migration 099 reconciliada e aplicada no banco compartilhado para suportar a trilha `security_audit_logs`
- redaction global de secrets/tokens em logs implementada
 - trilha de auditoria leve implementada para eventos sensiveis e administrativos

Pendente:
- revisar queries criticas restantes para filtro explicito por `tenant_id`

### Phase 6 — Headers, CORS, Arquivos e Bordas Publicas
Status: parcial avancado.

Concluido:
- CORS restrito em producao
- CSP adicionada ao frontend
- sanitizacao de `Content-Disposition` e ajustes de cache em rotas publicas de arquivo
- validacao por magic bytes e normalizacao de nome/extensao para audio, TTS, posts, upload standalone de imagens, `articles`, `newsletters`, `landing_pages`, `carousel` e `lead_magnets`

Pendente:
- revisar superfícies publicas restantes de S3/MinIO e exposicao operacional de Flower/Redis/Postgres

### Phase 7 — Observabilidade, Alertas e CI
Status: parcial avancado.

Concluido:
- monitor operacional de DR ativo no host para archiving, replicacao e Redis AOF
 - workflows de CI para backend/frontend/extensao com job de integracao backend em Postgres e Redis
 - auditoria RLS, `pip-audit`, `npm audit` e secret scanning/Gitleaks em workflows dedicados

Pendente:
- dashboard operacional versionado
- cadencia operacional formal de drills mensais/trimestrais

### Observacoes importantes
- Nao registrar credenciais, tokens ou segredos neste documento.
- A role de replicacao existe e esta funcional, mas qualquer senha deve permanecer apenas no host/cofre.
- O monitor local suporta webhook opcional via `ALERT_WEBHOOK_URL` em `/root/prospector-alerts/alert.env`.

## Postgres DR Access Probe — 2026-05-01
- Conexao testada com sucesso no banco `prospector` em Postgres 17.9.
- Usuario conectado: `postgres`; possui `rolsuper=true`, `rolreplication=true`, `rolcreaterole=true`, `rolcreatedb=true`, `rolbypassrls=true`.
- Conexao atual esta sem SSL (`pg_stat_ssl.ssl=false`) porque a URL usa `sslmode=disable`; deve ser corrigido para producao se o endpoint suportar TLS.
- Config base verificada: `wal_level=replica`, `max_wal_senders=10`, `max_replication_slots=10`, `listen_addresses=*`, `hot_standby=on`.
- Antes da implantacao premium, faltavam `archive_mode`, `archive_command` e PITR real. Isso ja foi corrigido na producao auditada.
- `archive_mode` exige restart do Postgres; `archive_command`, `archive_timeout` e `wal_keep_size` sao recarregaveis.
- Funcoes permitidas ao usuario: `pg_reload_conf`, `pg_switch_wal`, `pg_create_physical_replication_slot`, `pg_drop_replication_slot`, `pg_create_restore_point`.
- Conclusao operacional: acesso SQL era suficiente para roles/slots/verificacao, mas a implantacao premium exigia acesso ao host/container/EasyPanel. Esse acesso foi usado para concluir a implantacao.

## Baseline Aprovado

Baseline definido pelo usuario: opcao robusta desde o inicio, com alvo de RPO de 5 a 15 minutos e RTO menor que 1 hora.

Para Postgres puro, isso exige:
- backups base regulares
- arquivamento continuo de WAL para storage externo
- PITR testado
- standby/replicacao pronta para promocao
- alertas rigorosos

Ferramenta principal recomendada: pgBackRest. Alternativa: WAL-G se o ambiente bloquear o pgBackRest.

## Plano Completo de Backup e Seguranca

### Phase 1 — Definicao de Arquitetura DR
1. Confirmar acesso operacional ao host do Postgres puro: shell/cron/systemd, permissoes para `archive_mode`, `archive_command`, replication slots/users, porta de replicacao e storage local. Esta confirmacao bloqueia a escolha final entre pgBackRest e WAL-G.
2. Definir topologia alvo: Postgres primary, Postgres standby streaming replication em outro host/volume, repositorio de backups/WAL em MinIO/S3 privado, e opcionalmente copia offsite em outro bucket/provedor.
3. Documentar metas: PostgreSQL RPO 5-15min, RTO <1h; MinIO/S3 RPO 1h-24h conforme prefixo; Redis RPO 5min; aplicacao RTO 15min; credenciais RTO 30min via cofre.
4. Criar `docs/BACKUP_DR.md` com matriz de criticidade, topologia, runbooks, cadencia de testes e criterios de sucesso.
5. Criar `docs/SECURITY.md` e `docs/INCIDENT_RESPONSE.md` para controles de protecao de dados, invasao, vazamento, rotacao de chaves e resposta a incidentes.

### Phase 2 — PostgreSQL PITR e Standby
6. Implantar pgBackRest preferencialmente: stanza do banco, repositorio S3/MinIO privado, backup full semanal, differential diario, incremental periodico, WAL archiving continuo e retencao que cubra pelo menos 7-14 dias de PITR.
7. Se pgBackRest nao for viavel, implantar WAL-G: base backups regulares, `archive_command` continuo, `restore_command` documentado e validacao de WAL no bucket.
8. Configurar streaming replication para standby: usuario de replicacao, `primary_conninfo`, replication slot quando adequado, hot standby e monitoramento de replication lag. O standby deve estar pronto para promocao manual em crise.
9. Criar runbook de failover: pausar `beat`, promover standby, trocar `DATABASE_URL`/DNS/host no EasyPanel, reiniciar API/workers, validar `/health`, rodar smoke tests, reativar `beat`.
10. Criar runbook de PITR: escolher timestamp alvo, restaurar backup base + WAL em host temporario, validar integridade, promover como primary se necessario, e so entao apontar aplicacao.
11. Implementar verificacao automatica diaria: restaurar backup em banco temporario/staging, rodar `alembic current`, `alembic upgrade head`, healthcheck da API e consultas amostrais multi-tenant.

### Phase 3 — Redis, Celery e MinIO/S3
12. Manter Redis com AOF, snapshot e backup offsite frequente do volume. Documentar que filas Celery sao recuperaveis parcialmente por idempotencia e estado persistido no banco.
13. Criar runbook de perda de Redis: pausar `beat`, subir Redis limpo/restaurado, iniciar workers, reativar `beat`, verificar cadencias/pollers e evitar duplicacoes de dispatch.
14. Implantar estrategia MinIO/S3: versionamento/lifecycle se disponivel, mirror frequente dos prefixos criticos (`audio/`, `lm-pdfs/`, `lm-images/`, `branding/`, `content/`) e backup de bucket/config/policies.
15. Para objetos sensiveis ou privados, manter bucket/prefixo sem public read e usar presigned URLs com TTL curto. Publico so para assets realmente publicos.

### Phase 4 — Hardening de Autenticacao e Sessoes
16. Implementar rate limiting Redis em `/auth/token`, Google OAuth e fluxos da extensao por IP, slug, `extension_id` e tentativa.
17. Trocar JWT em query string no login web por `grant_code` curto/single-use: backend redireciona com grant, frontend troca por sessao sem expor JWT longo em historico/logs.
18. Trocar WebSocket com JWT longo em query por ticket curto/single-use emitido via endpoint autenticado.
19. Endurecer extensao: validar callback origin, permitir API base URL apenas em hosts autorizados em producao, manter `EXTENSION_ALLOWED_IDS` obrigatorio, e preferir `chrome.storage.session` para tokens.
20. Adicionar validacao de schemas na extensao antes de persistir/enviar `ExtensionSession`, `CapturePreview` e payloads.

### Phase 5 — Tenant Isolation, Logs e Dados Sensiveis
21. Criar auditoria automatica de RLS: toda tabela com `tenant_id` precisa ter RLS/policy ativa; o teste deve falhar em CI.
22. Criar migrations para habilitar RLS/policies ausentes nas tabelas multi-tenant detectadas, principalmente Content Hub, engagement, extension captures, usage events e contact points.
23. Revisar queries criticas para filtro explicito por `tenant_id`, mesmo com RLS ativo.
24. Adicionar redaction global em `backend/core/logging.py` para tokens, secrets, senhas, API keys, refresh tokens, `li_at`, authorization e PII desnecessaria.
25. Criar trilha de auditoria leve: login, falhas, troca/rotacao de chaves, conexao de contas externas, upload/delete, acoes admin e alteracoes de tenant/users.

### Phase 6 — Headers, CORS, Arquivos e Bordas Publicas
26. Restringir CORS em `backend/api/main.py`: origins explicitas, headers/methods limitados em producao e sem `allow_headers=["*"]`.
27. Adicionar CSP ao frontend em `frontend/next.config.ts`, comecando por Report-Only se necessario e depois enforcement.
28. Revisar rotas de arquivo em `backend/api/routes/files.py` e `backend/integrations/s3_client.py`: presigned URLs para privados, content disposition seguro e politicas publicas minimas.
29. Centralizar politica de uploads para audio/imagem/PDF: tamanho maximo, MIME allowlist, magic bytes, normalizacao de nomes e chaves por tenant.
30. Garantir Flower/Redis/Postgres sem exposicao publica indevida; Flower so com Basic Auth forte e idealmente rede restrita.

### Phase 7 — Observabilidade, Alertas e CI
31. Criar alertas obrigatorios: backup base falhou, WAL archive atrasado, replication lag acima do limite, standby desconectado, restore drill falhou, uso de disco alto, Redis AOF falhou, MinIO mirror falhou, 5xx/API health e falhas repetidas de login.
32. Criar dashboard operacional com ultimas execucoes de backup, lag de replicacao, idade do ultimo WAL arquivado, estado do standby, saude de workers/beat e tamanho das filas.
33. Criar workflows de CI: backend lint/type/test, frontend build/test/typecheck, extension build, auditoria RLS, secret scanning e dependency audit.
34. Adicionar `pip-audit`, `npm audit` para `frontend/` e `extension/`, e Gitleaks/secret scanning.
35. Definir drill mensal inicialmente: alternar entre restore PITR, promocao de standby, perda de Redis e restore MinIO/S3; depois trimestral quando estabilizar.

## Arquivos Relevantes do Plano
- `backend/core/config.py` — configs de backup/DR, secrets, CORS e flags de seguranca.
- `backend/core/database.py` — referencia de RLS via `SET LOCAL app.current_tenant_id`.
- `backend/core/redis_client.py` — rate limits, grants/tickets single-use e estado temporario.
- `backend/core/logging.py` — redaction global de secrets/PII.
- `backend/api/main.py` — CORS e headers globais.
- `backend/api/routes/auth.py` — rate limit, grant single-use e fluxos da extensao.
- `backend/api/routes/ws.py` — ticket curto/single-use de WebSocket.
- `backend/api/routes/files.py`, `backend/api/routes/audio_files.py`, `backend/api/routes/tts.py` — arquivos, presigned URLs e upload policy.
- `backend/integrations/s3_client.py` — policies, presigned URLs e operacoes MinIO/S3.
- `backend/services/email_account_service.py` e `backend/services/linkedin_account_service.py` — Fernet e dependencia critica das encryption keys.
- `backend/models/base.py` e `backend/alembic/versions/` — auditoria/migrations de RLS.
- `backend/workers/celery_app.py`, `backend/scheduler/beats.py`, `backend/docker-compose.prod.yml` — recuperacao de workers/beat/Redis.
- `backend/scripts/` — novos scripts/verificadores de backup, restore e RLS.
- `docs/EASYPANEL_DEPLOY.md` — checklist de producao, failover e portas.
- `docs/BACKUP_DR.md`, `docs/SECURITY.md`, `docs/INCIDENT_RESPONSE.md` — documentos operacionais a detalhar.
- `frontend/next.config.ts` — CSP e headers.
- `frontend/src/app/auth/callback/page.tsx`, `frontend/src/app/auth/callback/callback-handler.tsx`, `frontend/src/lib/auth/config.ts` — troca de JWT em URL por grant.
- `frontend/src/lib/ws/use-events.ts` — ticket curto no WebSocket.
- `extension/src/background/storage.ts`, `extension/src/background/auth.ts`, `extension/src/manifest.ts`, `extension/src/shared/types.ts` — storage, OAuth callback, host allowlist e validacoes.
- `.github/workflows/` — CI, security scanning e dependency audit.

## Verificacao Planejada
1. Restaurar PITR em staging para timestamp especifico com backup base + WAL e medir RTO real.
2. Promover standby em drill controlado, trocar aplicacao para o standby e validar retomada em menos de 1h.
3. Medir replication lag e idade do ultimo WAL arquivado; alertar quando exceder limite compativel com RPO 5-15min.
4. Rodar restore automatico diario em banco temporario e validar `alembic current`, `/health`, login e consultas multi-tenant.
5. Simular perda de Redis e validar retomada sem duplicacoes criticas.
6. Restaurar prefixos MinIO/S3 em bucket temporario e comparar objetos contra referencias do banco.
7. Testar rate limit, grants/tickets single-use, expiracao, replay e tenant errado.
8. Rodar auditoria RLS e testes cross-tenant em CI.
9. Validar redaction de logs com tokens/secrets/PII sinteticos.
10. Validar CORS/CSP/upload/files com testes automatizados e checklist manual.
11. Rodar backend tests relevantes, frontend build/test, extension build, `pip-audit`, `npm audit` e Gitleaks.

## Decisoes Registradas
- Adotar opcao 3 como baseline: RPO 5-15min e RTO <1h.
- Postgres remoto e puro; nao usar Postgres local em container no dev.
- pgBackRest como ferramenta preferencial; WAL-G como alternativa se houver bloqueio de ambiente.
- Standby/replicacao faz parte do escopo base, nao e melhoria futura.
- Compliance formal ainda nao e obrigatorio, mas a arquitetura deve nascer com trilha de auditoria e resposta a incidentes.

## Consideracoes Futuras
1. Copia offsite real: MinIO/S3 no mesmo provedor protege contra erro logico e perda parcial, mas nao contra falha total do provedor. Para DR forte, replicar WAL/backups para outro provedor/regiao.
2. Failover automatico: nao implementar no primeiro momento sem maturidade operacional; comecar com promocao manual documentada e testada.
3. Criptografia de backups: se o storage nao criptografar server-side de forma confiavel, ativar criptografia client-side no pgBackRest/WAL-G e guardar keys em cofre.