"use client"

import { useState } from "react"
import {
  ArrowRight,
  BadgeCheck,
  ChartColumnIncreasing,
  Check,
  Download,
  Sparkles,
} from "lucide-react"
import { env } from "@/env"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type {
  LandingPagePublicCaptureInput,
  LandingPagePublicData,
} from "@/lib/content-inbound/types"

interface Props {
  page: LandingPagePublicData
}

export default function LandingPublicPage({ page }: Props) {
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [form, setForm] = useState<LandingPagePublicCaptureInput>({
    name: "",
    email: "",
    company: "",
    role: "",
    phone: "",
    linkedin_profile_url: "",
    session_id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`,
  })

  const isCalculator = page.lead_magnet_type === "calculator"

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/landing-pages/public/${page.slug}/capture`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        },
      )
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(
          payload && typeof payload === "object" && "detail" in payload
            ? String(payload.detail)
            : "Nao foi possivel liberar o material agora",
        )
      }
      window.location.assign(`/lm/${page.slug}/obrigado`)
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Falha ao enviar")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-(--bg-page) bg-[radial-gradient(circle_at_top_left,color-mix(in_srgb,var(--accent)_18%,transparent),transparent_34%),linear-gradient(180deg,var(--bg-page)_0%,var(--bg-surface)_100%)] text-(--text-primary)">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-10 lg:px-8 lg:py-14">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="default" className="px-3 py-1 text-[11px] uppercase tracking-[0.18em]">
            Content Hub Inbound
          </Badge>
          <Badge variant="outline">{page.lead_magnet_type.replace("_", " ")}</Badge>
          {page.social_proof_count > 0 && (
            <Badge variant="success">{page.social_proof_count}+ empresas interessadas</Badge>
          )}
        </div>

        <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
          <section className="flex flex-col gap-6">
            <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface)/90 p-7 shadow-(--shadow-lg) backdrop-blur">
              <div className="flex flex-col gap-4">
                <div className="inline-flex w-fit items-center gap-2 rounded-full bg-(--accent-subtle) px-3 py-1 text-xs font-medium text-(--accent-subtle-fg)">
                  <Sparkles className="h-3.5 w-3.5" />
                  Material desenhado para times B2B que precisam operar melhor sem aumentar equipe
                </div>

                <div className="space-y-3">
                  <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight lg:text-5xl">
                    {page.title}
                  </h1>
                  <p className="max-w-2xl text-base leading-7 text-(--text-secondary) lg:text-lg">
                    {page.subtitle ||
                      page.lead_magnet_description ||
                      "Acesse o material e leve um plano mais claro para o seu processo comercial e operacional."}
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {page.benefits.map((benefit) => (
                    <div
                      key={benefit}
                      className="flex items-start gap-3 rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4"
                    >
                      <div className="mt-0.5 rounded-full bg-(--success-subtle) p-1 text-(--success-subtle-fg)">
                        <Check className="h-3.5 w-3.5" />
                      </div>
                      <p className="text-sm leading-6 text-(--text-secondary)">{benefit}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
              <div className="rounded-3xl border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-sm)">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                  O que voce encontra aqui
                </p>
                <div className="mt-4 space-y-3">
                  <div className="rounded-2xl bg-(--bg-overlay) p-4">
                    <p className="text-sm font-medium text-(--text-primary)">
                      Clareza de diagnostico
                    </p>
                    <p className="mt-1 text-sm leading-6 text-(--text-secondary)">
                      O material mostra gargalos comuns, como priorizar o que automatizar e o que
                      nao vale manter manual.
                    </p>
                  </div>
                  <div className="rounded-2xl bg-(--bg-overlay) p-4">
                    <p className="text-sm font-medium text-(--text-primary)">Aplicacao imediata</p>
                    <p className="mt-1 text-sm leading-6 text-(--text-secondary)">
                      Sem teoria solta. O foco e em processo, ganho operacional e decisao executiva
                      com menos ruído.
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-sm)">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
                    <BadgeCheck className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-(--text-primary)">Quem assina</p>
                    <p className="text-sm text-(--text-secondary)">Composto Web</p>
                  </div>
                </div>

                <p className="mt-4 text-sm leading-6 text-(--text-secondary)">
                  {page.author_bio ||
                    "Time focado em estruturar automacoes e sistemas sob medida para operacoes B2B com processo complexo."}
                </p>

                <div className="mt-5 rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-(--text-primary)">
                    <ChartColumnIncreasing className="h-4 w-4 text-(--accent)" />
                    Resultado esperado
                  </div>
                  <p className="mt-2 text-sm leading-6 text-(--text-secondary)">
                    Menos improviso na operacao e mais criterio para decidir onde automatizar,
                    terceirizar ou redesenhar.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <aside className="lg:sticky lg:top-8">
            <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-lg)">
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                  {isCalculator ? "Acesso interativo" : "Liberar material"}
                </p>
                <h2 className="text-2xl font-semibold leading-tight">
                  {isCalculator ? "Calcule o ROI da automacao" : page.cta_text || "Receber agora"}
                </h2>
                <p className="text-sm leading-6 text-(--text-secondary)">
                  {isCalculator
                    ? "Use a calculadora publica para estimar custo anual, payback e ROI antes de falar com o time comercial."
                    : "Preencha os dados para receber o material e entrar na sequencia de nutricao configurada no SendPulse."}
                </p>
              </div>

              {isCalculator ? (
                <div className="mt-6 space-y-4">
                  <Button asChild className="w-full justify-between">
                    <a href={`/lm/calculadora?lead_magnet_id=${page.lead_magnet_id}`}>
                      Abrir calculadora
                      <ArrowRight className="h-4 w-4" />
                    </a>
                  </Button>
                  <Button asChild variant="outline" className="w-full justify-between">
                    <a href={page.public_url}>
                      Copiar link desta pagina
                      <ArrowRight className="h-4 w-4" />
                    </a>
                  </Button>
                </div>
              ) : (
                <form className="mt-6 space-y-3" onSubmit={handleSubmit}>
                  <Input
                    value={form.name}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, name: event.target.value }))
                    }
                    placeholder="Seu nome"
                    required
                  />
                  <Input
                    type="email"
                    value={form.email}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, email: event.target.value }))
                    }
                    placeholder="Seu melhor e-mail"
                    required
                  />
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      value={form.company || ""}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, company: event.target.value }))
                      }
                      placeholder="Empresa"
                      required
                    />
                    <Input
                      value={form.role || ""}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, role: event.target.value }))
                      }
                      placeholder="Cargo"
                      required
                    />
                  </div>
                  <Input
                    value={form.phone || ""}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, phone: event.target.value }))
                    }
                    placeholder="WhatsApp ou telefone"
                    required
                  />
                  <Input
                    value={form.linkedin_profile_url || ""}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        linkedin_profile_url: event.target.value,
                      }))
                    }
                    placeholder="LinkedIn opcional"
                  />

                  {error && (
                    <div className="rounded-2xl border border-(--danger)/30 bg-(--danger-subtle) px-3 py-2 text-sm text-(--danger-subtle-fg)">
                      {error}
                    </div>
                  )}

                  <Button type="submit" className="w-full justify-between" disabled={isSubmitting}>
                    {isSubmitting ? "Enviando..." : page.cta_text || "Receber material"}
                    <ArrowRight className="h-4 w-4" />
                  </Button>

                  <p className="text-xs leading-5 text-(--text-tertiary)">
                    Ao enviar, voce autoriza o contato sobre este material e sobre conteudos
                    relacionados ao tema.
                  </p>
                </form>
              )}

              {page.file_url && !isCalculator && (
                <div className="mt-6 rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-(--text-primary)">
                    <Download className="h-4 w-4 text-(--accent)" />
                    Entrega imediata
                  </div>
                  <p className="mt-2 text-sm leading-6 text-(--text-secondary)">
                    Depois do cadastro, voce vai para a pagina de obrigado e pode baixar o material
                    na hora.
                  </p>
                </div>
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
