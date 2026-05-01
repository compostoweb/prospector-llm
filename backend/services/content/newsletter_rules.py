"""
services/content/newsletter_rules.py

Regras + bancos de referencia da Newsletter "Operacao Inteligente".
Transcrito da skill 07-newsletter-linkedin/references/regras-newsletter.md.

Tudo que aqui esta como Final[...] reflete a fonte unica em
backend/docs/composto-web-skills/07-newsletter-linkedin/.
"""

from __future__ import annotations

import re
from typing import Final, TypedDict

# ── Identidade ────────────────────────────────────────────────────────

NEWSLETTER_NAME: Final[str] = "Operação Inteligente"
NEWSLETTER_SUBTITLE: Final[str] = (
    "IA, tecnologia e operações para quem toma decisões reais"
)
NEWSLETTER_FREQUENCY: Final[str] = "biweekly"  # dias 15 e 30
NEWSLETTER_TARGET_WORDS: Final[tuple[int, int]] = (1000, 1400)
NEWSLETTER_READ_TIME_MIN: Final[int] = 10
NEWSLETTER_NOTION_DB_ID: Final[str] = "eb13873b-1273-40c0-b684-1814971c177a"

# ── Estrutura das 5 secoes (ordem importa) ────────────────────────────

SECTION_TEMA_QUINZENA: Final[str] = "tema_quinzena"
SECTION_VISAO_OPINIAO: Final[str] = "visao_opiniao"
SECTION_MINI_TUTORIAL: Final[str] = "mini_tutorial"
SECTION_RADAR: Final[str] = "radar"
SECTION_PERGUNTA: Final[str] = "pergunta"

NEWSLETTER_SECTIONS: Final[tuple[str, ...]] = (
    SECTION_TEMA_QUINZENA,
    SECTION_VISAO_OPINIAO,
    SECTION_MINI_TUTORIAL,
    SECTION_RADAR,
    SECTION_PERGUNTA,
)


class SectionSpec(TypedDict):
    label: str
    weight_pct: int
    target_words: tuple[int, int]
    description: str


NEWSLETTER_SECTION_SPECS: Final[dict[str, SectionSpec]] = {
    SECTION_TEMA_QUINZENA: {
        "label": "① Tema da Quinzena",
        "weight_pct": 40,
        "target_words": (450, 600),
        "description": (
            "Análise aprofundada de 1 caso/padrão real. "
            "Abertura concreta, problema central, o que a maioria faz, "
            "o que funciona, significado para o leitor."
        ),
    },
    SECTION_VISAO_OPINIAO: {
        "label": "② Visão & Opinião",
        "weight_pct": 20,
        "target_words": (170, 240),
        "description": (
            "Ponto de vista direto sobre algo do mercado. "
            "Observação + por que é problema/oportunidade + posição clara."
        ),
    },
    SECTION_MINI_TUTORIAL: {
        "label": "③ Mini Tutorial",
        "weight_pct": 20,
        "target_words": (170, 240),
        "description": (
            "1 coisa prática para aplicar imediatamente. "
            "3-5 passos numerados + exemplo concreto + frase de impacto."
        ),
    },
    SECTION_RADAR: {
        "label": "④ Radar da Quinzena",
        "weight_pct": 10,
        "target_words": (80, 140),
        "description": (
            "🔧 ferramenta + 📊 número + 🔗 leitura (opcional). "
            "Sempre com limitação honesta na ferramenta."
        ),
    },
    SECTION_PERGUNTA: {
        "label": "⑤ Pergunta de Fechamento",
        "weight_pct": 10,
        "target_words": (40, 80),
        "description": (
            "Pergunta pessoal e específica conectada ao tema central. "
            "Convite a responder nos comentários ou DM."
        ),
    },
}

# ── Bancos de referencia ──────────────────────────────────────────────


class ThemeCentral(TypedDict):
    category: str
    title: str


