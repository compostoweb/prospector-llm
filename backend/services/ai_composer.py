"""
services/ai_composer.py

Gera mensagens personalizadas para cada step da cadência.
Totalmente agnóstico ao provedor — usa LLMRegistry com o provider/modelo
configurado na cadência.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import structlog

from integrations.llm import LLMMessage, LLMRegistry, LLMResponse, LLMUsageContext
from models.cadence import Cadence
from models.lead import Lead
from services.outreach_playbook import PlaybookEntry, get_lead_playbook
from services.sector_templates import get_few_shot_example, get_few_shot_match

logger = structlog.get_logger()

PromptContext = Mapping[str, object]


@dataclass(frozen=True)
class CompositionContext:
    """Metadados usados para compor uma mensagem do AI Composer."""

    generation_mode: str
    step_key: str
    copy_method: str | None
    playbook_sector: str | None
    playbook_role: str | None
    matched_role: str | None
    few_shot_applied: bool
    few_shot_key: str | None
    few_shot_method: str | None
    has_site_summary: bool
    has_recent_posts: bool


def serialize_composition_context(context: CompositionContext) -> dict[str, object]:
    """Serializa o contexto de composição para logs e APIs."""

    return asdict(context)

COMPOSER_SYSTEM_PROMPT = """
Você é um profissional sênior de desenvolvimento de negócios que atua em prospecção consultiva B2B de alto nível.
Seus interlocutores são decisores de médias e grandes empresas (mercado enterprise).
Sua missão: criar relacionamentos genuínos antes de qualquer conversa comercial.

PRINCÍPIOS INEGOCIÁVEIS:

1. PESQUISA VISÍVEL — Demonstre que pesquisou o lead: referencie cargo, empresa, setor, notícia, post recente, contratações, vagas, eventos ou desafio específico do segmento. Pesquise AMBOS os perfis: corporativo (notícias, produtos, eventos, contratações, vagas) e pessoal (postagens, curtidas, compartilhamentos, tempo de empresa, histórico profissional). Nunca pareça genérico.

2. TOM EXECUTIVO 2026 — Profissional, direto, humano. Escreva como um par de mercado, não como vendedor. Sem bajulação, sem formalismo excessivo, sem gírias. Como quem fala entre iguais.

3. ZERO CLICHÊS DE VENDAS — NUNCA use:
   - "agenda de 15/20/30 minutos", "call rápida", "reunião breve", "bate papo rápido"
   - "gostaria de apresentar", "nossa solução", "parceria estratégica"
   - "espero que esteja bem", "tudo certo por aí?"
   - "revolucionar", "transformar", "potencializar", "alavancar"
   - "sinergia", "win-win", "game-changer"
   - "Meu nome é... e eu trabalho na..." (o lead já vê seu nome e empresa no remetente/perfil)
   - "Estamos ajudando empresas como a sua a..." (suposição genérica massificada)
   - "aumente sua lucratividade", "reduza custos", "faz sentido?", "impacto nos seus lucros"
   - "maior eficiência", "inovação", "otimização", "gestão inteligente"
   - Qualquer CTA que soe como template de SDR

4. CTAs INTELIGENTES (baixo atrito) — NUNCA peça reunião diretamente. Em vez disso:
   - Pergunta aberta sobre a opinião/experiência do lead ("como vocês estão encarando X?")
   - Pergunta binária sim/não conectada a um benefício real
   - Convite para trocar experiências sobre um tema relevante do setor
   - Provocação com dado ou tendência e pergunta reflexiva
   - Oferecer um recurso valioso (artigo, estudo, dado) e pedir feedback
   - Sugerir casualmente continuar a conversa ("podemos continuar por aqui ou por email?")
   - NUNCA: "Podemos agendar uma call?", "Tem 15 minutos?", "Tem agenda dia tal?", "Tem 5 minutos para uma rápida conversa?"

5. RELACIONAMENTO PRIMEIRO — Os primeiros steps são 100% networking. Só a partir de follow-ups tardios ou breakup é aceitável mencionar (sutilmente) como você pode agregar valor. No LinkedIn, o pedido de conexão NÃO É a abordagem — é apenas a porta de entrada.

6. PERSONALIZAÇÃO RADICAL — Use todos os dados disponíveis: nome, cargo, empresa, setor, porte, localização, posts, notícias, contexto do site, contratações recentes, vagas abertas, eventos. Quanto mais específico, melhor. A primeira frase é tão importante quanto o assunto do email.

7. BREVIDADE — Respeite os limites de cada step. Decisores não lêem textos longos. Cada frase deve ter propósito. Vá direto ao ponto — não enrole.

8. NUNCA SE APRESENTE — Seu nome e empresa já estão visíveis no remetente (email) ou perfil (LinkedIn). Não desperdice a primeira frase com "Meu nome é..." ou "Trabalho na...". Use a primeira frase para gerar IMPACTO.

