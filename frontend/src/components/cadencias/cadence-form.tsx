"use client"

import { useState } from "react"
import { useCreateCadence, useUpdateCadence } from "@/lib/api/hooks/use-cadences"
import { useLeadLists } from "@/lib/api/hooks/use-lead-lists"
import { useEmailAccounts } from "@/lib/api/hooks/use-email-accounts"
import { useLinkedInAccounts } from "@/lib/api/hooks/use-linkedin-accounts"
import { LLMConfigForm, type LLMConfig } from "@/components/cadencias/llm-config-form"
import { TTSConfigForm, type TTSConfig } from "@/components/cadencias/tts-config-form"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useRouter } from "next/navigation"
import Link from "next/link"
import {
  FlaskConical,
  Tag,
  Zap,
  Users,
  BrainCircuit,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { Cadence, CreateCadenceBody, CadenceStep } from "@/lib/api/hooks/use-cadences"

interface CadenceFormProps {
  cadence?: Cadence
}

const DEFAULT_LLM = {
  llm_provider: "openai" as const,
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

// ── Section Card ───────────────────────────────────────────────────────────

interface SectionCardProps {
  number: string
  icon: React.ReactNode
  title: string
  subtitle?: string
  children: React.ReactNode
  className?: string
}

function SectionCard({ number, icon, title, subtitle, children, className }: SectionCardProps) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)",
        className,
      )}
    >
      <div className="flex items-center gap-3 border-b border-(--border-subtle) bg-(--bg-overlay) px-5 py-3.5">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-(--accent-subtle) text-xs font-bold text-(--accent)">
          {number}
        </span>
        <span className="text-(--text-tertiary)">{icon}</span>
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">{title}</p>
          {subtitle && <p className="text-xs text-(--text-tertiary)">{subtitle}</p>}
        </div>
      </div>
      <div className="space-y-4 p-5">{children}</div>
    </div>
  )
}

// ── Field ──────────────────────────────────────────────────────────────────

interface FieldProps {
  label: string
  htmlFor?: string
  hint?: string
  children: React.ReactNode
}

function Field({ label, htmlFor, hint, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      {htmlFor ? (
        <Label htmlFor={htmlFor} className="text-sm font-medium text-(--text-primary)">
          {label}
        </Label>
      ) : (
        <p className="text-sm font-medium text-(--text-primary)">{label}</p>
      )}
      {children}
      {hint && <p className="text-xs text-(--text-tertiary)">{hint}</p>}
    </div>
  )
}

// ── Styled Select ──────────────────────────────────────────────────────────

function StyledSelect({
  id,
  value,
  onChange,
  children,
  "aria-label": ariaLabel,
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      id={id}
      value={value}
      onChange={onChange}
      aria-label={ariaLabel}
      className="flex h-9 w-full rounded-lg border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 text-sm text-(--text-primary) shadow-(--shadow-sm) transition-colors focus:outline-none focus:ring-2 focus:ring-(--accent)/30 focus:border-(--accent)"
    >
      {children}
    </select>
  )
}

// ── Mode Card ──────────────────────────────────────────────────────────────

interface ModeCardProps {
  value: "automatic" | "semi_manual"
  onChange: (v: "automatic" | "semi_manual") => void
}

function ModeCard({ value, onChange }: ModeCardProps) {
  const OPTIONS = [
    {
      id: "automatic" as const,
      label: "Automático",
      description: "Todas as mensagens são enviadas automaticamente conforme o agendamento",
    },
    {
      id: "semi_manual" as const,
      label: "Semi-manual",
      description: "Convite enviado automaticamente; mensagens subsequentes revisadas por você",
    },
  ]
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {OPTIONS.map((opt) => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onChange(opt.id)}
          className={cn(
            "flex flex-col items-start gap-1 rounded-lg border px-4 py-3 text-left transition-all",
            value === opt.id
              ? "border-(--accent) bg-(--accent-subtle) shadow-(--shadow-sm)"
              : "border-(--border-default) bg-(--bg-overlay) hover:border-(--accent-border)",
          )}
        >
          <span
            className={cn(
              "text-sm font-semibold",
              value === opt.id ? "text-(--accent)" : "text-(--text-primary)",
            )}
          >
            {opt.label}
          </span>
          <span className="text-xs text-(--text-secondary)">{opt.description}</span>
        </button>
      ))}
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────

