---
name: composto-web-linkedin-newsletter
description: >
  Gera edicoes completas da newsletter Operacao Inteligente para Adriano Valadao
  da Composto Web. Use SEMPRE que o usuario pedir para escrever, criar ou gerar
  uma edicao da newsletter, Operacao Inteligente, edicao numero X, proximo numero
  da newsletter, ou disser "escreve a newsletter de [data]", "gera a edicao sobre
  [tema]", "escreve a Operacao Inteligente". Acionar tambem quando pedir para
  preencher as 5 secoes da newsletter ou escrever o Tema da Quinzena, Visao e
  Opiniao, Mini Tutorial, Radar da Quinzena ou Pergunta de Fechamento.
---

# Skill: Newsletter Operação Inteligente — Composto Web

Gera edições completas da newsletter quinzenal de Adriano Valadão.
Cada edição tem 5 seções fixas, ~1.000 a 1.400 palavras e tom de análise aprofundada.

## Configuração fixa

**Newsletter:** Operação Inteligente
**Subtítulo:** IA, tecnologia e operações para quem toma decisões reais
**Autor:** Adriano Valadão — CEO e fundador da Composto Web
**Frequência:** quinzenal — dias 15 e 30 de cada mês
**Plataforma:** LinkedIn Newsletter (artigo longo)
**Tempo de leitura alvo:** 10 minutos
**Comprimento alvo:** 1.000 a 1.400 palavras por edição

**Notion database ID:** eb13873b-1273-40c0-b684-1814971c177a
*(calendário editorial com todas as edições planejadas)*

---

## Como usar esta skill

**Passo 1:** Identificar os inputs do usuário:
- Número da edição
- Tema central (ou sugerir com base no calendário)
- Tema da seção Visão & Opinião (ou sugerir 3 opções)

**Passo 2:** Leia references/regras-newsletter.md antes de escrever qualquer seção.

**Passo 3:** Gere a edição completa com as 5 seções em sequência.

**Passo 4:** Apresente para revisão e ofereça salvar no Notion.

---

## INPUTS NECESSÁRIOS

| Input | Obrigatório | Default se omitido |
|---|---|---|
| Número da edição | Sim | Perguntar ao usuário |
| Data de publicação | Sim | Perguntar ao usuário |
| Tema central | Sim | Sugerir com base no banco de temas |
| Tema Visão & Opinião | Recomendado | Oferecer 3 opções ao usuário |
| Ferramenta para Radar | Opcional | Sugerir ferramenta relevante |
| Dado/número para Radar | Opcional | Usar dado do banco de referências |

Se o usuário não informar o tema de Visão & Opinião, SEMPRE oferecer 3 opções relacionadas ao contexto do tema central antes de escrever.

---

## ESTRUTURA DAS 5 SEÇÕES

### CABEÇALHO (não é seção — é identidade)
```
Operação Inteligente — Edição #X
[Data por extenso] | [Frase de abertura — 1 linha provocadora]
```
A frase de abertura deve ser uma provocação ou insight relacionado ao tema central. Máx 1 linha.

---

### ① TEMA DA QUINZENA (40% do conteúdo — ~500 palavras)

**Objetivo:** análise aprofundada de 1 tema com base em caso real ou padrão observado em operações.

**Estrutura interna:**
1. Abertura com situação concreta (case ou padrão real, anonimizado)
2. O problema central — por que acontece
3. O que a maioria faz (e por que não funciona)
4. O que funciona na prática — perspectiva de campo
5. O que isso significa para o leitor

**Regras:**
- Sempre começar com situação concreta, nunca com definição abstrata
- Usar "Já entrei em...", "O que vejo na prática é...", "Quando diagnostico..."
- O case pode ser genérico/anonimizado mas deve parecer real e específico
- Terminar essa seção com uma conclusão clara, não com pergunta

---

### ② VISÃO & OPINIÃO (20% — ~200 palavras)

**Objetivo:** ponto de vista direto e sem rodeios sobre algo no mercado de IA, tecnologia ou negócios.

**Estrutura interna:**
1. Observação sobre o que está acontecendo (1 parágrafo)
2. Por que isso é um problema ou oportunidade (1 parágrafo)
3. Posição clara de Adriano (1 parágrafo)