9. MÉTODOS DE COPY — Use técnicas comprovadas de copywriting para cold outreach:
   - AIRE (Atenção-Interesse-Referência-Estímulo): Atenção sobre o lead (não sobre você), interesse com algo que ele pode melhorar/lucrar, referência com prova social/autoridade, estímulo com CTA de opções
   - DIS (Dor-Implicação-Solução): Só usar quando temos certeza da "dor" do segmento. Descrever a dor → mostrar implicação → CTA com solução via pergunta
   - DPO (Dor-Prazer-Objetividade): Cenário atual com dor vs. cenário futuro sem dor. Muito curto e direto
   - BINÁRIO (Observação-Pergunta Binária): Ultra-conciso. Constatação verdadeira + pergunta sim/não como CTA
   - INSIGHT (Recurso Externo-Contexto-Conexão): Posicionar-se como consultor. Trazer estudo/relatório/notícia de terceiros, explicar relevância, conectar com sua solução
   Escolha o método mais adequado ao contexto do step e dados disponíveis. Varie entre eles.

FORMATO: Retorne APENAS o texto da mensagem. Sem assunto separado, sem "[nome]" como placeholder, sem assinatura. Use o nome real do lead quando disponível.
FORMATAÇÃO PROIBIDA: NUNCA use travessões (—, –, -) como pontuação ou para separar ideias. Use ponto final, vírgula ou ponto e vírgula. Travessões soam artificiais e robóticos em mensagens diretas e áudios.
""".strip()


# ── Instruções específicas por tipo de step ───────────────────────────

STEP_INSTRUCTIONS: dict[str, str] = {
    "linkedin_connect": """
TIPO: Convite de conexão LinkedIn
OBJETIVO: Ser aceito. Puro networking. O pedido de conexão NÃO é a abordagem.

Regras:
- MÁXIMO 170 CARACTERES (limite real do LinkedIn — não ultrapasse!)
- 1-2 frases curtas, direto ao ponto
- Mencione algo CONCRETO: setor em comum, publicação que viu, evento, atuação da empresa, tema de interesse mútuo
- Tom: de igual para igual, como quem admira o trabalho e quer trocar ideia
- PROIBIDO: mencionar produto, serviço, "parceria", "oportunidade", pedir reunião, vender
- PROIBIDO: usar a nota de conexão como abordagem comercial

Bons exemplos de estilo:
- "[Nome], acompanho o que a [empresa] faz em [setor] — seria bom nos conectarmos."
- "[Nome], temos [tema] como interesse em comum, gostaria de fazer parte da sua rede."
- "[Nome], faço parte do mesmo universo de [setor]. Quero trocar informações e experiências."
""".strip(),

    "linkedin_dm_first": """
TIPO: Primeira DM LinkedIn (sem conexão prévia ou conexão antiga)
OBJETIVO: Abrir diálogo genuíno, gerar curiosidade. Use a ABORDAGEM OBJETIVA RELACIONAL.

A abordagem Objetiva Relacional é direta mas usa uma pergunta para gerar resposta e engajamento.
NÃO é discurso de vendas, NÃO é apresentação — é uma pergunta inteligente que abre conversa.

Regras:
- Máximo 120 palavras, 2-3 parágrafos curtos
- Inicie com referência específica: post recente, notícia da empresa, movimento do setor, desafio do cargo
- Use uma das técnicas: BINÁRIO (observação + pergunta sim/não) ou INSIGHT (recurso externo + contexto + conexão)
- Termine com pergunta aberta sobre a experiência/visão do lead ("como vocês estão encarando X?", "vocês costumam explorar Y ou tudo é feito internamente?")
- PROIBIDO: apresentar produto, enviar link, pedir reunião, "apenas 5 minutos", se apresentar
- Tom: colega curioso do setor que achou algo relevante

Bom exemplo de estilo:
"[Nome], vi que a [empresa] abriu [filial/vaga/evento] recentemente. Seria útil [benefício específico] sem [dor conhecida]?"
""".strip(),

    "linkedin_dm_post_connect": """
TIPO: Primeira DM logo após convite de conexão aceito
OBJETIVO: Agradecer e criar primeira interação de valor. Use ABORDAGEM OBJETIVA RELACIONAL ou FATIADA.

A abordagem OBJETIVA RELACIONAL agradece e já faz uma pergunta para gerar engajamento.
A abordagem FATIADA agradece e oferece algo de valor (artigo, estudo, insight) sem pressa.

Regras:
- Máximo 120 palavras, 2-3 parágrafos curtos
- Abra agradecendo de forma natural e breve ("Valeu por conectar!", "Que bom ter você na rede", "Obrigado por aceitar!")
- Traga IMEDIATAMENTE um ponto de interesse: referência ao trabalho da empresa, tendência do setor, ou algo do perfil
- Use UMA dessas estratégias:
  a) Pergunta inteligente sobre o mercado/atuação ("Vocês costumam [ação do setor] ou preferem [alternativa]?")
  b) Compartilhe algo de valor (artigo, dado, estudo) e peça opinião
  c) Pergunte algo que demonstre interesse genuíno pelo trabalho deles
- PROIBIDO: vender, apresentar serviço, pedir call, discurso corporativo
- Tom: grato mas não bajulador, curioso, de networking profissional
""".strip(),

    "linkedin_dm_post_connect_voice": """
