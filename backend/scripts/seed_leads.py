"""
scripts/seed_leads.py

Seed de 10 leads de teste para desenvolvimento.
Idempotente — verifica por linkedin_url antes de inserir.

Uso:
    cd backend
    ENV=dev python -m scripts.seed_leads
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# Garante que o diretório backend está no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import AsyncSessionLocal
from models.lead import Lead
from models.lead_list import LeadList
from models.enums import LeadSource, LeadStatus

import structlog

logger = structlog.get_logger()

# ── Dados de teste ────────────────────────────────────────────────────

SEED_LEADS: list[dict] = [
    {
        "name": "Carlos Silva",
        "first_name": "Carlos",
        "last_name": "Silva",
        "job_title": "CTO",
        "company": "TechBR Soluções",
        "company_domain": "techbr.com.br",
        "industry": "Tecnologia",
        "company_size": "51-200",
        "linkedin_url": "https://www.linkedin.com/in/seed-carlos-silva",
        "city": "São Paulo",
        "location": "São Paulo, SP, Brasil",
        "segment": "SaaS B2B",
        "email_corporate": "carlos@techbr.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
    {
        "name": "Ana Oliveira",
        "first_name": "Ana",
        "last_name": "Oliveira",
        "job_title": "Head de Marketing",
        "company": "Agência Criativa Digital",
        "company_domain": "criativadigital.com.br",
        "industry": "Marketing Digital",
        "company_size": "11-50",
        "linkedin_url": "https://www.linkedin.com/in/seed-ana-oliveira",
        "city": "Rio de Janeiro",
        "location": "Rio de Janeiro, RJ, Brasil",
        "segment": "Agências",
        "email_corporate": "ana@criativadigital.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
    {
        "name": "Roberto Santos",
        "first_name": "Roberto",
        "last_name": "Santos",
        "job_title": "CEO",
        "company": "Inova Consultoria",
        "company_domain": "inovaconsultoria.com.br",
        "industry": "Consultoria",
        "company_size": "11-50",
        "linkedin_url": "https://www.linkedin.com/in/seed-roberto-santos",
        "city": "Belo Horizonte",
        "location": "Belo Horizonte, MG, Brasil",
        "segment": "Consultoria Empresarial",
        "email_corporate": "roberto@inovaconsultoria.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
    {
        "name": "Fernanda Costa",
        "first_name": "Fernanda",
        "last_name": "Costa",
        "job_title": "Diretora Comercial",
        "company": "VendaMais LTDA",
        "company_domain": "vendamais.com.br",
        "industry": "E-commerce",
        "company_size": "201-500",
        "linkedin_url": "https://www.linkedin.com/in/seed-fernanda-costa",
        "city": "Curitiba",
        "location": "Curitiba, PR, Brasil",
        "segment": "E-commerce",
        "email_corporate": "fernanda@vendamais.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.ENRICHED,
        "score": 85.0,
    },
    {
        "name": "Pedro Mendes",
        "first_name": "Pedro",
        "last_name": "Mendes",
        "job_title": "VP de Engenharia",
        "company": "CloudStack Brasil",
        "company_domain": "cloudstack.com.br",
        "industry": "Cloud Computing",
        "company_size": "51-200",
        "linkedin_url": "https://www.linkedin.com/in/seed-pedro-mendes",
        "city": "Florianópolis",
        "location": "Florianópolis, SC, Brasil",
        "segment": "Infraestrutura Cloud",
        "email_corporate": "pedro@cloudstack.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
    {
        "name": "Juliana Pereira",
        "first_name": "Juliana",
        "last_name": "Pereira",
        "job_title": "Gerente de Produto",
        "company": "FinTech Pay",
        "company_domain": "fintechpay.com.br",
        "industry": "Fintech",
        "company_size": "51-200",
        "linkedin_url": "https://www.linkedin.com/in/seed-juliana-pereira",
        "city": "São Paulo",
        "location": "São Paulo, SP, Brasil",
        "segment": "Pagamentos Digitais",
        "email_corporate": "juliana@fintechpay.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
    {
        "name": "Marcos Lima",
        "first_name": "Marcos",
        "last_name": "Lima",
        "job_title": "Founder & CEO",
        "company": "EduTech Academy",
        "company_domain": "edutechacademy.com.br",
        "industry": "EdTech",
        "company_size": "11-50",
        "linkedin_url": "https://www.linkedin.com/in/seed-marcos-lima",
        "city": "Porto Alegre",
        "location": "Porto Alegre, RS, Brasil",
        "segment": "Educação Online",
        "email_corporate": "marcos@edutechacademy.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
    {
        "name": "Camila Rodrigues",
        "first_name": "Camila",
        "last_name": "Rodrigues",
        "job_title": "Head de Growth",
        "company": "StartupHub",
        "company_domain": "startuphub.com.br",
        "industry": "Aceleradora",
        "company_size": "11-50",
        "linkedin_url": "https://www.linkedin.com/in/seed-camila-rodrigues",
        "city": "Campinas",
        "location": "Campinas, SP, Brasil",
        "segment": "Startups / Aceleração",
        "email_corporate": "camila@startuphub.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.ENRICHED,
        "score": 72.0,
    },
    {
        "name": "Lucas Almeida",
        "first_name": "Lucas",
        "last_name": "Almeida",
        "job_title": "Diretor de TI",
        "company": "LogBR Transportes",
        "company_domain": "logbr.com.br",
        "industry": "Logística",
        "company_size": "501-1000",
        "linkedin_url": "https://www.linkedin.com/in/seed-lucas-almeida",
        "city": "Goiânia",
        "location": "Goiânia, GO, Brasil",
        "segment": "Logística e Transporte",
        "email_corporate": "lucas@logbr.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
    {
        "name": "Beatriz Ferreira",
        "first_name": "Beatriz",
        "last_name": "Ferreira",
        "job_title": "COO",
        "company": "HealthTech Brasil",
        "company_domain": "healthtechbr.com.br",
        "industry": "HealthTech",
        "company_size": "51-200",
        "linkedin_url": "https://www.linkedin.com/in/seed-beatriz-ferreira",
        "city": "Recife",
        "location": "Recife, PE, Brasil",
        "segment": "Saúde Digital",
        "email_corporate": "beatriz@healthtechbr.com.br",
        "source": LeadSource.MANUAL,
        "status": LeadStatus.RAW,
    },
]


async def seed_leads(tenant_id: uuid.UUID) -> None:
    """Insere leads de teste e cria uma lista 'Leads Seed'."""
    async with AsyncSessionLocal() as session:
        # Injeta tenant no contexto RLS
        # SET LOCAL não suporta bind params em asyncpg — tenant_id é UUID validado
        tid = str(tenant_id)
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tid}'"))

        created = 0
        skipped = 0
        lead_objects: list[Lead] = []

        for data in SEED_LEADS:
            # Verifica se já existe por linkedin_url
            result = await session.execute(
                select(Lead).where(
                    Lead.linkedin_url == data["linkedin_url"],
                    Lead.tenant_id == tenant_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                skipped += 1
                lead_objects.append(existing)
                continue

            lead = Lead(tenant_id=tenant_id, **data)
            session.add(lead)
            lead_objects.append(lead)
            created += 1

        # Cria lista "Leads Seed" se não existir
        result = await session.execute(
            select(LeadList).where(
                LeadList.name == "Leads Seed (Teste)",
                LeadList.tenant_id == tenant_id,
            )
        )
        lead_list = result.scalar_one_or_none()
        if not lead_list:
            lead_list = LeadList(
                tenant_id=tenant_id,
                name="Leads Seed (Teste)",
                description="Lista de leads de teste criada pelo seed script",
            )
            session.add(lead_list)

        await session.flush()

        # Associa leads à lista via tabela associativa
        from models.lead_list import lead_list_members

        for lead in lead_objects:
            # Verifica se já está na lista
            exists = await session.execute(
                select(lead_list_members).where(
                    lead_list_members.c.lead_list_id == lead_list.id,
                    lead_list_members.c.lead_id == lead.id,
                )
            )
            if not exists.first():
                await session.execute(
                    lead_list_members.insert().values(
                        lead_list_id=lead_list.id,
                        lead_id=lead.id,
                    )
                )

        await session.commit()
        logger.info(
            "seed.leads.done",
            created=created,
            skipped=skipped,
            total=len(SEED_LEADS),
            list_name=lead_list.name,
            tenant_id=str(tenant_id),
        )


async def main() -> None:
    from models.tenant import Tenant

    # Busca o primeiro tenant ativo
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()

    if not tenant:
        logger.error("seed.no_tenant", msg="Nenhum tenant encontrado. Crie um tenant primeiro.")
        sys.exit(1)

    logger.info("seed.starting", tenant_id=str(tenant.id), tenant_name=tenant.name)
    await seed_leads(tenant.id)


if __name__ == "__main__":
    asyncio.run(main())
