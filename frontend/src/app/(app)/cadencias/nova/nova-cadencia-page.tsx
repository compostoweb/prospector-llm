"use client"

import { useEffect, useState } from "react"
import { type ReactNode } from "react"
import { useRouter } from "next/navigation"
import {
  GitBranch,
  Users,
  BrainCircuit,
  CheckCircle2,
  Plus,
  Trash2,
  Mail,
  Linkedin,
  ChevronRight,
  ChevronLeft,
  Loader2,
} from "lucide-react"
import {
  useCreateCadence,
  type CadenceStep,
  type CreateCadenceBody,
  type CadenceChannel,
  type StepType,
} from "@/lib/api/hooks/use-cadences"
import { useLeadLists, useLeadList } from "@/lib/api/hooks/use-lead-lists"
import { useEmailAccounts } from "@/lib/api/hooks/use-email-accounts"
import { useLinkedInAccounts } from "@/lib/api/hooks/use-linkedin-accounts"
import { getTenantLLMConfig, useTenant } from "@/lib/api/hooks/use-tenant"
import { LLMConfigForm, type LLMConfig } from "@/components/cadencias/llm-config-form"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

// ── Types ──────────────────────────────────────────────────────────────────

interface LocalStep {
  channel: CadenceChannel
  day_offset: number
  step_type: StepType | null
  subject_variants: string[]
}

interface CadencePreset {
  id: string
  label: string
  badge?: string
  description: string
  cadence_type: "mixed" | "email_only"
  mode: "automatic" | "semi_manual"
  steps: LocalStep[]
}

// ── Constants ──────────────────────────────────────────────────────────────

const CHANNEL_LABEL: Record<string, string> = {
  linkedin_connect: "LinkedIn – Pedido de conexão",
  linkedin_dm: "LinkedIn – Mensagem direta",
  email: "E-mail",
}

const CHANNEL_COLOR: Record<string, string> = {
  linkedin_connect: "bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300",
  linkedin_dm: "bg-sky-100 text-sky-700 dark:bg-sky-900/20 dark:text-sky-300",
  email: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300",
}

const CHANNEL_ICON: Record<string, ReactNode> = {
  linkedin_connect: <Linkedin size={11} aria-hidden="true" />,
  linkedin_dm: <Linkedin size={11} aria-hidden="true" />,
  email: <Mail size={11} aria-hidden="true" />,
}

const PRESETS: CadencePreset[] = [
  {
    id: "multicanal",
    label: "Multicanal",
    badge: "Recomendado",
    description: "LinkedIn + E-mail. Alta taxa de engajamento para leads frios.",
    cadence_type: "mixed",
    mode: "automatic",
    steps: [
      {
        channel: "linkedin_connect",
        day_offset: 0,
        step_type: "linkedin_connect",
        subject_variants: [],
      },
      {
        channel: "linkedin_dm",
        day_offset: 3,
        step_type: "linkedin_dm_post_connect",
        subject_variants: [],
      },
      {
        channel: "email",
        day_offset: 7,
        step_type: "email_first",
        subject_variants: ["Ideia para {{company}}"],
      },
      { channel: "email", day_offset: 14, step_type: "email_followup", subject_variants: [] },
    ],
  },
  {
    id: "cold-email",
    label: "Cold E-mail",
    description: "Só e-mail. Automático, ideal para alto volume.",
    cadence_type: "email_only",
    mode: "automatic",
    steps: [
      {
        channel: "email",
        day_offset: 0,
        step_type: "email_first",
        subject_variants: ["Ideia para {{company}}"],
      },
      { channel: "email", day_offset: 4, step_type: "email_followup", subject_variants: [] },
      {
        channel: "email",
        day_offset: 9,
        step_type: "email_breakup",
        subject_variants: ["Encerrando o contato"],
      },
    ],
  },
  {
    id: "networking",
    label: "Networking LinkedIn",
    description: "Conexão + mensagem manual personalizada no LinkedIn.",
    cadence_type: "mixed",
    mode: "semi_manual",
    steps: [
      {
        channel: "linkedin_connect",
        day_offset: 0,
        step_type: "linkedin_connect",
        subject_variants: [],
      },
      {
        channel: "linkedin_dm",
        day_offset: 5,
        step_type: "linkedin_dm_first",
        subject_variants: [],
      },
    ],
  },
  {
    id: "reativacao",
    label: "Reativação",
    description: "Retoma leads frios. Tom de retomada, sem pressão.",
    cadence_type: "email_only",
    mode: "automatic",
    steps: [
      {
        channel: "email",
        day_offset: 0,
        step_type: "email_first",
        subject_variants: ["Retomando contato, {{first_name}}"],
      },
      {
        channel: "email",
        day_offset: 5,
        step_type: "email_followup",
        subject_variants: ["Ainda faz sentido?"],
      },
      {
        channel: "email",
        day_offset: 11,
        step_type: "email_breakup",
        subject_variants: ["Fechando este ciclo"],
      },
    ],
  },
]

