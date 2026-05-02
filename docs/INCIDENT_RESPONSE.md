# Incident Response

Ultima atualizacao: 2026-05-01

## Escopo

Este documento cobre resposta inicial para:

- suspeita de invasao
- vazamento de dados ou credenciais
- indisponibilidade do banco principal
- falha severa de Redis ou filas
- corrupcao ou perda de objetos criticos em S3/MinIO

## Principios

- Conter antes de ampliar escopo.
- Preservar evidencias e rastros operacionais.
- Evitar mudancas destrutivas sem snapshot ou copia do estado atual.
- Comunicar impacto, decisao e horario de cada acao executada.

## Fluxo Basico

1. Classificar o incidente: autenticacao, dados, infraestrutura, fila, storage.
2. Congelar mudancas nao essenciais.
3. Isolar o componente afetado.
4. Preservar logs, configuracoes e referencias temporais.
5. Executar o runbook tecnico apropriado.
6. Validar recuperacao funcional minima.
7. Registrar causa, impacto e acoes corretivas.

## Playbooks Rapidos

### Suspeita de vazamento de token ou grant

1. Revogar ou rotacionar o segredo afetado.
2. Invalidar sessoes/grants/tickets relacionados no Redis.
3. Verificar logs redigidos, trilhas de auditoria e origem do abuso.
4. Confirmar se houve acesso cross-tenant ou exfiltracao.

### Comprometimento de conta externa

1. Desconectar ou pausar a integracao afetada.
2. Rotacionar credenciais no provedor externo.
3. Revisar eventos de auditoria da conta e webhooks recentes.
4. Revalidar sincronizacao antes de religar a integracao.

### Falha do PostgreSQL primary

1. Pausar Beat.
2. Confirmar se o standby esta pronto.
3. Executar failover manual ou PITR conforme o tipo de falha.
4. Reapontar aplicacao e validar `/health`, login e consultas essenciais.

### Falha de Redis

1. Pausar Beat.
2. Restaurar ou recriar Redis.
3. Reiniciar workers.
4. Validar se nao houve duplicacao critica de dispatch.

## Evidencias Minimas a Preservar

- Horario inicial percebido e horario de mitigacao.
- Logs de API e workers relevantes.
- Estado do Redis se houver suspeita de replay ou fila corrompida.
- Estado do banco antes de promocao/failover quando possivel.
- Chaves, contas e tenants potencialmente afetados.

## Pos-Incidente

- Atualizar [docs/BACKUP_SECURITY_PLAN_2026-05-01.md](docs/BACKUP_SECURITY_PLAN_2026-05-01.md) quando o incidente alterar o baseline.
- Criar tarefa de correcao permanente para a causa raiz.
- Registrar gaps de monitoramento, documentação e automacao descobertos no incidente.