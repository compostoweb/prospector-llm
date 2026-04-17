"use client"

import { useState } from "react"
import LandingThankYouPage from "@/components/content/inbound/landing-thankyou-page"
import type { LandingPagePublicData } from "@/lib/content-inbound/types"

// ── Mocks ──────────────────────────────────────────────────────────────────

const BASE: Omit<LandingPagePublicData, "lead_magnet_type" | "file_url"> = {
  id: "preview-ty",
  lead_magnet_id: "lm-preview",
  lead_magnet_title: "Guia de Automação B2B",
  lead_magnet_description: null,
  cta_text: null,
  slug: "guia-automacao-b2b",
  title: "Guia de Automação B2B",
  subtitle: null,
  hero_image_url: null,
  benefits: [],
  social_proof_count: 0,
  author_bio: null,
  author_photo_url: null,
  meta_title: null,
  meta_description: null,
  publisher_name: null,
  features: null,
  expected_result: null,
  badge_text: null,
  public_url: "/lm/guia-automacao-b2b",
}

const MOCKS: { key: string; label: string; badge: string; page: LandingPagePublicData }[] = [
  {
    key: "pdf",
    label: "PDF / Download",
    badge: "com file_url",
    page: {
      ...BASE,
      lead_magnet_type: "pdf",
      file_url: "https://cdn.compostoweb.com.br/guia-automacao-2025.pdf",
    },
  },
  {
    key: "link",
    label: "Link / Acesso",
    badge: "com file_url",
    page: {
      ...BASE,
      lead_magnet_type: "link",
      file_url: "https://notion.so/composto/planilha",
    },
  },
  {
    key: "email_sequence",
    label: "Sequência de e-mails",
    badge: "sem file_url",
    page: {
      ...BASE,
      lead_magnet_type: "email_sequence",
      file_url: null,
    },
  },
  {
    key: "calculator",
    label: "Calculadora",
    badge: "CTA especial",
    page: {
      ...BASE,
      lead_magnet_type: "calculator",
      file_url: null,
    },
  },
]

export default function ThankYouPreviewPage() {
  const [active, setActive] = useState("pdf")

  const current = MOCKS.find((m) => m.key === active) ?? MOCKS[0]

  if (!current) {
    return null
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Barra de seleção */}
      <div className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-900/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3">
          <span className="text-xs font-semibold uppercase tracking-widest text-zinc-400">
            Obrigado Preview
          </span>
          <div className="mx-3 h-4 w-px bg-zinc-700" />
          {MOCKS.map((m) => (
            <button
              key={m.key}
              onClick={() => setActive(m.key)}
              className={[
                "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                active === m.key
                  ? "bg-white text-zinc-950"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100",
              ].join(" ")}
            >
              {m.label}
              <span
                className={[
                  "ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                  active === m.key ? "bg-zinc-200 text-zinc-700" : "bg-zinc-800 text-zinc-500",
                ].join(" ")}
              >
                {m.badge}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Template renderizado */}
      <LandingThankYouPage key={active} page={current.page} />
    </div>
  )
}
