"use client"

import Image from "next/image"
import { useState } from "react"
import {
  ArrowRight,
  BadgeCheck,
  ChartColumnIncreasing,
  Check,
  Download,
  ExternalLink,
  Sparkles,
  Users,
} from "lucide-react"
import { env } from "@/env"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type {
  LandingPagePublicCaptureInput,
  LandingPagePublicData,
} from "@/lib/content-inbound/types"

interface Props {
  page: LandingPagePublicData
}

const BRAND_LOGO_SRC = `${env.NEXT_PUBLIC_API_URL}/assets/branding/compostoweb-logo-primary-transparent.webp`

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

  // ── Shared form JSX ──────────────────────────────────────────────────────
  const sharedForm = (
    <form className="mt-6 space-y-3" onSubmit={handleSubmit}>
      <Input
        value={form.name}
        onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
        placeholder="Seu nome"
        required
      />
      <Input
        type="email"
        value={form.email}
        onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
        placeholder="Seu melhor e-mail"
        required
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          value={form.company || ""}
          onChange={(event) => setForm((current) => ({ ...current, company: event.target.value }))}
          placeholder="Empresa"
          required
        />
        <Input
          value={form.role || ""}
          onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}
          placeholder="Cargo"
          required
        />
      </div>
      <Input
        value={form.phone || ""}
        onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
        placeholder="WhatsApp ou telefone"
        required
      />
      <Input
        value={form.linkedin_profile_url || ""}
        onChange={(event) =>
          setForm((current) => ({ ...current, linkedin_profile_url: event.target.value }))
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
        Ao enviar, voce autoriza o contato sobre este material e sobre conteudos relacionados ao
        tema.
      </p>
    </form>
  )

  // ── Template: Trust/Sequence (type = email_sequence) ─────────────────────
  if (page.lead_magnet_type === "email_sequence") {
    const sequenceSteps =
      page.features && page.features.length > 0
        ? page.features.map((f, i) => ({
            step: String(i + 1).padStart(2, "0"),
            label: f.title,
            desc: f.description,
          }))
        : [
            {
              step: "01",
              label: "Boas-vindas",
              desc: "Uma mensagem direta com o contexto do material e o que você vai receber nos próximos dias.",
            },
            {
              step: "02",
              label: "Conteúdo principal",
              desc: "O núcleo do material — insights, dados e frameworks aplicáveis ao seu cenário operacional.",
            },
            {
              step: "03",
              label: "Próximos passos",
              desc: "Recomendações concretas e, se fizer sentido, uma abertura para conversar com o time.",
            },
          ]

    return (
      <div className="min-h-screen bg-(--bg-page) bg-[radial-gradient(circle_at_top_left,color-mix(in_srgb,var(--accent)_18%,transparent),transparent_34%),linear-gradient(180deg,var(--bg-page)_0%,var(--bg-surface)_100%)] text-(--text-primary)">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-10 lg:px-8 lg:py-14">
          {/* Logo + Social proof */}
          <div className="flex flex-col gap-3">
            <Image
              src={BRAND_LOGO_SRC}
              alt="Composto Web"
              width={208}
              height={48}
              unoptimized
              className="h-auto w-52 object-contain"
            />

            <div className="flex flex-wrap items-center gap-3">
              {page.social_proof_count > 0 && (
                <div className="inline-flex items-center gap-2.5 rounded-full border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 shadow-sm">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-(--success-subtle) text-(--success-subtle-fg)">
                    <Users className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-sm font-bold text-(--success-subtle-fg)">
                    +{page.social_proof_count}
                  </span>
                  <span className="text-xs text-(--text-secondary)">
                    profissionais e empresas já acessaram
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
            <section className="flex flex-col gap-6">
              <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface)/90 p-7 shadow-(--shadow-lg) backdrop-blur">
                <div className="flex flex-col gap-4">
                  <div className="inline-flex w-fit items-center gap-2 rounded-full bg-(--accent-subtle) px-3 py-1 text-xs font-medium text-(--accent-subtle-fg)">
                    <Sparkles className="h-3.5 w-3.5" />
                    {page.badge_text ||
                      `Sequência curada pela ${page.publisher_name || "Composto Web"}`}
                  </div>
                  <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight lg:text-5xl">
                    {page.title}
                  </h1>
                  <p className="max-w-2xl text-base leading-7 text-(--text-secondary) lg:text-lg">
                    {page.subtitle ||
                      page.lead_magnet_description ||
                      "Uma sequência de e-mails com o que importa para quem precisa operar melhor sem aumentar equipe."}
                  </p>
                </div>
              </div>

              <div className="rounded-3xl border border-(--border-default) bg-(--bg-surface) p-6">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                  O que chega no seu e-mail
                </p>
                <div className="mt-4 flex flex-col gap-3">
                  {sequenceSteps.map(({ step, label, desc }) => (
                    <div
                      key={step}
                      className="flex gap-4 rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-(--accent) text-xs font-semibold text-(--accent)">
                        {step}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-(--text-primary)">{label}</p>
                        <p className="mt-0.5 text-sm leading-6 text-(--text-secondary)">{desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {page.benefits.length > 0 && (
                <div className="rounded-3xl border border-(--border-default) bg-(--bg-surface) p-6">
                  <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                    O que você vai receber
                  </p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
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
              )}

              <div className="flex items-center gap-3 rounded-2xl border border-(--border-subtle) bg-(--bg-surface) p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
                  <BadgeCheck className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-(--text-primary)">
                    {page.publisher_name || "Composto Web"}
                  </p>
                  <p className="text-xs leading-5 text-(--text-secondary)">
                    {page.author_bio ||
                      "Automações e sistemas sob medida para operações B2B com processo complexo."}
                  </p>
                </div>
              </div>
            </section>

            <aside className="lg:sticky lg:top-8">
              <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-lg)">
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                    Garanta sua vaga
                  </p>
                  <h2 className="text-2xl font-semibold leading-tight">
                    {page.cta_text || "Quero receber"}
                  </h2>
                  <p className="text-sm leading-6 text-(--text-secondary)">
                    Preencha os dados e receba cada e-mail da sequência no prazo certo.
                  </p>
                </div>
                {sharedForm}
              </div>
            </aside>
          </div>
        </div>
      </div>
    )
  }

  // ── Template: Link Externo ────────────────────────────────────────────────
  if (page.lead_magnet_type === "link") {
    return (
      <div className="min-h-screen bg-(--bg-page) bg-[radial-gradient(circle_at_top_left,color-mix(in_srgb,var(--accent)_18%,transparent),transparent_34%),linear-gradient(180deg,var(--bg-page)_0%,var(--bg-surface)_100%)] text-(--text-primary)">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-10 lg:px-8 lg:py-14">
          {/* Logo + Social proof */}
          <div className="flex flex-col gap-3">
            <Image
              src={BRAND_LOGO_SRC}
              alt="Composto Web"
              width={208}
              height={48}
              unoptimized
              className="h-auto w-52 object-contain"
            />
            <div className="flex flex-wrap items-center gap-3">
              {page.social_proof_count > 0 && (
                <div className="inline-flex items-center gap-2.5 rounded-full border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 shadow-sm">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-(--success-subtle) text-(--success-subtle-fg)">
                    <Users className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-sm font-bold text-(--success-subtle-fg)">
                    +{page.social_proof_count}
                  </span>
                  <span className="text-xs text-(--text-secondary)">
                    profissionais e empresas já acessaram
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
            <section className="flex flex-col gap-6">
              <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface)/90 p-7 shadow-(--shadow-lg) backdrop-blur">
                <div className="flex flex-col gap-4">
                  <div className="inline-flex w-fit items-center gap-2 rounded-full bg-(--accent-subtle) px-3 py-1 text-xs font-medium text-(--accent-subtle-fg)">
                    <ExternalLink className="h-3.5 w-3.5" />
                    {page.badge_text || "Recurso externo"}
                  </div>
                  <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight lg:text-5xl">
                    {page.title}
                  </h1>
                  <p className="max-w-2xl text-base leading-7 text-(--text-secondary) lg:text-lg">
                    {page.subtitle ||
                      page.lead_magnet_description ||
                      "Acesse o recurso e leve mais clareza para o seu processo."}
                  </p>
                </div>
              </div>

              {page.benefits.length > 0 && (
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
              )}

              {page.features && page.features.length > 0 && (
                <div className="rounded-3xl border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-sm)">
                  <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                    Sobre o recurso
                  </p>
                  <div className="mt-4 space-y-3">
                    {page.features.map((feature, index) => (
                      <div key={index} className="rounded-2xl bg-(--bg-overlay) p-4">
                        <p className="text-sm font-medium text-(--text-primary)">{feature.title}</p>
                        <p className="mt-1 text-sm leading-6 text-(--text-secondary)">
                          {feature.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 rounded-2xl border border-(--border-subtle) bg-(--bg-surface) p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
                  <BadgeCheck className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-(--text-primary)">
                    {page.publisher_name || "Composto Web"}
                  </p>
                  <p className="text-xs leading-5 text-(--text-secondary)">
                    {page.author_bio ||
                      "Automacoes e sistemas sob medida para operacoes B2B com processo complexo."}
                  </p>
                </div>
              </div>
            </section>

            <aside className="lg:sticky lg:top-8">
              <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-lg)">
                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                    Acessar recurso
                  </p>
                  <h2 className="text-2xl font-semibold leading-tight">
                    {page.cta_text || "Quero acessar"}
                  </h2>
                  <p className="text-sm leading-6 text-(--text-secondary)">
                    Preencha os dados e receba o link de acesso direto por e-mail.
                  </p>
                </div>
                {sharedForm}
                {page.file_url && (
                  <div className="mt-6 rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-(--text-primary)">
                      <ExternalLink className="h-4 w-4 text-(--accent)" />
                      Acesso imediato
                    </div>
                    <p className="mt-2 text-sm leading-6 text-(--text-secondary)">
                      Você será redirecionado para o recurso assim que confirmar o cadastro.
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

  // ── Template: Full/Rich (type = pdf | ferramenta | default) ────────────────────────────
  return (
    <div className="min-h-screen bg-(--bg-page) bg-[radial-gradient(circle_at_top_left,color-mix(in_srgb,var(--accent)_18%,transparent),transparent_34%),linear-gradient(180deg,var(--bg-page)_0%,var(--bg-surface)_100%)] text-(--text-primary)">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-10 lg:px-8 lg:py-14">
        {/* Logo + Social proof */}
        <div className="flex flex-col gap-3">
          <Image
            src={BRAND_LOGO_SRC}
            alt="Composto Web"
            width={208}
            height={48}
            unoptimized
            className="h-auto w-52 object-contain"
          />
          <div className="flex flex-wrap items-center gap-3">
            {page.social_proof_count > 0 && (
              <div className="inline-flex items-center gap-2.5 rounded-full border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 shadow-sm">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-(--success-subtle) text-(--success-subtle-fg)">
                  <Users className="h-3.5 w-3.5" />
                </div>
                <span className="text-sm font-bold text-(--success-subtle-fg)">
                  +{page.social_proof_count}
                </span>
                <span className="text-xs text-(--text-secondary)">
                  profissionais e empresas já acessaram
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
          <section className="flex flex-col gap-6">
            <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface)/90 p-7 shadow-(--shadow-lg) backdrop-blur">
              <div className="flex flex-col gap-4">
                <div className="inline-flex w-fit items-center gap-2 rounded-full bg-(--accent-subtle) px-3 py-1 text-xs font-medium text-(--accent-subtle-fg)">
                  <Sparkles className="h-3.5 w-3.5" />
                  {page.badge_text ||
                    "Material desenhado para times B2B que precisam operar melhor sem aumentar equipe"}
                </div>

                {page.hero_image_url && (
                  <div className="overflow-hidden rounded-2xl">
                    <Image
                      src={page.hero_image_url}
                      alt={page.title}
                      width={1200}
                      height={675}
                      unoptimized
                      className="h-auto w-full object-cover"
                    />
                  </div>
                )}

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
                  {(page.features && page.features.length > 0
                    ? page.features
                    : [
                        {
                          title: "Clareza de diagnostico",
                          description:
                            "O material mostra gargalos comuns, como priorizar o que automatizar e o que nao vale manter manual.",
                        },
                        {
                          title: "Aplicacao imediata",
                          description:
                            "Sem teoria solta. O foco e em processo, ganho operacional e decisao executiva com menos ruido.",
                        },
                      ]
                  ).map((feature, index) => (
                    <div key={index} className="rounded-2xl bg-(--bg-overlay) p-4">
                      <p className="text-sm font-medium text-(--text-primary)">{feature.title}</p>
                      <p className="mt-1 text-sm leading-6 text-(--text-secondary)">
                        {feature.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-3xl border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-sm)">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
                    {page.author_photo_url ? (
                      <Image
                        src={page.author_photo_url}
                        alt={page.publisher_name || "Autor"}
                        width={48}
                        height={48}
                        unoptimized
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <BadgeCheck className="h-5 w-5" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-(--text-primary)">Quem assina</p>
                    <p className="text-sm text-(--text-secondary)">
                      {page.publisher_name || "Composto Web"}
                    </p>
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
                    {page.expected_result ||
                      "Menos improviso na operacao e mais criterio para decidir onde automatizar, terceirizar ou redesenhar."}
                  </p>
                </div>
              </div>
            </div>
          </section>

          <aside className="lg:sticky lg:top-8">
            <div className="rounded-[28px] border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-lg)">
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                  Liberar material
                </p>
                <h2 className="text-2xl font-semibold leading-tight">
                  {page.cta_text || "Receber agora"}
                </h2>
                <p className="text-sm leading-6 text-(--text-secondary)">
                  Preencha os dados e receba o material direto no seu e-mail.
                </p>
              </div>

              {sharedForm}

              {page.file_url && (
                <div className="mt-6 rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-(--text-primary)">
                    <Download className="h-4 w-4 text-(--accent)" />
                    Entrega por e-mail
                  </div>
                  <p className="mt-2 text-sm leading-6 text-(--text-secondary)">
                    Entrega imediata: você recebe o material no e-mail e tem link de download
                    disponível assim que confirmar.
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
