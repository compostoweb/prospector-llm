# Regras e Referências — Newsletter Operação Inteligente

---

## CALENDÁRIO EDITORIAL

| Edição | Data | Status | Tema Central |
|---|---|---|---|
| 1 | 30/04/2026 | Publicado | Por que a maioria dos projetos de IA falha antes de ir para produção |
| 2 | 15/05/2026 | Planejado | IA privada: quando faz sentido rodar modelos locais na empresa |
| 3 | 30/05/2026 | Planejado | O problema que o ERP não resolve (e o que resolve) |
| 4 | 15/06/2026 | Planejado | Como calcular o custo real de um processo manual |
| 5 | 30/06/2026 | Planejado | Agentes de IA no atendimento: o que funciona, o que não funciona |
| 6 | 15/07/2026 | Planejado | O que aprendi diagnosticando operações em 6 setores |

---

## BANCO DE TEMAS CENTRAIS (não publicados)

**IA e Tecnologia:**
- IA privada vs APIs comerciais: o que ninguém conta sobre seus dados
- Como um agente de IA de verdade funciona (vs chatbot glorificado)
- Ollama na prática: rodando IA local em 20 minutos
- O que é LangChain e quando usar (sem o hype)
- n8n para automação de negócios: por onde começar

**Operações e Processos:**
- O processo que ninguém documentou (e o risco que isso representa)
- Como mapear onde o dado para numa operação em 1 tarde
- Por que o fechamento mensal ainda leva dias (e o que resolver primeiro)
- A planilha que virou sistema: como sair sem trauma
- O gargalo invisível: retrabalho que não aparece no P&L

**Integração e Sistemas:**
- Por onde começar a integrar sistemas sem trocar o ERP
- API, webhook ou ETL: quando usar cada um sem ser técnico
- O custo real de sistemas desconectados (com cálculo)
- Dado em tempo real: o que é, o que não é e por que importa

**Gestão e Negócio:**
- Como apresentar um projeto de automação para o CFO
- O que o CEO precisa entender sobre IA antes de contratar
- Como calcular ROI de automação de forma que o board entenda
- Soberania digital: você é dono do software que usa?
- SaaS vs software próprio: a conta que ninguém faz

---

## BANCO DE TEMAS PARA VISÃO & OPINIÃO

**Sobre IA:**
- O mercado está chamando de "agente de IA" qualquer automação com prompt no meio *(usado na Edição 1)*
- CEOs estão terceirizando a decisão de IA para o TI — e isso é um erro estratégico
- O dado de ontem está tomando a decisão de hoje em 90% das empresas
- IA generativa não substitui raciocínio. Ela amplifica quem já pensa bem.
- O problema com "implementar IA" como projeto: tecnologia não é projeto, é camada

**Sobre mercado:**
- Fornecedores de tecnologia vendem complexidade como diferencial
- O consultor que não cobra pelo diagnóstico não confia no próprio diagnóstico
- Lock-in disfarçado de parceria: o que avaliar antes de assinar
- Por que a maioria dos projetos de transformação digital vira relatório de PowerPoint

**Sobre gestão:**
- Gestor que delega tecnologia sem entender o problema não está delegando, está abandonando
- A cultura de "funciona assim há 10 anos" é o maior obstáculo à automação
- Contratar mais gente para resolver problema de processo é postergação cara

---

## BANCO DE MINI TUTORIAIS

**Já usado:**
- Como calcular o custo real de um processo manual *(Edição 1)*

**Disponíveis:**
- Como testar o Ollama em 20 minutos no seu computador
- Como estruturar um prompt para análise de contrato jurídico
- Como mapear fluxo de dado entre sistemas numa tarde
- Como calcular o payback de um projeto de automação
- Como criar uma automação simples de notificação no n8n
- Como avaliar uma ferramenta de IA antes de contratar (5 perguntas)
- Como identificar o gargalo real numa operação (método de 3 perguntas)
- Como montar um dashboard de custo operacional no Google Sheets