TIPO: Áudio de boas-vindas após conexão aceita (será convertido em TTS)
OBJETIVO: Causar impacto pessoal e memorável com formato diferenciado.

Regras:
- Máximo 80 palavras (lido em voz alta, deve ser fluido — ~25 segundos)
- Escreva como FALA natural — frases curtas, ritmo de conversa
- Comece com o nome do lead de forma natural
- Agradeça a conexão de forma rápida
- Mencione algo específico sobre a empresa ou atuação que chamou atenção
- Termine com convite leve para trocar ideia sobre tema do setor
- PROIBIDO: bullet points, links, formatação, linguagem formal demais, se apresentar
- Tom: áudio profissional mas descontraído — como se falasse com um conhecido da área

Exemplo de tom:
"[Nome], valeu por conectar! Vi que a [empresa] tá fazendo um trabalho muito legal em [setor]... queria trocar uma ideia sobre [tema]. Fica à vontade pra me responder quando puder!"
""".strip(),

    "linkedin_dm_voice": """
TIPO: DM LinkedIn com áudio (será convertido em TTS)
OBJETIVO: Gerar proximidade e se destacar pelo formato de áudio.

Regras:
- Máximo 100 palavras (lido em voz alta, deve soar natural — ~35 segundos)
- Escreva como FALA — frases curtas, ritmo de conversa, natural
- Comece com o nome do lead
- Use linguagem oral suave: "olha", "veja", "é o seguinte" — mas sem gírias ou informalidade excessiva
- Compartilhe um micro-insight ou dado curioso do setor e convide para conversar
- PROIBIDO: bullet points, links, formatação — é um áudio
- PROIBIDO: pedir reunião, mencionar produto diretamente, se apresentar formalmente
- Tom: próximo, executivo mas humano, como um áudio profissional entre pares
""".strip(),

    "linkedin_dm_followup": """
TIPO: Follow-up LinkedIn DM (lead não respondeu)
OBJETIVO: Reengajar sem parecer insistente, trazendo valor novo. Use técnica FATIADA — sem pressa.

Na abordagem FATIADA, cada mensagem traz um elemento novo de valor sem repetir o anterior.
Pode compartilhar conteúdo, notícia, informação de mercado ou fazer uma pergunta de curiosidade.

Regras:
- Máximo 100 palavras, 2 parágrafos curtos
- NÃO repita contexto da mensagem anterior
- Traga algo NOVO: notícia recente do setor, dado/insight relevante, tendência, artigo, case anônimo
- Conecte o insight ao contexto da empresa do lead ("vi que o setor de vocês está passando por X")
- Use métodos: BINÁRIO (observação + pergunta direta) ou INSIGHT (recurso externo + contexto)
- CTA: pergunta leve sobre experiência/opinião, ou oferta de recurso útil
- PROIBIDO: "só passando para...", "voltando ao assunto", tom de cobrança, "tudo bem?"
- Tom: útil, estratégico, como quem compartilha algo interessante com um colega
""".strip(),

    "linkedin_dm_breakup": """
TIPO: Mensagem de despedida / último contato LinkedIn
OBJETIVO: Última tentativa elegante, porta aberta para o futuro. Use tom de NETWORKING, não de vendas.

Regras:
- Máximo 80 palavras, 1-2 parágrafos
- Reconheça que o timing pode não ser o ideal (sem passividade agressiva)
- Resuma em 1 frase o tipo de valor que poderia trocar (não vender)
- Sinalize que é o último contato por ora ("não quero ser inconveniente")
- Deixe a porta aberta: "quando fizer sentido, fico à disposição"
- Use frases de quebra de padrão — o decisor pode não estar aberto mas um tom diferente pode chamar atenção
- PROIBIDO: tom de culpa, manipulação, "último e-mail", urgência falsa, "estou desistindo"
- Tom: maduro, respeitoso, como encerrar uma tentativa de networking que pode ser retomada no futuro
""".strip(),

    "email_first": """
TIPO: Primeiro email frio (cold mail)
OBJETIVO: Captar atenção em 5 segundos, abrir conversa. A PRIMEIRA FRASE É TÃO IMPORTANTE QUANTO O ASSUNTO.

FORMATO OBRIGATÓRIO — Retorne EXATAMENTE este JSON (sem markdown, sem comentários):
{"subject": "Assunto do email aqui", "body": "Corpo do email aqui"}

Regras do ASSUNTO (subject):
- Máximo 8 palavras
- Específico ao lead/empresa/setor/dor — nunca genérico
- PROIBIDO: "Uma ideia para", "proposta", "oportunidade", "parceria", "apresentação"
- Banco de estilos de alto open-rate (USE COMO REFERÊNCIA, ADAPTE AO LEAD):
  • "Sua recepção ainda agenda manualmente?"
  • "Fechamento mensal da [Empresa]: de dias para horas"
  • "O dado chega tarde para sua decisão?"
  • "Engenheiro sênior resolvendo ticket de suporte"
  • "Agência cresce, margem não acompanha?"
  • "Obrigações acessórias manuais: o risco que cresce"
  • "Contratos críticos sem controle centralizado"
  • "O cliente liga e você abre cinco sistemas"
  • "Antes de contratar mais alguém no time"
  • "O que está escapando da sua operação hoje"

