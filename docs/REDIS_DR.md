# Redis DR Runbook

Ultima atualizacao: 2026-05-02

## Objetivo

Padronizar resposta a perda total, corrupcao de AOF, restart em branco ou restauracao de Redis sem causar reenvios indevidos, perda silenciosa de rate limits ou reativacao desordenada de Celery Beat.

## Escopo

- Redis operacional do backend
- chaves de rate limit
- grants e tickets single-use
- filas Celery e locks transitórios

## Premissas

- O estado canonico de negocio continua no PostgreSQL.
- Redis e camada operacional efemera com parte do estado recuperavel por idempotencia.
- Celery Beat deve permanecer pausado durante a recuperacao.

## Quando acionar

- Redis nao sobe ou entra em loop por corrupcao de AOF.
- Perda total do volume.
- Restore de snapshot/AOF para host novo.
- Suspeita de replay de grants, tickets ou rate limits corrompidos.

## Pre-checks

1. Registrar horario do incidente e a ultima confirmacao de Redis saudavel.
2. Identificar se houve perda logica, perda de volume ou apenas restart frio.
3. Confirmar que o PostgreSQL esta saudavel.
4. Pausar Celery Beat antes de religar workers.

## Procedimento de restauracao

1. Parar workers de dispatch, cadence, capture e content.
2. Pausar Celery Beat.
3. Subir Redis restaurado do volume/snapshot mais recente ou iniciar uma instancia limpa se o restore falhar.
4. Confirmar configuracao minima:
   - appendonly yes
   - appendfsync everysec
   - volume persistente montado
5. Validar conectividade basica com ping e leitura/escrita simples.
6. Subir primeiro os workers.
7. Validar que filas processam jobs sem explosao de retries.
8. Reativar Celery Beat apenas apos smoke operacional.

## Smoke operacional obrigatorio

1. Executar healthcheck da API.
2. Validar login de tenant e emissao de token.
3. Validar consumo unico de grant_code e ws ticket.
4. Validar uma janela curta de rate limit em auth.
5. Confirmar que nao houve disparo em massa retroativo de cadencias.

## Comandos versionados do repositório

- Verificacao de restore de banco e API:
  - backend/scripts/verify_restore_target.py
- Verificacao de object storage apos restore:
  - backend/scripts/verify_object_storage_restore.py

Exemplo de restore smoke apos retorno do Redis:

```powershell
Set-Location backend
c:/python314/python.exe .\scripts\verify_restore_target.py \
  --database-url "$env:RESTORE_CHECK_DATABASE_URL" \
  --api-url "http://127.0.0.1:8000" \
  --tenant-slug "$env:RESTORE_CHECK_TENANT_SLUG" \
  --tenant-api-key "$env:RESTORE_CHECK_TENANT_API_KEY"
```

## Riscos conhecidos

- Rate limits, grants e tickets podem ser perdidos ao iniciar Redis limpo.
- Locks e caches podem sumir e causar recomputacao temporaria.
- Jobs em voo podem reexecutar se a camada idempotente nao estiver correta.

## Criterios de saida

- API responde em healthcheck.
- Auth de tenant funcional.
- Workers estao consumindo normalmente.
- Nenhum flood anormal de dispatch foi detectado nos primeiros minutos.
- Beat reativado apenas apos validacao.