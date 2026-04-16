"use client"

import { useState } from "react"
import LandingPublicPage from "@/components/content/inbound/landing-public-page"
import type { LandingPagePublicData } from "@/lib/content-inbound/types"

// ── Mock data por tipo ────────────────────────────────────────────────────────

const MOCK_PDF: LandingPagePublicData = {
  id: "preview-pdf",
  lead_magnet_id: "lm-pdf",
  lead_magnet_type: "pdf",
  lead_magnet_title: "Guia de Automação de Processos B2B",
  lead_magnet_description: "Aprenda a automatizar sem aumentar equipe.",
  file_url: "https://cdn.compostoweb.com.br/guia-automacao-2025.pdf",
  cta_text: "Baixar guia agora",
  slug: "guia-automacao-b2b",
  title: "Automação B2B: o guia definitivo para operar mais com menos",
  subtitle:
    "37 páginas com frameworks, checklists e cases reais para times de operação, financeiro e atendimento.",
  hero_image_url: null,
  benefits: [
    "Mapeamento de processos que deveriam ter sido automatizados ontem",
    "Frameworks de priorização por ROI e esforço de implementação",
    "Checklist de ferramentas por área: financeira, operacional e RH",
    "Template de proposta para aprovação interna do projeto",
    "Case real: como uma indústria reduziu 80% do retrabalho em 60 dias",
  ],
  social_proof_count: 240,
  author_bio:
    "Time especializado em estruturar automações e sistemas sob medida para operações B2B com processo complexo.",
  author_photo_url: null,
  meta_title: null,
  meta_description: null,
  publisher_name: null,
  features: null,
  expected_result: null,
  badge_text: null,
  public_url: "https://app.compostoweb.com.br/lm/guia-automacao-b2b",
}

const MOCK_LINK: LandingPagePublicData = {
  id: "preview-link",
  lead_magnet_id: "lm-link",
  lead_magnet_type: "link",
  lead_magnet_title: "Planilha de Controle de Processos Operacionais",
  lead_magnet_description: null,
  file_url: "https://notion.so/composto/planilha-controle",
  cta_text: "Acessar planilha agora",
  slug: "planilha-controle-operacional",
  title: "Planilha de Controle Operacional para Times B2B",
  subtitle:
    "Modelo no Notion pronto para duplicar e adaptar ao seu processo em menos de 10 minutos.",
  hero_image_url: null,
  benefits: [
    "Visão por processo, responsável e status de automação",
    "Coluna de prioridade por custo e frequência",
    "Integrado com visão de backlog e roadmap",
  ],
  social_proof_count: 95,
  author_bio: null,
  author_photo_url: null,
  meta_title: null,
  meta_description: null,
  publisher_name: null,
  features: null,
  expected_result: null,
  badge_text: null,
  public_url: "https://app.compostoweb.com.br/lm/planilha-controle-operacional",
}

const MOCK_SEQUENCE: LandingPagePublicData = {
  id: "preview-seq",
  lead_magnet_id: "lm-seq",
  lead_magnet_type: "email_sequence",
  lead_magnet_title: "Sequência B2B: Do Lead ao Contrato",
  lead_magnet_description: null,
  file_url: null,
  cta_text: "Quero receber a sequência",
  slug: "sequencia-lead-contrato",
  title: "Do Lead ao Contrato: uma sequência para fechar mais em B2B",
  subtitle:
    "5 emails com o que realmente move o funil — sem pitch agressivo, sem template genérico.",
  hero_image_url: null,
  benefits: [
    "Email 1: diagnóstico de onde estão as perdas no seu funil atual",
    "Email 2: framework de qualificação que elimina reuniões sem potencial",
    "Email 3: proposta de valor em uma frase — como construir a sua",
    "Email 4: objeções comuns e como dissolvê-las sem pressão",
    "Email 5: follow-up que não irrita e mantém o lead no funil",
  ],
  social_proof_count: 310,
  author_bio:
    "Adriano Lula e time Composto Web — especialistas em operação comercial B2B de ciclo longo.",
  author_photo_url: null,
  meta_title: null,
  meta_description: null,
  publisher_name: null,
  features: null,
  expected_result: null,
  badge_text: null,
  public_url: "https://app.compostoweb.com.br/lm/sequencia-lead-contrato",
}

const MOCK_CALCULATOR: LandingPagePublicData = {
  id: "preview-calc",
  lead_magnet_id: "lm-calc",
  lead_magnet_type: "calculator",
  lead_magnet_title: "Calculadora de ROI da Automação",
  lead_magnet_description: null,
  file_url: null,
  cta_text: null,
  slug: "calculadora-roi",
  title: "Calcule o ROI da automação no seu processo",
  subtitle:
    "Preencha as variáveis do seu cenário e receba uma estimativa de custo, payback e ROI antes de falar com o time.",
  hero_image_url: null,
  benefits: [
    "Custo anual atual com o processo manual",
    "Faixa de investimento estimado para automação",
    "ROI esperado e prazo de payback",
    "PDF com diagnóstico executivo do cenário",
  ],
  social_proof_count: 180,
  author_bio: null,
  author_photo_url: null,
  meta_title: null,
  meta_description: null,
  publisher_name: null,
  features: null,
  expected_result: null,
  badge_text: null,
  public_url: "https://app.compostoweb.com.br/lm/calculadora-roi",
}

type TemplateKey = "pdf" | "link" | "email_sequence" | "calculator"

const TEMPLATES: { key: TemplateKey; label: string; badge: string; page: LandingPagePublicData }[] =
  [
    { key: "pdf", label: "PDF / Rich", badge: "Full template", page: MOCK_PDF },
    { key: "link", label: "Link / Minimal", badge: "Minimal template", page: MOCK_LINK },
    {
      key: "email_sequence",
      label: "Sequência de emails",
      badge: "Trust template",
      page: MOCK_SEQUENCE,
    },
    {
      key: "calculator",
      label: "Calculadora",
      badge: "Calculator template",
      page: MOCK_CALCULATOR,
    },
  ]

export default function LpPreviewPage() {
  const [active, setActive] = useState<TemplateKey>("pdf")

  const current = TEMPLATES.find((t) => t.key === active)!

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* ── Barra de seleção de template ── */}
      <div className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-900/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3">
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
            LP Preview
          </span>
          <div className="mx-3 h-4 w-px bg-zinc-700" />
          {TEMPLATES.map((t) => (
            <button
              key={t.key}
              onClick={() => setActive(t.key)}
              className={[
                "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                active === t.key
                  ? "bg-white text-zinc-950"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100",
              ].join(" ")}
            >
              {t.label}
              <span
                className={[
                  "ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                  active === t.key ? "bg-zinc-200 text-zinc-700" : "bg-zinc-800 text-zinc-500",
                ].join(" ")}
              >
                {t.badge}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Template renderizado ── */}
      <LandingPublicPage key={active} page={current.page} />
    </div>
  )
}