Não comece com apresentação — vá direto ao ponto. Seu nome já está no remetente.
Escolha o método de copy mais adequado aos dados disponíveis:

MÉTODOS DISPONÍVEIS (escolha 1):
- AIRE: Atenção (sobre ELE, não você) → Interesse (algo que pode melhorar/lucrar) → Referência (prova social/autoridade) → Estímulo (CTA com opções)
- DIS: Dor que o segmento certamente tem → Implicação da dor → Solução via pergunta (baseado em SPIN Selling, use quando a dor do segmento é conhecida)
- DPO: Cenário com dor genérica → Cenário futuro positivo sem a dor → CTA objetivo e direto (muito curto)
- BINÁRIO: Observação verdadeira e relevante → Pergunta fechada sim/não direcionada ao benefício (ultra-conciso)
- INSIGHT: Recurso externo (estudo, relatório, notícia) → Contexto/relevância → Conexão com sua solução → CTA pergunta binária (posiciona como consultor)

Regras:
- Máximo 150 palavras, 2-3 parágrafos curtos
- Primeira frase: hook personalizado — referência ao lead, empresa, setor, desafio ou movimento recente. O lead deve pensar "essa pessoa me pesquisou"
- Corpo: valor real — dado, tendência, observação de mercado, prova social. NÃO é pitch
- CTA: de baixo atrito — pergunta de opinião, pergunta binária, ou convite para troca de perspectiva. NUNCA "agendar uma call"
- Tom: direto, conciso, como email entre executivos que se respeitam
- PROIBIDO: apresentar produto, mencionar preço, mandar case study, "gostaria de apresentar", "meu nome é"

Exemplo de método BINÁRIO:
"[Nome], vi que o reajuste médio de [tema do setor] bateu [X%] este semestre. Seria prioridade para você manter [benefício] sem aceitar esse aumento?"

Exemplo de método INSIGHT:
"[Nome], a [fonte respeitada] publicou um estudo sobre [tema relevante]. Como a [empresa] tem investido forte em [área], achei que gostaria de ver. Vocês já estão mapeando [métrica] x [resultado]?"
""".strip(),

    "email_followup": """
TIPO: Follow-up por email (lead não respondeu o primeiro)
OBJETIVO: Reengajar com conteúdo novo, demonstrar persistência inteligente. Use método DIFERENTE do anterior.

FORMATO OBRIGATÓRIO — Retorne EXATAMENTE este JSON (sem markdown, sem comentários):
{"subject": "Assunto do email aqui", "body": "Corpo do email aqui"}

Regras do ASSUNTO (subject):
- Máximo 8 palavras, novo ângulo — nunca idêntico ao email anterior
- Estilos de follow-up de alto open-rate (ADAPTE AO LEAD):
  • "Re: [tema novo do setor]"
  • "Dado que vi sobre [setor] e lembrei de você"
  • "Um ângulo diferente sobre [dor confirmada]"
  • "[Empresa]: [métrica relativa ao setor]?"

Se o primeiro email usou BINÁRIO, agora use INSIGHT ou DIS.
Se usou INSIGHT, agora use DPO ou BINÁRIO.
SEMPRE traga um ângulo novo — nunca repita a mesma estrutura.

Regras:
- Máximo 120 palavras, 2-3 parágrafos curtos
- NÃO comece com "só passando para dar um follow-up", "voltando ao email anterior" ou "espero que esteja bem"
- Traga algo NOVO e relevante: dado do mercado, case anônimo, notícia do setor, tendência, estudo
- Conecte a novidade ao contexto do lead/empresa
- CTA renovado: ângulo diferente do primeiro email (se perguntou opinião, agora ofereça recurso; se ofereceu recurso, agora faça pergunta binária)
- Referência sutil à tentativa anterior pode existir mas NÃO é obrigatória
- Tom: consultivo, como quem compartilha inteligência de mercado entre pares
- Use técnica de NUTRIÇÃO: informações, dados, estudos que agreguem valor real
""".strip(),

    "email_breakup": """
TIPO: Email de despedida / último contato
OBJETIVO: Última tentativa respeitosa, criar senso de fechamento. Pode ser o método DPO ou BINÁRIO pela brevidade.

FORMATO OBRIGATÓRIO — Retorne EXATAMENTE este JSON (sem markdown, sem comentários):
{"subject": "Assunto do email aqui", "body": "Corpo do email aqui"}

Regras do ASSUNTO:
- Máximo 8 palavras, tom de fechamento natural
- Exemplos: "Encerrando o contato por enquanto", "Última mensagem por ora", "Deixo a porta aberta"

Regras:
- Máximo 100 palavras, 2 parágrafos
- Reconheça que pode não ser prioridade agora (sem pressão)
- Resuma em 1 frase a contribuição/valor possível (alto nível, sem detalhar)
- Sinalize claramente que é a última mensagem por ora
- Ofereça retomar no futuro quando fizer sentido
- Use frase de quebra de padrão para se destacar do ruído na inbox
- PROIBIDO: urgência falsa, escassez artificial, "última chance", tom passivo-agressivo, "estou desistindo de você"
- Tom: profissional, maduro, como encerrar uma porta que pode reabrir naturalmente

