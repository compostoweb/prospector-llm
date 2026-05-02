# DR Drills

Ultima atualizacao: 2026-05-02

## Cadencia

- mensal: restore verification de banco e API
- mensal: object storage verification
- bimestral: perda de Redis com retomada controlada
- trimestral: PITR com timestamp alvo
- trimestral: promocao controlada de standby

## Sequencia sugerida

### Mes 1

- restore verification com backend/scripts/verify_restore_target.py
- object storage verification com backend/scripts/verify_object_storage_restore.py

### Mes 2

- drill de perda de Redis seguindo docs/REDIS_DR.md

### Mes 3

- PITR controlado
- promocao de standby

Repetir o ciclo e ajustar a frequencia quando houver tres ciclos consecutivos sem falha operacional.

## Evidencias minimas por drill

- horario de inicio e fim
- operador responsavel
- ambiente usado
- JSON gerado pelos scripts versionados quando aplicavel
- anomalias encontradas
- acoes corretivas abertas

## Criterios de aprovacao

- restore verification com overall_ok true
- object storage verification com overall_ok true
- sem perda funcional relevante em auth, leads e filas apos o drill
- backlog de correcoes registrado se houver qualquer desvio