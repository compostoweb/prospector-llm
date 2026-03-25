"""
services/ai_composer.py

Gera mensagens personalizadas para cada step da cadência.
Totalmente agnóstico ao provedor — usa LLMRegistry com o provider/modelo
configurado na cadência.
"""

from __future__ import annotations

import json
import structlog
from integrations.llm import LLMMessage, LLMRegistry, LLMResponse
from models.cadence import Cadence
from models.lead import Lead

logger = structlog.get_logger()

COMPOSER_SYSTEM_PROMPT = """
Você é um profissional sênior de desenvolvimento de negócios que atua em prospecção consultiva B2B de alto nível.
Seus interlocutores são decisores de médias e grandes empresas (mercado enterprise).
Sua missão: criar relacionamentos genuínos antes de qualquer conversa comercial.

PRINCÍPIOS INEGOCIÁVEIS:

1. PESQUISA VISÍVEL — Demonstre que você pesquisou o lead: referencie cargo, empresa, setor, notícia, post recente ou desafio específico do segmento. Nunca pareça genérico.

2. TOM EXECUTIVO 2026 — Profissional, direto, humano. Escreva como um par de mercado, não como vendedor. Sem bajulação, sem formalismo excessivo, sem gírias.

3. ZERO CLICHÊS DE VENDAS — NUNCA use:
   - "agenda de 15/20/30 minutos", "call rápida", "reunião breve"
   - "gostaria de apresentar", "nossa solução", "parceria estratégica"
   - "espero que esteja bem", "tudo certo por aí?"
   - "revolucionar", "transformar", "potencializar", "alavancar"
   - "sinergia", "win-win", "game-changer"
   - Qualquer CTA que soe como template de SDR

4. CTAs INTELIGENTES — Em vez de pedir reunião, use:
   - Compartilhar um insight e perguntar a opinião
   - Convidar para trocar experiências sobre um tema do setor
   - Provocar reflexão com dado ou tendência relevante
   - Sugerir casualmente "seria legal bater um papo sobre isso"
   - Perguntar como o lead está lidando com um desafio real do mercado

5. RELACIONAMENTO PRIMEIRO — Os primeiros steps são 100% networking. Só a partir de follow-ups tardios ou breakup é aceitável mencionar (sutilmente) como você pode agregar valor.

6. PERSONALIZAÇÃO RADICAL — Use todos os dados disponíveis: nome, cargo, empresa, setor, porte, localização, posts, notícias, contexto do site. Quanto mais específico, melhor.

7. BREVIDADE — Respeite os limites de cada step. Decisores não lêem textos longos. Cada frase deve ter propósito.

FORMATO: Retorne APENAS o texto da mensagem. Sem assunto, sem "Olá [nome]," separado, sem assinatura.
""".strip()


# ── Instruções específicas por tipo de step ───────────────────────────