const WIZARD_STEPS = [
  { label: "Estrutura", icon: GitBranch },
  { label: "Audiência", icon: Users },
  { label: "IA & Conteúdo", icon: BrainCircuit },
  { label: "Revisão", icon: CheckCircle2 },
]

const STEP_SUBTITLES = [
  "Defina o nome, o preset e os passos da cadência.",
  "Escolha a lista de leads e as contas de envio.",
  "Configure o modelo de IA e o contexto comercial.",
  "Revise tudo antes de criar a cadência.",
]

function cloneSteps(steps: LocalStep[]): LocalStep[] {
  return steps.map((step) => ({ ...step, subject_variants: [...step.subject_variants] }))
}

function getInitialSteps(): LocalStep[] {
  const preset = PRESETS.find((item) => item.id === "multicanal")
  return preset ? cloneSteps(preset.steps) : []
}

// ── StepCard ──────────────────────────────────────────────────────────────

function StepCard({
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
  const isEmail = step.channel === "email"

  return (
    <div className="overflow-hidden rounded-lg border border-(--border-default) bg-(--bg-surface)">
      <div className="flex items-center gap-2 border-b border-(--border-subtle) bg-(--bg-overlay) px-4 py-2.5">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-(--bg-surface) text-[10px] font-bold text-(--text-secondary) ring-1 ring-(--border-default)">
          {index + 1}
        </span>

        <select
          value={step.channel}
          onChange={(e) =>
            onChange({ ...step, channel: e.target.value as CadenceChannel, step_type: null })
          }
          aria-label={`Canal do passo ${index + 1}`}
          className="flex-1 rounded border border-(--border-default) bg-(--bg-surface) px-2 py-1 text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
        >
          {Object.entries(CHANNEL_LABEL).map(([ch, lbl]) => (
            <option key={ch} value={ch}>
              {lbl}
            </option>
          ))}
        </select>

        <div className="flex shrink-0 items-center gap-1">
          <span className="text-[10px] text-(--text-tertiary)">Dia</span>
          <input
            type="number"
            min={0}
            max={90}
            value={step.day_offset}
            onChange={(e) => onChange({ ...step, day_offset: Math.max(0, Number(e.target.value)) })}
            aria-label={`Dia do passo ${index + 1}`}
            className="w-12 rounded border border-(--border-default) bg-(--bg-surface) px-2 py-0.5 text-center text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
          />
        </div>

        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            aria-label="Remover passo"
            className="shrink-0 rounded p-0.5 text-(--text-tertiary) hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
          >
            <Trash2 size={13} aria-hidden="true" />
          </button>
        )}
      </div>

      {isEmail && (
        <div className="space-y-2 p-4">
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-(--text-secondary)">Assunto do e-mail</span>
            <Input
              value={step.subject_variants[0] ?? ""}
              onChange={(e) => onChange({ ...step, subject_variants: [e.target.value] })}
              placeholder="Ex: Ideia para {{company}}"
              className="h-8 text-xs"
              aria-label="Assunto do e-mail"
            />
            <p className="text-[10px] text-(--text-tertiary)">
              Variáveis: <code className="rounded bg-(--bg-overlay) px-1">{"{{company}}"}</code>{" "}
              <code className="rounded bg-(--bg-overlay) px-1">{"{{first_name}}"}</code>
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Step 0 — Estrutura ────────────────────────────────────────────────────

function StepEstrutura({
  name,
  setName,
  presetId,
  setPresetId,
  steps,
  setSteps,
  setCadenceType,
}: {
  name: string
  setName(v: string): void
  presetId: string
  setPresetId(v: string): void
  steps: LocalStep[]
  setSteps(s: LocalStep[]): void
  setCadenceType(v: "mixed" | "email_only"): void
}) {
  function pickPreset(p: CadencePreset) {
    setPresetId(p.id)
    setCadenceType(p.cadence_type)
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
      { channel: "email", day_offset: nextDay, step_type: "email_followup", subject_variants: [] },
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
        <Label htmlFor="cadence-name">
          Nome da cadência{" "}
          <span className="text-red-400" aria-hidden="true">
            *
          </span>
        </Label>
        <Input
          id="cadence-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ex: Outbound SaaS Q2 2026"
        />
      </div>

      <div>
        <p className="mb-3 text-sm font-medium text-(--text-primary)">Preset</p>
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
                <GitBranch
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
                  <p className="mt-1 text-[10px] text-(--text-tertiary)">
                    {p.cadence_type === "email_only" ? "Só e-mail" : "Multicanal"} ·{" "}
                    {p.mode === "automatic" ? "Auto" : "Semi-manual"}
                  </p>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium text-(--text-primary)">
            Passos da sequência{" "}
            <span className="text-xs font-normal text-(--text-tertiary)">
              ({steps.length} passo{steps.length !== 1 ? "s" : ""})
            </span>
          </p>
          <button
            type="button"
            onClick={addStep}
            className="flex items-center gap-1.5 rounded-md border border-(--border-default) px-3 py-1.5 text-xs text-(--text-primary) hover:bg-(--bg-overlay)"
          >
            <Plus size={12} aria-hidden="true" />
            Adicionar passo
          </button>
        </div>
        <div className="space-y-3">
          {steps.map((step, i) => (
            <StepCard
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
  cadenceType,
  leadListId,
  setLeadListId,
  emailAccountId,
  setEmailAccountId,
  linkedInAccountId,
  setLinkedInAccountId,
}: {
  cadenceType: "mixed" | "email_only"
  leadListId: string
  setLeadListId(v: string): void
  emailAccountId: string
  setEmailAccountId(v: string): void
  linkedInAccountId: string
  setLinkedInAccountId(v: string): void
}) {
  const { data: lists } = useLeadLists()
  const { data: listDetail } = useLeadList(leadListId)
  const { data: emailAccountsData } = useEmailAccounts()
  const { data: linkedInAccountsData } = useLinkedInAccounts()
  const emailAccounts = (emailAccountsData?.accounts ?? []).filter((a) => a.is_active)
  const linkedInAccounts = (linkedInAccountsData?.accounts ?? []).filter((a) => a.is_active)

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
            </span>
          </div>
        )}
        {!leadListId && (
          <p className="text-xs text-(--text-tertiary)">
            Inscreva leads depois, na página da cadência criada.
          </p>
        )}
      </div>

      {cadenceType !== "mixed" || true ? (
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
            {emailAccounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.display_name} — {a.email_address}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {cadenceType === "mixed" && (
        <div className="space-y-2">
          <Label htmlFor="linkedin-account">Conta LinkedIn</Label>
          <select
            id="linkedin-account"
            value={linkedInAccountId}
            onChange={(e) => setLinkedInAccountId(e.target.value)}
            aria-label="Conta LinkedIn"
            className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
          >
            <option value="">Selecione uma conta LinkedIn</option>
            {linkedInAccounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.display_name ?? a.id} ·{" "}
                {a.provider_type === "unipile" ? "Unipile" : "Cookie li_at"}
                {a.supports_inmail ? " · InMail" : " · sem InMail"}
              </option>
            ))}
          </select>
        </div>
      )}
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
          Modelo usado ao gerar mensagens desta cadência.
        </p>
        <LLMConfigForm value={llmConfig} onChange={setLlmConfig} />
      </div>

      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5">
        <p className="text-sm font-semibold text-(--text-primary)">Contexto comercial</p>
        <p className="mb-5 mt-0.5 text-xs text-(--text-secondary)">
          Quanto mais específico, mais relevante será a mensagem gerada.
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
              placeholder="Ex: Tomador de decisão técnica, busca ROI rápido"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="offer">O que você está oferecendo</Label>
            <Textarea
              id="offer"
              value={offerDescription}
              onChange={(e) => setOfferDescription(e.target.value)}
              rows={3}
              placeholder="Ex: Plataforma de automação de prospecção B2B"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tone">Tom da comunicação</Label>
            <Textarea
              id="tone"
              value={toneInstructions}
              onChange={(e) => setToneInstructions(e.target.value)}
              rows={3}
              placeholder="Ex: Direto, consultivo, sem buzzwords"
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
  cadenceType,
  leadListId,
  emailAccountId,
  linkedInAccountId,
  llmConfig,
  targetSegment,
  offerDescription,
}: {
  name: string
  steps: LocalStep[]
  cadenceType: "mixed" | "email_only"
  leadListId: string
  emailAccountId: string
  linkedInAccountId: string
  llmConfig: LLMConfig
  targetSegment: string
  offerDescription: string
}) {
  const { data: lists } = useLeadLists()
  const { data: accountsData } = useEmailAccounts()
  const { data: linkedInData } = useLinkedInAccounts()
  const list = lists?.find((l) => l.id === leadListId)
  const emailAccount = accountsData?.accounts.find((a) => a.id === emailAccountId)
  const linkedInAccount = linkedInData?.accounts.find((a) => a.id === linkedInAccountId)
  const totalDays = steps.at(-1)?.day_offset ?? 0

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface)">
        <div className="border-b border-(--border-subtle) px-5 py-4">
          <p className="font-semibold text-(--text-primary)">Resumo da cadência</p>
        </div>
        <div className="px-5 py-1">
          <SummaryRow label="Nome" value={name || "—"} />
          <SummaryRow
            label="Tipo"
            value={cadenceType === "email_only" ? "Só e-mail" : "Multicanal"}
          />
          <SummaryRow
            label="Sequência"
            value={`${steps.length} passo${steps.length !== 1 ? "s" : ""} · ${totalDays} dias`}
          />
          <SummaryRow
            label="Lista"
            value={list ? `${list.name} (${list.lead_count} leads)` : "Nenhuma — inscrição manual"}
          />
          {emailAccount && (
            <SummaryRow
              label="E-mail"
              value={`${emailAccount.display_name} — ${emailAccount.email_address}`}
            />
          )}
          {cadenceType === "mixed" && linkedInAccount && (
            <SummaryRow
              label="LinkedIn"
              value={`${linkedInAccount.display_name ?? linkedInAccount.id} · ${linkedInAccount.provider_type === "unipile" ? "Unipile" : "Cookie li_at"}${linkedInAccount.supports_inmail ? " · InMail habilitado" : " · sem InMail"}`}
            />
          )}
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
          <p className="font-semibold text-(--text-primary)">Passos</p>
        </div>
        <div className="divide-y divide-(--border-subtle)">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-3 px-5 py-3">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-(--bg-overlay) text-[10px] font-bold text-(--text-secondary)">
                {i + 1}
              </span>
              <span
                className={cn(
                  "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
                  CHANNEL_COLOR[s.channel] ?? "bg-(--bg-overlay) text-(--text-secondary)",
                )}
              >
                {CHANNEL_ICON[s.channel]}
                {CHANNEL_LABEL[s.channel] ?? s.channel}
              </span>
              <span className="text-xs text-(--text-tertiary)">Dia {s.day_offset}</span>
              {s.channel === "email" && s.subject_variants[0] && (
                <span className="ml-auto truncate text-xs text-(--text-secondary)">
                  {s.subject_variants[0]}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function NovaCadenciaPage() {
  const router = useRouter()
  const createCadence = useCreateCadence()
  const { data: tenant, isFetched: tenantFetched, isError: tenantLoadFailed } = useTenant()

  const [activeStep, setActiveStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Step 0
  const [name, setName] = useState("")
  const [presetId, setPresetId] = useState("multicanal")
  const [cadenceType, setCadenceType] = useState<"mixed" | "email_only">("mixed")
  const [steps, setSteps] = useState<LocalStep[]>(getInitialSteps)

  // Step 1
  const [leadListId, setLeadListId] = useState("")
  const [emailAccountId, setEmailAccountId] = useState("")
  const [linkedInAccountId, setLinkedInAccountId] = useState("")

  // Step 2
  const [llmDirty, setLlmDirty] = useState(false)
  const tenantLLMScope = cadenceType === "email_only" ? "cold_email" : "system"
  const llmConfigReady = llmDirty || (tenantFetched && !tenantLoadFailed)
  const llmConfigError = tenantLoadFailed
    ? "Nao foi possivel carregar as configuracoes de IA do tenant. Recarregue a pagina ou ajuste manualmente antes de criar a cadencia."
    : "As configuracoes de IA do tenant ainda estao carregando. Aguarde ou ajuste manualmente antes de criar a cadencia."
  const [llmConfig, setLlmConfig] = useState<LLMConfig>(() =>
    getTenantLLMConfig(undefined, "system"),
  )
  const [targetSegment, setTargetSegment] = useState("")
  useEffect(() => {
    if (llmDirty) return
    setLlmConfig(getTenantLLMConfig(tenant?.integration, tenantLLMScope))
  }, [llmDirty, tenant?.integration, tenantLLMScope])

  function handleLlmConfigChange(nextConfig: LLMConfig) {
    setLlmDirty(true)
    setLlmConfig(nextConfig)
  }

  const [personaDescription, setPersonaDescription] = useState("")
  const [offerDescription, setOfferDescription] = useState("")
  const [toneInstructions, setToneInstructions] = useState("")

  function validate(): string | null {
    if (activeStep === 0) {
      if (!name.trim()) return "Nome da cadência é obrigatório."
      if (steps.length === 0) return "Adicione pelo menos um passo."
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
    if (!llmConfigReady) {
      setError(llmConfigError)
      return
    }
    setError(null)

    const effectiveLlmConfig = llmDirty
      ? llmConfig
      : getTenantLLMConfig(tenant?.integration, tenantLLMScope)

    const cadenceSteps: CadenceStep[] = steps.map((s) => ({
      channel: s.channel,
      day_offset: s.day_offset,
      message_template: "",
      use_voice: false,
      audio_file_id: null,
      step_type: s.step_type,
      subject_variants:
        s.channel === "email" && s.subject_variants.filter(Boolean).length > 0
          ? s.subject_variants.filter(Boolean)
          : null,
      email_template_id: null,
    }))

    const body: CreateCadenceBody = {
      name: name.trim(),
      mode: PRESETS.find((p) => p.id === presetId)?.mode ?? "automatic",
      cadence_type: cadenceType,
      llm: {
        provider: effectiveLlmConfig.llm_provider,
        model: effectiveLlmConfig.llm_model,
        temperature: effectiveLlmConfig.llm_temperature,
        max_tokens: effectiveLlmConfig.llm_max_tokens,
      },
      lead_list_id: leadListId || null,
      email_account_id: emailAccountId || null,
      linkedin_account_id: cadenceType === "mixed" ? linkedInAccountId || null : null,
      target_segment: targetSegment.trim() || null,
      persona_description: personaDescription.trim() || null,
      offer_description: offerDescription.trim() || null,
      tone_instructions: toneInstructions.trim() || null,
      steps_template: cadenceSteps,
    }

    try {
      const created = await createCadence.mutateAsync(body)
      toast.success("Cadência criada em pausa. Use o play para iniciar quando estiver pronta.")
      router.push(`/cadencias/${created.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar cadência.")
    }
  }

  const stepContent = [
    <StepEstrutura
      key="est"
      name={name}
      setName={setName}
      presetId={presetId}
      setPresetId={setPresetId}
      steps={steps}
      setSteps={setSteps}
      setCadenceType={setCadenceType}
    />,
    <StepAudiencia
      key="aud"
      cadenceType={cadenceType}
      leadListId={leadListId}
      setLeadListId={setLeadListId}
      emailAccountId={emailAccountId}
      setEmailAccountId={setEmailAccountId}
      linkedInAccountId={linkedInAccountId}
      setLinkedInAccountId={setLinkedInAccountId}
    />,
    <StepConteudo
      key="cont"
      llmConfig={llmConfig}
      setLlmConfig={handleLlmConfigChange}
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
      cadenceType={cadenceType}
      leadListId={leadListId}
      emailAccountId={emailAccountId}
      linkedInAccountId={linkedInAccountId}
      llmConfig={llmConfig}
      targetSegment={targetSegment}
      offerDescription={offerDescription}
    />,
  ]

  const currentWizardStep = WIZARD_STEPS[activeStep] ?? { label: "Estrutura", icon: GitBranch }
  const currentSubtitle =
    STEP_SUBTITLES[activeStep] ?? "Defina o nome, o preset e os passos da cadência."

  return (
    <div className="mx-auto max-w-3xl space-y-8 pb-16">
      {/* Page header */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-(--accent)">Cadências</p>
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
          onClick={() => router.push("/cadencias")}
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
              Próximo
              <ChevronRight size={14} aria-hidden="true" />
            </button>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={createCadence.isPending || !llmConfigReady}
              className="flex items-center gap-1.5 rounded-md bg-(--accent) px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
            >
              {createCadence.isPending ? (
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
              ) : null}
              {llmConfigReady ? "Criar cadência" : "Carregando IA..."}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
