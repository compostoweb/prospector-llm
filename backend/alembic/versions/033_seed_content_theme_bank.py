"""033 -- Seed do banco inicial de temas do Content Hub por tenant.

Insere 42 temas base da Composto Web em `content_themes` para todos os tenants
existentes, preservando dados ja inseridos manualmente.

Revision ID: 033
Revises: 032
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


THEME_SEEDS: tuple[tuple[str, str, bool], ...] = (
    (
        "Por que integração de sistemas falha mais por processo do que por tecnologia",
        "authority",
        False,
    ),
    ("A diferença entre RPA e automação inteligente (e quando usar cada um)", "authority", False),
    (
        "Como IA privada (Ollama) funciona e quando faz sentido sobre APIs comerciais",
        "authority",
        False,
    ),
    ("Por que 35% do gasto em cloud é desperdiçado e como identificar o seu", "authority", False),
    (
        "O que é self-healing em automação e por que importa para operações críticas",
        "authority",
        False,
    ),
    (
        "DevOps não é só deploy. É a diferença entre sistema que cai e sistema que aguenta",
        "authority",
        False,
    ),
    ('A verdade sobre LGPD e sistemas que "garantem conformidade"', "authority", False),
    ("Por que o ERP não resolve o problema (e o que resolve)", "authority", False),
    ("Quando vale a pena construir software sob medida vs usar SaaS", "authority", False),
    ("Como funciona um agente de IA no WhatsApp na prática (sem hype)", "authority", False),
    ("O diagnóstico que impediu um projeto desnecessário (caso genérico)", "case", False),
    ("Como uma clínica reduziu no-show sem trocar o sistema de gestão", "case", False),
    ("O fechamento mensal que caiu de 5 dias para 6 horas", "case", False),
    ("Por que o primeiro projeto de automação da empresa quase foi um desastre", "case", False),
    (
        'O que encontrei quando fui diagnosticar uma operação "que já tinha tudo automatizado"',
        "case",
        False,
    ),
    (
        "Como um escritório jurídico parou de usar ChatGPT e melhorou os resultados com IA privada",
        "case",
        False,
    ),
    (
        "Bastidor: como mapeamos um processo de 40 etapas e encontramos o gargalo na etapa 7",
        "case",
        False,
    ),
    ("O cliente que queria chatbot e precisava de integração de ERP", "case", False),
    (
        "Por que entregamos o código e a documentação: o dia que um cliente nos agradeceu por isso",
        "case",
        False,
    ),
    ("O que acontece quando um projeto de TI vai pra produção sem teste de carga", "case", False),
    (
        "Automação não é sobre demitir pessoas. É sobre parar de contratar para o problema errado",
        "vision",
        False,
    ),
    (
        "A empresa que não tem dado em tempo real já está tomando decisões erradas agora",
        "vision",
        False,
    ),
    ('Por que "vamos fazer internamente" custa mais do que parece', "vision", False),
    ("O maior erro das empresas com IA: implementar antes de entender o problema", "vision", False),
    (
        "Soberania digital: você é dono do seu software ou está alugando dependência?",
        "vision",
        False,
    ),
    (
        "Em 3 anos, a diferença entre quem cresce e quem trava vai ser o dado em tempo real",
        "vision",
        False,
    ),
    ("Por que projetos de tecnologia que começam pelo código geralmente falham", "vision", False),
    ("O que os melhores CFOs estão fazendo diferente com automação financeira", "vision", False),
    (
        "A pergunta que faço antes de qualquer projeto: qual é o custo real de não resolver isso?",
        "vision",
        False,
    ),
    (
        'Por que "nossa operação é muito específica para automação" quase sempre é mito',
        "vision",
        False,
    ),
    ("O problema raramente está onde você acha", "vision", True),
    ("Automatizar processo ruim é piorar mais rápido", "authority", True),
    ("A clínica que queria chatbot", "case", True),
    ("Empresas não têm problema de IA. Têm problema de dado.", "vision", True),
    ("Projeto que começa pelo código já começa errado", "authority", True),
    ("O que aprendi diagnosticando operações", "case", True),
    ("Você está decidindo com dado de ontem", "vision", True),
    ("Antes de colocar seus contratos no ChatGPT", "authority", True),
    ("O cliente queria trocar o ERP", "case", True),
    ("O dado em tempo real vai separar quem cresce de quem trava", "vision", True),
    ("Você é dono do seu software?", "authority", True),
    ("Toda solução começa com uma pergunta", "case", True),
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)
    tenants = sa.table(
        "tenants",
        sa.column("id", postgresql.UUID(as_uuid=True)),
    )
    content_themes = sa.table(
        "content_themes",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.column("title", sa.String()),
        sa.column("pillar", sa.String()),
        sa.column("used", sa.Boolean()),
        sa.column("used_at", sa.DateTime(timezone=True)),
        sa.column("used_in_post_id", postgresql.UUID(as_uuid=True)),
        sa.column("is_custom", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    tenant_rows = bind.execute(sa.select(tenants.c.id)).fetchall()
    for tenant_row in tenant_rows:
        tenant_id = tenant_row.id
        existing_titles = {
            row[0]
            for row in bind.execute(
                sa.select(content_themes.c.title).where(content_themes.c.tenant_id == tenant_id)
            ).fetchall()
        }

        rows_to_insert = [
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "title": title,
                "pillar": pillar,
                "used": used,
                "used_at": now if used else None,
                "used_in_post_id": None,
                "is_custom": False,
                "created_at": now,
                "updated_at": now,
            }
            for title, pillar, used in THEME_SEEDS
            if title not in existing_titles
        ]
        if rows_to_insert:
            op.bulk_insert(content_themes, rows_to_insert)


def downgrade() -> None:
    bind = op.get_bind()
    content_themes = sa.table(
        "content_themes",
        sa.column("title", sa.String()),
        sa.column("is_custom", sa.Boolean()),
    )
    bind.execute(
        sa.delete(content_themes).where(
            content_themes.c.is_custom.is_(False),
            content_themes.c.title.in_([title for title, _, _ in THEME_SEEDS]),
        )
    )
