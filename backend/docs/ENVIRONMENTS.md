# Ambientes — Dev Local e Produção

## Visão geral

| | Dev | Prod |
|---|---|---|
| Arquivo .env | `.env.dev` | `.env.prod` |
| Banco | PostgreSQL **remoto** | PostgreSQL **remoto** |
| Database name | `prospector_dev` | `prospector_prod` |
| Redis | container local porta 6379 | container no VPS |
| API porta | 8000 (com --reload) | 8000 (2 workers) |
| Volumes de código | montados (hot reload) | não (imagens builadas) |
| Compose file | `docker-compose.dev.yml` | `docker-compose.prod.yml` |

---

## Banco remoto — configuração recomendada

### Opção A — Neon (neon.tech)
Free tier generoso, branching de banco (útil para dev/prod no mesmo cluster).

```
Dev:  postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/prospector_dev?sslmode=require
Prod: postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/prospector_prod?sslmode=require
```

### Opção B — Supabase
Free tier com 500MB, painel visual, RLS nativo.

```
Dev:  postgresql+asyncpg://postgres:[password]@db.xxx.supabase.co:5432/postgres
```
> No Supabase, usar schemas separados (`search_path=dev` / `search_path=prod`)
> ou projetos separados.

---

## Como o código detecta o ambiente

```python
# core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV = os.getenv("ENV", "dev")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f".env.{ENV}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = ENV
    DEBUG: bool = False
    DATABASE_URL: str
    REDIS_URL: str
    # ... demais campos

settings = Settings()
```

A variável `ENV` é passada via `environment:` no docker-compose:
```yaml
environment:
  - ENV=dev   # ou ENV=prod
```

---

## Fluxo de desenvolvimento

### Primeira vez (setup completo)

```bash
# 1. Clonar
git clone https://github.com/compostoweb/prospector.git
cd prospector

# 2. Criar .env.dev a partir do template
cp .env.example .env.dev
# Editar .env.dev com as chaves reais

# 3. Subir stack dev
docker compose -f docker-compose.dev.yml up -d

# 4. Aplicar migrations no banco remoto
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# 5. Verificar
curl http://localhost:8000/health
# Flower: http://localhost:5555
```

### Dia a dia (dev)

```bash
# Subir (se não estiver rodando)
docker compose -f docker-compose.dev.yml up -d

# Ver logs da API em tempo real
docker compose -f docker-compose.dev.yml logs -f api

# Ver logs dos workers
docker compose -f docker-compose.dev.yml logs -f worker-general
docker compose -f docker-compose.dev.yml logs -f worker-content

# Parar tudo
docker compose -f docker-compose.dev.yml down
```

### Criar e aplicar migration

```bash
# Gerar migration a partir dos models
docker compose -f docker-compose.dev.yml exec api \
  alembic revision --autogenerate -m "descricao_da_mudanca"

# Aplicar no dev
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# Ver histórico
docker compose -f docker-compose.dev.yml exec api alembic history
```

---

## Deploy em produção

### Primeira vez no VPS

```bash
# No VPS
git clone https://github.com/compostoweb/prospector.git /app/prospector
cd /app/prospector

# Criar .env.prod
cp .env.example .env.prod
nano .env.prod   # preencher com valores de produção

# Subir
docker compose -f docker-compose.prod.yml up -d --build

# Migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Atualizar produção (deploy)

```bash
cd /app/prospector
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Rollback rápido

```bash
git checkout <commit-anterior>
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

---

## Diferenças importantes dev vs prod

| Aspecto | Dev | Prod |
|---|---|---|
| `--reload` | Sim (hot reload) | Não |
| `DEBUG=` | `true` | `false` |
| Workers uvicorn | 1 | 2 |
| Workers celery dispatch | 2 | 4 (escalável) |
| Volumes de código | Montados (`- .:/app`) | Não montados |
| Log level | `info` | `warning` |
| Flower auth | Não | Sim (`FLOWER_USER` + `FLOWER_PASSWORD`) |
| Redis persistência | Não | Sim (`appendonly yes`) |

---

## Variáveis que diferem entre dev e prod

```bash
# .env.dev
ENV=dev
DEBUG=true
DATABASE_URL=postgresql+asyncpg://user:pass@host/prospector_dev
REDIS_URL=redis://localhost:6379/0

# .env.prod
ENV=prod
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@host/prospector_prod
REDIS_URL=redis://redis:6379/0   # nome do container no compose
FLOWER_USER=admin
FLOWER_PASSWORD=senha-forte-aqui
```

> No prod, o Redis URL usa `redis://redis:6379/0` (nome do serviço no Docker network).
> No dev, usa `redis://localhost:6379/0` (exposto na porta local).

---

## Checklist antes de fazer deploy em prod

- [ ] `.env.prod` com todas as chaves preenchidas
- [ ] `SECRET_KEY` diferente do dev e com 32+ chars
- [ ] `DEBUG=false`
- [ ] Migrations testadas no dev primeiro
- [ ] Backup do banco antes de migrations destrutivas
- [ ] `FLOWER_USER` e `FLOWER_PASSWORD` definidos
- [ ] Webhook URL da Unipile apontando para o domínio de produção
