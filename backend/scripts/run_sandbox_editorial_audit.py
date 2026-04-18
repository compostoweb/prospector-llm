"""
scripts/run_sandbox_editorial_audit.py

Roda uma bateria manual de exemplos usando a mesma pipeline do composer/sandbox
e grava um relatorio markdown com a validacao editorial de cada saida.

Uso:
    cd backend
    python scripts/run_sandbox_editorial_audit.py
    python scripts/run_sandbox_editorial_audit.py --provider openai --model gpt-5.4-mini --limit 4
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.config import settings
from core.redis_client import redis_client
from integrations.llm import LLMRegistry
from models.cadence import Cadence
from models.lead import Lead
from services.ai_composer import AIComposer, prepare_composer_messages
from services.editorial_validator import serialize_editorial_validation, validate_editorial_output


@dataclass(frozen=True)
class AuditScenario:
    key: str
    label: str
    channel: str
    step_number: int
    total_steps: int
    lead_data: dict[str, Any]
    context: dict[str, str]
    previous_channel: str | None = None
    use_voice: bool = False
    step_type: str | None = None


_SCENARIOS: list[AuditScenario] = [
    AuditScenario(
        key="saude_linkedin_connect",
        label="Saude | Convite de conexao",
        channel="linkedin_connect",
        step_number=1,
        total_steps=5,
        lead_data={
            "name": "Marina Torres",
            "company": "Clinica Horizonte",
            "job_title": "Diretora da Clinica",
            "industry": "Saude e clinicas",
            "website": "https://clinicahorizonte.example",
            "linkedin_url": "https://linkedin.com/in/marinatorres",
        },
        context={
            "site_summary": "Rede de clinicas com foco em especialidades e atendimento particular, ampliando agenda e unidade.",
            "company_news": "A Clinica Horizonte anunciou ampliacao do horario de atendimento e novas especialidades.",
        },
    ),
    AuditScenario(
        key="varejo_email_first",
        label="Varejo | Email inicial",
        channel="email",
        step_number=1,
        total_steps=5,
        lead_data={
            "name": "Ricardo Araujo",
            "company": "Casa Nativa",
            "job_title": "CEO de E-commerce",
            "industry": "Varejo e e-commerce",
            "website": "https://casanativa.example",
        },
        context={
            "site_summary": "Marca omnichannel com e-commerce proprio, marketplace e operacao de fulfillment regional.",
            "company_news": "A Casa Nativa abriu novo centro de distribuicao e expandiu operacao marketplace.",
        },
    ),
    AuditScenario(
        key="educacao_email_followup",
        label="Educacao | Email follow-up",
        channel="email",
        step_number=3,
        total_steps=5,
        lead_data={
            "name": "Carla Mota",
            "company": "Instituto Vanguarda",
            "job_title": "Diretora Academica",
            "industry": "Educacao e EdTech",
            "website": "https://vanguarda.example",
        },
        context={
            "site_summary": "Instituicao com operacao hibrida e foco em rematricula e engajamento continuado.",
            "company_news": "O Instituto Vanguarda anunciou nova vertical de cursos tecnicos e ampliacao da area EAD.",
        },
    ),
    AuditScenario(
        key="imobiliario_linkedin_followup",
        label="Imobiliario | LinkedIn follow-up",
        channel="linkedin_dm",
        step_number=4,
        total_steps=5,
        lead_data={
            "name": "Felipe Rezende",
            "company": "Orbita Urbanismo",
            "job_title": "Diretor Comercial",
            "industry": "Imobiliario e construcao",
            "website": "https://orbita.example",
            "linkedin_url": "https://linkedin.com/in/feliperezende",
        },
        context={
            "site_summary": "Incorporadora focada em lancamentos residenciais de medio padrao com forte captacao digital.",
            "company_news": "A Orbita Urbanismo abriu novo lancamento em Campinas e ampliou equipe de corretores parceiros.",
        },
    ),
    AuditScenario(
        key="seguros_email_first",
        label="Seguros | Email inicial",
        channel="email",
        step_number=1,
        total_steps=5,
        lead_data={
            "name": "Luciana Prado",
            "company": "Atlas Pay",
            "job_title": "CEO Fintech",
            "industry": "Seguros e fintech",
            "website": "https://atlaspay.example",
        },
        context={
            "site_summary": "Fintech B2B com onboarding regulado, analise de risco e operacao multicanal.",
            "company_news": "A Atlas Pay anunciou produto novo para PME com jornada digital de onboarding.",
        },
    ),
    AuditScenario(
        key="agro_linkedin_first",
        label="Agro | LinkedIn inicial",
        channel="linkedin_dm",
        step_number=2,
        total_steps=5,
        previous_channel="linkedin_connect",
        lead_data={
            "name": "Paulo Siqueira",
            "company": "Verde Forte Agro",
            "job_title": "Diretor Agro",
            "industry": "Agro e agroindustria",
            "website": "https://verdeforte.example",
            "linkedin_url": "https://linkedin.com/in/paulosiqueira",
        },
        context={
            "site_summary": "Grupo agroindustrial com multiplas unidades, rastreabilidade e operacao de campo distribuida.",
            "company_news": "A Verde Forte Agro ampliou a estrutura de armazenagem e iniciou novo programa de rastreabilidade.",
        },
    ),
    AuditScenario(
        key="rh_email_first",
        label="RH | Email inicial",
        channel="email",
        step_number=1,
        total_steps=5,
        lead_data={
            "name": "Aline Duarte",
            "company": "Grupo Prisma",
            "job_title": "CHRO",
            "industry": "RH e gestao de pessoas",
            "website": "https://grupoprisma.example",
        },
        context={
            "site_summary": "Grupo corporativo com operacao nacional e agenda de people analytics para o board.",
            "company_news": "O Grupo Prisma abriu vagas para people analytics e reforcou a agenda de lideranca.",
        },
    ),
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Roda auditoria editorial manual do sandbox.")
    parser.add_argument("--provider", type=str, default=None)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_ROOT / "preview" / "sandbox_editorial_audit.md",
    )
    return parser.parse_args()


def _default_model_for(provider: str) -> str:
    return {
        "openai": "gpt-5.4-mini",
        "gemini": "gemini-2.5-flash",
        "anthropic": "claude-3-5-haiku-latest",
        "openrouter": "openai/gpt-5.4-mini",
    }.get(provider, "gpt-5.4-mini")


def _build_lead(lead_data: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name=lead_data["name"],
        company=lead_data.get("company"),
        first_name=str(lead_data["name"]).split(" ")[0],
        last_name=" ".join(str(lead_data["name"]).split(" ")[1:]),
        job_title=lead_data.get("job_title"),
        industry=lead_data.get("industry"),
        company_size=lead_data.get("company_size"),
        website=lead_data.get("website"),
        linkedin_url=lead_data.get("linkedin_url"),
        linkedin_recent_posts_json=lead_data.get("linkedin_recent_posts_json"),
        city=lead_data.get("city"),
        location=lead_data.get("location"),
        segment=lead_data.get("segment"),
    )


def _build_cadence(*, tenant_id: uuid.UUID, provider: str, model: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Sandbox Editorial Audit",
        llm_provider=provider,
        llm_model=model,
        llm_temperature=0.4,
        llm_max_tokens=450,
        target_segment="Operacoes B2B com gargalos manuais e necessidade de integracao entre sistemas.",
        persona_description="Decisores com responsabilidade por operacao, crescimento e previsibilidade.",
        offer_description="Automacao sob medida, integracao de sistemas e IA aplicada em processos criticos.",
        tone_instructions="PT-BR, executivo, direto, sem pitch precoce.",
    )


async def _run_scenario(
    composer: AIComposer,
    scenario: AuditScenario,
    *,
    provider: str,
    model: str,
) -> dict[str, Any]:
    lead: Lead = cast(Lead, _build_lead(scenario.lead_data))
    cadence: Cadence = cast(
        Cadence,
        _build_cadence(tenant_id=lead.tenant_id, provider=provider, model=model),
    )
    _, composition_context = prepare_composer_messages(
        lead=lead,
        channel=scenario.channel,
        step_number=scenario.step_number,
        context=scenario.context,
        total_steps=scenario.total_steps,
        use_voice=scenario.use_voice,
        previous_channel=scenario.previous_channel,
        cadence=cadence,
        step_type=scenario.step_type,
    )

    if scenario.channel == "email":
        subject, body = await composer.compose_email(
            lead=lead,
            step_number=scenario.step_number,
            context=scenario.context,
            cadence=cadence,
            step_type=scenario.step_type,
            total_steps=scenario.total_steps,
            previous_channel=scenario.previous_channel,
        )
        validation = validate_editorial_output(
            composition_context.step_key,
            body,
            subject=subject,
        )
        return {
            "scenario": scenario,
            "composition_context": composition_context,
            "subject": subject,
            "body": body,
            "validation": serialize_editorial_validation(validation),
        }

    body = await composer.compose(
        lead=lead,
        channel=scenario.channel,
        step_number=scenario.step_number,
        context=scenario.context,
        cadence=cadence,
        total_steps=scenario.total_steps,
        use_voice=scenario.use_voice,
        previous_channel=scenario.previous_channel,
        step_type=scenario.step_type,
    )
    validation = validate_editorial_output(composition_context.step_key, body)
    return {
        "scenario": scenario,
        "composition_context": composition_context,
        "subject": None,
        "body": body,
        "validation": serialize_editorial_validation(validation),
    }


def _render_report(
    results: list[dict[str, Any]],
    *,
    provider: str,
    model: str,
) -> str:
    total_hard_failures = sum(result["validation"]["hard_failures"] for result in results)
    total_warnings = sum(result["validation"]["warnings"] for result in results)
    generated_at = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Sandbox Editorial Audit",
        "",
        f"- Gerado em: {generated_at}",
        f"- Provider/model: {provider} / {model}",
        f"- Cenarios: {len(results)}",
        f"- Hard failures: {total_hard_failures}",
        f"- Warnings: {total_warnings}",
        "",
    ]

    for result in results:
        scenario: AuditScenario = result["scenario"]
        context = result["composition_context"]
        validation = result["validation"]
        lines.extend(
            [
                f"## {scenario.label}",
                "",
                f"- Step key: {context.step_key}",
                f"- Metodo: {context.copy_method}",
                f"- Playbook: {context.playbook_sector}/{context.playbook_role} ({context.playbook_match_type})",
                f"- Few-shot: {context.few_shot_key or 'nenhum'} ({context.few_shot_match_type or 'none'})",
                f"- Validacao: ok={validation['ok']} | hard_failures={validation['hard_failures']} | warnings={validation['warnings']}",
            ]
        )
        if result["subject"]:
            lines.extend(["", f"Assunto: {result['subject']}"])
        lines.extend(["", "Mensagem:", "", "```text", str(result["body"]), "```", ""])
        if validation["issues"]:
            lines.append("Issues:")
            for issue in validation["issues"]:
                lines.append(f"- [{issue['severity']}] {issue['code']}: {issue['message']}")
        else:
            lines.append("Issues:")
            lines.append("- Nenhuma")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


async def main() -> None:
    args = _parse_args()
    registry = LLMRegistry(settings=settings, redis=redis_client)
    provider = args.provider or (
        "openai"
        if "openai" in registry.available_providers()
        else registry.available_providers()[0]
    )
    model = args.model or _default_model_for(provider)
    scenarios = _SCENARIOS[: args.limit] if args.limit else _SCENARIOS
    composer = AIComposer(registry)

    try:
        results: list[dict[str, Any]] = []
        for scenario in scenarios:
            print(f"→ Gerando cenário: {scenario.label}...")
            results.append(
                await _run_scenario(
                    composer,
                    scenario,
                    provider=provider,
                    model=model,
                )
            )

        report = _render_report(results, provider=provider, model=model)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"\nRelatorio gerado em: {args.output}")
    finally:
        await registry.aclose()


if __name__ == "__main__":
    asyncio.run(main())