STEP_INSTRUCTIONS: dict[str, str] = {
    "linkedin_connect": """
TIPO: Convite de conexão LinkedIn
OBJETIVO: Ser aceito. Puro networking.

Regras:
- MÁXIMO 50 palavras (LinkedIn trunca convites longos)
- 1-2 frases, direto ao ponto
- Mencione algo CONCRETO: setor em comum, publicação que viu, evento, atuação da empresa
- Tom: de igual para igual, como quem admira o trabalho e quer trocar ideia
- PROIBIDO: mencionar produto, serviço, "parceira", "oportunidade" ou qualquer linguagem comercial
- Bons exemplos de abertura: "Acompanho o que a {empresa} faz em {setor} — seria bom nos conectarmos." / "Vi seu perfil, estou no mesmo segmento e admiro a linha de trabalho de vocês."
""".strip(),

    "linkedin_dm_first": """
TIPO: Primeira DM LinkedIn (sem conexão prévia ou conexão antiga)
OBJETIVO: Abrir diálogo genuíno, gerar curiosidade sobre um tema do setor.

Regras:
- Máximo 120 palavras, 2-3 parágrafos curtos
- Inicie com referência específica: post recente, notícia da empresa, movimento do setor, desafio do cargo
- Construa o interesse: compartilhe um micro-insight ou dado relevante do mercado deles
- Termine com pergunta aberta sobre a experiência/visão do lead ("como vocês estão encarando X?", "curiosa sua visão sobre Y")
- PROIBIDO: apresentar produto, enviar link, pedir reunião, usar "apenas 5 minutos"
- Tom: colega curioso do setor, não vendedor
""".strip(),

    "linkedin_dm_post_connect": """
TIPO: Primeira DM logo após convite de conexão aceito
OBJETIVO: Agradecer a conexão e criar primeira interação de valor.

Regras:
- Máximo 120 palavras, 2-3 parágrafos curtos
- Abra agradecendo de forma natural e breve ("Valeu por conectar!", "Que bom ter você na rede")
- Traga IMEDIATAMENTE um ponto de interesse: referência ao trabalho da empresa, tendência do setor, ou algo específico do perfil do lead
- Desperte curiosidade com uma pergunta inteligente sobre o mercado/atuação deles
- Tom: grato mas não bajulador, curioso, de rede profissional
- PROIBIDO: vender, apresentar serviço, pedir call
""".strip(),

    "linkedin_dm_post_connect_voice": """
TIPO: Áudio de boas-vindas após conexão aceita (será convertido em TTS)
OBJETIVO: Causar impacto pessoal e memorável com formato diferenciado.

Regras:
- Máximo 80 palavras (lido em voz alta, deve ser fluido)
- Escreva como FALA natural — frases curtas, ritmo de conversa
- Comece com "{nome}, tudo bem?" ou similar
- Agradeça a conexão de forma rápida e natural
- Mencione algo específico sobre a empresa ou atuação que chamou atenção
- Termine com convite leve para trocar ideia sobre tema do setor
- PROIBIDO: bullet points, links, formatação, linguagem formal demais
- Tom: como um áudio profissional mas descontraído — como se falasse com um conhecido da área
""".strip(),

    "linkedin_dm_voice": """
TIPO: DM LinkedIn com áudio (será convertido em TTS)
OBJETIVO: Gerar proximidade e se destacar pelo formato de áudio.

Regras:
- Máximo 100 palavras (lido em voz alta, deve soar natural)
- Escreva como FALA — frases curtas, ritmo de conversa, natural
- Comece com o nome do lead
- Use linguagem oral suave: "olha", "veja", "é o seguinte" — mas sem gírias ou informalidade excessiva
- Compartilhe uma ideia/insight e convide o lead a conversar sobre
- PROIBIDO: bullet points, links, formatação — é um áudio
- PROIBIDO: pedir reunião, mencionar produto diretamente
- Tom: próximo, executivo mas humano, como um áudio profissional entre pares
""".strip(),

    "linkedin_dm_followup": """
TIPO: Follow-up LinkedIn DM (lead não respondeu)
OBJETIVO: Reengajar sem parecer insistente, trazendo valor novo.

Regras:
- Máximo 100 palavras, 2 parágrafos curtos
- NÃO repita contexto da mensagem anterior
- Traga algo NOVO: notícia recente do setor, dado/insight relevante, tendência, case anônimo
- Conecte o insight ao contexto da empresa do lead ("vi que o setor de vocês está passando por X")
- CTA: pergunta leve sobre a experiência/opinião deles, ou sugestão de troca de ideias
- PROIBIDO: "só passando para...", "voltando ao assunto", tom de cobrança
- Tom: útil, estratégico, como quem compartilha algo interessante entre pares
""".strip(),

    "linkedin_dm_breakup": """
TIPO: Mensagem de despeida / último contato LinkedIn
OBJETIVO: Última tentativa elegante, porta aberta para o futuro.

Regras:
- Máximo 80 palavras, 1-2 parágrafos
- Reconheça que o timing pode não ser o ideal (sem passividade agressiva)
- Resuma em 1 frase o tipo de contribuição que poderia trazer (sem vender)
- Sinalize claramente que é o último contato por ora ("não quero ser inconveniente")
- Deixe a porta aberta: "quando fizer sentido, fico à disposição"
- PROIBIDO: tom de culpa, manipulação, "último e-mail", urgência falsa
- Tom: maduro, respeitoso, profissional — como encerrar uma tentativa de networking que não vingou
""".strip(),

    "email_first": """
TIPO: Primeiro email frio
OBJETIVO: Captar atenção em 5 segundos, abrir conversa.

Regras:
- Máximo 150 palavras, 3 parágrafos curtos
- Parágrafo 1: hook específico — referência ao lead, empresa, setor, desafio ou movimento recente. O lead deve pensar "essa pessoa me pesquisou"
- Parágrafo 2: micro-insight de valor — um dado, tendência ou observação que conecte seu expertise ao mundo do lead. NÃO é pitch.
- Parágrafo 3: CTA inteligente — pergunta sobre a experiência deles ou convite para trocar perspectivas. NUNCA "agendar uma call"
- Tom: direto, conciso, como email entre executivos que se respeitam
- PROIBIDO: apresentar produto detalhadamente, mencionar preço, mandar case study, "gostaria de apresentar"
""".strip(),

    "email_followup": """
TIPO: Follow-up por email
OBJETIVO: Reengajar com conteúdo novo, demonstrar persistência inteligente.

Regras:
- Máximo 120 palavras, 2-3 parágrafos curtos
- NÃO comece com "só passando para dar um follow-up" ou "voltando ao email anterior"
- Traga algo NOVO e relevante: dado do mercado, case (anônimo), notícia do setor, tendência
- Conecte a novidade ao contexto do lead/empresa
- CTA renovado: ângulo diferente do primeiro email
- Referência sutil à tentativa anterior ("na semana passada comentei sobre X — achei que este dado complementa")
- Tom: consultivo, como quem compartilha inteligência de mercado
""".strip(),

    "email_breakup": """
TIPO: Email de despedida / último contato
OBJETIVO: Última tentativa respeitosa, criar senso de fechamento.

Regras:
- Máximo 100 palavras, 2 parágrafos
- Reconheça que pode não ser prioridade agora (sem pressão)
- Resuma em 1 frase a contribuição possível (alto nível, sem detalhar)
- Sinalize claramente que é a última mensagem
- Ofereça retomar no futuro quando fizer sentido
- PROIBIDO: urgência falsa, escassez artificial, "última chance", tom passivo-agressivo
- Tom: profissional, maduro, como encerrar uma porta que pode reabrir naturalmente
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
        context: dict,              # vindo de context_fetcher
        cadence: Cadence,
    ) -> str:
        """
        Gera uma mensagem personalizada para o lead/canal/step.
        Usa o provider e modelo configurados na cadência.
        """
        user_prompt = _build_user_prompt(lead, channel, step_number, context, cadence=cadence)

        messages = [
            LLMMessage(role="system", content=COMPOSER_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        response: LLMResponse = await self._registry.complete(
            messages=messages,
            provider=cadence.llm_provider,
            model=cadence.llm_model,
            temperature=cadence.llm_temperature,
            max_tokens=cadence.llm_max_tokens,
        )

        logger.info(
            "ai_composer.composed",
            lead_id=str(lead.id),
            channel=channel,
            step=step_number,
            provider=response.provider,
            model=response.model,
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
        )

        return response.text.strip()


def _build_user_prompt(
    lead: Lead,
    channel: str,
    step: int,
    context: dict,
    total_steps: int = 1,
    use_voice: bool = False,
    previous_channel: str | None = None,
    cadence: Cadence | None = None,
) -> str:
    site_summary = context.get("site_summary", "Não disponível")
    linkedin_post = context.get("recent_linkedin_post", "Não disponível")
    news = context.get("company_news", "Nenhuma notícia recente")

    step_key = resolve_step_key(channel, step, total_steps, use_voice, previous_channel)
    step_instruction = STEP_INSTRUCTIONS.get(step_key, "")

    # Dados ricos do lead
    lead_lines = [
        f"Nome: {lead.name}",
        f"Cargo: {lead.job_title or 'Não informado'}",
        f"Empresa: {lead.company or 'Não informado'}",
        f"Setor/indústria: {lead.industry or 'Não informado'}",
        f"Porte da empresa: {lead.company_size or 'Não informado'}",
        f"Segmento: {lead.segment or 'Não informado'}",
        f"Localização: {lead.location or lead.city or 'Não informado'}",
    ]
    if lead.linkedin_url:
        lead_lines.append(f"LinkedIn: {lead.linkedin_url}")

    # Contexto da cadência (segmento-alvo, persona, oferta)
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

    return f"""
{step_instruction}

---

DADOS DO LEAD:
{chr(10).join(lead_lines)}

CONTEXTO DA CAMPANHA:
{cadence_block}

PESQUISA SOBRE A EMPRESA:
{site_summary}

POST RECENTE DO LEAD NO LINKEDIN:
{linkedin_post}

NOTÍCIAS RECENTES DA EMPRESA/SETOR:
{news}

POSIÇÃO NA CADÊNCIA: Step {step} de {total_steps}.

Escreva a mensagem agora:
""".strip()


def resolve_step_key(
    channel: str,
    step_number: int,
    total_steps: int,
    use_voice: bool = False,
    previous_channel: str | None = None,
) -> str:
    """Resolve qual instrução de step usar baseado no canal, posição, voz e step anterior."""
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