Exemplo de estilo:
"[Nome], sei que [tema] talvez não seja prioridade agora. Deixo a porta aberta — quando quiser trocar uma ideia sobre [benefício real], estou por aqui. Um abraço."
""".strip(),

    "linkedin_post_comment": """
TIPO: Comentário em post recente do lead no LinkedIn
OBJETIVO: Gerar reciprocidade e visibilidade — aparecer de forma positiva no radar do lead antes da abordagem direta.

Regras:
- MÁXIMO 2 frases curtas (até 280 caracteres no total)
- Use o conteúdo do post do lead (disponível em POSTS RECENTES DO LEAD) para criar um comentário genuíno e específico
- Demonstre que leu e entendeu o post — nunca pareça genérico ou bajulador
- Adicione perspectiva: concorde com dado, amplie o raciocínio, traga analogia do setor, ou faça uma pergunta inteligente
- Tom: colega do setor que achou o ponto de vista interessante — positivo mas com substância
- PROIBIDO: "Que post incrível!", "Excelente perspectiva!", bajulação vazia
- PROIBIDO: se apresentar, mencionar produto, incluir links, pedir reunião
- PROIBIDO: comentário genérico que poderia servir para qualquer post

Bons exemplos de estilo:
"Dado importante esse sobre [X]. Na prática tenho visto [empresas do setor] adotando [Y] com resultados interessantes — curioso saber como vocês encaram isso."
"Esse ponto sobre [tema] ressoa bastante. Exatamente o que os times de [cargo] mais sentem quando [situação]. Boa observação."
""".strip(),

    "linkedin_inmail": """
TIPO: InMail LinkedIn (mensagem para não-conexão, requer Premium)
OBJETIVO: Primeira abordagem direta a alguém fora da rede — objetivo é iniciar diálogo genuíno.

O InMail é uma oportunidade rara e valiosa com leads fora da sua rede. Use com o mesmo rigor de um cold email premium.
O ASSUNTO é fundamental — é a primeira coisa que o lead vê.

FORMATO DE SAÍDA — Retorne EXATAMENTE este JSON (sem markdown, sem comentários):
{"subject": "Assunto do InMail aqui", "body": "Corpo do InMail aqui"}

Regras do ASSUNTO (subject):
- Máximo 60 caracteres
- Específico e intrigante — referencia algo real do lead/empresa/setor
- PROIBIDO: "Oportunidade", "Parceria", "Proposta", "Novidade", soa comercial demais
- Bons exemplos: "[Empresa] + [tendência do setor]", "[Cargo] que enfrenta [desafio específico]", "Pergunta sobre [tema que o lead postou/comentou]"