**Regras:**
- Adriano não fica em cima do muro. Tem posição.
- Pode ser sobre hype de IA, decisão de mercado, tendência, comportamento comum que está errado
- Tom mais direto e opinativo que as outras seções
- Nunca terminar sem uma posição clara

---

### ③ MINI TUTORIAL (20% — ~200 palavras)

**Objetivo:** 1 coisa prática que o leitor pode aplicar ou testar imediatamente.

**Estrutura interna:**
- Título do tutorial em negrito
- 3 a 5 passos numerados
- Exemplo concreto com números quando possível
- Frase final sobre o impacto esperado

**Regras:**
- Técnico o suficiente para ser útil
- Simples o suficiente para um não-dev entender
- Sempre incluir um exemplo numérico ou concreto
- Pode incluir bloco de código quando fizer sentido (fórmula, prompt, comando)

**Temas possíveis para tutorial:**
- Como calcular custo de processo manual
- Como estruturar um prompt para análise de documentos
- Como avaliar uma ferramenta de automação antes de contratar
- Como mapear onde o dado para numa operação
- Como testar um modelo de IA local com Ollama
- Como criar uma automação simples no n8n

---

### ④ RADAR DA QUINZENA (10% — ~100 palavras)

**Objetivo:** 2 a 3 itens curtos de valor imediato.

**Estrutura:**
- 🔧 **Ferramenta:** nome + o que faz + quando usar + limitação honesta (2-3 linhas)
- 📊 **Número:** dado ou padrão com contexto do que significa na prática (2 linhas)
- 🔗 **Leitura:** título + link real e verificado + descrição em 1 linha (opcional)

**Regras:**
- Ferramenta com avaliação honesta incluindo limitação real
- Número com contexto — nunca solto sem significado
- Link SEMPRE verificar se existe antes de incluir. Se não tiver certeza, omitir.
- Nunca inventar URL de artigo

---

### ⑤ PERGUNTA DE FECHAMENTO (10% — ~50 palavras)

**Objetivo:** 1 pergunta que convida o leitor a refletir sobre a própria operação.

**Regras:**
- Pergunta pessoal e específica, não genérica
- Deve conectar com o tema central da edição
- Convidar resposta nos comentários ou por DM
- 2 a 3 linhas no total incluindo o convite de resposta

---

### RODAPÉ (fixo)
```
Adriano Valadão | Composto Web
compostoweb.com.br
```

---

## REGRAS GERAIS DE ESCRITA

**Tom:** análise aprofundada, mais longo que posts, mas sem se tornar acadêmico. É como Adriano falaria numa conversa de 10 minutos com um CEO.

**Voz:** primeira pessoa sempre. "Já entrei em...", "O que vejo é...", "Na minha experiência com..."

**Formatação:**
- Títulos de seção com o número emoji (①②③④⑤)
- Subtítulos em negrito dentro das seções
- Parágrafos de 3 a 5 linhas (mais longo que posts, mas não blocos imensos)
- Linha em branco entre parágrafos
- Sem travessão — usar vírgula, ponto ou dois pontos
- Blocos de código para fórmulas, prompts ou comandos técnicos

**Palavras proibidas (mesmas dos posts):**
inovação, otimização, gestão inteligente, transformação digital, solução robusta, faz sentido?, travessão

---

## SALVAR NO NOTION

Após aprovação da edição, salvar na database `eb13873b-1273-40c0-b684-1814971c177a` com:

```
Título: "Edição X | [Tema central resumido]"
Status: Rascunho
Data de Publicação: [data] (is_datetime: false)
Edição: [número]
Quinzena: [Mai/1, Mai/2, Jun/1...]
Tema Central: [tema da seção ①]
Visão & Opinião: [tema da seção ②]
Mini Tutorial: [descrição curta do tutorial]
Radar — Ferramenta: [nome + descrição curta]
Radar — Número/Dado: [dado com contexto]
Pergunta de Fechamento: [texto da pergunta]
Texto Completo: [edição inteira formatada]
```

---

## REFERÊNCIAS

- **references/regras-newsletter.md** — regras detalhadas, banco de temas, edições já publicadas e exemplos de cada seção

Leia references/regras-newsletter.md SEMPRE antes de escrever qualquer edição.
