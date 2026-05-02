# Backup e Disaster Recovery

Ultima atualizacao: 2026-05-01

## Objetivos

- PostgreSQL: RPO de 5 a 15 minutos e RTO menor que 1 hora.
- Aplicacao: RTO operacional de 15 minutos apos recuperacao do banco.
- Redis: RPO de ate 5 minutos com AOF ativo.
- Objetos em S3/MinIO: preservar prefixos criticos e reduzir perda operacional.

## Topologia Atual

- PostgreSQL primary com pgBackRest persistido no servico.
- WAL archiving ativo e validado.
- Standby real por streaming replication com slot fisico `prospector_replica_slot`.
- Redis com AOF habilitado.
- Restore drill isolado ja executado com sucesso sem tocar no primary.
- Monitor de saude DR rodando no host a cada 5 minutos.

## Artefatos Operacionais no Host

- Restore drill:
  - `/root/prospector-restore-drill/data`
  - `/root/prospector-restore-drill/pgbackrest/pgbackrest.conf`
  - `/root/prospector-restore-drill/restore.log`
- Alertas DR:
  - `/root/prospector-alerts/check_dr_health.py`
  - `/root/prospector-alerts/alert.env`
  - `/root/prospector-alerts/state.json`
  - `/var/log/prospector-dr-alert.log`
- Cron:
  - `*/5 * * * * /root/prospector-alerts/check_dr_health.py >> /var/log/prospector-dr-alert.log 2>&1`

## Runbook de Failover Manual

1. Pausar Celery Beat.
2. Confirmar estado do standby e o lag atual.
3. Promover o standby.
4. Atualizar `DATABASE_URL` ou o alvo DNS/host no EasyPanel.
5. Reiniciar API, workers e processos dependentes.
6. Validar `/health`, login e smoke tests essenciais.
7. Reativar Beat somente apos confirmacao da consistencia.

## Runbook de PITR

1. Definir timestamp alvo do recovery.
2. Restaurar backup base mais WAL em host ou container isolado.
3. Validar startup, `pg_is_in_recovery()`, `alembic current` e consultas amostrais.
4. Promover somente apos validacao funcional.
5. Reapontar aplicacao para a instancia recuperada se necessario.

## Runbook de Redis

1. Pausar Beat.
2. Subir Redis restaurado ou limpo.
3. Reiniciar workers.
4. Validar retomada de filas, cadencias e pollers.
5. Reativar Beat.

## Verificacoes Obrigatorias

- Backup base executado com sucesso.
- Idade do ultimo WAL arquivado dentro do limite compativel com RPO.
- Lag de replicacao dentro do limite operacional.
- Standby conectado e pronto para promocao.
- Redis AOF operacional.

## Pendencias Abertas

- Automatizar restore diario em ambiente temporario/staging.
- Formalizar restore de prefixos criticos de S3/MinIO.
- Versionar checklist de failover e retorno ao primary apos crise.
- Definir estrategia offsite real para backups e WAL.