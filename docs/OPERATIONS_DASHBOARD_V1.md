# Operations Dashboard v1

Ultima atualizacao: 2026-05-02

## Objetivo

Definir um dashboard operacional versionado para DR, filas e storage, independente da ferramenta final de visualizacao.

## Blocos obrigatorios

### 1. Backup e Restore

- ultimo backup base concluido
- idade do ultimo WAL arquivado
- ultimo restore verification status
- ultimo object storage verification status

### 2. Replicacao

- standby conectado
- replication lag atual
- slot prospector_replica_slot ativo

### 3. Redis e Filas

- Redis ping/status
- AOF habilitado
- tamanho das filas por queue: capture, enrich, cadence, dispatch, content
- workers ativos por fila

### 4. Aplicacao

- health da API
- erro 5xx por janela
- falhas recentes de auth rate-limited
- latencia basica de login e /health

### 5. Storage

- total de missing assets na ultima verificacao
- assets parse_error na ultima verificacao
- ultima execucao bem-sucedida do mirror/offsite

## Contrato minimo do snapshot

```json
{
  "generated_at": "2026-05-02T12:00:00Z",
  "backup": {
    "last_base_backup_at": "2026-05-02T02:00:00Z",
    "last_wal_archive_age_seconds": 180,
    "restore_verification_ok": true,
    "object_storage_verification_ok": true
  },
  "replication": {
    "standby_connected": true,
    "lag_seconds": 4,
    "slot_active": true
  },
  "redis": {
    "ping_ok": true,
    "aof_enabled": true,
    "queues": {
      "capture": 0,
      "enrich": 1,
      "cadence": 4,
      "dispatch": 0,
      "content": 0
    }
  },
  "api": {
    "health_ok": true,
    "http_5xx_last_15m": 0
  },
  "storage": {
    "missing_assets": 0,
    "parse_errors": 0,
    "last_offsite_mirror_ok": true
  }
}
```

## Fontes dos dados

- host monitor de DR
- backend/scripts/verify_restore_target.py
- backend/scripts/verify_object_storage_restore.py
- health da API
- Redis INFO / fila Celery

## Regra operacional

Sem esse snapshot minimo, nenhum drill mensal pode ser considerado completo.