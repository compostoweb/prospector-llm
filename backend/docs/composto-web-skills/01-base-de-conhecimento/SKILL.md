---
name: composto-web-knowledge
description: >
  Base de conhecimento estratégico da Composto Web. Use SEMPRE que qualquer pergunta
  envolver: posicionamento da Composto Web, verticais técnicas (RPA, integracao, IA,
  cloud, telefonia, software sob medida), Metodo Nucleo (5 fases: Imersao, Engenharia,
  Construcao, Homologacao, Soberania), ICP e perfil de cliente ideal, anti-ICP, modelos
  de engajamento (Diagnostico Nucleo, Projeto Estruturado, Parceria Continua, Squad
  Dedicado, Parceria de Produto), slogan e variacoes, setores atendidos, personas e
  dores por cargo, objecoes e contra-argumentos. Acionar tambem quando o usuario
  perguntar quem somos, o que fazemos, qual nosso diferencial, como apresentar para
  um CEO ou CTO ou CFO, como qualificar esse lead, esse cliente e ICP, ou pedir ajuda
  para montar pitch, apresentacao ou proposta.
---

# Composto Web: Base de Conhecimento Estratégico

Documento de referência interno para Adriano e equipe. Contém posicionamento, verticais, metodologia, ICP e modelos de engajamento.

## Como usar esta skill

Para perguntas de posicionamento e pitch: leia a seção 1 e 2.
Para qualificar um lead: leia a seção 3 (ICP).
Para apresentar a metodologia: leia a seção 4 (Método Núcleo).
Para propor um modelo de contrato: leia a seção 5 (Modelos de Engajamento).
Para dores por setor e cargo: leia o arquivo references/playbook-setores.md.
Para objeções e contra-argumentos: leia references/objecoes.md.

---

## 1. POSICIONAMENTO

A Composto Web é uma empresa de tecnologia com foco em parceria estratégica. Desenvolvemos engenharia de soluções para desafios e problemas de negócio, com imersão profunda nos processos de cada departamento.

Não entregamos ferramentas. Entregamos ativos digitais que eliminam gargalos, escalam operações e permanecem sob controle total do cliente.

**Slogan principal:** Engenharia de soluções. Do processo ao crescimento.

**Variações por contexto:**
- Site (hero): Engenharia de soluções. Do processo ao crescimento.
- Google Ads: Automação e IA sob medida para sua operação
- LinkedIn Ads: Não vendemos software. Construímos o ativo digital da sua operação.
- Proposta (capa): Do processo ao crescimento. Com engenharia, parceria e soberania.
- Pitch C-Level: Entramos nos seus processos. Saímos com o gargalo eliminado.
- Assinatura de e-mail: Engenharia de soluções | compostoweb.com.br

**Diferenciais centrais:**
- Soberania Digital: código-fonte e PI pertencem integralmente ao cliente
- Sem lock-in: se o cliente encerrar o suporte, o software continua rodando
- Valor patrimonial: a automação vira ativo real no balanço da empresa
- Parceria de longo prazo: não somos fornecedores pontuais, somos o braço técnico estratégico
- Adriano: 22 anos de bagagem técnica liderando cada projeto

---

## 2. VERTICAIS TÉCNICAS

São 6 verticais. Podem ser contratadas isoladamente ou combinadas.

**A. Hiperautomação (RPA + IA)**
Substituição de trabalho repetitivo por robôs 24/7. Parceria estratégica com BotCity para projetos enterprise (pode haver licença). Para projetos onde PI integral é prioridade, desenvolvemos com stack próprio (Python, Node.js).
Quando indicar: processos manuais diários, planilhas, cópia-e-cola, erros que geram multa ou retrabalho.

**B. Engenharia de Integração**
Camada de comunicação entre sistemas que não se conversam. APIs middleware, webhooks, EDA, conectores para legados.
Quando indicar: 3+ sistemas desconectados, redigitação de dados, relatórios manuais, dado defasado na decisão.
Case real: integração de agente IA no WhatsApp com ERP e plataforma de atendimento de clínica médica, automatizando triagem de pacientes e agendamento.

**C. IA Generativa e NLP Aplicado**
IA como componente de processo, não chatbot genérico. Stack multi-modelo:
- GPT-4.1 / o3: raciocínio complexo, análise de documentos
- Claude Opus/Sonnet: contextos longos, análise jurídica e financeira
- Gemini Pro/Flash: multimodalidade, Google Workspace
- Ollama + open-source (Llama, Mistral, Qwen): ambientes privados, dados sensíveis
- Servidor dedicado de inferência: enterprise sem envio de dados para APIs externas, sem custo por token
Quando indicar: alto volume de texto, atendimento repetitivo, análise de documentos, automação que trata exceções.
Cases reais: agente IA no WhatsApp para clínica, blog com IA, geração de imagens com IA (plataforma própria).

