"""
services/sector_templates.py

Few-shot examples de mensagens reais da Composto Web por setor, cargo e canal.
Usados como bloco "EXEMPLO DE REFERÊNCIA" injetado no user prompt do AIComposer,
orientando o LLM em tom, estrutura e ângulo de dor sem restringir a personalização.

Fonte: docs/composto-web-skills/03-prospeccao-linkedin/ + 04-coldmail/
Cobertura: 9 setores × até 2 cargos × 2 canais (linkedin / email)

Injeção no prompt via:
    from services.sector_templates import get_few_shot_example
    block = get_few_shot_example(sector, role, channel, step_key)
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Estrutura de dados ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FewShotExample:
    sector: str
    role: str
    channel: str           # "linkedin" | "email"
    step_type: str         # "first" | "followup" | "breakup"
    method: str            # AIRE | DIS | DPO | BINÁRIO | INSIGHT
    subject: str           # email only — vazio para linkedin
    message: str


# ── Banco de exemplos ──────────────────────────────────────────────────────────
# Chave: (sector, role, channel, step_type)
# role pode ser genérico (ex: "ceo") para abranger variações de cargo detectadas

_EXAMPLES: dict[tuple[str, str, str, str], FewShotExample] = {

    # ══════════════════════════════════════════════════════════════════════════
    # SAÚDE / CLÍNICAS
    # ══════════════════════════════════════════════════════════════════════════

    ("saude", "diretor_clinica", "email", "first"): FewShotExample(
        sector="saude", role="diretor_clinica",
        channel="email", step_type="first", method="DIS",
        subject="Sua recepção ainda agenda manualmente?",
        message=(
            "Oi [Nome],\n\n"
            "Clínicas com alto volume de atendimento geralmente têm a mesma situação: "
            "recepcionistas sobrecarregadas respondendo as mesmas perguntas no WhatsApp, "
            "agenda com buracos por no-show e pacientes que desistem de agendar porque "
            "ninguém atende fora do horário comercial.\n\n"
            "O resultado aparece no faturamento: horários vagos que não voltam, equipe "
            "travada no operacional e paciente que vai para o concorrente que atende no "
            "domingo às 22h.\n\n"
            "Nós construímos um agente de IA no WhatsApp para uma clínica médica que "
            "integra direto no ERP. Hoje a triagem e o agendamento acontecem "
            "automaticamente, 24 horas, sem depender da recepcionista.\n\n"
            "[Nome], isso resolve um problema real na [Clínica] hoje?"
        ),
    ),

    ("saude", "diretor_clinica", "linkedin", "first"): FewShotExample(
        sector="saude", role="diretor_clinica",
        channel="linkedin", step_type="first", method="DIS",
        subject="",
        message=(
            "Fala, [Nome]. Trabalho com automação de atendimento para clínicas via "
            "WhatsApp com IA. Vi seu perfil na [Clínica] e tenho algo relevante pra "
            "compartilhar."
        ),
    ),

    ("saude", "diretor_clinica", "linkedin", "followup"): FewShotExample(
        sector="saude", role="diretor_clinica",
        channel="linkedin", step_type="followup", method="BINÁRIO",
        subject="",
        message=(
            "Fala [Nome], só um ângulo diferente. Além do agendamento, nossos agentes "
            "de IA para clínicas também fazem confirmação automática de consulta, "
            "redução de no-show e coleta de dados do paciente antes da consulta. Tudo "
            "integrado ao que vocês já usam, sem trocar sistema. Vale uma conversa rápida?"
        ),
    ),

    ("saude", "gerente_administrativo", "email", "first"): FewShotExample(
        sector="saude", role="gerente_administrativo",
        channel="email", step_type="first", method="DPO",
        subject="Recepção sobrecarregada ou atendimento 24h sem contratar mais ninguém",
        message=(
            "Oi [Nome],\n\n"
            "A rotina de uma clínica sem automação de atendimento é sempre a mesma: "
            "recepcionistas respondendo WhatsApp fora do horário, pacientes sem resposta "
            "que vão para o concorrente, agenda com falhas por confirmação manual e "
            "no-show que ninguém preveniu.\n\n"
            "Com um agente de IA no WhatsApp integrado ao ERP da [Clínica], triagem e "
            "agendamento acontecem automaticamente, 24 horas por dia. A recepção para de "
            "ser um gargalo e passa a focar no que precisa de atenção humana de verdade.\n\n"
            "Posso te mostrar como isso funcionou na prática em uma clínica que atendemos?"
        ),
    ),

    ("saude", "gerente_administrativo", "linkedin", "followup"): FewShotExample(
        sector="saude", role="gerente_administrativo",
        channel="linkedin", step_type="followup", method="INSIGHT",
        subject="",
        message=(
            "Fala [Nome], clínicas sem confirmação automática de consulta têm índice de "
            "no-show entre 20% e 30% da agenda. Para uma agenda cheia, isso é "
            "faturamento perdido que não volta. A automação de confirmação via WhatsApp "
            "com IA resolve exatamente isso, integrada ao sistema que vocês já usam. "
            "Vocês já tentaram resolver o no-show de alguma forma?"
        ),
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # JURÍDICO / ADVOCACIA
    # ══════════════════════════════════════════════════════════════════════════

    ("juridico", "socio_advocacia", "email", "first"): FewShotExample(
        sector="juridico", role="socio_advocacia",
        channel="email", step_type="first", method="AIRE",
        subject="IA jurídica que não envia dados para fora do escritório",
        message=(
            "Oi [Nome],\n\n"
            "Escritórios que já tentaram usar ferramentas de IA como ChatGPT para "
            "análise de contratos geralmente esbarram no mesmo problema: colocar dados "
            "sensíveis de clientes em uma API externa é um risco jurídico que o "
            "escritório não pode assumir.\n\n"
            "A consequência prática é que a IA fica restrita a tarefas genéricas e os "
            "advogados continuam fazendo manualmente o que poderia ser automatizado com "
            "segurança.\n\n"
            "Nós implementamos modelos de IA privados (Ollama + Llama/Mistral) que "
            "rodam integralmente na infraestrutura do escritório. Nenhum dado sai do seu "
            "ambiente. A IA processa contratos e gera minutas com a mesma qualidade dos "
            "modelos comerciais, sem o risco.\n\n"
            "Isso resolve uma preocupação real no [Escritório] hoje?"
        ),
    ),

    ("juridico", "socio_advocacia", "linkedin", "first"): FewShotExample(
        sector="juridico", role="socio_advocacia",
        channel="linkedin", step_type="first", method="DIS",
        subject="",
        message=(
            "Fala, [Nome]. Trabalho com engenharia de soluções para escritórios de "
            "advocacia, IA privada e automação de documentos. Vi seu perfil no [Escritório]."
        ),
    ),

    ("juridico", "diretor_juridico", "email", "first"): FewShotExample(
        sector="juridico", role="diretor_juridico",
        channel="email", step_type="first", method="DIS",
        subject="Contratos críticos da [Empresa] sem controle centralizado",
        message=(
            "Oi [Nome],\n\n"
            "Departamentos jurídicos corporativos geralmente têm contratos espalhados em "
            "e-mail, servidor local e sistemas distintos, sem controle real de "
            "vencimentos e renovações automáticas. Quando alguém cobra, a busca vira "
            "processo manual que consome horas.\n\n"
            "Um contrato que vence silenciosamente pode comprometer uma operação inteira. "
            "E a pressão cai sobre o jurídico, que não tinha como prever o problema num "
            "sistema descentralizado.\n\n"
            "Nós construímos sistemas de gestão contratual que rodam na infraestrutura "
            "da [Empresa], com IA privada para análise de cláusulas e alertas automáticos "
            "de vencimento. Nenhum dado de contrato sai do seu ambiente.\n\n"
            "Isso resolve uma dor real no jurídico de vocês hoje?"
        ),
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # FINANCEIRO / CONTABILIDADE
    # ══════════════════════════════════════════════════════════════════════════

    ("financeiro", "cfo", "email", "first"): FewShotExample(
        sector="financeiro", role="cfo",
        channel="email", step_type="first", method="DPO",
        subject="Fechamento mensal da [Empresa]: de dias para horas sem trocar o ERP",
        message=(
            "Oi [Nome],\n\n"
            "CFOs em empresas de médio porte geralmente vivem a mesma situação no "
            "fechamento: consolidação manual de ERP, bancos e planilhas, equipe sob "
            "pressão de prazo e sempre aquela incerteza de se o número está certo antes "
            "de apresentar para o board.\n\n"
            "Com a camada de integração certa entre os sistemas da [Empresa], o "
            "fechamento mensal cai de dias para horas. Conciliação automática, dado em "
            "tempo real, trilha de auditoria completa. A equipe para de montar o relatório "
            "e começa a analisá-lo.\n\n"
            "Posso te mostrar como isso funciona na prática?"
        ),
    ),

    ("financeiro", "cfo", "linkedin", "first"): FewShotExample(
        sector="financeiro", role="cfo",
        channel="linkedin", step_type="first", method="DIS",
        subject="",
        message=(
            "Fala, [Nome]. Trabalho com automação de processos financeiros e integração "
            "de sistemas para empresas em crescimento. Vi seu perfil na [Empresa]."
        ),
    ),

    ("financeiro", "cfo", "linkedin", "followup"): FewShotExample(
        sector="financeiro", role="cfo",
        channel="linkedin", step_type="followup", method="BINÁRIO",
        subject="",
        message=(
            "Oi [Nome], seria útil ter visibilidade do fluxo de caixa em tempo real, "
            "integrado a todos os sistemas da [Empresa], sem depender de relatório "
            "manual do analista?"
        ),
    ),

    ("financeiro", "coo", "email", "first"): FewShotExample(
        sector="financeiro", role="coo",
        channel="email", step_type="first", method="AIRE",
        subject="Operação que cresceu mas a eficiência não acompanhou",
        message=(
            "Oi [Nome],\n\n"
            "Empresas que crescem rápido chegam num ponto onde o volume novo não cabe "
            "mais nos processos antigos. O que funcionava com 50 pessoas começa a "
            "engasgar com 200.\n\n"
            "O custo aparece de formas diferentes: retrabalho que ninguém contabiliza, "
            "dado que chega tarde para a decisão, dependência de pessoas específicas que "
            "carregam o processo na cabeça.\n\n"
            "Nós entramos nos processos de cada departamento como parceiros. Mapeamos "
            "onde o dado para, calculamos o custo real do problema e construímos a "
            "automação específica. Sem trocar o ERP. O que construímos fica com a "
            "propriedade intelectual da [Empresa].\n\n"
            "Isso se aplica a algum ponto que está travando a operação de vocês hoje?"
        ),
    ),

    ("financeiro", "contador", "email", "first"): FewShotExample(
        sector="financeiro", role="contador",
        channel="email", step_type="first", method="DIS",
        subject="Obrigações acessórias manuais: o risco que cresce com a carteira",
        message=(
            "Oi [Nome],\n\n"
            "Escritórios contábeis em crescimento geralmente chegam num ponto crítico: "
            "a carteira aumentou, mas o processo de geração e envio de obrigações "
            "acessórias ainda depende de analistas fazendo operações manuais repetitivas "
            "em cada cliente.\n\n"
            "Com volume alto e processo manual, o risco de erro e multa cresce "
            "proporcionalmente à carteira. E o analista que poderia estar fazendo análise "
            "real passa o dia operando sistemas.\n\n"
            "Nós automatizamos os processos de maior repetição em escritórios contábeis: "
            "geração de SPED, EFD e NFe, validação automática antes do envio. O resultado "
            "é menos erro, menos retrabalho e uma equipe que escala sem crescer no mesmo "
            "ritmo.\n\n"
            "Isso resolve um gargalo real no [Escritório] hoje?"
        ),
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # EMPRESAS DE TI
    # ══════════════════════════════════════════════════════════════════════════

    ("ti", "ceo_cto_ti", "email", "first"): FewShotExample(
        sector="ti", role="ceo_cto_ti",
        channel="email", step_type="first", method="DIS",
        subject="Engenheiro sênior resolvendo ticket de suporte: o custo invisível",
        message=(
            "Oi [Nome],\n\n"
            "Empresas de TI em crescimento chegam num ponto onde o time de engenharia "
            "passa mais tempo em suporte interno, onboarding de clientes e geração de "
            "relatórios do que desenvolvendo produto.\n\n"
            "Cada hora de engenheiro sênior gasta em tarefa operacional é uma feature "
            "que não foi desenvolvida e uma vantagem competitiva que ficou no papel.\n\n"
            "Nós construímos as automações de CS, onboarding e suporte que liberam o "
            "time de engenharia para focar no que gera valor: produto. E o que "
            "construímos fica com a propriedade intelectual da [Empresa], sem dependência "
            "de plataforma terceira.\n\n"
            "Isso se aplica ao momento da [Empresa] hoje?"
        ),
    ),

    ("ti", "ceo_cto_ti", "linkedin", "first"): FewShotExample(
        sector="ti", role="ceo_cto_ti",
        channel="linkedin", step_type="first", method="DIS",
        subject="",
        message=(
            "Fala, [Nome]. Trabalho com engenharia de soluções e automação para "
            "empresas de tecnologia. Vi seu perfil na [Empresa] e tenho algo relevante."
        ),
    ),

    ("ti", "ceo_cto_ti", "linkedin", "followup"): FewShotExample(
        sector="ti", role="ceo_cto_ti",
        channel="linkedin", step_type="followup", method="BINÁRIO",
        subject="",
        message=(
            "Fala [Nome], além da capacidade de produto, outro ponto que aparece muito "
            "em empresas de TI em crescimento: onboarding de clientes que escala sem "
            "crescer linearmente o time de CS. Construímos automações de health score e "
            "onboarding que permitem servir mais clientes sem aumentar proporcionalmente "
            "a equipe. Isso é relevante para o estágio da [Empresa] agora?"
        ),
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # INDÚSTRIA / LOGÍSTICA
    # ══════════════════════════════════════════════════════════════════════════

    ("industria", "diretor_industrial", "linkedin", "first"): FewShotExample(
        sector="industria", role="diretor_industrial",
        channel="linkedin", step_type="first", method="DIS",
        subject="",
        message=(
            "Fala, [Nome]. Trabalho com engenharia de soluções para operações "
            "industriais. Automação de processos, integração de sistemas e visibilidade "
            "em tempo real. Vi seu perfil na [Empresa]."
        ),
    ),

    ("industria", "diretor_industrial", "linkedin", "followup"): FewShotExample(
        sector="industria", role="diretor_industrial",
        channel="linkedin", step_type="followup", method="INSIGHT",
        subject="",
        message=(
            "Fala [Nome], além da visibilidade operacional, outro ponto crítico em "
            "indústrias em crescimento: PCP com dado em tempo real. Planejamento baseado "
            "em dados de ontem garante erro embutido no processo. Construímos a "
            "integração entre ERP e chão de fábrica para que o planejador trabalhe com "
            "estoque e capacidade atualizados ao minuto. Isso é relevante para vocês?"
        ),
    ),

    ("industria", "diretor_industrial", "email", "first"): FewShotExample(
        sector="industria", role="diretor_industrial",
        channel="email", step_type="first", method="DIS",
        subject="Chão de fábrica sem visibilidade em tempo real",
        message=(
            "Oi [Nome],\n\n"
            "Operações industriais em crescimento chegam num ponto comum: o que "
            "funcionava com menor volume começa a gerar gargalos que aparecem horas "
            "depois de já terem custado produção.\n\n"
            "Quando algo para na linha de produção, o gestor descobre pelo relatório do "
            "dia seguinte. O custo já foi embora e a correção acontece tarde demais.\n\n"
            "Nós construímos a torre de controle industrial: monitoramento em tempo real "
            "do chão de fábrica com alertas automáticos, integrado ao seu ERP, sob medida "
            "para a especificidade da sua operação.\n\n"
            "Isso resolve um problema real na [Empresa] hoje?"
        ),
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # AGÊNCIAS DE MARKETING
    # ══════════════════════════════════════════════════════════════════════════

    ("agencia", "ceo_agencia", "email", "first"): FewShotExample(
        sector="agencia", role="ceo_agencia",
        channel="email", step_type="first", method="DPO",
        subject="Sua agência cresce, mas a margem não acompanha?",
        message=(
            "Oi [Nome],\n\n"
            "Agências que crescem em clientes geralmente veem a margem cair junto: mais "
            "cliente é mais reunião de alinhamento, mais relatório manual, mais gestão de "
            "aprovação de conteúdo, mais gente para operacionalizar o que deveria ser "
            "automático.\n\n"
            "Com os processos operacionais certos automatizados, cada cliente novo "
            "adiciona receita sem adicionar proporcionalmente overhead de gestão. O time "
            "criativo foca em estratégia e criatividade. Relatórios, aprovações e "
            "monitoramento de campanhas acontecem sozinhos.\n\n"
            "Posso te mostrar como isso funciona na prática?"
        ),
    ),

    ("agencia", "ceo_agencia", "linkedin", "first"): FewShotExample(
        sector="agencia", role="ceo_agencia",
        channel="linkedin", step_type="first", method="DPO",
        subject="",
        message=(
            "Fala, [Nome]. Trabalho com automação de processos operacionais para "
            "agências, liberando o time criativo do trabalho manual. Vi seu perfil na "
            "[Agência]."
        ),
    ),

    ("agencia", "ceo_agencia", "linkedin", "followup"): FewShotExample(
        sector="agencia", role="ceo_agencia",
        channel="linkedin", step_type="followup", method="DPO",
        subject="",
        message=(
            "Fala [Nome], agências que crescem em clientes geralmente veem a margem "
            "cair junto porque cada cliente novo traz mais reunião, mais relatório manual, "
            "mais aprovação de conteúdo. O time criativo que deveria estar em estratégia "
            "fica no operacional. Com os processos certos automatizados, mais cliente "
            "vira mais receita sem virar mais overhead. Isso é um gargalo real na "
            "[Agência] hoje?"
        ),
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # MARKETING INTERNO (DEPTOS DE MARKETING)
    # ══════════════════════════════════════════════════════════════════════════

    ("marketing", "cmo", "email", "first"): FewShotExample(
        sector="marketing", role="cmo",
        channel="email", step_type="first", method="AIRE",
        subject="Os dados de clientes da [Empresa] chegam tarde para as campanhas?",
        message=(
            "Oi [Nome],\n\n"
            "Times de marketing em empresas de médio e grande porte geralmente têm o "
            "mesmo problema: dados de clientes espalhados entre CRM, e-commerce, "
            "plataforma de e-mail e canais de atendimento, sem integração em tempo real. "
            "A segmentação das campanhas acaba sendo baseada em dados defasados ou em "
            "intuição.\n\n"
            "Com dado de comportamento fragmentado, as campanhas perdem precisão, o ROI "
            "é difícil de medir e oportunidades de recompra e retenção ficam na mesa por "
            "falta de visibilidade de quem está pronto para comprar.\n\n"
            "Nós construímos a camada de integração que une todas as fontes de dado de "
            "cliente em uma visão única, alimentando o CRM e as campanhas "
            "automaticamente com segmentação comportamental real. O que construímos fica "
            "com a propriedade intelectual da [Empresa], sem dependência de plataforma "
            "de CDP terceira.\n\n"
            "Isso resolve um problema real no marketing da [Empresa] hoje?"
        ),
    ),

    ("marketing", "gerente_marketing", "email", "first"): FewShotExample(
        sector="marketing", role="gerente_marketing",
        channel="email", step_type="first", method="DIS",
        subject="CRM que se alimenta sozinho na [Empresa]",
        message=(
            "Oi [Nome],\n\n"
            "Times de marketing com múltiplos canais de captação geralmente têm o CRM "
            "como o elo mais fraco: depende da equipe alimentar manualmente, fica sempre "
            "desatualizado e não reflete o histórico real de cada lead.\n\n"
            "Sem histórico confiável de comportamento, cada campanha começa do zero. "
            "Oportunidades de upsell e retenção passam despercebidas. E o gestor não "
            "consegue atribuir resultado de campanha com precisão.\n\n"
            "Nós construímos a integração entre seus canais de captação e o CRM, criando "
            "o lead e registrando cada interação automaticamente, sem depender da equipe "
            "digitar nada. O dado chega limpo, enriquecido e em tempo real.\n\n"
            "Isso resolve um gargalo real no marketing da [Empresa] hoje?"
        ),
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # MENSAGENS DE BREAKUP (cross-setor — tom padrão da Composto Web)
    # ══════════════════════════════════════════════════════════════════════════

    ("saude", "diretor_clinica", "linkedin", "breakup"): FewShotExample(
        sector="saude", role="diretor_clinica",
        channel="linkedin", step_type="breakup", method="DPO",
        subject="",
        message=(
            "Oi [Nome], entendo que pode não ser o momento. Não vou mais entrar em contato. "
            "Se a pauta de automação de atendimento ou IA no WhatsApp surgir, "
            "compostoweb.com.br ou me chame. Abraço, Adriano"
        ),
    ),

    ("financeiro", "cfo", "linkedin", "breakup"): FewShotExample(
        sector="financeiro", role="cfo",
        channel="linkedin", step_type="breakup", method="DPO",
        subject="",
        message=(
            "Oi [Nome], entendo que pode não ser o momento. Não vou mais entrar em contato. "
            "Se a pauta de automação financeira aparecer, compostoweb.com.br ou me chame. "
            "Abraço, Adriano"
        ),
    ),

    ("ti", "ceo_cto_ti", "linkedin", "breakup"): FewShotExample(
        sector="ti", role="ceo_cto_ti",
        channel="linkedin", step_type="breakup", method="DPO",
        subject="",
        message=(
            "Oi [Nome], não vou mais entrar em contato. Se a pauta de automação ou "
            "capacidade técnica surgir, compostoweb.com.br ou me chame. Abraço, Adriano"
        ),
    ),

    ("agencia", "ceo_agencia", "linkedin", "breakup"): FewShotExample(
        sector="agencia", role="ceo_agencia",
        channel="linkedin", step_type="breakup", method="DPO",
        subject="",
        message=(
            "Oi [Nome], entendo que pode não ser o momento. Se a pauta de automação "
            "operacional na agência surgir, compostoweb.com.br ou me chame. Abraço, Adriano"
        ),
    ),
}


# ── Mapeamento de fallback: cargo → cargo genérico ────────────────────────────
# Quando não há exemplo exato para o cargo, tenta cargos mais genéricos do setor.

_ROLE_FALLBACK: dict[str, list[str]] = {
    # Saúde
    "gerente_administrativo": ["diretor_clinica"],
    "ti_saude": ["diretor_clinica"],
    "medico_socio": ["diretor_clinica"],
    # Jurídico
    "gestor_juridico": ["socio_advocacia"],
    "advogado": ["socio_advocacia"],
    "diretor_juridico": ["diretor_juridico", "socio_advocacia"],
    # Financeiro
    "controller": ["cfo"],
    "analista": ["cfo"],
    "contador": ["contador", "cfo"],
    # Indústria
    "gerente_logistica": ["diretor_industrial"],
    "ti_industria": ["diretor_industrial"],
    "pcp": ["diretor_industrial"],
    # TI
    "cs_ti": ["ceo_cto_ti"],
    "devops_ti": ["ceo_cto_ti"],
    # Agência
    "conteudo_agencia": ["ceo_agencia"],
    # Marketing
    "gerente_crm": ["gerente_marketing", "cmo"],
    # RH (sem templates específicos — usa None)
    "chro": [],
    "recrutamento": [],
    "dp": [],
    "td": [],
    # Varejo (sem templates específicos — usa None)
    "ceo_ecommerce": [],
    "gerente_operacoes": [],
    "gerente_crm": [],
    "sac": [],
    # Educação (sem templates específicos — usa None)
    "diretor_academico": [],
    "financeiro_educacao": [],
    "coordenador_pedagogico": [],
}


# ── Função principal de busca ─────────────────────────────────────────────────


def get_few_shot_example(
    sector: str | None,
    role: str | None,
    channel: str,
    step_key: str,
) -> str:
    """Retorna o bloco de few-shot para injeção no user prompt.

    Args:
        sector: Chave de setor de outreach_playbook (ex: "financeiro")
        role: Chave de cargo de outreach_playbook (ex: "cfo")
        channel: "linkedin" | "email"
        step_key: resolve_step_key() output (ex: "email_first", "linkedin_dm")

    Returns:
        String formatada com o exemplo, ou string vazia se não houver match.
    """
    if not sector:
        return ""

    step_type = _step_key_to_type(step_key)
    if not step_type:
        return ""

    norm_channel = "email" if "email" in channel else "linkedin"

    example = _find_example(sector, role, norm_channel, step_type)
    if not example:
        return ""

    return _format_example(example)


def _step_key_to_type(step_key: str) -> str | None:
    """Converte step_key de resolve_step_key() para tipo simplificado."""
    if not step_key:
        return None
    if "breakup" in step_key:
        return "breakup"
    # followup = qualquer step com número > 1 ou que contenha followup
    if "followup" in step_key:
        return "followup"
    if "first" in step_key:
        return "first"
    # linkedin_connect / linkedin_dm sem sufixo = first contact
    if step_key in ("linkedin_connect", "linkedin_dm"):
        return "first"
    return None


def _find_example(
    sector: str,
    role: str | None,
    channel: str,
    step_type: str,
) -> FewShotExample | None:
    """Busca exemplo com fallback progressivo de cargo."""
    # Tenta cargo exato
    if role:
        key = (sector, role, channel, step_type)
        if key in _EXAMPLES:
            return _EXAMPLES[key]

        # Tenta cargos de fallback definidos para este cargo
        for fallback_role in _ROLE_FALLBACK.get(role, []):
            key = (sector, fallback_role, channel, step_type)
            if key in _EXAMPLES:
                return _EXAMPLES[key]

    # Tenta qualquer cargo do setor (primeiro match no dict)
    for (s, r, c, t), ex in _EXAMPLES.items():
        if s == sector and c == channel and t == step_type:
            return ex

    return None


def _format_example(example: FewShotExample) -> str:
    """Formata o exemplo como bloco de texto para injeção no prompt."""
    lines = [
        "EXEMPLO DE REFERÊNCIA (tom e estrutura da Composto Web — adapt para este lead):",
        f"  Método: {example.method}",
    ]
    if example.subject:
        lines.append(f"  Assunto de referência: {example.subject}")
    lines.append(f"  Mensagem:\n---\n{example.message}\n---")
    return "\n".join(lines)