NEWSLETTER_THEMES_CENTRAL: Final[list[ThemeCentral]] = [
    # IA e Tecnologia
    {"category": "IA e Tecnologia", "title": "IA privada vs APIs comerciais: o que ninguém conta sobre seus dados"},
    {"category": "IA e Tecnologia", "title": "Como um agente de IA de verdade funciona (vs chatbot glorificado)"},
    {"category": "IA e Tecnologia", "title": "Ollama na prática: rodando IA local em 20 minutos"},
    {"category": "IA e Tecnologia", "title": "O que é LangChain e quando usar (sem o hype)"},
    {"category": "IA e Tecnologia", "title": "n8n para automação de negócios: por onde começar"},
    # Operações e Processos
    {"category": "Operações e Processos", "title": "O processo que ninguém documentou (e o risco que isso representa)"},
    {"category": "Operações e Processos", "title": "Como mapear onde o dado para numa operação em 1 tarde"},
    {"category": "Operações e Processos", "title": "Por que o fechamento mensal ainda leva dias (e o que resolver primeiro)"},
    {"category": "Operações e Processos", "title": "A planilha que virou sistema: como sair sem trauma"},
    {"category": "Operações e Processos", "title": "O gargalo invisível: retrabalho que não aparece no P&L"},
    # Integração e Sistemas
    {"category": "Integração e Sistemas", "title": "Por onde começar a integrar sistemas sem trocar o ERP"},
    {"category": "Integração e Sistemas", "title": "API, webhook ou ETL: quando usar cada um sem ser técnico"},
    {"category": "Integração e Sistemas", "title": "O custo real de sistemas desconectados (com cálculo)"},
    {"category": "Integração e Sistemas", "title": "Dado em tempo real: o que é, o que não é e por que importa"},
    # Gestão e Negócio
    {"category": "Gestão e Negócio", "title": "Como apresentar um projeto de automação para o CFO"},
    {"category": "Gestão e Negócio", "title": "O que o CEO precisa entender sobre IA antes de contratar"},
    {"category": "Gestão e Negócio", "title": "Como calcular ROI de automação de forma que o board entenda"},
    {"category": "Gestão e Negócio", "title": "Soberania digital: você é dono do software que usa?"},
    {"category": "Gestão e Negócio", "title": "SaaS vs software próprio: a conta que ninguém faz"},
]


NEWSLETTER_VISION_THEMES: Final[list[str]] = [
    # Sobre IA
    "O mercado está chamando de 'agente de IA' qualquer automação com prompt no meio",
    "CEOs estão terceirizando a decisão de IA para o TI — e isso é um erro estratégico",
    "O dado de ontem está tomando a decisão de hoje em 90% das empresas",
    "IA generativa não substitui raciocínio. Ela amplifica quem já pensa bem.",
    "O problema com 'implementar IA' como projeto: tecnologia não é projeto, é camada",
    # Sobre mercado
    "Fornecedores de tecnologia vendem complexidade como diferencial",
    "O consultor que não cobra pelo diagnóstico não confia no próprio diagnóstico",
    "Lock-in disfarçado de parceria: o que avaliar antes de assinar",
    "Por que a maioria dos projetos de transformação digital vira relatório de PowerPoint",
    # Sobre gestão
    "Gestor que delega tecnologia sem entender o problema não está delegando, está abandonando",
    "A cultura de 'funciona assim há 10 anos' é o maior obstáculo à automação",
    "Contratar mais gente para resolver problema de processo é postergação cara",
]


NEWSLETTER_TUTORIAL_BANK: Final[list[str]] = [
    "Como testar o Ollama em 20 minutos no seu computador",
    "Como estruturar um prompt para análise de contrato jurídico",
    "Como mapear fluxo de dado entre sistemas numa tarde",
    "Como calcular o payback de um projeto de automação",
    "Como criar uma automação simples de notificação no n8n",
    "Como avaliar uma ferramenta de IA antes de contratar (5 perguntas)",
    "Como identificar o gargalo real numa operação (método de 3 perguntas)",
    "Como montar um dashboard de custo operacional no Google Sheets",
]


class ToolEntry(TypedDict):
    name: str
    what: str
    when: str
    limitation: str