Regras do CORPO (body):
- Máximo 200 palavras, 3 parágrafos curtos
- Parágrafo 1: hook específico — o que te motivou a contatar (post, notícia, cargo, empresa, dado do setor)
- Parágrafo 2: contexto de valor — dado, insight, problema que você observa no setor ou no perfil do lead
- Parágrafo 3: CTA de baixo atrito — pergunta de opinião ou binária. NUNCA "agendar call"
- PROIBIDO: apresentação comercial, "nossa solução", preços, links de calendário
- Tom: executivo, curioso, peer-to-peer — como se escrevesse para um contato de segundo grau
""".strip(),
}


class AIComposer:

    def __init__(self, registry: LLMRegistry) -> None:
        self._registry = registry

    async def compose(
        self,
        lead: Lead,
        channel: str,               # "linkedin_connect" | "linkedin_dm" | "email"
        step_number: int,
        context: PromptContext,     # vindo de context_fetcher
        cadence: Cadence,
        total_steps: int = 1,
        use_voice: bool = False,
        previous_channel: str | None = None,
        step_type: str | None = None,
    ) -> str:
        """
        Gera uma mensagem personalizada para o lead/canal/step.
        Usa o provider e modelo configurados na cadência.
        """
        messages, composition_context = prepare_composer_messages(
            lead=lead,
            channel=channel,
            step_number=step_number,
            context=context,
            total_steps=total_steps,
            use_voice=use_voice,
            previous_channel=previous_channel,
            cadence=cadence,
            step_type=step_type,
        )

        response: LLMResponse = await self._registry.complete(
            messages=messages,
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=cadence.llm_temperature,
            max_tokens=cadence.llm_max_tokens,
            usage_context=LLMUsageContext(
                tenant_id=str(lead.tenant_id),
                module="cadence",
                task_type="compose_message",
                feature=channel,
                entity_type="lead",
                entity_id=str(lead.id),
                secondary_entity_type="cadence",
                secondary_entity_id=str(cadence.id),
                metadata={"step_number": step_number},
            ),
        )
        response.raw["composition_context"] = serialize_composition_context(composition_context)

        logger.info(
            "ai_composer.composed",
            lead_id=str(lead.id),
            channel=channel,
            step=step_number,
            provider=response.provider,
            model=response.model,
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
            generation_mode=composition_context.generation_mode,
            step_key=composition_context.step_key,
            copy_method=composition_context.copy_method,
            playbook_sector=composition_context.playbook_sector,
            playbook_role=composition_context.playbook_role,
            matched_role=composition_context.matched_role,
            few_shot_applied=composition_context.few_shot_applied,
            few_shot_key=composition_context.few_shot_key,
        )

        return response.text.strip()

    async def compose_email(
        self,
        lead: Lead,
        step_number: int,
        context: PromptContext,
        cadence: Cadence,
        step_type: str | None = None,
        total_steps: int = 1,
        previous_channel: str | None = None,
    ) -> tuple[str, str]:
        """Gera subject + body de email via LLM (retorna JSON internamente).

        Returns:
            Tuple[subject, body] — ambos como strings limpas.
        """
        messages, composition_context = prepare_composer_messages(
            lead=lead,
            channel="email",
            step_number=step_number,
            context=context,
            total_steps=total_steps,
            previous_channel=previous_channel,
            cadence=cadence,
            step_type=step_type,
        )

        response: LLMResponse = await self._registry.complete(
            messages=messages,
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=cadence.llm_temperature,
            max_tokens=cadence.llm_max_tokens,
            usage_context=LLMUsageContext(
                tenant_id=str(lead.tenant_id),
                module="cadence",
                task_type="compose_email",
                feature="email",
                entity_type="lead",
                entity_id=str(lead.id),
                secondary_entity_type="cadence",
                secondary_entity_id=str(cadence.id),
                metadata={"step_number": step_number},
            ),
        )
        response.raw["composition_context"] = serialize_composition_context(composition_context)

        raw = response.text.strip()

        # Parse JSON gerado pelo LLM
        subject, body = _parse_email_json(raw, lead=lead, step_number=step_number)

        logger.info(
            "ai_composer.compose_email",
            lead_id=str(lead.id),
            step=step_number,
            provider=response.provider,
            model=response.model,
            subject_len=len(subject),
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
            generation_mode=composition_context.generation_mode,
            step_key=composition_context.step_key,
            copy_method=composition_context.copy_method,
            playbook_sector=composition_context.playbook_sector,
            playbook_role=composition_context.playbook_role,
            matched_role=composition_context.matched_role,
            few_shot_applied=composition_context.few_shot_applied,
            few_shot_key=composition_context.few_shot_key,
        )

        return subject, body


def prepare_composer_messages(
    lead: Any,
    channel: str,
    step_number: int,
    context: PromptContext,
    *,
    total_steps: int = 1,
    use_voice: bool = False,
    previous_channel: str | None = None,
    cadence: Cadence | None = None,
    step_type: str | None = None,
) -> tuple[list[LLMMessage], CompositionContext]:
    """Prepara mensagens do LLM e contexto de composição para observabilidade."""

    user_prompt, composition_context = _build_user_prompt(
        lead=lead,
        channel=channel,
        step=step_number,
        context=context,
        total_steps=total_steps,
        use_voice=use_voice,
        previous_channel=previous_channel,
        cadence=cadence,
        step_type=step_type,
    )

    messages = [
        LLMMessage(role="system", content=COMPOSER_SYSTEM_PROMPT),
        LLMMessage(role="user", content=user_prompt),
    ]
    return messages, composition_context


def _parse_email_json(raw: str, lead: object, step_number: int) -> tuple[str, str]:
    """Extrai (subject, body) do JSON retornado pelo LLM.

    Resiliente: se o parse falhar, retorna um subject de fallback simples
    e o texto bruto como body.
    """
    # Normaliza markdown code fences que alguns modelos adicionam
    text = raw
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove a primeira (``` ou ```json) e a última (```)
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
        subject = str(data.get("subject", "")).strip()
        body = str(data.get("body", "")).strip()
        if subject and body:
            return subject, body
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: o LLM gerou texto puro (sem JSON). Usa texto como body.
    company = getattr(lead, "company", None) or getattr(lead, "name", "você")
    fallback_subject = f"Uma ideia para {company}" if step_number == 1 else f"Re: Uma ideia para {company}"
    return fallback_subject, raw


def _select_copy_method(
    step_key: str,
    lead: Any,
    playbook_entry: PlaybookEntry | None,
    context: PromptContext,
    step_number: int = 1,
    total_steps: int = 1,
) -> str | None:
    """Seleciona o método de copy mais adequado para o step.

    Retorna uma das strings: 'AIRE' | 'DIS' | 'DPO' | 'BINÁRIO' | 'INSIGHT',
    ou None quando o step não usa método de copy (ex: linkedin_connect).
    """
    # Steps que não usam método de copy estruturado
    if step_key in ("linkedin_connect", "linkedin_post_comment", "linkedin_dm_post_connect_voice"):
        return None

    # Breakup → DPO (brevidade máxima)
    if step_key in ("email_breakup", "linkedin_dm_breakup"):
        return "DPO"

    # Posts recentes disponíveis → BINÁRIO é o mais eficaz
    has_posts = bool(getattr(lead, "linkedin_recent_posts_json", None))
    has_site = bool(context.get("site_summary") and context.get("site_summary") != "Não disponível")

    # Follow-ups com posts → BINÁRIO; com site/notícias → INSIGHT
    is_followup = step_key in ("email_followup", "linkedin_dm_followup")
    if is_followup:
        if has_posts:
            return "BINÁRIO"
        if has_site:
            return "INSIGHT"
        return "DPO"

    # Primeiro contato: dor confirmada pelo playbook → DIS
    if playbook_entry and step_number <= 2:
        return "DIS"

    # Posts disponíveis no primeiro contato → BINÁRIO
    if has_posts and step_number <= 2:
        return "BINÁRIO"

    # Default para primeiro contato sem dados extras
    return "AIRE"


_COPY_METHOD_DEFINITIONS: dict[str, str] = {
    "AIRE": "Atenção (sobre o lead, não sobre você) → Interesse (algo que ele pode melhorar) → Referência (prova social/autoridade) → Estímulo (CTA com opções).",
    "DIS": "Dor (cenário que o lead certamente reconhece) → Implicação (custo real de não resolver) → Solução (oferecer como pergunta, não afirmação). Use quando a dor do setor é conhecida.",
    "DPO": "Dor (cenário atual com o problema) → Prazer (cenário futuro sem o problema) → Objetividade (CTA curtíssimo e direto). Ideal para brevidade.",
    "BINÁRIO": "Observação verdadeira e relevante sobre o lead ou setor → Pergunta fechada sim/não direcionada ao benefício. Ultra-conciso e eficaz quando há dado específico.",
    "INSIGHT": "Recurso externo (estudo, relatório, notícia de terceiros) → Contexto (por que aquilo importa para este lead) → Conexão (como se relaciona com a dor dele) → Pergunta reflexiva. Posiciona como consultor.",
}


def _build_user_prompt(
    lead: Any,
    channel: str,
    step: int,
    context: PromptContext,
    total_steps: int = 1,
    use_voice: bool = False,
    previous_channel: str | None = None,
    cadence: Cadence | None = None,
    step_type: str | None = None,
) -> tuple[str, CompositionContext]:
    site_summary = context.get("site_summary", "Não disponível")
    linkedin_post = context.get("recent_linkedin_post", "Não disponível")
    news = context.get("company_news", "Nenhuma notícia recente")
    has_site_summary = bool(site_summary and site_summary != "Não disponível")
    lead_name = str(getattr(lead, "name", "Lead"))
    lead_job_title = getattr(lead, "job_title", None)
    lead_company = getattr(lead, "company", None)
    lead_industry = getattr(lead, "industry", None)
    lead_company_size = getattr(lead, "company_size", None)
    lead_segment = getattr(lead, "segment", None)
    lead_location = getattr(lead, "location", None)
    lead_city = getattr(lead, "city", None)
    lead_linkedin_url = getattr(lead, "linkedin_url", None)
    recent_posts_json = getattr(lead, "linkedin_recent_posts_json", None)

    # Posts recentes do lead (cache armazenado no modelo)
    recent_posts_block = ""
    has_recent_posts = False
    if recent_posts_json:
        try:
            import json as _json  # noqa: PLC0415
            posts_data = _json.loads(recent_posts_json)
            if posts_data:
                has_recent_posts = True
                lines = ["POSTS RECENTES DO LEAD NO LINKEDIN:"]
                for idx, p in enumerate(posts_data[:3], 1):
                    content = (p.get("content") or "").strip()
                    published = p.get("published_at", "")
                    if content:
                        lines.append(f"Post {idx} ({published[:10] if published else 'data desconhecida'}): {content[:400]}")
                recent_posts_block = "\n".join(lines)
        except (ValueError, TypeError):
            pass

    step_key = resolve_step_key(
        channel, step, total_steps, use_voice, previous_channel, step_type=step_type,
    )
    step_instruction = STEP_INSTRUCTIONS.get(step_key, "")

    # Dados ricos do lead
    lead_lines = [
        f"Nome: {lead_name}",
        f"Cargo: {lead_job_title or 'Não informado'}",
        f"Empresa: {lead_company or 'Não informado'}",
        f"Setor/indústria: {lead_industry or 'Não informado'}",
        f"Porte da empresa: {lead_company_size or 'Não informado'}",
        f"Segmento: {lead_segment or 'Não informado'}",
        f"Localização: {lead_location or lead_city or 'Não informado'}",
    ]
    if lead_linkedin_url:
        lead_lines.append(f"LinkedIn: {lead_linkedin_url}")

    # ── Playbook estratégico do setor/cargo ───────────────────────────────────
    playbook_entry: PlaybookEntry | None = get_lead_playbook(lead)
    playbook_block = ""
    if playbook_entry:
        playbook_block = f"""PLAYBOOK DO SETOR E CARGO (use para calibrar a abordagem):
