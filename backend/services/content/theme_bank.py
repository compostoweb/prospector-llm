"""
services/content/theme_bank.py

Banco inicial de temas editoriais da Composto Web para o Content Hub.

Mantem duas colecoes:
- temas disponiveis para novos posts
- historico inicial de temas ja publicados para evitar repeticao
"""

from __future__ import annotations

import uuid
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.content_theme import ContentTheme


class ThemeSeed(TypedDict):
    title: str
    pillar: str
    used: bool


DEFAULT_CONTENT_THEME_BANK: tuple[ThemeSeed, ...] = (
    {
        "title": "Por que integração de sistemas falha mais por processo do que por tecnologia",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "A diferença entre RPA e automação inteligente (e quando usar cada um)",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "Como IA privada (Ollama) funciona e quando faz sentido sobre APIs comerciais",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "Por que 35% do gasto em cloud é desperdiçado e como identificar o seu",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "O que é self-healing em automação e por que importa para operações críticas",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "DevOps não é só deploy. É a diferença entre sistema que cai e sistema que aguenta",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": 'A verdade sobre LGPD e sistemas que "garantem conformidade"',
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "Por que o ERP não resolve o problema (e o que resolve)",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "Quando vale a pena construir software sob medida vs usar SaaS",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "Como funciona um agente de IA no WhatsApp na prática (sem hype)",
        "pillar": "authority",
        "used": False,
    },
    {
        "title": "O diagnóstico que impediu um projeto desnecessário (caso genérico)",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "Como uma clínica reduziu no-show sem trocar o sistema de gestão",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "O fechamento mensal que caiu de 5 dias para 6 horas",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "Por que o primeiro projeto de automação da empresa quase foi um desastre",
        "pillar": "case",
        "used": False,
    },
    {
        "title": 'O que encontrei quando fui diagnosticar uma operação "que já tinha tudo automatizado"',
        "pillar": "case",
        "used": False,
    },
    {
        "title": "Como um escritório jurídico parou de usar ChatGPT e melhorou os resultados com IA privada",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "Bastidor: como mapeamos um processo de 40 etapas e encontramos o gargalo na etapa 7",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "O cliente que queria chatbot e precisava de integração de ERP",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "Por que entregamos o código e a documentação: o dia que um cliente nos agradeceu por isso",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "O que acontece quando um projeto de TI vai pra produção sem teste de carga",
        "pillar": "case",
        "used": False,
    },
    {
        "title": "Automação não é sobre demitir pessoas. É sobre parar de contratar para o problema errado",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": "A empresa que não tem dado em tempo real já está tomando decisões erradas agora",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": 'Por que "vamos fazer internamente" custa mais do que parece',
        "pillar": "vision",
        "used": False,
    },
    {
        "title": "O maior erro das empresas com IA: implementar antes de entender o problema",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": "Soberania digital: você é dono do seu software ou está alugando dependência?",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": "Em 3 anos, a diferença entre quem cresce e quem trava vai ser o dado em tempo real",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": "Por que projetos de tecnologia que começam pelo código geralmente falham",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": "O que os melhores CFOs estão fazendo diferente com automação financeira",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": "A pergunta que faço antes de qualquer projeto: qual é o custo real de não resolver isso?",
        "pillar": "vision",
        "used": False,
    },
    {
        "title": 'Por que "nossa operação é muito específica para automação" quase sempre é mito',
        "pillar": "vision",
        "used": False,
    },
)


PUBLISHED_CONTENT_THEME_HISTORY: tuple[ThemeSeed, ...] = (
    {"title": "O problema raramente está onde você acha", "pillar": "vision", "used": True},
    {
        "title": "Automatizar processo ruim é piorar mais rápido",
        "pillar": "authority",
        "used": True,
    },
    {"title": "A clínica que queria chatbot", "pillar": "case", "used": True},
    {
        "title": "Empresas não têm problema de IA. Têm problema de dado.",
        "pillar": "vision",
        "used": True,
    },
    {
        "title": "Projeto que começa pelo código já começa errado",
        "pillar": "authority",
        "used": True,
    },
    {"title": "O que aprendi diagnosticando operações", "pillar": "case", "used": True},
    {"title": "Você está decidindo com dado de ontem", "pillar": "vision", "used": True},
    {"title": "Antes de colocar seus contratos no ChatGPT", "pillar": "authority", "used": True},
    {"title": "O cliente queria trocar o ERP", "pillar": "case", "used": True},
    {
        "title": "O dado em tempo real vai separar quem cresce de quem trava",
        "pillar": "vision",
        "used": True,
    },
    {"title": "Você é dono do seu software?", "pillar": "authority", "used": True},
    {"title": "Toda solução começa com uma pergunta", "pillar": "case", "used": True},
)


ALL_CONTENT_THEME_SEEDS: tuple[ThemeSeed, ...] = (
    *DEFAULT_CONTENT_THEME_BANK,
    *PUBLISHED_CONTENT_THEME_HISTORY,
)


async def seed_theme_bank_for_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Adiciona ao tenant os temas padrao que ainda nao existirem."""
    result = await db.execute(select(ContentTheme.title).where(ContentTheme.tenant_id == tenant_id))
    existing_titles = set(result.scalars().all())

    missing_seeds = [
        seed for seed in ALL_CONTENT_THEME_SEEDS if seed["title"] not in existing_titles
    ]
    if not missing_seeds:
        return 0

    db.add_all(
        [
            ContentTheme(
                tenant_id=tenant_id,
                title=seed["title"],
                pillar=seed["pillar"],
                used=seed["used"],
                is_custom=False,
            )
            for seed in missing_seeds
        ]
    )
    return len(missing_seeds)