NEWSLETTER_TOOLS_BANK: Final[list[ToolEntry]] = [
    {
        "name": "Ollama",
        "what": "Roda modelos de IA localmente",
        "when": "Dados sensíveis, privacidade",
        "limitation": "Modelos inferiores aos comerciais em raciocínio complexo",
    },
    {
        "name": "n8n",
        "what": "Automação e integração de sistemas",
        "when": "Orquestração de fluxos sem código intensivo",
        "limitation": "Curva de aprendizado para fluxos complexos",
    },
    {
        "name": "LangChain",
        "what": "Framework para agentes de IA",
        "when": "Construir agentes com múltiplas ferramentas",
        "limitation": "Overhead para casos simples",
    },
    {
        "name": "Supabase",
        "what": "Banco de dados com API automática",
        "when": "Backend rápido para projetos de dados",
        "limitation": "Não substitui PostgreSQL gerenciado em produção crítica",
    },
    {
        "name": "Flowise",
        "what": "Interface visual para agentes IA",
        "when": "Prototipagem rápida de agentes",
        "limitation": "Limitações em customização avançada",
    },
    {
        "name": "Directus",
        "what": "CMS headless com API",
        "when": "Gestão de conteúdo e dados sem código",
        "limitation": "Mais complexo que alternativas simples",
    },
    {
        "name": "Baserow",
        "what": "Planilha com banco de dados",
        "when": "Substituir planilhas que viraram sistemas",
        "limitation": "Menos recursos que Airtable",
    },
    {
        "name": "Grafana",
        "what": "Dashboards e observabilidade",
        "when": "Monitorar sistemas e operações em tempo real",
        "limitation": "Requer configuração técnica inicial",
    },
]


class DataPoint(TypedDict):
    fact: str
    source: str
    context: str


NEWSLETTER_DATA_BANK: Final[list[DataPoint]] = [
    {
        "fact": "67% dos projetos de transformação digital falham",
        "source": "McKinsey",
        "context": "Principal fator: falta de clareza sobre o problema",
    },
    {
        "fact": "43% das empresas de médio porte operam com 6+ sistemas desconectados",
        "source": "Gartner",
        "context": "Custo não aparece no P&L, aparece nas decisões erradas",
    },
    {
        "fact": "35% do gasto em cloud é desperdiçado",
        "source": "Flexera",
        "context": "Não por falta de dinheiro, por falta de visibilidade",
    },
    {
        "fact": "ROI médio de automação bem feita: 250% em 18 meses",
        "source": "Forrester",
        "context": "O problema é o 'bem feita'",
    },
    {
        "fact": "70% do tempo de analistas financeiros vai para coleta e formatação de dados",
        "source": "Deloitte",
        "context": "Sobra 30% para análise real",
    },
    {
        "fact": "Custo médio de retrabalho: 20-30% do custo total do projeto",
        "source": "PMI",
        "context": "Raramente contabilizado antes do projeto",
    },
]


NEWSLETTER_OPENING_TEMPLATES: Final[list[dict[str, str]]] = [
    {
        "kind": "case_diagnostico",
        "template": (
            "Nos últimos [período], entrei em [número] de operações para diagnosticar "
            "[problema]. Em [proporção] delas, o cliente chegou com a mesma frase: "
            "[frase comum]."
        ),
    },
    {
        "kind": "padrao_recorrente",
        "template": (
            "[Padrão] aparece em quase toda empresa que tenta [ação]. "
            "Não é coincidência. É uma consequência de [causa]."
        ),
    },
    {
        "kind": "tecnico_negocio",
        "template": (
            "Toda vez que [situação comum], a primeira pergunta que faço é: "
            "[pergunta que revela o problema real]."
        ),
    },
    {
        "kind": "tendencia",
        "template": (
            "Nos últimos meses, [tendência observada]. O problema não é a tendência "
            "em si. É [o que a maioria não percebe]."
        ),
    },
]