---

## BANCO DE FERRAMENTAS PARA RADAR

| Ferramenta | O que faz | Quando usar | Limitação |
|---|---|---|---|
| Ollama | Roda modelos de IA localmente | Dados sensíveis, privacidade | Modelos inferiores aos comerciais em raciocínio complexo |
| n8n | Automação e integração de sistemas | Orquestração de fluxos sem código intensivo | Curva de aprendizado para fluxos complexos |
| LangChain | Framework para agentes de IA | Construir agentes com múltiplas ferramentas | Overhead para casos simples |
| Supabase | Banco de dados com API automática | Backend rápido para projetos de dados | Não substitui PostgreSQL gerenciado em produção crítica |
| Flowise | Interface visual para agentes IA | Prototipagem rápida de agentes | Limitações em customização avançada |
| Directus | CMS headless com API | Gestão de conteúdo e dados sem código | Mais complexo que alternativas simples |
| Baserow | Planilha com banco de dados | Substituir planilhas que viraram sistemas | Menos recursos que Airtable |
| Grafana | Dashboards e observabilidade | Monitorar sistemas e operações em tempo real | Requer configuração técnica inicial |

---

## BANCO DE DADOS E NÚMEROS

| Dado | Fonte | Contexto |
|---|---|---|
| 67% dos projetos de transformação digital falham | McKinsey | Principal fator: falta de clareza sobre o problema |
| 43% das empresas de médio porte operam com 6+ sistemas desconectados | Gartner | Custo não aparece no P&L, aparece nas decisões erradas |
| 35% do gasto em cloud é desperdiçado | Flexera | Não por falta de dinheiro, por falta de visibilidade |
| ROI médio de automação bem feita: 250% em 18 meses | Forrester | O problema é o "bem feita" |
| 70% do tempo de analistas financeiros vai para coleta e formatação de dados | Deloitte | Sobra 30% para análise real |
| Custo médio de retrabalho: 20-30% do custo total do projeto | PMI | Raramente contabilizado antes do projeto |

---

## REGRAS DE LINK NO RADAR

Antes de incluir qualquer link:
1. Só incluir links de domínios conhecidos e confiáveis: MIT Sloan, Harvard Business Review, McKinsey, Gartner, Forrester, documentação oficial de ferramentas
2. Nunca inventar URL — se não tiver certeza do link exato, omitir a seção de leitura
3. Descrever o artigo com o que ele realmente contém, não com o que seria ideal conter
4. Se o link foi verificado e existe: incluir com título real e descrição precisa

---

## EXEMPLOS DE ABERTURA POR TIPO DE TEMA

**Para tema de case/diagnóstico:**
> "Nos últimos [período], entrei em [número] de operações para diagnosticar [problema]. Em [proporção] delas, o cliente chegou com a mesma frase: [frase comum]."

**Para tema de padrão recorrente:**
> "[Padrão] aparece em quase toda empresa que tenta [ação]. Não é coincidência. É uma consequência de [causa]."

**Para tema técnico com linguagem de negócio:**
> "Toda vez que [situação comum], a primeira pergunta que faço é: [pergunta que revela o problema real]."

**Para tema de tendência:**
> "Nos últimos meses, [tendência observada]. O problema não é a tendência em si. É [o que a maioria não percebe]."

---

## EDIÇÕES PUBLICADAS — RESUMO DE CONTEÚDO

### Edição 1 — 30/04/2026
**Tema:** Por que a maioria dos projetos de IA falha antes de ir para produção
**Visão & Opinião:** O mercado está chamando de "agente de IA" qualquer automação com prompt no meio
**Mini Tutorial:** Como calcular o custo real de um processo manual em 15 minutos
**Radar Ferramenta:** Ollama
**Radar Número:** 67% dos projetos de transformação digital falham (McKinsey)
**Pergunta:** Qual é o processo na sua operação que todo mundo sabe que está quebrado, mas ninguém calculou quanto isso custa por mês?