**D. Cloud, DevOps e Resiliência**
Arquitetura de nuvem, CI/CD, FinOps, segurança nativa (OAuth2, AES-256), conformidade LGPD, observabilidade (Grafana/Prometheus).
Quando indicar: aplicações críticas sem redundância, fatura de cloud crescendo sem controle, TI preso em incêndios.

**E. Telefonia Inteligente e Integrada**
PABX IP integrado ao CRM, transcrição com Whisper AI, gatilhos pós-chamada, URA com IA, dashboards de atendimento.
Quando indicar: alto volume de ligações sem registro, vendedores digitando no CRM, sem visibilidade de qualidade.

**F. Software Sob Medida**
Desenvolvimento de sistemas, plataformas e produtos digitais do zero para problemas que nenhum SaaS resolve com precisão.
Quando indicar: problema específico demais para prateleira, cliente quer ativo proprietário, custo de licença SaaS proibitivo a médio prazo.
Cases reais: sistema de rastreamento, sistema financeiro (em dev), Prospector (plataforma de prospecção B2B em dev), automação de clínica médica.

**Tech stack principal:** Python (FastAPI), Node.js (Fastify), .NET, Next.js, PostgreSQL, Redis, BullMQ, Docker, Easypanel, n8n, Grafana/Prometheus.

---

## 3. ICP: PERFIL DO CLIENTE IDEAL

Para detalhamento completo, leia references/icp.md.

**ICP Primário (alvo de crescimento):**
- Porte: 100 a 1.000 funcionários
- Faturamento: R$10M a R$500M/ano
- TI interna: time pequeno (1-5 pessoas) sem capacidade para projetos complexos
- Ticket mínimo: setup R$20.000 + mensalidade R$3.000
- Decisor: CEO, CTO, CFO, COO com autonomia de R$20k+
- Dor central: operação crescendo mais rápido que a capacidade de gestão

**ICP Secundário (base atual PME):**
- Porte: 10 a 100 funcionários
- Ticket: R$3.000 a R$19.000 setup + R$800 a R$2.999/mês
- Estratégia: atender bem, não prospectar ativamente; usar como pipeline de upsell

**Anti-ICP (não atender):**
- Quer "só um site" sem complexidade
- Startup early-stage sem produto validado buscando CTO barato
- Quer pagar por entrega e nunca mais falar com o fornecedor
- Sem budget mínimo de R$5.000

**Gatilhos de prospecção (momento ideal para abordar):**
1. Crescimento acelerado nos últimos 12 meses
2. Troca de ERP ou CRM
3. Fusão ou aquisição
4. Novo produto ou canal
5. Regulação ou auditoria (LGPD, ISO)
6. Saída de pessoa-chave de TI
7. Problema público (sistema caiu, dados incorretos)

---

## 4. MÉTODO NÚCLEO

A metodologia proprietária da Composto Web. 5 fases que traduzem complexidade técnica em previsibilidade para o cliente. O nome vem do núcleo âmbar da logo: entramos no centro da operação e construímos de dentro para fora.

```
IMERSÃO > ENGENHARIA > CONSTRUÇÃO > HOMOLOGAÇÃO > SOBERANIA
3-10d      5-15d        30-120d       5-15d          5-10d + 30d hipercare
```

**Fase 1: Imersão**
Entramos no negócio antes de propor qualquer solução. Entrevistas com C-Level, gerentes e usuários finais. Mapeamento dos fluxos reais (as-is). Identificação de gargalos e custo real do problema (horas x pessoas x frequência).
Entregável: Relatório de Imersão com mapa de processos, gargalos priorizados e custo estimado.
Diferencial: cobramos por ela. Diagnóstico errado garante projeto errado.

**Fase 2: Engenharia**
Nenhuma linha de código antes do projeto técnico aprovado. Arquitetura completa, KPIs de sucesso, riscos mapeados, cronograma detalhado.
Entregável: Documento de Engenharia aprovado + PI formalmente atribuída ao cliente desde o início.

**Fase 3: Construção**
Sprints de 15 a 30 dias com módulo funcional entregue ao final de cada ciclo. Cliente acompanha, valida e influencia. Mudanças são bem-vindas, documentadas e precificadas com transparência.
Entregável por sprint: módulo em homologação + documentação atualizada + relatório de progresso.

**Fase 4: Homologação**
Testamos como adversários para garantir como parceiros. Testes de carga (2x, 5x, 10x volume), falha, segurança, UAT com usuários reais, plano de rollback testado antes do go-live.
Entregável: Relatório de Homologação com evidências e checklist de go-live.