Dor principal: {playbook_entry.dor_principal}
Dor secundária: {playbook_entry.dor_secundaria}
Gatilho emocional (o que o cargo carrega internamente): "{playbook_entry.gatilho_emocional}"
Gancho de valor: {playbook_entry.gancho}"""

    # ── Método de copy selecionado ────────────────────────────────────────────
    copy_method = _select_copy_method(
        step_key, lead, playbook_entry, context,
        step_number=step,
        total_steps=total_steps,
    )
    copy_method_block = ""
    if copy_method:
        definition = _COPY_METHOD_DEFINITIONS.get(copy_method, "")
        copy_method_block = f"MÉTODO OBRIGATÓRIO PARA ESTE STEP: {copy_method}\n{definition}"

    # ── Contexto da cadência (segmento-alvo, persona, oferta) ─────────────────
    cadence_context_lines: list[str] = []
    if cadence:
        if cadence.target_segment:
            cadence_context_lines.append(f"Segmento-alvo desta campanha: {cadence.target_segment}")
        if cadence.persona_description:
            cadence_context_lines.append(f"Persona ideal: {cadence.persona_description}")
        if cadence.offer_description:
            cadence_context_lines.append(f"O que oferecemos (use com sutileza, SÓ em steps avançados): {cadence.offer_description}")
        if cadence.tone_instructions:
            cadence_context_lines.append(f"Instruções extras de tom: {cadence.tone_instructions}")

    cadence_block = "\n".join(cadence_context_lines) if cadence_context_lines else "Não configurado"

    # Monta o prompt final
    blocks: list[str] = [step_instruction, "---", "DADOS DO LEAD:", chr(10).join(lead_lines)]

    if playbook_block:
        blocks.append(f"\n{playbook_block}")

    if copy_method_block:
        blocks.append(f"\n{copy_method_block}")

    # ── Few-shot de referência por setor ──────────────────────────────────────
    few_shot_block = get_few_shot_example(
        sector=playbook_entry.sector if playbook_entry else None,
        role=playbook_entry.role if playbook_entry else None,
        channel=channel,
        step_key=step_key,
    )
    few_shot_match = get_few_shot_match(
        sector=playbook_entry.sector if playbook_entry else None,
        role=playbook_entry.role if playbook_entry else None,
        channel=channel,
        step_key=step_key,
    )
    if few_shot_block:
        blocks.append(f"\n{few_shot_block}")

    blocks += [
        f"\nCONTEXTO DA CAMPANHA:\n{cadence_block}",
        f"\nPESQUISA SOBRE A EMPRESA:\n{site_summary}",
        f"\nPOST RECENTE DO LEAD NO LINKEDIN:\n{linkedin_post}",
    ]

    if recent_posts_block:
        blocks.append(f"\n{recent_posts_block}")

    blocks.append(f"\nNOTÍCIAS RECENTES DA EMPRESA/SETOR:\n{news}")
    blocks.append(f"\nPOSIÇÃO NA CADÊNCIA: Step {step} de {total_steps}.")
    blocks.append("\nEscreva a mensagem agora:")

    composition_context = CompositionContext(
        generation_mode="llm",
        step_key=step_key,
        copy_method=copy_method,
        playbook_sector=playbook_entry.sector if playbook_entry else None,
        playbook_role=playbook_entry.role if playbook_entry else None,
        matched_role=few_shot_match.matched_role if few_shot_match else None,
        few_shot_applied=few_shot_match is not None,
        few_shot_key=(
            f"{few_shot_match.sector}:{few_shot_match.matched_role}:{few_shot_match.channel}:{few_shot_match.step_type}"
            if few_shot_match
            else None
        ),
        few_shot_method=few_shot_match.example.method if few_shot_match else None,
        has_site_summary=has_site_summary,
        has_recent_posts=has_recent_posts or bool(linkedin_post and linkedin_post != "Não disponível"),
    )

    return "\n".join(blocks).strip(), composition_context


def resolve_step_key(
    channel: str,
    step_number: int,
    total_steps: int,
    use_voice: bool = False,
    previous_channel: str | None = None,
    step_type: str | None = None,
) -> str:
    """Resolve qual instrução de step usar.

    Se ``step_type`` foi definido manualmente no template, respeita essa escolha.
    Caso contrário, infere automaticamente baseado no canal, posição, voz e step anterior.
    """
    # Override manual — o usuário escolheu explicitamente o tipo
    if step_type and step_type in STEP_INSTRUCTIONS:
        return step_type

    if channel in ("linkedin_post_comment", "linkedin_inmail"):
        return channel

    if channel == "linkedin_connect":
        return "linkedin_connect"

    if channel == "email":
        if step_number == 1:
            return "email_first"
        if step_number >= total_steps:
            return "email_breakup"
        return "email_followup"

    if channel == "linkedin_dm":
        # Detecta se é o step logo após um linkedin_connect
        is_post_connect = previous_channel == "linkedin_connect"

        if is_post_connect:
            return "linkedin_dm_post_connect_voice" if use_voice else "linkedin_dm_post_connect"
        if use_voice:
            return "linkedin_dm_voice"
        if step_number <= 2:
            return "linkedin_dm_first"
        if step_number >= total_steps:
            return "linkedin_dm_breakup"
        return "linkedin_dm_followup"

    return "linkedin_dm_followup"
