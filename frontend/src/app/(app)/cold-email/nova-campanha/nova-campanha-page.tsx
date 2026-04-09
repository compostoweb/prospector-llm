"use client"

import { useState } from "react"
import { type ReactNode } from "react"
import { useRouter } from "next/navigation"
import {
  Mail,
  Users,
  BrainCircuit,
  CheckCircle2,
  Plus,
  Trash2,
  X,
  ChevronRight,
  ChevronLeft,
  Loader2,
  MailCheck,
  Calendar,
} from "lucide-react"
import {
  useCreateCadence,
  type CadenceStep,
  type CreateCadenceBody,
} from "@/lib/api/hooks/use-cadences"
import { useLeadLists, useLeadList } from "@/lib/api/hooks/use-lead-lists"
import { useEmailAccounts } from "@/lib/api/hooks/use-email-accounts"
import { LLMConfigForm, type LLMConfig } from "@/components/cadencias/llm-config-form"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

// ── Types ──────────────────────────────────────────────────────────────────

type EmailStepType = "email_first" | "email_followup" | "email_breakup"

interface LocalStep {
  day_offset: number
  step_type: EmailStepType
  subject_variants: string[]
}

interface EmailPreset {
  id: string
  label: string
  badge?: string
  description: string
  daysLabel: string
  steps: LocalStep[]
}

// ── Constants ──────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<EmailStepType, string> = {
  email_first: "Primeiro contato",
  email_followup: "Follow-up",
  email_breakup: "Encerramento",
}

const TYPE_COLOR: Record<EmailStepType, string> = {
  email_first: "bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300",
  email_followup: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300",
  email_breakup: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
}

const PRESETS: EmailPreset[] = [
  {
    id: "3-toques",
    label: "3 toques",
    badge: "Popular",
    description: "Primeiro contato, follow-up e encerramento. Sequência objetiva para volume.",
    daysLabel: "D0 · D4 · D9",
    steps: [
      {
        day_offset: 0,
        step_type: "email_first",
        subject_variants: ["Ideia para {{company}}", "{{first_name}}, ideia rápida"],
      },
      { day_offset: 4, step_type: "email_followup", subject_variants: [""] },
      { day_offset: 9, step_type: "email_breakup", subject_variants: ["Encerrando o contato"] },
    ],
  },
  {
    id: "5-toques",
    label: "5 toques",
    description: "Dois follows adicionais. Indicado para segmentos de ticket maior.",
    daysLabel: "D0 · D3 · D7 · D12 · D17",
    steps: [
      { day_offset: 0, step_type: "email_first", subject_variants: ["Ideia para {{company}}"] },
      { day_offset: 3, step_type: "email_followup", subject_variants: [""] },
      { day_offset: 7, step_type: "email_followup", subject_variants: [""] },
      { day_offset: 12, step_type: "email_followup", subject_variants: [""] },
      { day_offset: 17, step_type: "email_breakup", subject_variants: ["Encerrando o contato"] },
    ],
  },
  {
    id: "reativacao",
    label: "Reativação",
    description: "Retoma leads frios que já tiveram contato. Tom de retomada sem pressão.",
    daysLabel: "D0 · D5 · D11",
    steps: [
      {
        day_offset: 0,
        step_type: "email_first",
        subject_variants: ["Retomando contato, {{first_name}}"],
      },
      { day_offset: 5, step_type: "email_followup", subject_variants: ["Ainda faz sentido?"] },
      { day_offset: 11, step_type: "email_breakup", subject_variants: ["Fechando este ciclo"] },
    ],
  },
  {
    id: "custom",
    label: "Do zero",
    description: "Monte a sequência com total controle de dias e assuntos.",
    daysLabel: "Personalizado",
    steps: [{ day_offset: 0, step_type: "email_first", subject_variants: [""] }],
  },
]