# Whitelist de dominios para a secao Radar (link de leitura).
NEWSLETTER_LINK_WHITELIST: Final[tuple[str, ...]] = (
    "mitsloan.mit.edu",
    "sloanreview.mit.edu",
    "hbr.org",
    "mckinsey.com",
    "gartner.com",
    "forrester.com",
    "flexera.com",
    "deloitte.com",
    "pmi.org",
    # docs oficiais comuns
    "ollama.com",
    "n8n.io",
    "langchain.com",
    "supabase.com",
    "flowiseai.com",
    "directus.io",
    "baserow.io",
    "grafana.com",
)


# ── Calendario / publicadas ───────────────────────────────────────────


class PublishedEdition(TypedDict):
    edition: int
    date: str
    theme_central: str
    vision_theme: str
    tutorial: str
    radar_tool: str
    radar_data: str


NEWSLETTER_PUBLISHED_HISTORY: Final[list[PublishedEdition]] = [
    {
        "edition": 1,
        "date": "30/04/2026",
        "theme_central": "Por que a maioria dos projetos de IA falha antes de ir para produção",
        "vision_theme": "O mercado está chamando de 'agente de IA' qualquer automação com prompt no meio",
        "tutorial": "Como calcular o custo real de um processo manual em 15 minutos",
        "radar_tool": "Ollama",
        "radar_data": "67% dos projetos de transformação digital falham (McKinsey)",
    },
]


class PlannedEdition(TypedDict):
    edition: int
    date: str
    theme_central: str


NEWSLETTER_PLANNED_EDITIONS: Final[list[PlannedEdition]] = [
    {"edition": 2, "date": "15/05/2026", "theme_central": "IA privada: quando faz sentido rodar modelos locais na empresa"},
    {"edition": 3, "date": "30/05/2026", "theme_central": "O problema que o ERP não resolve (e o que resolve)"},
    {"edition": 4, "date": "15/06/2026", "theme_central": "Como calcular o custo real de um processo manual"},
    {"edition": 5, "date": "30/06/2026", "theme_central": "Agentes de IA no atendimento: o que funciona, o que não funciona"},
    {"edition": 6, "date": "15/07/2026", "theme_central": "O que aprendi diagnosticando operações em 6 setores"},
]


# ── Palavras proibidas ────────────────────────────────────────────────

NEWSLETTER_FORBIDDEN_WORDS: Final[list[str]] = [
    "inovação",
    "inovador",
    "inovar",
    "otimização",
    "gestão inteligente",
    "transformação digital",
    "solução robusta",
    "faz sentido?",
    "travessão",
    "—",  # caractere de travessão literal
]


# ── Validacao ─────────────────────────────────────────────────────────