export function CadenceForm({ cadence }: CadenceFormProps) {
  const router = useRouter()
  const createCadence = useCreateCadence()
  const updateCadence = useUpdateCadence()
  const { data: lists } = useLeadLists()

  const [name, setName] = useState(cadence?.name ?? "")
  const [description, setDescription] = useState(cadence?.description ?? "")
  const [mode, setMode] = useState<"automatic" | "semi_manual">(cadence?.mode ?? "automatic")
  const [cadenceType, setCadenceType] = useState<"mixed" | "email_only">(
    cadence?.cadence_type ?? "mixed",
  )
  const [leadListId, setLeadListId] = useState(cadence?.lead_list_id ?? "")
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    llm_provider: (cadence?.llm_provider ?? DEFAULT_LLM.llm_provider) as LLMConfig["llm_provider"],
    llm_model: cadence?.llm_model ?? DEFAULT_LLM.llm_model,
    llm_temperature: cadence?.llm_temperature ?? DEFAULT_LLM.llm_temperature,
    llm_max_tokens: cadence?.llm_max_tokens ?? DEFAULT_LLM.llm_max_tokens,
  })
  const [ttsConfig, setTtsConfig] = useState<TTSConfig>({
    tts_provider: cadence?.tts_provider ?? null,
    tts_voice_id: cadence?.tts_voice_id ?? null,
    tts_speed: cadence?.tts_speed ?? 1.0,
    tts_pitch: cadence?.tts_pitch ?? 0.0,
  })
  const [emailAccountId, setEmailAccountId] = useState<string>(cadence?.email_account_id ?? "")
  const { data: emailAccountsData } = useEmailAccounts()
  const [linkedInAccountId, setLinkedInAccountId] = useState<string>(
    cadence?.linkedin_account_id ?? "",
  )
  const { data: linkedInAccountsData } = useLinkedInAccounts()
  const [targetSegment, setTargetSegment] = useState(cadence?.target_segment ?? "")
  const [personaDescription, setPersonaDescription] = useState(cadence?.persona_description ?? "")
  const [offerDescription, setOfferDescription] = useState(cadence?.offer_description ?? "")
  const [toneInstructions, setToneInstructions] = useState(cadence?.tone_instructions ?? "")
  const [contextOpen, setContextOpen] = useState(
    !!(
      cadence?.target_segment ||
      cadence?.persona_description ||
      cadence?.offer_description ||
      cadence?.tone_instructions
    ),
  )
  const [error, setError] = useState<string | null>(null)

  const isLoading = createCadence.isPending || updateCadence.isPending
  const isEdit = !!cadence
  const hasContextFilled = !!(
    targetSegment ||
    personaDescription ||
    offerDescription ||
    toneInstructions
  )

  // Na edição, preserva os passos existentes da cadência (gerenciados pela aba Passos)
  const existingSteps: CadenceStep[] = cadence?.steps_template ?? []

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError("Nome é obrigatório")
      return
    }

    const body: CreateCadenceBody = {
      name: name.trim(),
      ...(description.trim() ? { description: description.trim() } : {}),
      mode,
      cadence_type: cadenceType,
      llm: {
        provider: llmConfig.llm_provider as "openai" | "gemini",
        model: llmConfig.llm_model,
        temperature: llmConfig.llm_temperature,
        max_tokens: llmConfig.llm_max_tokens,
      },
      tts_provider: ttsConfig.tts_provider,
      tts_voice_id: ttsConfig.tts_voice_id,
      tts_speed: ttsConfig.tts_speed,
      tts_pitch: ttsConfig.tts_pitch,
      lead_list_id: leadListId || null,
      email_account_id: emailAccountId || null,
      linkedin_account_id: linkedInAccountId || null,
      target_segment: targetSegment.trim() || null,
      persona_description: personaDescription.trim() || null,
      offer_description: offerDescription.trim() || null,
      tone_instructions: toneInstructions.trim() || null,
      // Preserva passos ao salvar config (os passos são gerenciados na aba Passos)
      steps_template: existingSteps,
    }

    try {
      if (isEdit) {
        await updateCadence.mutateAsync({ id: cadence.id, ...body })
        router.push(`/cadencias/${cadence.id}`)
      } else {
        const created = await createCadence.mutateAsync(body)
        router.push(`/cadencias/${created.id}`)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar cadência. Tente novamente.")
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && (
        <div
          role="alert"
          className="mb-5 flex items-start gap-2.5 rounded-lg border border-(--danger)/30 bg-(--danger-subtle) px-4 py-3 text-sm text-(--danger-subtle-fg)"
        >
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="space-y-4">
        {/* 01 — Identidade */}
        <SectionCard
          number="01"
          icon={<Tag size={14} />}
          title="Identidade"
          subtitle="Nome e descrição desta cadência"
        >
          <Field label="Nome *" htmlFor="cadence-name">
            <Input
              id="cadence-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Prospecção SaaS B2B"
              required
            />
          </Field>
          <Field label="Descrição" htmlFor="cadence-desc">
            <Textarea
              id="cadence-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Público-alvo e objetivo desta cadência…"
            />
          </Field>
        </SectionCard>

        {/* 02 — Comportamento */}
        <SectionCard
          number="02"
          icon={<Zap size={14} />}
          title="Comportamento"
          subtitle="Como a cadência opera"
        >
          <Field label="Modo de operação">
            <ModeCard value={mode} onChange={setMode} />
          </Field>

          <Field label="Tipo de cadência" htmlFor="cadence-type">
            <StyledSelect
              id="cadence-type"
              value={cadenceType}
              onChange={(e) => setCadenceType(e.target.value as "mixed" | "email_only")}
              aria-label="Tipo de cadência"
            >
              <option value="mixed">Mista — LinkedIn + E-mail</option>
              <option value="email_only">Só E-mail — apenas passos de e-mail</option>
            </StyledSelect>
            {cadenceType === "email_only" && (
              <p className="mt-1 text-xs text-(--text-tertiary)">
                Todos os passos devem usar o canal E-mail. LinkedIn não se aplica.
              </p>
            )}
          </Field>
        </SectionCard>

        {/* 03 — Audiência e Canais */}
        <SectionCard
          number="03"
          icon={<Users size={14} />}
          title="Audiência e Canais"
          subtitle="Lista de leads e contas de envio"
        >
          <Field
            label="Lista de leads"
            htmlFor="cadence-list"
            hint="Leads adicionados a esta lista serão inscritos automaticamente na cadência."
          >
            <StyledSelect
              id="cadence-list"
              value={leadListId}
              onChange={(e) => setLeadListId(e.target.value)}
              aria-label="Selecionar lista de leads"
            >
              <option value="">Nenhuma lista vinculada</option>
              {lists?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.lead_count} leads)
                </option>
              ))}
            </StyledSelect>
          </Field>

          {cadenceType !== "email_only" && (
            <Field
              label="Conta LinkedIn"
              htmlFor="linkedin-account"
              hint="Deixe em branco para usar a conta Unipile global configurada em Integrações."
            >
              <StyledSelect
                id="linkedin-account"
                value={linkedInAccountId}
                onChange={(e) => setLinkedInAccountId(e.target.value)}
                aria-label="Conta LinkedIn"
              >
                <option value="">Padrão — conta Unipile global</option>
                {(linkedInAccountsData?.accounts ?? [])
                  .filter((a) => a.is_active)
                  .map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.display_name}
                      {acc.linkedin_username ? ` (${acc.linkedin_username})` : ""} —{" "}
                      {acc.provider_type === "native" ? "Cookie li_at" : "Unipile"}
                    </option>
                  ))}
              </StyledSelect>
            </Field>
          )}

          {cadenceType === "email_only" && (
            <Field
              label="Conta de e-mail"
              htmlFor="email-account"
              hint="Deixe em branco para usar a conta Unipile configurada em Integrações."
            >
              <StyledSelect
                id="email-account"
                value={emailAccountId}
                onChange={(e) => setEmailAccountId(e.target.value)}
                aria-label="Conta de e-mail"
              >
                <option value="">Padrão — conta Unipile global</option>
                {(emailAccountsData?.accounts ?? []).map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.display_name} ({acc.email_address})
                  </option>
                ))}
              </StyledSelect>
            </Field>
          )}
        </SectionCard>

        {/* 04 — Contexto para IA */}
        <div className="overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
          <button
            type="button"
            onClick={() => setContextOpen((v) => !v)}
            className="flex w-full items-center gap-3 border-b border-(--border-subtle) bg-(--bg-overlay) px-5 py-3.5 transition-colors hover:bg-(--bg-sunken)"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-(--accent-subtle) text-xs font-bold text-(--accent)">
              04
            </span>
            <span className="text-(--text-tertiary)">
              <BrainCircuit size={14} />
            </span>
            <div className="flex-1 text-left">
              <p className="text-sm font-semibold text-(--text-primary)">Contexto para IA</p>
              <p className="text-xs text-(--text-tertiary)">
                Alimenta o modelo com informações do seu negócio
              </p>
            </div>
            <div className="flex items-center gap-2">
              {hasContextFilled && (
                <span className="rounded-full bg-(--success-subtle) px-2 py-0.5 text-xs font-medium text-(--success)">
                  preenchido
                </span>
              )}
              {contextOpen ? (
                <ChevronUp size={14} className="text-(--text-tertiary)" />
              ) : (
                <ChevronDown size={14} className="text-(--text-tertiary)" />
              )}
            </div>
          </button>

          {contextOpen && (
            <div className="space-y-4 p-5">
              <Field label="Segmento-alvo" htmlFor="target-segment">
                <Input
                  id="target-segment"
                  value={targetSegment}
                  onChange={(e) => setTargetSegment(e.target.value)}
                  placeholder="Ex: SaaS B2B, indústria farmacêutica, varejo premium"
                  maxLength={300}
                />
              </Field>
              <Field label="Persona ideal" htmlFor="persona-desc">
                <Textarea
                  id="persona-desc"
                  value={personaDescription}
                  onChange={(e) => setPersonaDescription(e.target.value)}
                  rows={2}
                  placeholder="Ex: CTOs e VPs de Tecnologia de empresas com 200+ funcionários"
                />
              </Field>
              <Field
                label="Proposta de valor"
                htmlFor="offer-desc"
                hint="A IA mencionará isso sutilmente nos steps avançados."
              >
                <Textarea
                  id="offer-desc"
                  value={offerDescription}
                  onChange={(e) => setOfferDescription(e.target.value)}
                  rows={2}
                  placeholder="Ex: Automação de processos com IA para reduzir custos operacionais"
                />
              </Field>
              <Field label="Tom de escrita" htmlFor="tone-instructions">
                <Textarea
                  id="tone-instructions"
                  value={toneInstructions}
                  onChange={(e) => setToneInstructions(e.target.value)}
                  rows={2}
                  placeholder="Ex: Tom executivo mas descontraído. Evite jargões técnicos."
                />
              </Field>
            </div>
          )}
        </div>

        {/* 05 — Inteligência */}
        <SectionCard
          number="05"
          icon={<Sparkles size={14} />}
          title="Inteligência"
          subtitle="Modelo de linguagem e síntese de voz"
        >
          <LLMConfigForm value={llmConfig} onChange={setLlmConfig} />
          <div className="border-t border-(--border-subtle) pt-4">
            <TTSConfigForm
              value={ttsConfig}
              onChange={setTtsConfig}
              hasVoiceSteps={existingSteps.some((s) => s.use_voice)}
            />
          </div>
        </SectionCard>

        {/* Ações */}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isLoading} className="min-w-32">
            {isLoading ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar cadência"}
          </Button>
          {isEdit && cadence && (
            <Link href={`/cadencias/${cadence.id}/sandbox`}>
              <Button type="button" variant="outline">
                <FlaskConical size={14} aria-hidden="true" />
                Testar no Sandbox
              </Button>
            </Link>
          )}
        </div>
      </div>
    </form>
  )
}
