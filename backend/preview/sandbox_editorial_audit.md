# Sandbox Editorial Audit

- Gerado em: 2026-04-17 23:48 UTC
- Provider/model: openai / gpt-4o-mini
- Cenarios: 4
- Hard failures: 0
- Warnings: 1

## Saude | Convite de conexao

- Step key: linkedin_connect
- Metodo: None
- Playbook: saude/diretor_clinica (exact)
- Few-shot: saude:diretor_clinica:linkedin:first (exact)
- Validacao: ok=True | hard_failures=0 | warnings=1

Mensagem:

```text
Fala, Marina. Vi que a Clínica Horizonte está ampliando horários e especialidades. Seria bom nos conectarmos e trocarmos ideias sobre o setor.
```

Issues:
- [warning] too_many_sentences: Convite de conexao deve usar 1 ou 2 frases curtas.

## Varejo | Email inicial

- Step key: email_first
- Metodo: DIS
- Playbook: varejo/ceo_ecommerce (exact)
- Few-shot: varejo:ceo_ecommerce:email:first (exact)
- Validacao: ok=True | hard_failures=0 | warnings=0

Assunto: Margem encolhe com picos de pedidos?

Mensagem:

```text
Ricardo, operações de e-commerce frequentemente enfrentam desafios quando pedidos, estoque e atendimento estão desconectados. O aumento no volume de pedidos pode significar mais trabalho manual e menos margem, especialmente quando o tempo de resposta é crítico. Quando a visibilidade é tardia, custos como devoluções e retrabalho se acumulam rapidamente. Na Casa Nativa, a integração entre os sistemas de ERP, marketplace e atendimento já é uma prioridade?
```

Issues:
- Nenhuma

## Educacao | Email follow-up

- Step key: email_followup
- Metodo: INSIGHT
- Playbook: educacao/diretor_academico (exact)
- Few-shot: educacao:diretor_academico:email:followup (exact)
- Validacao: ok=True | hard_failures=0 | warnings=0

Assunto: Dado sobre engajamento em EAD

Mensagem:

```text
Carla, uma pesquisa recente revelou que instituições que utilizam análises preditivas para monitorar o engajamento dos alunos conseguem reduzir a evasão em até 30%. Isso acontece porque a detecção precoce de sinais de desengajamento permite intervenções mais eficazes e direcionadas. Considerando a nova vertical de cursos técnicos no Instituto Vanguarda, como vocês estão abordando a retenção de alunos em EAD? Esse tipo de análise já faz parte da estratégia de vocês ou ainda é um desafio a ser superado?
```

Issues:
- Nenhuma

## Imobiliario | LinkedIn follow-up

- Step key: linkedin_dm_followup
- Metodo: INSIGHT
- Playbook: saude/diretor_clinica (role_only)
- Few-shot: saude:diretor_clinica:linkedin:followup (exact)
- Validacao: ok=True | hard_failures=0 | warnings=0

Mensagem:

```text
Vi que a Orbita Urbanismo lançou um novo empreendimento em Campinas e ampliou a equipe de corretores parceiros. Isso é um passo interessante para aumentar a captação digital e atender à demanda do mercado.

Recentemente, um estudo apontou que empresas do setor imobiliário que implementam automação nos processos de agendamento e confirmação conseguem reduzir significativamente a taxa de não-comparecimento. Como vocês estão lidando com essa questão na Orbita?
```

Issues:
- Nenhuma