def _count_words(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def _domain_of(url: str) -> str:
    m = re.match(r"https?://([^/]+)/?", url.strip(), flags=re.IGNORECASE)
    if not m:
        return ""
    host = m.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def validate_newsletter_section(section_id: str, text: str) -> list[str]:
    """
    Valida uma secao individual.

    Retorna lista de violations + warnings (warnings prefixadas com 'Aviso:').
    """
    issues: list[str] = []

    if section_id not in NEWSLETTER_SECTION_SPECS:
        return [f"Secao desconhecida: {section_id}"]

    spec = NEWSLETTER_SECTION_SPECS[section_id]

    # Palavras proibidas (case-insensitive)
    lower = text.lower()
    for word in NEWSLETTER_FORBIDDEN_WORDS:
        # "—" e literal; demais comparados em lower
        if word == "—":
            if "—" in text:
                issues.append("Palavra/expressao proibida encontrada: travessao '—'.")
            continue
        if word.lower() in lower:
            issues.append(f"Palavra/expressao proibida encontrada: '{word}'.")

    # Range de palavras (warning, nao violation)
    words = _count_words(text)
    target_min, target_max = spec["target_words"]
    if words < target_min or words > target_max:
        issues.append(
            f"Aviso: secao '{section_id}' com {words} palavras fora do range "
            f"esperado ({target_min}-{target_max})."
        )

    return issues


def validate_radar_section(payload: dict) -> list[str]:
    """
    Valida secao Radar especificamente:
    - Ferramenta deve ter 'limitation' nao-vazia
    - Link (se presente) deve estar na whitelist
    """
    issues: list[str] = []

    tool = payload.get("tool")
    if not isinstance(tool, dict):
        issues.append("Radar: secao 'tool' ausente ou invalida.")
    else:
        limitation = (tool.get("limitation") or "").strip()
        if not limitation:
            issues.append("Radar: ferramenta sem 'limitation' honesta.")

    reading = payload.get("reading")
    if isinstance(reading, dict):
        url = (reading.get("url") or "").strip()
        if url:
            domain = _domain_of(url)
            if domain and domain not in NEWSLETTER_LINK_WHITELIST:
                issues.append(
                    f"Radar: dominio fora da whitelist ('{domain}'). "
                    f"Permitido apenas: {', '.join(NEWSLETTER_LINK_WHITELIST)}."
                )

    return issues


def validate_pergunta_section(text: str) -> list[str]:
    """
    Pergunta de fechamento NAO pode ser generica.
    Heuristica: deve mencionar 'sua operacao'/'sua empresa'/'seu time'/etc.
    """
    issues: list[str] = []

    lower = text.lower()
    personal_markers = [
        "sua operação",
        "sua operacao",
        "sua empresa",
        "seu time",
        "seu negócio",
        "seu negocio",
        "seu processo",
        "sua área",
        "sua area",
    ]
    if not any(marker in lower for marker in personal_markers):
        issues.append(
            "Aviso: pergunta sem referencia a operacao/empresa do leitor "
            "(considere especifica-la mais)."
        )
    return issues


def validate_full_newsletter(payload: dict) -> list[str]:
    """
    Valida estrutura completa de uma newsletter.
    Espera payload com chaves:
      title, subtitle, opening_line,
      section_tema_quinzena, section_visao_opiniao,
      section_mini_tutorial, section_radar, section_pergunta
    """
    issues: list[str] = []

    if not (payload.get("title") or "").strip():
        issues.append("Title ausente.")
    if not (payload.get("opening_line") or "").strip():
        issues.append("Opening line ausente.")

    # Secoes textuais
    for section_id, key in [
        (SECTION_TEMA_QUINZENA, "section_tema_quinzena"),
        (SECTION_VISAO_OPINIAO, "section_visao_opiniao"),
    ]:
        section = payload.get(key)
        if not isinstance(section, dict):
            issues.append(f"Secao '{section_id}' ausente.")
            continue
        body = section.get("body") or ""
        issues.extend(validate_newsletter_section(section_id, body))

    # Mini tutorial: corpo formado por steps + example + impact
    tutorial = payload.get("section_mini_tutorial")
    if not isinstance(tutorial, dict):
        issues.append(f"Secao '{SECTION_MINI_TUTORIAL}' ausente.")
    else:
        steps = tutorial.get("steps") or []
        if not isinstance(steps, list) or len(steps) < 3:
            issues.append("Mini tutorial: deve ter pelo menos 3 passos.")
        combined = "\n".join(
            [
                str(tutorial.get("heading") or ""),
                "\n".join(str(s) for s in steps if isinstance(s, str)),
                str(tutorial.get("example") or ""),
                str(tutorial.get("impact") or ""),
            ]
        )
        issues.extend(validate_newsletter_section(SECTION_MINI_TUTORIAL, combined))

    # Radar
    radar = payload.get("section_radar")
    if not isinstance(radar, dict):
        issues.append(f"Secao '{SECTION_RADAR}' ausente.")
    else:
        issues.extend(validate_radar_section(radar))

    # Pergunta
    pergunta = payload.get("section_pergunta")
    if isinstance(pergunta, str):
        pergunta_text = pergunta
    elif isinstance(pergunta, dict):
        pergunta_text = pergunta.get("body") or pergunta.get("text") or ""
    else:
        pergunta_text = ""
    if not pergunta_text.strip():
        issues.append(f"Secao '{SECTION_PERGUNTA}' ausente.")
    else:
        issues.extend(validate_newsletter_section(SECTION_PERGUNTA, pergunta_text))
        issues.extend(validate_pergunta_section(pergunta_text))

    return issues