const DEFAULT_LLM: LLMConfig = {
  llm_provider: "openai",
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

const WIZARD_STEPS = [
  { label: "Sequência", icon: Mail },
  { label: "Audiência", icon: Users },
  { label: "IA & Conteúdo", icon: BrainCircuit },
  { label: "Revisão", icon: CheckCircle2 },
]

const STEP_SUBTITLES = [
  "Defina o nome e os e-mails da campanha.",
  "Escolha a lista de leads e a conta de envio.",
  "Configure o modelo de IA e o contexto comercial.",
  "Revise tudo antes de criar a campanha.",
]

function cloneSteps(steps: LocalStep[]): LocalStep[] {
  return steps.map((step) => ({ ...step, subject_variants: [...step.subject_variants] }))
}

function getInitialSteps(): LocalStep[] {
  const preset = PRESETS.find((item) => item.id === "3-toques")
  return preset ? cloneSteps(preset.steps) : []
}

// ── EmailStepCard ──────────────────────────────────────────────────────────

function EmailStepCard({
  step,
  index,
  canRemove,
  onChange,
  onRemove,
}: {
  step: LocalStep
  index: number
  canRemove: boolean
  onChange: (s: LocalStep) => void
  onRemove: () => void
}) {
  function updateVariant(i: number, value: string) {
    const sv = [...step.subject_variants]
    sv[i] = value
    onChange({ ...step, subject_variants: sv })
  }

  function addVariant() {
    if (step.subject_variants.length >= 4) return
    onChange({ ...step, subject_variants: [...step.subject_variants, ""] })
  }

  function removeVariant(i: number) {
    const sv = step.subject_variants.filter((_, j) => j !== i)
    onChange({ ...step, subject_variants: sv.length > 0 ? sv : [""] })
  }

  const isAB = step.subject_variants.length > 1

  return (
    <div className="overflow-hidden rounded-lg border border-(--border-default) bg-(--bg-surface)">
      <div className="flex items-center gap-2 border-b border-(--border-subtle) bg-(--bg-overlay) px-4 py-2.5">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-(--bg-surface) text-[10px] font-bold text-(--text-secondary) ring-1 ring-(--border-default)">
          {index + 1}
        </span>

        <select
          value={step.step_type}
          onChange={(e) => onChange({ ...step, step_type: e.target.value as EmailStepType })}
          aria-label={`Tipo do e-mail ${index + 1}`}
          className="flex-1 rounded border border-(--border-default) bg-(--bg-surface) px-2 py-1 text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
        >
          {(Object.entries(TYPE_LABEL) as [EmailStepType, string][]).map(([t, l]) => (
            <option key={t} value={t}>
              {l}
            </option>
          ))}
        </select>

        {isAB && (
          <span className="shrink-0 rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700 dark:bg-violet-900/20 dark:text-violet-300">
            A/B
          </span>
        )}

        <div className="flex shrink-0 items-center gap-1">
          <Calendar size={11} className="text-(--text-tertiary)" aria-hidden="true" />
          <label htmlFor={`day-${index}`} className="sr-only">
            Dia de envio
          </label>
          <input
            id={`day-${index}`}
            type="number"
            min={0}
            max={90}
            value={step.day_offset}
            onChange={(e) => onChange({ ...step, day_offset: Math.max(0, Number(e.target.value)) })}
            className="w-12 rounded border border-(--border-default) bg-(--bg-surface) px-2 py-0.5 text-center text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
          />
          <span className="text-[10px] text-(--text-tertiary)">dia</span>
        </div>

        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            aria-label="Remover e-mail"
            className="shrink-0 rounded p-0.5 text-(--text-tertiary) hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
          >
            <Trash2 size={13} aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="space-y-2 p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-(--text-secondary)">
            {isAB ? "Variantes de assunto (teste A/B)" : "Assunto do e-mail"}
          </span>
          {step.subject_variants.length < 4 && (
            <button
              type="button"
              onClick={addVariant}
              className="flex items-center gap-0.5 text-xs text-(--accent) hover:underline"
            >
              <Plus size={10} aria-hidden="true" />
              Variante A/B
            </button>
          )}
        </div>

        {step.subject_variants.map((sv, i) => (
          <div key={i} className="flex items-center gap-1.5">
            {isAB && (
              <span className="w-4 shrink-0 text-center text-[10px] font-bold text-(--text-tertiary)">
                {String.fromCharCode(65 + i)}
              </span>
            )}
            <Input
              value={sv}
              onChange={(e) => updateVariant(i, e.target.value)}
              placeholder={i === 0 ? "Ex: Ideia para {{company}}" : "Assunto alternativo"}
              className="h-8 text-xs"
              aria-label={`Assunto variante ${String.fromCharCode(65 + i)}`}
            />
            {step.subject_variants.length > 1 && (
              <button
                type="button"
                onClick={() => removeVariant(i)}
                aria-label="Remover variante"
                className="shrink-0 text-(--text-tertiary) hover:text-red-500"
              >
                <X size={12} aria-hidden="true" />
              </button>
            )}
          </div>
        ))}

        <p className="mt-1 text-[10px] text-(--text-tertiary)">
          Variáveis: <code className="rounded bg-(--bg-overlay) px-1">{"{{company}}"}</code>{" "}
          <code className="rounded bg-(--bg-overlay) px-1">{"{{first_name}}"}</code>{" "}
          <code className="rounded bg-(--bg-overlay) px-1">{"{{job_title}}"}</code>
        </p>
      </div>
    </div>
  )
}

// ── Step 0 — Sequência ────────────────────────────────────────────────────

function StepSequencia({
  name,
  setName,
  presetId,
  setPresetId,
  steps,
  setSteps,
}: {
  name: string
  setName(v: string): void
  presetId: string
  setPresetId(v: string): void
  steps: LocalStep[]
  setSteps(s: LocalStep[]): void
}) {
  function pickPreset(p: EmailPreset) {
    setPresetId(p.id)
    setSteps(cloneSteps(p.steps))
  }

  function updateStep(i: number, updated: LocalStep) {
    const next = [...steps]
    next[i] = updated
    setSteps(next)
  }

  function addStep() {
    const last = steps.at(-1)
    const nextDay = last ? last.day_offset + 5 : 0
    setSteps([
      ...steps,
      { day_offset: nextDay, step_type: "email_followup", subject_variants: [""] },
    ])
    if (presetId !== "custom") setPresetId("custom")
  }

  function removeStep(i: number) {
    if (steps.length <= 1) return
    setSteps(steps.filter((_, j) => j !== i))
  }

  return (
    <div className="space-y-8">
      <div className="max-w-md space-y-1.5">
        <Label htmlFor="campaign-name">
          Nome da campanha{" "}
          <span className="text-red-400" aria-hidden="true">
            *
          </span>
        </Label>
        <Input
          id="campaign-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ex: SaaS Mid-Market Q2 2026"
        />
      </div>

      <div>
        <p className="mb-3 text-sm font-medium text-(--text-primary)">Estrutura da sequência</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {PRESETS.map((p) => {
            const isChosen = presetId === p.id
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => pickPreset(p)}
                className={cn(
                  "relative flex flex-col items-start gap-2 rounded-xl border-2 p-4 text-left transition-all",
                  isChosen
                    ? "border-(--accent) bg-(--accent)/5"
                    : "border-(--border-default) bg-(--bg-surface) hover:border-(--border-strong) hover:bg-(--bg-overlay)",
                )}
              >
                {p.badge && (
                  <span className="absolute right-2.5 top-2.5 rounded-full bg-(--accent)/15 px-2 py-px text-[9px] font-semibold uppercase tracking-wide text-(--accent)">
                    {p.badge}
                  </span>
                )}
                <Mail
                  size={16}
                  className={isChosen ? "text-(--accent)" : "text-(--text-tertiary)"}
                  aria-hidden="true"
                />
                <div>
                  <p className="text-sm font-semibold text-(--text-primary)">{p.label}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-(--text-secondary)">
                    {p.description}
                  </p>
                </div>
                <div className="mt-auto w-full">
                  <div className="flex gap-1" aria-hidden="true">
                    {p.steps.map((_, j) => (
                      <div
                        key={j}
                        className={cn(
                          "h-1 flex-1 rounded-full",
                          isChosen ? "bg-(--accent)" : "bg-(--border-default)",
                        )}
                      />
                    ))}
                  </div>
                  <p className="mt-1 text-[10px] text-(--text-tertiary)">{p.daysLabel}</p>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium text-(--text-primary)">
            E-mails na sequência{" "}
            <span className="text-xs font-normal text-(--text-tertiary)">
              ({steps.length} e-mail{steps.length !== 1 ? "s" : ""})
            </span>
          </p>
          <button
            type="button"
            onClick={addStep}
            className="flex items-center gap-1.5 rounded-md border border-(--border-default) px-3 py-1.5 text-xs text-(--text-primary) hover:bg-(--bg-overlay)"
          >
            <Plus size={12} aria-hidden="true" />
            Adicionar e-mail
          </button>
        </div>
        <div className="space-y-3">
          {steps.map((step, i) => (
            <EmailStepCard
              key={i}
              step={step}
              index={i}
              canRemove={steps.length > 1}
              onChange={(u) => updateStep(i, u)}
              onRemove={() => removeStep(i)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Step 1 — Audiência ────────────────────────────────────────────────────

function StepAudiencia({
  leadListId,
  setLeadListId,
  emailAccountId,
  setEmailAccountId,
  usePersonalFallback,
  setUsePersonalFallback,
}: {
  leadListId: string
  setLeadListId(v: string): void
  emailAccountId: string
  setEmailAccountId(v: string): void
  usePersonalFallback: boolean
  setUsePersonalFallback(v: boolean): void
}) {
  const { data: lists } = useLeadLists()
  const { data: listDetail } = useLeadList(leadListId)
  const { data: emailAccountsData } = useEmailAccounts()
  const accounts = (emailAccountsData?.accounts ?? []).filter((a) => a.is_active)
  const selectedAccount = accounts.find((a) => a.id === emailAccountId)

  return (
    <div className="max-w-lg space-y-8">
      <div className="space-y-2">
        <Label htmlFor="lead-list">Lista de leads</Label>
        <select
          id="lead-list"
          value={leadListId}
          onChange={(e) => setLeadListId(e.target.value)}
          aria-label="Lista de leads"
          className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
        >
          <option value="">Sem lista (inscrição manual depois)</option>
          {(lists ?? []).map((l) => (
            <option key={l.id} value={l.id}>
              {l.name} — {l.lead_count} lead{l.lead_count !== 1 ? "s" : ""}
            </option>
          ))}
        </select>

        {leadListId && listDetail && (
          <div className="flex items-center gap-2 rounded-md border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2.5 text-xs text-(--text-secondary)">
            <Users size={12} aria-hidden="true" />
            <span>
              <strong className="text-(--text-primary)">{listDetail.lead_count}</strong> lead
              {listDetail.lead_count !== 1 ? "s" : ""} na lista
              {listDetail.leads && listDetail.leads.length > 0 && (
                <span className="text-(--text-tertiary)">
                  {" · "}
                  {listDetail.leads
                    .slice(0, 3)
                    .map((l) => l.company)
                    .filter(Boolean)
                    .join(", ")}
                  {listDetail.leads.length > 3 ? "…" : ""}
                </span>
              )}
            </span>
          </div>
        )}

        {!leadListId && (
          <p className="text-xs text-(--text-tertiary)">
            Você poderá inscrever leads depois, direto pela página da cadência criada.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="email-account">Conta de e-mail de envio</Label>
        <select
          id="email-account"
          value={emailAccountId}
          onChange={(e) => setEmailAccountId(e.target.value)}
          aria-label="Conta de e-mail de envio"
          className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
        >
          <option value="">Conta padrão do sistema</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.display_name} — {a.email_address}
            </option>
          ))}
        </select>

        {selectedAccount && (
          <div className="flex items-center gap-2 rounded-md border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2.5 text-xs text-(--text-secondary)">
            <MailCheck size={12} aria-hidden="true" />
            <span>
              Limite:{" "}
              <strong className="text-(--text-primary)">
                {selectedAccount.daily_send_limit} e-mails/dia
              </strong>
              {" · "}
              {selectedAccount.from_name ?? selectedAccount.display_name}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-start gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
        <Switch
          id="personal-fallback"
          checked={usePersonalFallback}
          onCheckedChange={setUsePersonalFallback}
        />
        <div>
          <Label htmlFor="personal-fallback" className="cursor-pointer text-sm font-medium">
            Usar e-mail pessoal como fallback
          </Label>
          <p className="mt-0.5 text-xs text-(--text-secondary)">
            Quando o lead não tem e-mail corporativo, usa o e-mail pessoal cadastrado.
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Step 2 — IA & Conteúdo ────────────────────────────────────────────────

function StepConteudo({
  llmConfig,
  setLlmConfig,
  targetSegment,
  setTargetSegment,
  personaDescription,
  setPersonaDescription,
  offerDescription,
  setOfferDescription,
  toneInstructions,
  setToneInstructions,
}: {
  llmConfig: LLMConfig
  setLlmConfig(v: LLMConfig): void
  targetSegment: string
  setTargetSegment(v: string): void
  personaDescription: string
  setPersonaDescription(v: string): void
  offerDescription: string
  setOfferDescription(v: string): void
  toneInstructions: string
  setToneInstructions(v: string): void
}) {
  return (
    <div className="space-y-8">
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5">
        <p className="text-sm font-semibold text-(--text-primary)">Modelo de IA</p>
        <p className="mb-4 mt-0.5 text-xs text-(--text-secondary)">
          Modelo usado ao gerar o copy desta campanha de e-mail.
        </p>
        <LLMConfigForm value={llmConfig} onChange={setLlmConfig} />
      </div>

      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5">
        <p className="text-sm font-semibold text-(--text-primary)">Contexto comercial</p>
        <p className="mb-5 mt-0.5 text-xs text-(--text-secondary)">
          Quanto mais específico, mais relevante e personalizado será o e-mail gerado.
        </p>
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="target-segment">Segmento-alvo</Label>
            <Textarea
              id="target-segment"
              value={targetSegment}
              onChange={(e) => setTargetSegment(e.target.value)}
              rows={3}
              placeholder="Ex: Diretores de TI em empresas B2B de 100–500 funcionários"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="persona">Perfil do ICP</Label>
            <Textarea
              id="persona"
              value={personaDescription}
              onChange={(e) => setPersonaDescription(e.target.value)}
              rows={3}
              placeholder="Ex: Tomador de decisão técnica, busca ROI rápido, avesso a jargão"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="offer">O que você está oferecendo</Label>
            <Textarea
              id="offer"
              value={offerDescription}
              onChange={(e) => setOfferDescription(e.target.value)}
              rows={3}
              placeholder="Ex: Plataforma de automação de prospecção B2B com integração ao CRM"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tone">Tom da comunicação</Label>
            <Textarea
              id="tone"
              value={toneInstructions}
              onChange={(e) => setToneInstructions(e.target.value)}
              rows={3}
              placeholder="Ex: Direto, consultivo, sem buzzwords, sem gerundismo"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Step 3 — Revisão ──────────────────────────────────────────────────────

function SummaryRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-(--border-subtle) py-2.5 last:border-0">
      <span className="shrink-0 text-sm text-(--text-secondary)">{label}</span>
      <span className="text-right text-sm font-medium text-(--text-primary)">{value}</span>
    </div>
  )
}

function StepRevisao({
  name,
  steps,
  leadListId,
  emailAccountId,
  usePersonalFallback,
  llmConfig,
  targetSegment,
  offerDescription,
}: {
  name: string
  steps: LocalStep[]
  leadListId: string
  emailAccountId: string
  usePersonalFallback: boolean
  llmConfig: LLMConfig
  targetSegment: string
  offerDescription: string
}) {
  const { data: lists } = useLeadLists()
  const { data: accountsData } = useEmailAccounts()
  const list = lists?.find((l) => l.id === leadListId)
  const account = accountsData?.accounts.find((a) => a.id === emailAccountId)
  const totalDays = steps.at(-1)?.day_offset ?? 0

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface)">
        <div className="border-b border-(--border-subtle) px-5 py-4">
          <p className="font-semibold text-(--text-primary)">Resumo da campanha</p>
        </div>
        <div className="px-5 py-1">
          <SummaryRow label="Nome" value={name || "—"} />
          <SummaryRow label="Tipo" value="Só e-mail · Automática" />
          <SummaryRow
            label="Sequência"
            value={`${steps.length} e-mail${steps.length !== 1 ? "s" : ""} · ${totalDays} dias`}
          />
          <SummaryRow
            label="Lista"
            value={list ? `${list.name} (${list.lead_count} leads)` : "Nenhuma — inscrição manual"}
          />
          <SummaryRow
            label="Conta de envio"
            value={
              account
                ? `${account.display_name} — ${account.email_address}`
                : "Conta padrão do sistema"
            }
          />
          <SummaryRow
            label="Fallback pessoal"
            value={usePersonalFallback ? "Ativo" : "Desativado"}
          />
          <SummaryRow
            label="Modelo IA"
            value={`${llmConfig.llm_provider} / ${llmConfig.llm_model}`}
          />
          {targetSegment && <SummaryRow label="Segmento" value={targetSegment} />}
          {offerDescription && <SummaryRow label="Oferta" value={offerDescription} />}
        </div>
      </div>

      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface)">
        <div className="border-b border-(--border-subtle) px-5 py-4">
          <p className="font-semibold text-(--text-primary)">Sequência de e-mails</p>
        </div>
        <div className="divide-y divide-(--border-subtle)">
          {steps.map((s, i) => (
            <div key={i} className="flex items-start gap-3 px-5 py-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-(--bg-overlay) text-[10px] font-bold text-(--text-secondary)">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-medium",
                      TYPE_COLOR[s.step_type],
                    )}
                  >
                    {TYPE_LABEL[s.step_type]}
                  </span>
                  <span className="text-xs text-(--text-tertiary)">Dia {s.day_offset}</span>
                </div>
                {s.subject_variants.filter(Boolean).length > 0 && (
                  <p className="mt-1 truncate text-xs text-(--text-secondary)">
                    {s.subject_variants.filter(Boolean).join(" · ")}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function NovaCampanhaPage() {
  const router = useRouter()
  const createCadence = useCreateCadence()

  const [activeStep, setActiveStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Step 0
  const [name, setName] = useState("")
  const [presetId, setPresetId] = useState("3-toques")
  const [steps, setSteps] = useState<LocalStep[]>(getInitialSteps)

  // Step 1
  const [leadListId, setLeadListId] = useState("")
  const [emailAccountId, setEmailAccountId] = useState("")
  const [usePersonalFallback, setUsePersonalFallback] = useState(false)

  // Step 2
  const [llmConfig, setLlmConfig] = useState<LLMConfig>(DEFAULT_LLM)
  const [targetSegment, setTargetSegment] = useState("")
  const [personaDescription, setPersonaDescription] = useState("")
  const [offerDescription, setOfferDescription] = useState("")
  const [toneInstructions, setToneInstructions] = useState("")

  function validate(): string | null {
    if (activeStep === 0) {
      if (!name.trim()) return "Nome da campanha é obrigatório."
      if (steps.length === 0) return "Adicione pelo menos um e-mail na sequência."
    }
    return null
  }

  function goNext() {
    const err = validate()
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setActiveStep((p) => Math.min(p + 1, 3))
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  function goBack() {
    setError(null)
    setActiveStep((p) => Math.max(p - 1, 0))
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  async function submit() {
    if (!name.trim()) {
      setError("Nome é obrigatório.")
      return
    }
    setError(null)

    const cadenceSteps: CadenceStep[] = steps.map((s) => ({
      channel: "email" as const,
      day_offset: s.day_offset,
      message_template: "",
      use_voice: false,
      audio_file_id: null,
      step_type: s.step_type,
      subject_variants:
        s.subject_variants.filter(Boolean).length > 0 ? s.subject_variants.filter(Boolean) : null,
      email_template_id: null,
    }))

    const body: CreateCadenceBody & { allow_personal_email: boolean } = {
      name: name.trim(),
      mode: "automatic",
      cadence_type: "email_only",
      llm: {
        provider: llmConfig.llm_provider as "openai" | "gemini",
        model: llmConfig.llm_model,
        temperature: llmConfig.llm_temperature,
        max_tokens: llmConfig.llm_max_tokens,
      },
      lead_list_id: leadListId || null,
      email_account_id: emailAccountId || null,
      target_segment: targetSegment.trim() || null,
      persona_description: personaDescription.trim() || null,
      offer_description: offerDescription.trim() || null,
      tone_instructions: toneInstructions.trim() || null,
      allow_personal_email: usePersonalFallback,
      steps_template: cadenceSteps,
    }

    try {
      const created = await createCadence.mutateAsync(body)
      toast.success("Campanha criada com sucesso!")
      router.push(`/cadencias/${created.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar campanha.")
    }
  }

  const stepContent = [
    <StepSequencia
      key="seq"
      name={name}
      setName={setName}
      presetId={presetId}
      setPresetId={setPresetId}
      steps={steps}
      setSteps={setSteps}
    />,
    <StepAudiencia
      key="aud"
      leadListId={leadListId}
      setLeadListId={setLeadListId}
      emailAccountId={emailAccountId}
      setEmailAccountId={setEmailAccountId}
      usePersonalFallback={usePersonalFallback}
      setUsePersonalFallback={setUsePersonalFallback}
    />,
    <StepConteudo
      key="cont"
      llmConfig={llmConfig}
      setLlmConfig={setLlmConfig}
      targetSegment={targetSegment}
      setTargetSegment={setTargetSegment}
      personaDescription={personaDescription}
      setPersonaDescription={setPersonaDescription}
      offerDescription={offerDescription}
      setOfferDescription={setOfferDescription}
      toneInstructions={toneInstructions}
      setToneInstructions={setToneInstructions}
    />,
    <StepRevisao
      key="rev"
      name={name}
      steps={steps}
      leadListId={leadListId}
      emailAccountId={emailAccountId}
      usePersonalFallback={usePersonalFallback}
      llmConfig={llmConfig}
      targetSegment={targetSegment}
      offerDescription={offerDescription}
    />,
  ]

  const currentWizardStep = WIZARD_STEPS[activeStep] ?? { label: "Sequência", icon: Mail }
  const currentSubtitle = STEP_SUBTITLES[activeStep] ?? "Defina o nome e os e-mails da campanha."

  return (
    <div className="mx-auto max-w-3xl space-y-8 pb-16">
      {/* Page header */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-(--accent)">
          Cold Email
        </p>
        <h1 className="mt-1 text-2xl font-bold text-(--text-primary)">{currentWizardStep.label}</h1>
        <p className="mt-1 text-sm text-(--text-secondary)">{currentSubtitle}</p>
      </div>

      {/* Stepper */}
      <nav aria-label="Etapas do wizard">
        <ol className="flex items-center">
          {WIZARD_STEPS.map((step, i) => {
            const isActive = i === activeStep
            const isDone = i < activeStep
            return (
              <li key={i} className="flex flex-1 items-center">
                <button
                  type="button"
                  disabled={i > activeStep}
                  onClick={() => {
                    if (isDone) {
                      setActiveStep(i)
                      setError(null)
                    }
                  }}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors",
                    isActive
                      ? "bg-(--accent)/10 text-(--accent)"
                      : isDone
                        ? "cursor-pointer text-(--accent) hover:bg-(--accent)/5"
                        : "cursor-default text-(--text-disabled)",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ring-1",
                      isActive
                        ? "bg-(--accent) text-white ring-(--accent)"
                        : isDone
                          ? "bg-(--accent) text-white ring-(--accent)"
                          : "bg-(--bg-overlay) text-(--text-disabled) ring-(--border-default)",
                    )}
                  >
                    {isDone ? "✓" : i + 1}
                  </span>
                  <span className="hidden sm:inline">{step.label}</span>
                </button>
                {i < WIZARD_STEPS.length - 1 && (
                  <div
                    className={cn(
                      "mx-1 h-px flex-1",
                      isDone ? "bg-(--accent)" : "bg-(--border-default)",
                    )}
                    aria-hidden="true"
                  />
                )}
              </li>
            )
          })}
        </ol>
      </nav>

      {/* Step content */}
      {stepContent[activeStep]}

      {/* Error banner */}
      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between border-t border-(--border-default) pt-6">
        <button
          type="button"
          onClick={() => router.push("/cold-email")}
          className="text-sm text-(--text-secondary) hover:text-(--text-primary)"
        >
          Cancelar
        </button>

        <div className="flex items-center gap-2">
          {activeStep > 0 && (
            <button
              type="button"
              onClick={goBack}
              className="flex items-center gap-1.5 rounded-md border border-(--border-default) px-4 py-2 text-sm text-(--text-primary) hover:bg-(--bg-overlay)"
            >
              <ChevronLeft size={14} aria-hidden="true" />
              Voltar
            </button>
          )}

          {activeStep < 3 ? (
            <button
              type="button"
              onClick={goNext}
              className="flex items-center gap-1.5 rounded-md bg-(--accent) px-5 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              Continuar
              <ChevronRight size={14} aria-hidden="true" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void submit()}
              disabled={createCadence.isPending}
              className="flex items-center gap-1.5 rounded-md bg-(--accent) px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {createCadence.isPending ? (
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
              ) : (
                <MailCheck size={14} aria-hidden="true" />
              )}
              {createCadence.isPending ? "Criando…" : "Criar campanha"}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