**Fase 5: Soberania**
Entrega de PI integral: código, documentação, credenciais. Treinamento das equipes. 30 dias de hipercare inclusos. Definição do modelo de evolução contínua.
Entregável: Pacote de Soberania Digital + roadmap.

**Como apresentar para o cliente:**
"Antes de qualquer proposta, fazemos uma imersão nos seus processos para entender onde está o gargalo real, quanto ele está custando e qual é a solução mais eficiente. Você recebe um relatório executivo com o diagnóstico e o caminho recomendado. E esse valor é abatido integralmente se você avançar com o projeto."

---

## 5. MODELOS DE ENGAJAMENTO

Para detalhamento completo com preços e critérios, leia references/engajamento.md.

**Diagnóstico Núcleo** (porta de entrada)
R$3.000 a R$8.000. Fase 1 do Método Núcleo vendida independentemente. Valor abatido no projeto se avançar. Ideal para leads sem clareza de escopo ou que precisam justificar internamente.

**Projeto Estruturado** (core do negócio)
Setup R$20.000 a R$150.000+. Mensalidade R$3.000 a R$8.000/mês. Método Núcleo completo. 30 dias hipercare inclusos.

**Parceria Contínua** (retainer mensal)
Essencial: 20h/mês por R$4.500. Avançada: 40h/mês por R$8.500. Estratégica: 80h/mês por R$15.000.

**Squad Dedicado** (time alocado)
R$25.000 a R$60.000/mês. Mínimo 3 meses. Tech Lead + 1-2 devs sênior + especialista conforme demanda.

**Parceria de Produto** (co-construção com upside)
Revenue share 5-15% ou equity 5-20% ou híbrido. Para projetos onde a Composto Web acredita no negócio e quer skin in the game.

**Fluxo comercial recomendado:**
Lead com escopo claro e budget aprovado: ir direto para Projeto Estruturado.
Lead cético ou sem clareza: propor Diagnóstico Núcleo (valor abatido no projeto).

---

---

## 6. SETORES ATENDIDOS

13 setores cobertos com cargos, dores e ganchos específicos. Para detalhamento completo por setor e cargo, leia references/playbook-setores.md.

**Setores e cargos prioritários para prospecção ativa:**

| Setor | Cargos prioritários | Foco principal |
|---|---|---|
| Financeiro | CFO, COO, Controller | Fechamento mensal, conciliação, integração ERP-bancos |
| Contabilidade | Sócio de escritório, Gerente Financeiro interno | Obrigações acessórias, escala de carteira sem crescer equipe |
| Jurídico / Advocacia | Sócio/Advogado Sênior, Diretor Jurídico In-House | IA privada (Ollama), gestão de contratos, automação de documentos |
| Saúde / Clínicas | CEO/Dono, Gerente Administrativo | IA no WhatsApp, triagem de pacientes, agendamento, integração ERP |
| Indústria / Logística | Diretor Industrial/COO, Gerente de TI | Visibilidade em tempo real, integração ERP, PCP com dado ao minuto |
| Varejo / E-commerce | CEO/Diretor, Gerente de Operações, Gerente de Marketing | Omnichannel, fulfillment, CDP, SAC com IA |
| Educação / EdTech | Diretor Acadêmico, Gerente Financeiro | Radar de evasão preditivo, régua de cobrança, dashboard pedagógico |
| Imobiliário / Construtoras | Diretor Comercial, Gerente de Obras | CRM que se alimenta sozinho, painel de obras, portal do comprador |
| Seguros / Fintechs | CEO/Diretor de Operações, Gerente de Compliance | Onboarding automatizado, motor de decisão auditável, PLD/FT |
| Agro / Agroindustrial | Diretor Agrícola, Gerente Financeiro | Plataforma offline-first, rastreabilidade de lote, integração ERP |
| RH / Gestão de Pessoas | CHRO, Gerente de R&S, Gerente de DP | People analytics, triagem automatizada, compliance de treinamento |
| Empresas de TI | CEO/CTO, Gerente de CS, Tech Lead | Automação de suporte/onboarding, health score, extensão de engenharia |
| Agências de Marketing | CEO/Sócio | Automação do operacional, relatórios automáticos, fluxo de conteúdo |
| Marketing Interno (deptos) | CMO, Gerente de Marketing/CRM, Coord. BI | CDP sob medida, CRM que se alimenta sozinho, data pipeline de marketing |

**Nota sobre Agências de Marketing:** o cargo Gerente de Tráfego Pago não é ICP para prospecção ativa da Composto Web.

---

*Composto Web | compostoweb.com.br*
*Para dores detalhadas por setor e cargo: leia references/playbook-setores.md*
*Para objeções e respostas: leia references/objecoes.md*
