"""
services/outreach_playbook.py

Dados estratégicos de prospecção da Composto Web codificados em Python:
- PlaybookEntry: dores, gatilho emocional, objeção, gancho por setor+cargo
- PLAYBOOK: mapa completo (13 setores × até 4 cargos)
- detect_sector / detect_role: normalização dos campos do Lead para chaves canônicas
- get_lead_playbook: combina detecção e retorna PlaybookEntry ou None
- score_lead_icp: pontua o lead contra o ICP primário/secundário da Composto Web

Fonte: docs/composto-web-skills/01-base-de-conhecimento/ + 02-playbook-setores/
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

# ── Estrutura de dados ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlaybookEntry:
    sector: str
    role: str
    dor_principal: str
    dor_secundaria: str
    gatilho_emocional: str
    objecao_comum: str
    gancho: str


@dataclass(frozen=True)
class PlaybookMatch:
    sector: str
    requested_role: str | None
    matched_role: str
    match_type: str
    entry: PlaybookEntry


# ── Playbook completo ──────────────────────────────────────────────────────────
# Estrutura: PLAYBOOK[sector_key][role_key]

PLAYBOOK: dict[str, dict[str, PlaybookEntry]] = {
    # ── 1. Financeiro / Contabilidade ─────────────────────────────────────────
    "financeiro": {
        "cfo": PlaybookEntry(
            sector="financeiro",
            role="cfo",
            dor_principal="Fechamento mensal demorado, dependente de consolidação manual de dados vindos de múltiplas fontes (ERP, planilhas, bancos).",
            dor_secundaria="Falta de visibilidade preditiva do fluxo de caixa; dados chegam sempre tarde para decisões estratégicas.",
            gatilho_emocional="Não posso levar números incertos para o board. Se o dado está errado, a culpa cai em mim.",
            objecao_comum="Já tentamos integrar sistemas antes e foi um caos. Não quero abrir mais uma caixa de Pandora.",
            gancho="Fechamento em minutos, não em dias: construímos a camada de integração entre seu ERP e seus bancos, com conciliação automática, auditável e 100% sob soberania da sua empresa.",
        ),
        "controller": PlaybookEntry(
            sector="financeiro",
            role="controller",
            dor_principal="Operação refém de planilhas frágeis com fórmulas que quebram, versões conflitantes e dependência de pessoas específicas para funcionar.",
            dor_secundaria="Tempo excessivo gasto em conciliação bancária e de contas a pagar/receber, impedindo análise real.",
            gatilho_emocional="Eu sei que tem erro em algum lugar, mas não consigo encontrar antes do prazo.",
            objecao_comum="Nosso ERP deveria resolver isso. O problema é que ninguém aqui sabe configurar direito.",
            gancho="Eliminamos o erro na origem: integramos seu ERP com validação automática de entrada de dados, sem depender de configuração interna nem de fornecedor de software.",
        ),
        "analista": PlaybookEntry(
            sector="financeiro",
            role="analista",
            dor_principal="Passa horas por dia em tarefas repetitivas: baixar extratos, classificar lançamentos, montar relatórios que ninguém lê.",
            dor_secundaria="Sente que o trabalho real de análise nunca acontece por falta de tempo.",
            gatilho_emocional="Sou analista, mas me sinto um digitador glorificado.",
            objecao_comum="A direção não vai aprovar mais um projeto de TI agora.",
            gancho="Robôs para o operacional, você para a análise: automatizamos as rotinas de extração e classificação para que sua equipe foque no que gera valor real.",
        ),
        "contador": PlaybookEntry(
            sector="financeiro",
            role="contador",
            dor_principal="Obrigações acessórias (SPED, ECF, EFD, NFe) com prazos rígidos, geradas manualmente com alto risco de erro e multa.",
            dor_secundaria="Retrabalho constante por divergência entre dados contábeis e fiscais.",
            gatilho_emocional="Uma multa por erro meu pode custar meu emprego ou a reputação do escritório.",
            objecao_comum="Contabilidade tem regras específicas demais. Automação genérica não funciona aqui.",
            gancho="Automação contábil sob medida: desenvolvemos robôs que conhecem as especificidades do SPED e das obrigações fiscais da sua operação, eliminando o risco de multa por erro manual.",
        ),
    },
    # ── 2. Jurídico / Advocacia ───────────────────────────────────────────────
    "juridico": {
        "socio_advocacia": PlaybookEntry(
            sector="juridico",
            role="socio_advocacia",
            dor_principal="Tempo do sócio — o ativo mais caro do escritório — consumido em tarefas de monitoramento processual e geração de relatórios.",
            dor_secundaria="Risco de perda de prazo fatal por falha humana no monitoramento de diários e tribunais.",
            gatilho_emocional="Uma perda de prazo pode custar um cliente milionário e destruir décadas de reputação.",
            objecao_comum="Já usamos um sistema jurídico. Não preciso de mais software.",
            gancho="Seu sistema jurídico organiza. Nós automatizamos: integramos seu software com crawlers de tribunais, alertas em tempo real e geração automática de minutas, sem trocar o que você já usa.",
        ),
        "gestor_juridico": PlaybookEntry(
            sector="juridico",
            role="gestor_juridico",
            dor_principal="Monitoramento manual diário de diários oficiais e portais de tribunais para dezenas ou centenas de processos simultâneos.",
            dor_secundaria="Falta de métricas e dashboards para reportar performance do jurídico à diretoria em linguagem de negócio.",
            gatilho_emocional="Não consigo dormir tranquilo sabendo que um prazo pode ter passado e eu não vi.",
            objecao_comum="Os tribunais mudam o layout dos sites constantemente. Qualquer automação vai quebrar.",
            gancho="Crawler Jurídico com self-healing: nossos robôs detectam mudanças nos portais e se adaptam automaticamente. Você recebe a pauta do dia com minutas pré-preenchidas antes das 8h.",
        ),
        "diretor_juridico": PlaybookEntry(
            sector="juridico",
            role="diretor_juridico",
            dor_principal="Gestão de contratos descentralizada — contratos espalhados em e-mail, servidor local e sistemas distintos, sem controle de vencimentos e renovações.",
            dor_secundaria="Dificuldade em demonstrar o valor do jurídico para o C-Level em termos financeiros.",
            gatilho_emocional="O jurídico é visto como custo, não como proteção estratégica. Preciso mudar isso.",
            objecao_comum="Contratos têm dados sensíveis. Não posso colocar isso em qualquer sistema.",
            gancho="Gestão de contratos com soberania total: construímos o sistema dentro da sua infraestrutura, com criptografia AES-256 e conformidade LGPD. Seus dados nunca saem do seu ambiente.",
        ),
        "advogado": PlaybookEntry(
            sector="juridico",
            role="advogado",
            dor_principal="Digitação e preenchimento manual de petições, contratos e documentos padronizados que consomem horas por dia.",
            dor_secundaria="Pesquisa jurisprudencial demorada e desorganizada.",
            gatilho_emocional="Estudei anos para ser advogado e passo o dia copiando e colando texto em formulários.",
            objecao_comum="IA jurídica ainda não é confiável para uso profissional sério.",
            gancho="IA como assistente, advogado como decisor: automatizamos a geração de minutas e petições a partir de templates validados pela sua equipe. A IA esboça, o advogado assina.",
        ),
    },
    # ── 3. Saúde / Clínicas ───────────────────────────────────────────────────
    "saude": {
        "diretor_clinica": PlaybookEntry(
            sector="saude",
            role="diretor_clinica",
            dor_principal="Alta taxa de não-comparecimento (no-show) de pacientes, gerando ociosidade da agenda e perda direta de receita.",
            dor_secundaria="Processos administrativos (agendamento, confirmação, faturamento) completamente manuais e dependentes de recepcionistas sobrecarregadas.",
            gatilho_emocional="Cada horário vazio é dinheiro jogado fora que não consigo recuperar.",
            objecao_comum="Nossos pacientes são mais velhos e não se adaptam bem a tecnologia.",
            gancho="Redução de no-show em até 40%: implementamos fluxo automático de confirmação via WhatsApp com reagendamento inteligente, sem exigir que o paciente use app ou crie conta.",
        ),
        "gerente_administrativo": PlaybookEntry(
            sector="saude",
            role="gerente_administrativo",
            dor_principal="Faturamento de planos de saúde manual, sujeito a glosas por inconsistências no preenchimento de guias.",
            dor_secundaria="Comunicação caótica entre recepção, médicos e laboratório; informações se perdem entre papéis e WhatsApp pessoal.",
            gatilho_emocional="Perco receita toda semana por glosa de plano. Sei que tem erro, mas não tenho como auditar tudo.",
            objecao_comum="Nosso sistema de gestão de clínica já tem automação básica. Não sei se vale investir em mais.",
            gancho="Auditoria automática de guias: validamos cada guia antes do envio ao plano, cruzando procedimentos, CID e autorizações. Redução de glosa na primeira entrega.",
        ),
        "ti_saude": PlaybookEntry(
            sector="saude",
            role="ti_saude",
            dor_principal="Sistemas legados de gestão hospitalar (MV, Tasy, Soul MV) sem API aberta, impossibilitando integrações com ferramentas modernas.",
            dor_secundaria="Pressão das áreas clínicas e administrativas por relatórios e integrações que o sistema nativo não entrega.",
            gatilho_emocional="Fico entre a pedra e o martelo: a diretoria quer integração e o fornecedor do sistema cobra uma fortuna ou simplesmente não faz.",
            objecao_comum="O fornecedor do nosso HIS diz que qualquer integração terceirizada pode invalidar o suporte.",
            gancho="Integração sem toque no core do sistema: usamos camadas de middleware e RPA cognitivo para extrair e alimentar dados sem modificar o HIS. Seu suporte de fornecedor permanece intacto.",
        ),
        "medico_socio": PlaybookEntry(
            sector="saude",
            role="medico_socio",
            dor_principal="Tempo clínico consumido em tarefas administrativas: prontuário manual, prescrições repetitivas, solicitação de exames.",
            dor_secundaria="Dificuldade em acompanhar resultados de exames e histórico do paciente de forma organizada antes da consulta.",
            gatilho_emocional="Cada minuto que gasto em burocracia é um paciente a menos atendido.",
            objecao_comum="Prontuário eletrônico já resolveu isso. Não preciso de mais automação.",
            gancho="Prontuário inteligente: integramos seu PEP com alertas de exames críticos, prescrições por voz (Whisper AI) e resumo automático do histórico antes de cada consulta.",
        ),
    },
    # ── 4. Indústria / Logística ──────────────────────────────────────────────
    "industria": {
        "diretor_industrial": PlaybookEntry(
            sector="industria",
            role="diretor_industrial",
            dor_principal="Incapacidade de escalar produção sem escalar proporcionalmente o custo fixo com mão de obra e supervisão.",
            dor_secundaria="Falta de visibilidade em tempo real do chão de fábrica: dados chegam no dia seguinte, já velhos para tomada de decisão.",
            gatilho_emocional="Quando algo para na linha de produção, descubro horas depois. O custo já foi embora.",
            objecao_comum="Nossa operação é muito específica. Soluções de prateleira não funcionam aqui.",
            gancho="Torre de controle industrial: monitoramento em tempo real do chão de fábrica com alertas automáticos, integrado ao seu ERP, construído sob medida para a especificidade da sua operação.",
        ),
        "gerente_logistica": PlaybookEntry(
            sector="industria",
            role="gerente_logistica",
            dor_principal="Rastreamento de cargas e pedidos fragmentado entre transportadoras, planilhas e sistemas desconectados.",
            dor_secundaria="Gestão de estoque imprecisa, com rupturas e excessos simultâneos em diferentes SKUs.",
            gatilho_emocional="O cliente liga perguntando onde está o pedido e eu preciso abrir cinco sistemas para responder. Isso me envergonha.",
            objecao_comum="Já temos um TMS / WMS. O problema é de processo, não de tecnologia.",
            gancho="Hub logístico unificado: integramos todas as suas transportadoras e seu WMS em uma camada única, com rastreamento em tempo real e alertas proativos para o cliente, antes que ele ligue.",
        ),
        "ti_industria": PlaybookEntry(
            sector="industria",
            role="ti_industria",
            dor_principal="ERPs industriais antigos (SAP, TOTVS, Senior) com customizações frágeis e custo altíssimo para qualquer nova integração via fornecedor oficial.",
            dor_secundaria="Time de TI interno pequeno, preso em sustentação, sem capacidade de tocar projetos de inovação.",
            gatilho_emocional="Cada nova demanda das áreas vira uma batalha com o fornecedor do ERP que leva meses e custa uma fortuna.",
            objecao_comum="A fábrica não para para projeto. Não tenho janela de manutenção disponível.",
            gancho="Integração sem downtime: desenvolvemos as integrações em camadas paralelas ao ERP, com rollback garantido e implantação em janelas mínimas. Seu ERP não para, não recompila, não muda.",
        ),
        "pcp": PlaybookEntry(
            sector="industria",
            role="pcp",
            dor_principal="Planejamento de produção baseado em planilhas que não conversam com o estoque real, gerando ordens equivocadas e desperdício.",
            dor_secundaria="Tempo excessivo consolidando dados de múltiplas fontes para montar o plano do dia.",
            gatilho_emocional="Planejo com dados de ontem para produzir hoje. O erro está embutido no processo.",
            objecao_comum="Já tentamos implementar um APS e não deu certo. Desistiram na metade.",
            gancho="PCP com dado em tempo real: construímos a integração entre seu ERP e o chão de fábrica para que o planejador trabalhe com estoque e capacidade atualizados ao minuto, não ao dia.",
        ),
    },
    # ── 5. Varejo / E-commerce ────────────────────────────────────────────────
    "varejo": {
        "ceo_ecommerce": PlaybookEntry(
            sector="varejo",
            role="ceo_ecommerce",
            dor_principal="Operação omnichannel fragmentada: estoque, pedidos e atendimento em sistemas que não se conversam.",
            dor_secundaria="Custo operacional crescendo mais rápido que a receita à medida que o volume de pedidos aumenta.",
            gatilho_emocional="Vendo mais, mas lucro menos. Cada pedido a mais traz mais problema, não mais margem.",
            objecao_comum="Já temos Vtex / Shopify / TOTVS. Não quero adicionar mais uma ferramenta.",
            gancho="Escala sem dor operacional: construímos a espinha dorsal de integração entre sua plataforma, ERP e marketplaces, para que dobrar o volume não dobre o headcount de operação.",
        ),
        "gerente_operacoes": PlaybookEntry(
            sector="varejo",
            role="gerente_operacoes",
            dor_principal="Separação e expedição de pedidos lentas e sujeitas a erros humanos, gerando alto índice de devolução.",
            dor_secundaria="Gestão de estoque inconsistente entre loja física, CD e marketplace, com divergências constantes.",
            gatilho_emocional="Cada devolução é uma bomba: reembolso, logística reversa, produto danificado e cliente que nunca volta.",
            objecao_comum="Nossa operação é muito sazonal. Não vale investir em automação para um pico de 2 meses.",
            gancho="Automação elástica para sazonalidade: desenhamos a solução para escalar no pico e custar menos na baixa. A operação se ajusta sem você precisar contratar e demitir.",
        ),
        "gerente_crm": PlaybookEntry(
            sector="varejo",
            role="gerente_crm",
            dor_principal="Dados de clientes fragmentados entre plataforma de e-commerce, ERP, ferramenta de email marketing e WhatsApp.",
            dor_secundaria="Campanhas disparadas no escuro, sem segmentação precisa por comportamento de compra.",
            gatilho_emocional="Sei que tenho ouro nos meus dados de clientes, mas não consigo acessá-lo de forma útil.",
            objecao_comum="Já temos uma ferramenta de CRM/automação de marketing. O problema é alimentá-la.",
            gancho="CDP sob medida: unificamos todos os seus dados de cliente em uma fonte única de verdade, alimentando seu CRM e suas campanhas com segmentação comportamental real em tempo real.",
        ),
        "sac": PlaybookEntry(
            sector="varejo",
            role="sac",
            dor_principal="Volume de tickets repetitivos (onde está meu pedido?, como troco?, prazo de entrega) consumindo toda a capacidade do time.",
            dor_secundaria="Falta de contexto na abertura do ticket: atendente precisa pesquisar em múltiplos sistemas.",
            gatilho_emocional="Minha equipe está no limite. Quando o pico chega, o atendimento desmorona.",
            objecao_comum="Chatbot vai frustrar o cliente. Prefiro atendimento humano.",
            gancho="IA para o automático, humano para o complexo: implementamos triagem inteligente onde 70% dos tickets são resolvidos sem intervenção humana, e o atendente recebe o caso já com contexto completo.",
        ),
    },
    # ── 6. Educação / EdTech ──────────────────────────────────────────────────
    "educacao": {
        "diretor_academico": PlaybookEntry(
            sector="educacao",
            role="diretor_academico",
            dor_principal="Alta taxa de evasão de alunos, especialmente em cursos EAD, com detecção tardia do problema e intervenção ineficaz.",
            dor_secundaria="Processo de matrícula e rematrícula manual e demorado, gerando perda de alunos na jornada de conversão.",
            gatilho_emocional="Cada aluno que evade já pagou o custo de aquisição. Perco duas vezes: a receita e o investimento.",
            objecao_comum="Nosso LMS já tem relatórios de engajamento. Não preciso de mais dado.",
            gancho="Radar de evasão preditivo: cruzamos dados de acesso, notas e comportamento do aluno no LMS para alertar o tutor antes que o aluno desengaje.",
        ),
        "financeiro_educacao": PlaybookEntry(
            sector="educacao",
            role="financeiro_educacao",
            dor_principal="Gestão de inadimplência manual, com boletos vencidos acumulando e processo de cobrança ineficiente.",
            dor_secundaria="Controle de bolsas, descontos e acordos financeiros descentralizado e sujeito a fraude ou erro.",
            gatilho_emocional="Tenho vergonha do nível de inadimplência quando apresento para a direção. Parece desleixo meu.",
            objecao_comum="Já mandamos e-mail de cobrança. O problema é que o aluno simplesmente ignora.",
            gancho="Régua de cobrança inteligente multicanal: sequência automática de WhatsApp, e-mail e SMS com tom progressivo, integrada ao seu ERP, com oferta de acordo personalizada no momento certo.",
        ),
        "coordenador_pedagogico": PlaybookEntry(
            sector="educacao",
            role="coordenador_pedagogico",
            dor_principal="Acompanhamento de desempenho de turmas e alunos feito manualmente, sem capacidade de personalizar a intervenção em escala.",
            dor_secundaria="Comunicação com alunos e responsáveis fragmentada entre e-mail, app do LMS e WhatsApp pessoal dos tutores.",
            gatilho_emocional="Sei que tenho alunos em risco nessa turma, mas não sei quais são sem revisar tudo manualmente.",
            objecao_comum="Professores resistem a mudar a forma como trabalham. Qualquer nova tecnologia gera atrito.",
            gancho="Dashboard pedagógico em tempo real: o coordenador vê quais alunos estão em risco, qual tutor tem maior taxa de recuperação e onde a intervenção deve acontecer, tudo em uma tela.",
        ),
    },
    # ── 7. Imobiliário / Construtoras ─────────────────────────────────────────
    "imobiliario": {
        "diretor_comercial": PlaybookEntry(
            sector="imobiliario",
            role="diretor_comercial",
            dor_principal="Ciclo de venda longo com leads frios: prospects que demonstraram interesse somem e o follow-up depende da disciplina individual de cada corretor.",
            dor_secundaria="Falta de visibilidade do funil comercial em tempo real.",
            gatilho_emocional="Gastei uma fortuna em lançamento e não sei dizer para o sócio quantos leads viraram visita e quantas visitas viraram proposta.",
            objecao_comum="Já temos CRM imobiliário. O problema é que os corretores não alimentam.",
            gancho="CRM que se alimenta sozinho: integramos seus canais de captação (portais, WhatsApp, Instagram) com o CRM, criando o lead e registrando cada interação automaticamente.",
        ),
        "gerente_obras": PlaybookEntry(
            sector="imobiliario",
            role="gerente_obras",
            dor_principal="Controle de cronograma e avanço físico-financeiro da obra feito em planilhas que ninguém atualiza no ritmo certo.",
            dor_secundaria="Gestão de fornecedores e subcontratados descentralizada, com medições, contratos e notas em papel ou e-mail.",
            gatilho_emocional="A obra está atrasada e eu fico sabendo pela visita do diretor, não pelo meu sistema.",
            objecao_comum="Cada obra é única. Não tem como padronizar.",
            gancho="Painel de obras em tempo real: digitalizamos o avanço físico com check-in de equipes via mobile, integrado ao seu cronograma e ao ERP financeiro, com alertas de desvio antes que o problema escale.",
        ),
        "pos_venda": PlaybookEntry(
            sector="imobiliario",
            role="pos_venda",
            dor_principal="Atendimento a clientes compradores no período entre contrato e entrega é caótico: perguntas repetitivas sobrecarregam a equipe.",
            dor_secundaria="Alto índice de distrato em empreendimentos longos, com detecção tardia de compradores insatisfeitos.",
            gatilho_emocional="Distrato é o pior dos mundos: perco a unidade, pago de volta e ainda tenho processo.",
            objecao_comum="Nosso portal do comprador já atende básico. Não preciso de mais.",
            gancho="Portal do comprador automatizado: o cliente acompanha o andamento da obra, recebe atualizações e tem suas dúvidas respondidas via chatbot especializado, reduzindo o volume de contato humano em mais de 60%.",
        ),
    },
    # ── 8. Seguros / Fintechs ─────────────────────────────────────────────────
    "seguros": {
        "ceo_fintech": PlaybookEntry(
            sector="seguros",
            role="ceo_fintech",
            dor_principal="Onboarding de clientes lento e manual, com coleta de documentos, análise de risco e aprovação levando dias, gerando abandono na jornada.",
            dor_secundaria="Custo operacional de sinistro/análise de crédito alto por dependência de analistas humanos para tarefas repetitivas.",
            gatilho_emocional="O cliente consegue abrir conta no banco digital em 3 minutos. Nosso processo leva 3 dias. Estou perdendo para a concorrência.",
            objecao_comum="Regulação do setor limita o que podemos automatizar. Compliance vai barrar.",
            gancho="Onboarding em minutos com compliance nativo: construímos o fluxo de análise e aprovação com automação de consultas (bureaus, BACEN, Receita Federal) e trilha de auditoria completa para o regulador.",
        ),
        "analise_credito": PlaybookEntry(
            sector="seguros",
            role="analise_credito",
            dor_principal="Análise manual de sinistros ou crédito dependente de checklist humano, sujeita a inconsistência de critério entre analistas e fraude não detectada.",
            dor_secundaria="SLA de resposta ao cliente alto por volume de casos e falta de priorização inteligente.",
            gatilho_emocional="Sei que estou aprovando casos que não deveria e reprovando clientes bons. Mas não consigo provar nem corrigir sistematicamente.",
            objecao_comum="Automação de análise de crédito/sinistro requer aprovação do atuário e do jurídico. Processo longo.",
            gancho="Motor de decisão auditável: construímos o sistema de scoring e análise com regras definidas pela sua equipe técnica, rodando de forma consistente 24/7, com log completo de cada decisão.",
        ),
        "compliance": PlaybookEntry(
            sector="seguros",
            role="compliance",
            dor_principal="Monitoramento de transações para PLD/FT (Prevenção à Lavagem de Dinheiro) manual e reativo, com risco de multa pelo BACEN/SUSEP.",
            dor_secundaria="Gestão de políticas internas e treinamentos de compliance sem rastreabilidade.",
            gatilho_emocional="Uma autuação do regulador pode comprometer a licença de operação. É risco existencial, não só financeiro.",
            objecao_comum="Nosso banco de dados tem dados sensíveis demais para qualquer integração externa.",
            gancho="Compliance automático com soberania total: todo o sistema roda na sua infraestrutura, com criptografia de ponta a ponta. Entregamos a Propriedade Intelectual integral.",
        ),
    },
    # ── 9. Agro / Agroindustrial ──────────────────────────────────────────────
    "agro": {
        "diretor_agro": PlaybookEntry(
            sector="agro",
            role="diretor_agro",
            dor_principal="Tomada de decisão agronômica baseada em dados defasados ou na intuição do técnico de campo, sem integração com dados climáticos, de solo e de mercado em tempo real.",
            dor_secundaria="Dificuldade em rastrear a cadeia produtiva para fins de certificação e acesso a mercados premium.",
            gatilho_emocional="Uma decisão errada de plantio ou tratamento não compromete o mês, compromete a safra inteira.",
            objecao_comum="Conectividade no campo é ruim. Tecnologia não funciona na fazenda.",
            gancho="Plataforma offline-first para o campo: sistemas que funcionam sem internet e sincronizam quando há sinal, com dashboards de gestão para o escritório que consolidam dados de todas as fazendas em tempo real.",
        ),
        "financeiro_agro": PlaybookEntry(
            sector="agro",
            role="financeiro_agro",
            dor_principal="Gestão financeira de cooperativa ou agroindústria com múltiplos centros de custo, safras e contratos de venda futura em planilhas desconectadas do ERP.",
            dor_secundaria="Relacionamento com cooperados ou fornecedores rurais feito por telefone e WhatsApp pessoal, sem histórico centralizado.",
            gatilho_emocional="Na época de safra, perco o controle. O volume de transações explode e minha equipe não acompanha.",
            objecao_comum="Já tentamos um ERP agrícola e foi um fracasso de implantação. Não quero passar por isso de novo.",
            gancho="Integração sobre o que você já tem: não trocamos seu ERP. Construímos a camada de automação sobre ele, eliminando o trabalho manual sem o trauma de uma nova implantação.",
        ),
        "rastreabilidade": PlaybookEntry(
            sector="agro",
            role="rastreabilidade",
            dor_principal="Registro de rastreabilidade de lotes feito em papel ou planilha, impossibilitando auditoria rápida e acesso a certificações.",
            dor_secundaria="Comunicação de não-conformidades na linha de processamento lenta, causando contaminação de lotes maiores.",
            gatilho_emocional="Se houver uma auditoria de certificação ou um recall, não consigo rastrear o lote em menos de 1 dia. Isso inviabiliza a exportação.",
            objecao_comum="Nossa operação tem muita variabilidade. Difícil de padronizar em sistema.",
            gancho="Rastreabilidade digital de lote: digitalizamos o registro de cada etapa produtiva com QR code e mobile, gerando o dossiê de rastreabilidade em segundos para auditorias e certificações de exportação.",
        ),
    },
    # ── 10. RH / Gestão de Pessoas ────────────────────────────────────────────
    "rh": {
        "chro": PlaybookEntry(
            sector="rh",
            role="chro",
            dor_principal="Decisões de gestão de pessoas tomadas com base em feeling, sem dados confiáveis de turnover, engajamento, absenteísmo e performance por área.",
            dor_secundaria="Dificuldade em demonstrar o ROI das iniciativas de RH para o C-Level em linguagem financeira.",
            gatilho_emocional="O CEO me pede dados de pessoas e eu tenho que juntar tudo na mão antes da reunião. Parece amador.",
            objecao_comum="Já temos um HRIS (Workday, SAP HCM, Gupy). O problema é que ninguém usa direito.",
            gancho="People Analytics real: extraímos os dados do seu HRIS atual e os transformamos em um dashboard executivo com indicadores de people em linguagem de negócio, sem trocar seu sistema.",
        ),
        "recrutamento": PlaybookEntry(
            sector="rh",
            role="recrutamento",
            dor_principal="Triagem manual de centenas de currículos por vaga, consumindo tempo de profissionais sêniores em tarefas de baixo valor.",
            dor_secundaria="Experiência do candidato ruim (sem feedback, processo lento), gerando desistência de talentos que recebem outra oferta.",
            gatilho_emocional="Perdi o candidato ideal para um concorrente porque meu processo de triagem levou 2 semanas.",
            objecao_comum="IA de triagem tem viés. Não posso usar algo que discrimine candidatos.",
            gancho="Triagem com critérios definidos por você: o sistema filtra com base nos critérios que sua equipe define e valida, com transparência total do raciocínio. O recrutador decide; a IA elimina o trabalho braçal.",
        ),
        "dp": PlaybookEntry(
            sector="rh",
            role="dp",
            dor_principal="Folha de pagamento processada manualmente com dados vindos de ponto eletrônico, benefícios, horas extras e afastamentos em sistemas diferentes.",
            dor_secundaria="eSocial e obrigações trabalhistas com risco constante de multa por envio incorreto ou fora do prazo.",
            gatilho_emocional="Dia de fechamento de folha é o mês mais estressante do meu time. Alguém vai errar.",
            objecao_comum="Folha de pagamento é sensível demais para automação. Precisa de validação humana em tudo.",
            gancho="Pré-processamento automático com validação humana no final: automatizamos a coleta e consolidação de todos os dados antes do fechamento, entregando para o analista uma folha pré-calculada para revisão.",
        ),
        "td": PlaybookEntry(
            sector="rh",
            role="td",
            dor_principal="Controle de treinamentos obrigatórios (NRs, compliance, onboarding) em planilhas, sem visibilidade de quem está em dia.",
            dor_secundaria="Onboarding de novos colaboradores lento e inconsistente, dependendo da disponibilidade de cada gestor.",
            gatilho_emocional="Se houver uma fiscalização do MTE e um funcionário não tiver o treinamento de NR em dia, a responsabilidade cai em mim.",
            objecao_comum="Já temos uma plataforma EAD corporativa. O problema é que os líderes não cobram suas equipes.",
            gancho="Compliance de treinamento automático: alertas automáticos para o colaborador, para o gestor e para o RH quando um treinamento está próximo do vencimento, com escalada progressiva e registro de auditoria.",
        ),
    },
    # ── 11. Empresas de TI ────────────────────────────────────────────────────
    "ti": {
        "ceo_cto_ti": PlaybookEntry(
            sector="ti",
            role="ceo_cto_ti",
            dor_principal="Time de engenharia passa mais tempo em suporte interno, onboarding de clientes e geração de relatórios do que desenvolvendo produto.",
            dor_secundaria="Onboarding de novos clientes que não escala sem crescer linearmente o time de CS.",
            gatilho_emocional="Cada hora de engenheiro sênior gasta em tarefa operacional é uma feature que não foi desenvolvida e uma vantagem competitiva que ficou no papel.",
            objecao_comum="Podemos construir essas automações internamente quando tivermos tempo.",
            gancho="Libere a engenharia para produto: construímos as automações de CS, onboarding e suporte que liberam o time técnico para focar no que gera valor. O que construímos fica com a propriedade intelectual da sua empresa.",
        ),
        "cs_ti": PlaybookEntry(
            sector="ti",
            role="cs_ti",
            dor_principal="Onboarding de clientes lento e inconsistente, dependendo de call de configuração manual com cada novo cliente.",
            dor_secundaria="Health score de clientes calculado manualmente ou sem dados suficientes para prever churn com antecedência.",
            gatilho_emocional="Meu time de CS está dando conta, mas qualquer pico de novos clientes vai quebrar o processo.",
            objecao_comum="Nosso produto é muito customizável. Difícil automatizar o onboarding.",
            gancho="Onboarding que escala: automatizamos o fluxo de configuração inicial e criamos o health score contínuo, liberando o CS para relacionamento com clientes em risco, não para operacional.",
        ),
        "devops_ti": PlaybookEntry(
            sector="ti",
            role="devops_ti",
            dor_principal="Infraestrutura crescendo sem FinOps: custos de cloud subindo sem controle, sem visibilidade de onde está sendo gasto.",
            dor_secundaria="Alertas de monitoramento mal configurados: ou alarme demais (fadiga) ou alarme de menos (problema silencioso).",
            gatilho_emocional="Fico sabendo de problema em produção pelo cliente, não pelo meu sistema de monitoramento.",
            objecao_comum="Nossa infra está no Kubernetes gerenciado. Não preciso de consultoria de infra.",
            gancho="Observabilidade e FinOps integrados: construímos o stack completo de Grafana/Prometheus com alertas inteligentes por severidade e dashboards de custo por serviço/cliente, com recomendações de otimização automáticas.",
        ),
    },
    # ── 12. Agências de Marketing ─────────────────────────────────────────────
    "agencia": {
        "ceo_agencia": PlaybookEntry(
            sector="agencia",
            role="ceo_agencia",
            dor_principal="Margem caindo à medida que a carteira de clientes cresce: cada cliente novo traz mais overhead de gestão (reunião, relatório, aprovação) que não é cobrado.",
            dor_secundaria="Time criativo que deveria estar em estratégia fica travado no operacional.",
            gatilho_emocional="Cresci em clientes mas a margem caiu. Trabalho mais e ganho menos proporcionalmente.",
            objecao_comum="Nossa operação é muito artesanal. Difícil padronizar o que fazemos.",
            gancho="Operacional automatizado, criativo liberado: automatizamos relatórios, aprovações de conteúdo e gestão de campanhas para que a equipe criativa foque em estratégia. Cada cliente novo vira receita, não overhead.",
        ),
        "conteudo_agencia": PlaybookEntry(
            sector="agencia",
            role="conteudo_agencia",
            dor_principal="Gestão de aprovação de conteúdo manual via e-mail e WhatsApp, com versões conflitantes, clientes que somem e prazos que estouram.",
            dor_secundaria="Relatórios de resultado montados manualmente para cada cliente, consumindo horas do time a cada ciclo.",
            gatilho_emocional="Passo mais tempo gerenciando aprovação do que criando conteúdo de qualidade.",
            objecao_comum="Os clientes têm processos de aprovação muito específicos. Não tem como padronizar.",
            gancho="Fluxo de aprovação automatizado: cada peça entra no portal, o cliente aprova com um clique e o histórico fica registrado. Fim do caos de e-mail e versão errada publicada.",
        ),
    },
    # ── 13. Marketing Interno (deptos de marketing) ───────────────────────────
    "marketing": {
        "cmo": PlaybookEntry(
            sector="marketing",
            role="cmo",
            dor_principal="Dados de clientes fragmentados entre CRM, e-commerce, plataforma de e-mail e canais de atendimento, sem integração em tempo real para segmentação precisa.",
            dor_secundaria="Dificuldade em demonstrar ROI de marketing para o C-Level com atribuição de receita precisa.",
            gatilho_emocional="Invisto em marketing mas não consigo provar quanto cada canal realmente gerou de receita.",
            objecao_comum="Já temos ferramentas de marketing (HubSpot, RD Station, Salesforce). O problema é integração.",
            gancho="CDP sob medida sobre o que você já tem: unificamos todas as fontes de dado de cliente em uma visão única, alimentando seu CRM e campanhas com segmentação comportamental real, sem trocar suas ferramentas.",
        ),
        "gerente_marketing": PlaybookEntry(
            sector="marketing",
            role="gerente_marketing",
            dor_principal="CRM desatualizado por depender de alimentação manual da equipe, gerando campanhas baseadas em dados defasados.",
            dor_secundaria="Atribuição de conversão imprecisa entre canais, impossibilitando otimização do mix de mídia.",
            gatilho_emocional="Minha segmentação de campanha usa dados de 3 meses atrás. Estou atirando às cegas.",
            objecao_comum="Já mandamos dados para o CRM via integração básica. Não precisa de mais.",
            gancho="CRM que se alimenta sozinho: integramos todos os pontos de contato do cliente em tempo real, com enriquecimento automático de dados comportamentais. Suas campanhas passam a usar segmentação do momento, não do passado.",
        ),
    },
}


# ── Detecção de setor ─────────────────────────────────────────────────────────

_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "financeiro": [
        "financeiro",
        "contabil",
        "contabilidade",
        "contábil",
        "accounting",
        "finance",
        "bpo",
        "auditoria",
        "fiscal",
        "tributário",
        "tributario",
        "escritório contábil",
        "escritorio contabil",
        "ctrl",
    ],
    "juridico": [
        "jurídico",
        "juridico",
        "advocacia",
        "law",
        "legal",
        "litigi",
        "escritório de advoc",
        "escritorio de advoc",
        "tribunal",
    ],
    "saude": [
        "saúde",
        "saude",
        "clínica",
        "clinica",
        "hospital",
        "médico",
        "medico",
        "odont",
        "farmác",
        "farmac",
        "laborat",
        "health",
        "plano de saúde",
        "plano de saude",
    ],
    "industria": [
        "indústria",
        "industria",
        "industrial",
        "manufacturing",
        "fábrica",
        "fabrica",
        "logíst",
        "logist",
        "supply chain",
        "transport",
        "distribuidor",
    ],
    "varejo": [
        "varejo",
        "retail",
        "e-commerce",
        "ecommerce",
        "loja",
        "marketplace",
        "fulfillment",
        "atacado",
    ],
    "educacao": [
        "educação",
        "educacao",
        "edtech",
        "escola",
        "faculdade",
        "universidade",
        "ensino",
        "curso",
        "treinamento corporativo",
    ],
    "imobiliario": [
        "imobiliário",
        "imobiliario",
        "imobiliária",
        "imobiliaria",
        "construtora",
        "construção",
        "construcao",
        "incorporadora",
        "corretor",
        "real estate",
    ],
    "seguros": [
        "seguro",
        "seguradora",
        "fintech",
        "crédito",
        "credito",
        "financiamento",
        "banco",
        "pagamento",
        "investimento",
    ],
    "agro": [
        "agro",
        "agrícola",
        "agricola",
        "cooperativa",
        "fazenda",
        "rural",
        "agroindustrial",
    ],
    "rh": [
        "recursos humanos",
        "rh",
        "human resources",
        "hr",
        "talentos",
        "gente",
        "people",
        "departamento pessoal",
    ],
    "ti": [
        "tecnologia",
        "software",
        "saas",
        "tech",
        "startup",
        "desenvolvimento",
        "ti ",
        " ti",
        "it ",
        " it",
    ],
    "agencia": [
        "agência",
        "agencia",
        "marketing digital",
        "publicidade",
        "comunicação",
        "comunicacao",
        "mídia",
        "midia",
    ],
    "marketing": [
        "marketing",
        "crm",
        "e-mail marketing",
        "growth",
    ],
}


def detect_sector(industry: str | None) -> str | None:
    """Normaliza `lead.industry` para uma chave canônica de setor.

    Retorna None se nenhuma correspondência for encontrada.
    """
    if not industry:
        return None
    text = industry.lower()
    for sector_key, keywords in _SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return sector_key
    return None


# ── Detecção de cargo ─────────────────────────────────────────────────────────

_ROLE_KEYWORDS: dict[str, list[str]] = {
    # Financeiro
    "cfo": ["cfo", "diretor financeiro", "diretor de finanças", "vp financ"],
    "controller": ["controller", "gerente financeiro", "coordenador financeiro"],
    "analista": ["analista financeiro", "analista contábil", "analista fiscal"],
    "contador": ["contador", "gerente contábil", "gerente fiscal", "contábil"],
    # Jurídico
    "socio_advocacia": ["sócio", "socio", "advogado sênior", "advogado senior", "partner"],
    "gestor_juridico": [
        "gerente jurídico",
        "gerente juridico",
        "coordenador jurídico",
        "coordenador juridico",
        "legal ops",
        "legalops",
    ],
    "diretor_juridico": [
        "diretor jurídico",
        "diretor juridico",
        "general counsel",
        "gc ",
        "chief legal",
    ],
    "advogado": ["advogado", "lawyer", "analista jurídico", "analista juridico"],
    # Saúde
    "diretor_clinica": ["diretor", "administrador", "dono", "ceo", "proprietário", "proprietario"],
    "gerente_administrativo": [
        "gerente administrativo",
        "gerente operacional",
        "coord. admin",
        "coordenador administrativo",
    ],
    "ti_saude": ["ti", "tecnologia", "sistemas", "coord. ti", "gerente de ti"],
    "medico_socio": ["médico", "medico", "dentista", "doutor", "dr."],
    # Indústria
    "diretor_industrial": ["diretor industrial", "coo", "chief operating", "diretor de operações"],
    "gerente_logistica": ["logística", "logistica", "supply chain", "gerente de logística"],
    "ti_industria": ["gerente de ti", "coord. ti", "ti industrial"],
    "pcp": ["pcp", "planejamento", "programação", "producao", "produção"],
    # Varejo
    "ceo_ecommerce": ["ceo", "diretor de e-commerce", "fundador"],
    "gerente_operacoes": ["gerente de operações", "fulfillment", "operações"],
    "gerente_crm": ["crm", "gerente de marketing", "retention"],
    "sac": ["atendimento", "sac", "customer service", "suporte ao cliente"],
    # Educação
    "diretor_academico": [
        "diretor acadêmico",
        "diretor academico",
        "diretora acadêmica",
        "diretora academica",
        "pró-reitor",
        "pro-reitor",
    ],
    "financeiro_educacao": [
        "financeiro educacional",
        "diretor financeiro",
        "gerente financeiro",
        "administrativo financeiro",
    ],
    "coordenador_pedagogico": [
        "coordenador pedagógico",
        "coordenador pedagogico",
        "coordenação pedagógica",
        "coordenacao pedagogica",
        "tutoria",
    ],
    # Imobiliário
    "diretor_comercial": [
        "diretor comercial",
        "diretora comercial",
        "head comercial",
        "diretor de vendas",
    ],
    "gerente_obras": ["gerente de obras", "engenheiro residente", "coordenação de obras"],
    "pos_venda": ["pós-venda", "pos-venda", "relacionamento com cliente comprador"],
    # Seguros / Fintechs
    "ceo_fintech": ["ceo", "coo", "diretor de operações", "fundador"],
    "analise_credito": ["análise de crédito", "analise de credito", "sinistros"],
    "compliance": ["compliance", "risco", "pld", "susep", "bacen"],
    # Agro
    "diretor_agro": [
        "diretor agro",
        "diretor agrícola",
        "diretor agricola",
        "gerente agrícola",
        "gerente agricola",
    ],
    "financeiro_agro": ["financeiro agro", "controller agro", "gerente financeiro agro"],
    "rastreabilidade": ["rastreabilidade", "qualidade", "certificação", "certificacao"],
    # RH
    "chro": ["chro", "diretor de rh", "vp de pessoas", "head de pessoas", "diretor de gente"],
    "recrutamento": ["recrutamento", "r&s", "talent acquisition", "seleção", "selecao"],
    "dp": ["departamento pessoal", "dp ", " dp", "folha", "payroll"],
    "td": ["t&d", "treinamento", "desenvolvimento", "l&d"],
    # TI
    "ceo_cto_ti": ["ceo", "cto", "cofundador", "co-founder", "founder", "fundador"],
    "cs_ti": ["customer success", "cs ", " cs", "sucesso do cliente"],
    "devops_ti": ["devops", "sre", "infraestrutura", "cloud", "infra"],
    # Agência
    "ceo_agencia": ["ceo", "sócio", "socio", "fundador", "founder", "head"],
    "conteudo_agencia": ["conteúdo", "conteudo", "social media", "creative", "redação"],
    # Marketing
    "cmo": ["cmo", "diretor de marketing", "vp de marketing", "chief marketing"],
    "gerente_marketing": ["gerente de marketing", "marketing manager", "growth"],
}

# Mapeamento: role_key → sector_key esperado (para resolução de conflitos)
_ROLE_TO_SECTOR: dict[str, str] = {
    "cfo": "financeiro",
    "controller": "financeiro",
    "analista": "financeiro",
    "contador": "financeiro",
    "socio_advocacia": "juridico",
    "gestor_juridico": "juridico",
    "diretor_juridico": "juridico",
    "advogado": "juridico",
    "diretor_clinica": "saude",
    "gerente_administrativo": "saude",
    "ti_saude": "saude",
    "medico_socio": "saude",
    "diretor_industrial": "industria",
    "gerente_logistica": "industria",
    "ti_industria": "industria",
    "pcp": "industria",
    "ceo_ecommerce": "varejo",
    "gerente_operacoes": "varejo",
    "gerente_crm": "varejo",
    "sac": "varejo",
    "diretor_academico": "educacao",
    "financeiro_educacao": "educacao",
    "coordenador_pedagogico": "educacao",
    "diretor_comercial": "imobiliario",
    "gerente_obras": "imobiliario",
    "pos_venda": "imobiliario",
    "ceo_fintech": "seguros",
    "analise_credito": "seguros",
    "compliance": "seguros",
    "diretor_agro": "agro",
    "financeiro_agro": "agro",
    "rastreabilidade": "agro",
    "chro": "rh",
    "recrutamento": "rh",
    "dp": "rh",
    "td": "rh",
    "ceo_cto_ti": "ti",
    "cs_ti": "ti",
    "devops_ti": "ti",
    "ceo_agencia": "agencia",
    "conteudo_agencia": "agencia",
    "cmo": "marketing",
    "gerente_marketing": "marketing",
}


def detect_role(job_title: str | None, sector: str | None = None) -> str | None:
    """Normaliza `lead.job_title` para uma chave canônica de cargo.

    Retorna None se nenhuma correspondência for encontrada.
    """
    if not job_title:
        return None
    text = job_title.lower()

    if sector:
        sector_match = _find_best_role_match(
            text,
            (
                (role_key, keywords)
                for role_key, keywords in _ROLE_KEYWORDS.items()
                if _ROLE_TO_SECTOR.get(role_key) == sector
            ),
        )
        if sector_match:
            return sector_match

    return _find_best_role_match(text, _ROLE_KEYWORDS.items())


def _find_best_role_match(
    text: str,
    candidates: Iterable[tuple[str, list[str]]],
) -> str | None:
    best_role: str | None = None
    best_keyword_length = -1

    for role_key, keywords in candidates:
        for kw in keywords:
            if kw in text and len(kw) > best_keyword_length:
                best_role = role_key
                best_keyword_length = len(kw)

    return best_role


# ── API pública ───────────────────────────────────────────────────────────────


def get_lead_playbook_match(lead: object) -> PlaybookMatch | None:
    """Retorna metadados do match de playbook quando houver confiança suficiente."""
    industry: str | None = getattr(lead, "industry", None)
    job_title: str | None = getattr(lead, "job_title", None)

    sector = detect_sector(industry)
    role = detect_role(job_title, sector=sector)

    if sector and role:
        sector_data = PLAYBOOK.get(sector, {})
        entry = sector_data.get(role)
        if entry:
            return PlaybookMatch(
                sector=sector,
                requested_role=role,
                matched_role=role,
                match_type="exact",
                entry=entry,
            )
        # Cargo encontrado mas não neste setor: tenta com sector do role_key
        fallback_sector = _ROLE_TO_SECTOR.get(role)
        if fallback_sector:
            fallback_entry = PLAYBOOK.get(fallback_sector, {}).get(role)
            if fallback_entry:
                return PlaybookMatch(
                    sector=fallback_sector,
                    requested_role=role,
                    matched_role=role,
                    match_type="role_sector_fallback",
                    entry=fallback_entry,
                )

    if role and not sector:
        # Derivar setor a partir do role e tentar PLAYBOOK
        fallback_sector = _ROLE_TO_SECTOR.get(role)
        if fallback_sector:
            fallback_entry = PLAYBOOK.get(fallback_sector, {}).get(role)
            if fallback_entry:
                return PlaybookMatch(
                    sector=fallback_sector,
                    requested_role=role,
                    matched_role=role,
                    match_type="role_only",
                    entry=fallback_entry,
                )

    return None


def get_lead_playbook(lead: object) -> PlaybookEntry | None:
    """Retorna o PlaybookEntry mais relevante para o lead.

    Usa `lead.industry` e `lead.job_title` para detectar setor e cargo.
    Retorna None se não houver correspondência suficientemente específica.
    """
    match = get_lead_playbook_match(lead)
    if match is None:
        return None
    return match.entry


def score_lead_icp(lead: object) -> str:
    """Retorna 'primary', 'secondary' ou 'unknown' com base no ICP da Composto Web.

    ICP primário: 100-1000 funcionários, setores prioritários, cargo decisor.
    ICP secundário: 10-100 funcionários (PMEs).
    """
    industry: str | None = getattr(lead, "industry", None)
    job_title: str | None = getattr(lead, "job_title", None)
    company_size: str | None = getattr(lead, "company_size", None)

    sector = detect_sector(industry)
    role = detect_role(job_title, sector=sector)

    # Setores prioritários do ICP primário
    primary_sectors = {"financeiro", "juridico", "saude", "industria", "varejo", "ti"}

    # Cargos decisores (poder de compra R$20k+)
    decision_roles = {
        "cfo",
        "coo",
        "ceo_cto_ti",
        "ceo_ecommerce",
        "ceo_agencia",
        "ceo_fintech",
        "diretor_industrial",
        "diretor_juridico",
        "diretor_clinica",
        "diretor_comercial",
        "diretor_agro",
        "chro",
        "cmo",
        "socio_advocacia",
    }

    # Estimativa de porte via company_size
    is_large = False
    is_medium = False
    if company_size:
        size_lower = company_size.lower()
        large_signals = ["201-500", "501-1000", "1001-5000", "5000+", ">200", ">500", "grande"]
        medium_signals = ["51-200", "101-200", "11-50", "50-200"]
        if any(s in size_lower for s in large_signals):
            is_large = True
        elif any(s in size_lower for s in medium_signals):
            is_medium = True

    # Pontuação
    score = 0
    if sector in primary_sectors:
        score += 2
    if role in decision_roles:
        score += 2
    if is_large:
        score += 2
    elif is_medium:
        score += 1

    if score >= 4:
        return "primary"
    if score >= 2:
        return "secondary"
    return "unknown"
