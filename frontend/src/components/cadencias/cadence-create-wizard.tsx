"use client"

import type { Route as AppRoute } from "next"
import Link from "next/link"
import { useSession } from "next-auth/react"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import {
  AlertTriangle,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Linkedin,
  ListChecks,
  Mail,
  MessageSquare,
  Route,
  ShieldCheck,
  Sparkles,
  Users,
  Volume2,
  type LucideIcon,
} from "lucide-react"
import { CadenceSteps } from "@/components/cadencias/cadence-steps"
import { LLMConfigForm } from "@/components/cadencias/llm-config-form"
import { TTSConfigForm, type TTSConfig } from "@/components/cadencias/tts-config-form"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { useAudioFiles } from "@/lib/api/hooks/use-audio-files"
import {
  useCreateCadence,
  type CadenceChannel,
  type CadenceStep,
  type CreateCadenceBody,
} from "@/lib/api/hooks/use-cadences"
import { getTenantLLMConfig, useTenant } from "@/lib/api/hooks/use-tenant"
import { useEmailAccounts } from "@/lib/api/hooks/use-email-accounts"
import { useEmailTemplates } from "@/lib/api/hooks/use-email-templates"
import { useLeadList, useLeadLists } from "@/lib/api/hooks/use-lead-lists"
import { useLinkedInAccounts } from "@/lib/api/hooks/use-linkedin-accounts"
import { channelLabel, cn } from "@/lib/utils"

type CadenceMode = "automatic" | "semi_manual"
type CadenceType = "mixed" | "email_only"
type PresetId = "multichannel" | "cold-email" | "linkedin-handshake" | "reactivation" | "custom"

interface WizardStepDefinition {
  id: "strategy" | "audience" | "content" | "review"
  title: string
  description: string
  icon: LucideIcon
}

interface CadencePreset {
  id: Exclude<PresetId, "custom">
  title: string
  headline: string
  description: string
  bestFor: string
  cadenceType: CadenceType
  mode: CadenceMode
  icon: LucideIcon
  steps: CadenceStep[]
}

interface WizardLLMConfig {
  llm_provider: "openai" | "gemini" | "anthropic" | "openrouter"
  llm_model: string
  llm_temperature: number
  llm_max_tokens: number
}

interface ReadinessItem {
  title: string
  countLabel: string
  description: string
  href: AppRoute
  icon: LucideIcon
  state: "ready" | "attention" | "optional"
}

const SELECT_CLASSNAME =
  "flex h-10 w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) shadow-sm transition-colors focus:border-(--accent) focus:outline-none"

const WIZARD_STEPS: WizardStepDefinition[] = [
  {
    id: "strategy",
    title: "Estrutura",
    description: "Preset, tipo e modo da operação",
    icon: Route,
  },
  {
    id: "audience",
    title: "Audiência",
    description: "Lista, contas e prontidão do envio",
    icon: Users,
  },
  {
    id: "content",
    title: "Conteúdo",
    description: "Contexto comercial, IA e steps",
    icon: BrainCircuit,
  },
  {
    id: "review",
    title: "Revisão",
    description: "Resumo operacional antes de salvar",
    icon: ShieldCheck,
  },
]

function buildStep(
  channel: CadenceChannel,
  dayOffset: number,
  overrides: Partial<CadenceStep> = {},
): CadenceStep {
  return {
    channel,
    day_offset: dayOffset,
    message_template: "",
    use_voice: false,
    audio_file_id: null,
    step_type: null,
    subject_variants: null,
    email_template_id: null,
    ...overrides,
  }
}

const CADENCE_PRESETS: CadencePreset[] = [
  {
    id: "multichannel",
    title: "Outbound multicanal",
    headline: "LinkedIn + e-mail em sequência curta",
    description:
      "Convite no LinkedIn, abordagem por DM, e-mail com variantes de assunto e follow-up final com voz.",
    bestFor:
      "Primeiro contato com contas frias quando você quer cadência de volume sem perder contexto.",
    cadenceType: "mixed",
    mode: "automatic",
    icon: Sparkles,
    steps: [
      buildStep("linkedin_connect", 0, { step_type: "linkedin_connect" }),
      buildStep("linkedin_dm", 2, { step_type: "linkedin_dm_first" }),
      buildStep("email", 4, {
        step_type: "email_first",
        subject_variants: ["Ideia para {company}", "Pergunta rápida sobre {company}"],
      }),
      buildStep("linkedin_dm", 8, {
        step_type: "linkedin_dm_post_connect_voice",
        use_voice: true,
      }),
      buildStep("email", 12, { step_type: "email_followup" }),
    ],
  },
  {
    id: "cold-email",
    title: "Cold email em 3 toques",
    headline: "Sequência objetiva só por e-mail",
    description:
      "Primeiro contato, follow-up de lembrança e encerramento com variantes de assunto para medir tração.",
    bestFor:
      "Base com e-mails corporativos validados e cadências focadas em escala no canal de e-mail.",
    cadenceType: "email_only",
    mode: "automatic",
    icon: Mail,
    steps: [
      buildStep("email", 0, {
        step_type: "email_first",
        subject_variants: ["Ideia para {company}", "Como vocês estão tratando {company}?"],
      }),
      buildStep("email", 4, { step_type: "email_followup" }),
      buildStep("email", 9, { step_type: "email_breakup" }),
    ],
  },
  {
    id: "linkedin-handshake",
    title: "Networking semi-manual",
    headline: "Conecta automático, conversa com supervisão",
    description:
      "Convite automático no LinkedIn e continuidade orientada para operação semi-manual depois da conexão aceita.",
    bestFor:
      "Campanhas de ticket maior, onde a primeira conexão é automatizada e o restante pede julgamento humano.",
    cadenceType: "mixed",
    mode: "semi_manual",
    icon: Linkedin,
    steps: [
      buildStep("linkedin_connect", 0, { step_type: "linkedin_connect" }),
      buildStep("linkedin_dm", 2, { step_type: "linkedin_dm_post_connect" }),
      buildStep("manual_task", 5),
      buildStep("email", 7, { step_type: "email_followup" }),
    ],
  },
  {
    id: "reactivation",
    title: "Reativação de pipeline",
    headline: "Retoma conversas mornas com poucos toques",
    description:
      "Dois e-mails de retomada e um toque final para bases já aquecidas ou leads que esfriaram no meio do processo.",
    bestFor: "Reengajar leads antigos sem recriar uma jornada longa.",
    cadenceType: "email_only",
    mode: "automatic",
    icon: MessageSquare,
    steps: [
      buildStep("email", 0, { step_type: "email_first" }),
      buildStep("email", 5, {
        step_type: "email_followup",
        subject_variants: ["Retomando nossa conversa", "Ainda faz sentido para {company}?"],
      }),
      buildStep("email", 11, { step_type: "email_breakup" }),
    ],
  },
]

function cloneSteps(steps: CadenceStep[]): CadenceStep[] {
  return steps.map((step) => ({
    ...step,
    subject_variants: step.subject_variants ? [...step.subject_variants] : null,
  }))
}

function getPresetById(presetId: Exclude<PresetId, "custom">): CadencePreset {
  const fallbackPreset = CADENCE_PRESETS.at(0)

  if (!fallbackPreset) {
    throw new Error("Cadence presets não configurados.")
  }

  return CADENCE_PRESETS.find((preset) => preset.id === presetId) ?? fallbackPreset
}

function normalizeStepsForCadenceType(
  steps: CadenceStep[],
  cadenceType: CadenceType,
): CadenceStep[] {
  if (cadenceType !== "email_only") {
    return steps
  }

  const emailOnlySteps = steps
    .filter((step) => step.channel === "email")
    .map((step) => ({
      ...step,
      use_voice: false,
      audio_file_id: null,
    }))

  if (emailOnlySteps.length > 0) {
    return emailOnlySteps
  }

  return cloneSteps(getPresetById("cold-email").steps)
}

function resolvePresetId(rawPreset: string | null): Exclude<PresetId, "custom"> {
  switch (rawPreset) {
    case "cold-email":
    case "email":
    case "email-only":
      return "cold-email"
    case "linkedin":
    case "semi-manual":
      return "linkedin-handshake"
    case "reactivation":
      return "reactivation"
    default:
      return "multichannel"
  }
}

function countByChannel(steps: CadenceStep[]): Array<{ channel: string; count: number }> {
  const counts = new Map<string, number>()

  for (const step of steps) {
    counts.set(step.channel, (counts.get(step.channel) ?? 0) + 1)
  }

  return Array.from(counts.entries())
    .map(([channel, count]) => ({ channel, count }))
    .sort((left, right) => left.channel.localeCompare(right.channel))
}

function WizardStepButton({
  step,
  index,
  active,
  completed,
  onClick,
}: {
  step: WizardStepDefinition
  index: number
  active: boolean
  completed: boolean
  onClick: () => void
}) {
  const Icon = step.icon

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-start gap-3 rounded-2xl border p-4 text-left transition-colors",
        active
          ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
          : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--border-subtle) hover:bg-(--bg-overlay)",
      )}
    >
      <div
        className={cn(
          "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
          active
            ? "border-(--accent) bg-(--bg-surface) text-(--accent)"
            : completed
              ? "border-(--success) bg-(--success-subtle) text-(--success-subtle-fg)"
              : "border-(--border-default) bg-(--bg-overlay) text-(--text-tertiary)",
        )}
      >
        {completed ? (
          <CheckCircle2 size={16} aria-hidden="true" />
        ) : (
          <Icon size={16} aria-hidden="true" />
        )}
      </div>
      <div className="min-w-0">
        <p className={cn("text-sm font-semibold", active ? "text-(--text-primary)" : "")}>
          0{index + 1}. {step.title}
        </p>
        <p
          className={cn(
            "mt-1 text-xs",
            active ? "text-(--text-secondary)" : "text-(--text-tertiary)",
          )}
        >
          {step.description}
        </p>
      </div>
    </button>
  )
}

function PresetCard({
  preset,
  selected,
  onSelect,
}: {
  preset: CadencePreset
  selected: boolean
  onSelect: () => void
}) {
  const Icon = preset.icon

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group h-full rounded-2xl border text-left transition-all",
        selected
          ? "border-(--accent) bg-(--accent-subtle) shadow-(--shadow-sm)"
          : "border-(--border-default) bg-(--bg-surface) hover:-translate-y-0.5 hover:border-(--border-subtle) hover:shadow-(--shadow-sm)",
      )}
    >
      <div className="flex h-full flex-col gap-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-11 w-11 items-center justify-center rounded-2xl border",
                selected
                  ? "border-(--accent) bg-(--bg-surface) text-(--accent)"
                  : "border-(--border-default) bg-(--bg-overlay) text-(--text-tertiary)",
              )}
            >
              <Icon size={18} aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-(--text-primary)">{preset.title}</p>
              <p className="mt-1 text-xs text-(--text-secondary)">{preset.headline}</p>
            </div>
          </div>
          {selected ? <Badge variant="success">Base escolhida</Badge> : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant={preset.cadenceType === "email_only" ? "info" : "default"}>
            {preset.cadenceType === "email_only" ? "Só e-mail" : "Multicanal"}
          </Badge>
          <Badge variant={preset.mode === "semi_manual" ? "warning" : "outline"}>
            {preset.mode === "semi_manual" ? "Semi-manual" : "Automática"}
          </Badge>
          <Badge variant="outline">{preset.steps.length} passos</Badge>
        </div>

        <p className="text-sm leading-6 text-(--text-secondary)">{preset.description}</p>
        <p className="mt-auto text-xs text-(--text-tertiary)">{preset.bestFor}</p>
      </div>
    </button>
  )
}

function ReadinessCard({ item }: { item: ReadinessItem }) {
  const Icon = item.icon
  const badgeVariant =
    item.state === "ready" ? "success" : item.state === "attention" ? "warning" : "outline"
  const badgeLabel =
    item.state === "ready" ? "Pronto" : item.state === "attention" ? "Ação necessária" : "Opcional"

  return (
    <Card className="rounded-2xl shadow-none">
      <CardContent className="flex h-full flex-col gap-4 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-(--bg-overlay) text-(--text-tertiary)">
              <Icon size={16} aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-(--text-primary)">{item.title}</p>
              <p className="text-xs text-(--text-tertiary)">{item.countLabel}</p>
            </div>
          </div>
          <Badge variant={badgeVariant}>{badgeLabel}</Badge>
        </div>

        <p className="text-sm leading-6 text-(--text-secondary)">{item.description}</p>

        <Button asChild variant="link" size="sm" className="w-fit px-0">
          <Link href={item.href}>Abrir configuração</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 text-sm">
      <span className="text-(--text-tertiary)">{label}</span>
      <span className="text-right font-medium text-(--text-primary)">{value}</span>
    </div>
  )
}

export function CadenceCreateWizard({
  defaultPreset,
}: {
  defaultPreset?: Exclude<PresetId, "custom">
}) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { status } = useSession()
  const requestedPreset = getPresetById(
    defaultPreset ?? resolvePresetId(searchParams.get("preset")),
  )
  const createCadence = useCreateCadence()
  const { data: tenant, isFetched: tenantFetched, isError: tenantLoadFailed } = useTenant()
  const { data: lists, error: leadListsError, isLoading: loadingLeadLists } = useLeadLists()
  const { data: emailAccountsData } = useEmailAccounts()
  const { data: linkedInAccountsData } = useLinkedInAccounts()
  const { data: emailTemplates } = useEmailTemplates(undefined, true)
  const { data: audioFilesData } = useAudioFiles()

  const [activeStep, setActiveStep] = useState(0)
  const [selectedPresetId, setSelectedPresetId] = useState<PresetId>(requestedPreset.id)
  const [name, setName] = useState("")
  const [description, setDescription] = useState(requestedPreset.description)
  const [mode, setMode] = useState<CadenceMode>(requestedPreset.mode)
  const [cadenceType, setCadenceType] = useState<CadenceType>(requestedPreset.cadenceType)
  const [leadListId, setLeadListId] = useState("")
  const { data: leadListDetail } = useLeadList(leadListId)
  const [llmDirty, setLlmDirty] = useState(false)
  const llmScope = cadenceType === "email_only" ? "cold_email" : "system"
  const llmConfigReady = llmDirty || (tenantFetched && !tenantLoadFailed)
  const llmConfigError = tenantLoadFailed
    ? "Nao foi possivel carregar as configuracoes de IA do tenant. Recarregue a pagina ou ajuste manualmente antes de criar a cadencia."
    : "As configuracoes de IA do tenant ainda estao carregando. Aguarde ou ajuste manualmente antes de criar a cadencia."
  const [llmConfig, setLlmConfig] = useState<WizardLLMConfig>(() =>
    getTenantLLMConfig(
      undefined,
      requestedPreset.cadenceType === "email_only" ? "cold_email" : "system",
    ),
  )
  const [steps, setSteps] = useState<CadenceStep[]>(() => cloneSteps(requestedPreset.steps))
  const [ttsConfig, setTtsConfig] = useState<TTSConfig>({
    tts_provider: null,
    tts_voice_id: null,
    tts_speed: 1.0,
    tts_pitch: 0.0,
  })
  const [emailAccountId, setEmailAccountId] = useState("")
  const [linkedInAccountId, setLinkedInAccountId] = useState("")
  const [targetSegment, setTargetSegment] = useState("")
  const [personaDescription, setPersonaDescription] = useState("")
  const [offerDescription, setOfferDescription] = useState("")
  const [toneInstructions, setToneInstructions] = useState("")
  const [usePersonalEmailFallback, setUsePersonalEmailFallback] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedPreset =
    selectedPresetId === "custom"
      ? null
      : (CADENCE_PRESETS.find((preset) => preset.id === selectedPresetId) ?? null)

  const emailAccounts = useMemo(
    () => emailAccountsData?.accounts ?? [],
    [emailAccountsData?.accounts],
  )
  const linkedInAccounts = useMemo(
    () => linkedInAccountsData?.accounts ?? [],
    [linkedInAccountsData?.accounts],
  )
  const activeEmailAccounts = useMemo(
    () => emailAccounts.filter((account) => account.is_active),
    [emailAccounts],
  )
  const activeLinkedInAccounts = useMemo(
    () => linkedInAccounts.filter((account) => account.is_active),
    [linkedInAccounts],
  )
  const inmailCapableLinkedInAccounts = useMemo(
    () => activeLinkedInAccounts.filter((account) => account.supports_inmail),
    [activeLinkedInAccounts],
  )
  const activeEmailTemplates = emailTemplates ?? []
  const audioFiles = audioFilesData?.items ?? []

  const selectedLeadList = lists?.find((list) => list.id === leadListId) ?? null
  const selectedEmailAccount =
    emailAccounts.find((account) => account.id === emailAccountId) ?? null
  const selectedLinkedInAccount =
    linkedInAccounts.find((account) => account.id === linkedInAccountId) ?? null
  const hasEmailSteps = steps.some((step) => step.channel === "email")
  const hasLinkedInSteps = steps.some((step) => step.channel.startsWith("linkedin"))
  const hasInmailSteps = steps.some((step) => step.channel === "linkedin_inmail")
  const hasVoiceSteps = steps.some((step) => step.use_voice)
  const isListsPending = status === "loading" || loadingLeadLists
  const allowedChannels = cadenceType === "email_only" ? (["email"] as CadenceChannel[]) : undefined
  const totalLeads = leadListDetail?.lead_count ?? selectedLeadList?.lead_count ?? 0
  const channelCounts = useMemo(() => countByChannel(steps), [steps])

  const readinessItems: ReadinessItem[] = [
    {
      title: "Listas de leads",
      countLabel: isListsPending
        ? "Carregando listas..."
        : leadListsError
          ? "Falha ao carregar listas"
          : lists && lists.length > 0
            ? `${lists.length} lista${lists.length === 1 ? "" : "s"} pronta${lists.length === 1 ? "" : "s"}`
            : "Nenhuma lista criada",
      description: leadListsError
        ? "A API não retornou as listas do tenant atual. Confirme se o backend está ativo e recarregue a página."
        : leadListId && totalLeads > 0
          ? `${selectedLeadList?.name ?? "Lista selecionada"} com ${totalLeads} leads disponíveis para prévia e operação.`
          : "Vincular uma lista deixa o sandbox útil e já define a audiência inicial da cadência.",
      href: "/listas",
      icon: Users,
      state:
        leadListsError || (!isListsPending && (!lists || lists.length === 0))
          ? "attention"
          : "ready",
    },
    {
      title: "Contas de e-mail",
      countLabel:
        activeEmailAccounts.length > 0
          ? `${activeEmailAccounts.length} conta${activeEmailAccounts.length === 1 ? "" : "s"} ativa${activeEmailAccounts.length === 1 ? "" : "s"}`
          : "Nenhuma conta ativa",
      description:
        hasEmailSteps || cadenceType === "email_only"
          ? "Necessárias para steps de e-mail. Sem conta específica, a cadência depende da conta global configurada."
          : "Mesmo em cadências mistas, vale deixar uma conta pronta para fallback e follow-ups.",
      href: "/configuracoes/email-accounts",
      icon: Mail,
      state:
        hasEmailSteps || cadenceType === "email_only"
          ? activeEmailAccounts.length > 0 || !!emailAccountId
            ? "ready"
            : "attention"
          : "optional",
    },
    {
      title: "Contas LinkedIn",
      countLabel:
        activeLinkedInAccounts.length > 0
          ? hasInmailSteps
            ? `${activeLinkedInAccounts.length} conta${activeLinkedInAccounts.length === 1 ? "" : "s"} ativa${activeLinkedInAccounts.length === 1 ? "" : "s"} · ${inmailCapableLinkedInAccounts.length} com InMail`
            : `${activeLinkedInAccounts.length} conta${activeLinkedInAccounts.length === 1 ? "" : "s"} ativa${activeLinkedInAccounts.length === 1 ? "" : "s"}`
          : "Nenhuma conta ativa",
      description:
        cadenceType === "mixed"
          ? hasInmailSteps
            ? "Usadas para connect, DM e ações no LinkedIn. InMail só roda em conta marcada como compatível; sem conta específica, a cadência usa o fallback global."
            : "Usadas para connect, DM e ações no LinkedIn. Sem conta específica, a cadência usa o fallback global."
          : "Não são necessárias em campanhas só e-mail.",
      href: "/configuracoes/linkedin-accounts",
      icon: Linkedin,
      state:
        cadenceType === "mixed"
          ? activeLinkedInAccounts.length > 0 || !!linkedInAccountId
            ? "ready"
            : "attention"
          : "optional",
    },
    {
      title: "Templates de e-mail",
      countLabel:
        activeEmailTemplates.length > 0
          ? `${activeEmailTemplates.length} template${activeEmailTemplates.length === 1 ? "" : "s"} ativo${activeEmailTemplates.length === 1 ? "" : "s"}`
          : "Nenhum template ativo",
      description: hasEmailSteps
        ? "Templates aceleram steps de e-mail e mantêm o copy padronizado quando a IA não for suficiente."
        : "Opcional por enquanto, mas útil se você planeja expandir a cadência para e-mail.",
      href: "/cold-email/templates",
      icon: FileText,
      state: hasEmailSteps ? (activeEmailTemplates.length > 0 ? "ready" : "attention") : "optional",
    },
    {
      title: "Áudios prontos",
      countLabel:
        audioFiles.length > 0
          ? `${audioFiles.length} arquivo${audioFiles.length === 1 ? "" : "s"} disponível${audioFiles.length === 1 ? "" : "is"}`
          : "Nenhum áudio salvo",
      description: hasVoiceSteps
        ? "Útil quando você quer voz pré-gravada em vez de TTS. Se vazio, o sistema usa o provider TTS configurado."
        : "Opcional enquanto sua cadência não usar voice notes.",
      href: "/configuracoes/audios",
      icon: Volume2,
      state: hasVoiceSteps ? (audioFiles.length > 0 ? "ready" : "optional") : "optional",
    },
  ]

  const reviewWarnings = [
    !llmConfigReady ? llmConfigError : null,
    !leadListId
      ? "Nenhuma lista foi vinculada. Você ainda poderá salvar a cadência, mas precisará iniciar leads manualmente depois."
      : null,
    hasEmailSteps && activeEmailAccounts.length === 0 && !emailAccountId
      ? "Não há conta de e-mail ativa selecionada. Garanta que exista fallback global antes de colocar esta cadência em operação."
      : null,
    cadenceType === "mixed" &&
    hasLinkedInSteps &&
    activeLinkedInAccounts.length === 0 &&
    !linkedInAccountId
      ? "Não há conta LinkedIn ativa selecionada. A cadência dependerá da configuração global do tenant."
      : null,
    hasInmailSteps &&
    selectedLinkedInAccount !== null &&
    !selectedLinkedInAccount.supports_inmail
      ? "A conta LinkedIn selecionada não está marcada com suporte a InMail. Esses steps serão pulados antes de consumir budget."
      : null,
    hasInmailSteps && !linkedInAccountId && inmailCapableLinkedInAccounts.length === 0
      ? "Há steps de InMail, mas nenhuma conta ativa foi marcada com essa capability. O fallback global continua sem sinalização explícita aqui."
      : null,
    hasVoiceSteps && !ttsConfig.tts_provider
      ? "Há steps com voz e nenhum provider TTS específico configurado. O sistema vai cair no provider global, se existir."
      : null,
    hasEmailSteps && activeEmailTemplates.length === 0
      ? "Você está sem templates ativos de e-mail. Os steps vão depender apenas de texto manual ou geração por IA."
      : null,
  ].filter((warning): warning is string => Boolean(warning))

  const strategyHighlights = [
    `${steps.length} passo${steps.length === 1 ? "" : "s"} na sequência`,
    cadenceType === "email_only"
      ? "Fluxo concentrado em e-mail"
      : "Fluxo combinado entre LinkedIn e e-mail",
    mode === "semi_manual"
      ? "A operação exige supervisão após a conexão"
      : "Envio pensado para rodar automaticamente",
  ]

  function updateCadenceType(nextType: CadenceType) {
    setCadenceType(nextType)
    setSelectedPresetId("custom")

    if (nextType === "email_only") {
      setMode("automatic")
      setLinkedInAccountId("")
    }

    setSteps((currentSteps) => normalizeStepsForCadenceType(currentSteps, nextType))
  }

  useEffect(() => {
    if (llmDirty) return
    setLlmConfig(getTenantLLMConfig(tenant?.integration, llmScope))
  }, [llmDirty, tenant?.integration, llmScope])

  function handleLlmConfigChange(nextConfig: WizardLLMConfig) {
    setLlmDirty(true)
    setLlmConfig(nextConfig)
  }

  function updateMode(nextMode: CadenceMode) {
    if (cadenceType === "email_only" && nextMode === "semi_manual") {
      setError("Cadências só e-mail devem permanecer no modo automático.")
      return
    }

    setMode(nextMode)
    setSelectedPresetId("custom")
  }

  function applyPreset(preset: CadencePreset) {
    setSelectedPresetId(preset.id)
    setCadenceType(preset.cadenceType)
    setMode(preset.mode)
    setSteps(cloneSteps(preset.steps))
    setError(null)

    if (!description.trim() || description === selectedPreset?.description) {
      setDescription(preset.description)
    }

    if (preset.cadenceType === "email_only") {
      setLinkedInAccountId("")
    }
  }

  function resetStructure() {
    setSelectedPresetId("custom")
    setSteps([])
    setError(null)
  }

  function validateStep(stepIndex: number): string | null {
    if (stepIndex === 0 && !name.trim()) {
      return "Dê um nome para a cadência antes de avançar."
    }

    if (cadenceType === "email_only" && mode === "semi_manual") {
      return "Cadências só e-mail precisam usar modo automático."
    }

    if (stepIndex >= 2) {
      if (steps.length === 0) {
        return "Adicione pelo menos um passo ou escolha um preset antes de continuar."
      }
      if (cadenceType === "email_only" && steps.some((step) => step.channel !== "email")) {
        return "Cadências do tipo Só e-mail aceitam apenas passos com canal E-mail."
      }
    }

    return null
  }

  function handleStepJump(nextStep: number) {
    if (nextStep <= activeStep) {
      setActiveStep(nextStep)
      setError(null)
      return
    }

    for (let index = 0; index < nextStep; index += 1) {
      const validationError = validateStep(index)
      if (validationError) {
        setActiveStep(index)
        setError(validationError)
        return
      }
    }

    setActiveStep(nextStep)
    setError(null)
  }

  function handleNextStep() {
    const validationError = validateStep(activeStep)
    if (validationError) {
      setError(validationError)
      return
    }

    setError(null)
    setActiveStep((currentStep) => Math.min(currentStep + 1, WIZARD_STEPS.length - 1))
  }

  async function submitCadence() {
    const validationError = validateStep(WIZARD_STEPS.length - 1)
    if (validationError) {
      setError(validationError)
      return
    }

    if (!llmConfigReady) {
      setError(llmConfigError)
      return
    }

    const effectiveLlmConfig = llmDirty
      ? llmConfig
      : getTenantLLMConfig(tenant?.integration, llmScope)

    const body: CreateCadenceBody & { allow_personal_email?: boolean } = {
      name: name.trim(),
      ...(description.trim() ? { description: description.trim() } : {}),
      mode,
      cadence_type: cadenceType,
      llm: {
        provider: effectiveLlmConfig.llm_provider,
        model: effectiveLlmConfig.llm_model,
        temperature: effectiveLlmConfig.llm_temperature,
        max_tokens: effectiveLlmConfig.llm_max_tokens,
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
      allow_personal_email: usePersonalEmailFallback,
      steps_template: steps,
    }

    try {
      const created = await createCadence.mutateAsync(body)
      router.push(`/cadencias/${created.id}`)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Erro ao criar cadência.")
    }
  }

  async function handleFormSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (activeStep < WIZARD_STEPS.length - 1) {
      handleNextStep()
      return
    }

    await submitCadence()
  }

  return (
    <form onSubmit={(event) => void handleFormSubmit(event)} className="space-y-6">
      {error ? (
        <div
          role="alert"
          className="rounded-2xl border border-(--danger-subtle-fg) bg-(--danger-subtle) px-4 py-3 text-sm text-(--danger-subtle-fg)"
        >
          {error}
        </div>
      ) : null}

      <section className="relative overflow-hidden rounded-[28px] border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-sm)">
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-(--bg-overlay) opacity-80" />
        <div className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-(--accent-subtle) blur-3xl" />
        <div className="pointer-events-none absolute left-8 top-8 h-24 w-24 rounded-full bg-(--bg-overlay) blur-2xl" />
        <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl space-y-4">
            <Badge variant="info">Fluxo guiado</Badge>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-(--text-primary)">
                Monte uma cadência pronta para operar
              </h1>
              <p className="mt-3 text-sm leading-7 text-(--text-secondary)">
                Escolha um preset útil, valide contas e audiência, refine a IA e revise a operação
                antes de salvar. A ideia aqui é te tirar do formulário cru e te deixar perto de uma
                campanha usável.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {strategyHighlights.map((highlight) => (
                <span
                  key={highlight}
                  className="rounded-full border border-(--border-default) bg-(--bg-surface) px-3 py-1 text-xs font-medium text-(--text-secondary)"
                >
                  {highlight}
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:min-w-105">
            <HeroMetric label="Preset" value={selectedPreset?.title ?? "Custom"} />
            <HeroMetric label="Audiência" value={leadListId ? `${totalLeads} leads` : "Definir"} />
            <HeroMetric label="Canais" value={`${channelCounts.length || 0} ativos`} />
            <HeroMetric
              label="Prontidão"
              value={`${readinessItems.filter((item) => item.state === "ready").length}/${readinessItems.length}`}
            />
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {WIZARD_STEPS.map((step, index) => (
              <WizardStepButton
                key={step.id}
                step={step}
                index={index}
                active={index === activeStep}
                completed={index < activeStep}
                onClick={() => handleStepJump(index)}
              />
            ))}
          </div>

          {activeStep === 0 ? (
            <section className="space-y-6">
              <Card className="rounded-3xl">
                <CardHeader>
                  <CardTitle>Escolha um ponto de partida</CardTitle>
                  <CardDescription>
                    Os presets só aceleram a estrutura inicial. Você ainda pode editar os steps e o
                    copy com calma na próxima etapa.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 xl:grid-cols-2">
                    {CADENCE_PRESETS.map((preset) => (
                      <PresetCard
                        key={preset.id}
                        preset={preset}
                        selected={selectedPresetId === preset.id}
                        onSelect={() => applyPreset(preset)}
                      />
                    ))}
                  </div>

                  <div className="rounded-2xl border border-dashed border-(--border-default) bg-(--bg-surface) p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-(--text-primary)">
                          Quer partir do zero?
                        </p>
                        <p className="mt-1 text-sm text-(--text-secondary)">
                          Limpa a estrutura atual e deixa você montar os passos manualmente.
                        </p>
                      </div>
                      <Button type="button" variant="outline" onClick={resetStructure}>
                        Limpar estrutura
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-3xl">
                <CardHeader>
                  <CardTitle>Configuração base da operação</CardTitle>
                  <CardDescription>
                    Defina o nome da cadência, o tipo de jornada e como a equipe vai operar o fluxo.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="cadence-name">Nome da cadência</Label>
                        <Input
                          id="cadence-name"
                          value={name}
                          onChange={(event) => setName(event.target.value)}
                          placeholder="Ex: SaaS Mid-Market Q2"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="cadence-description">Objetivo comercial</Label>
                        <Textarea
                          id="cadence-description"
                          value={description}
                          onChange={(event) => setDescription(event.target.value)}
                          rows={4}
                          placeholder="Descreva o objetivo, a tese comercial e o que essa cadência deve provar."
                        />
                      </div>
                    </div>

                    <div className="space-y-4 rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm font-semibold text-(--text-primary)">
                          <ListChecks size={16} aria-hidden="true" />
                          Tipo da cadência
                        </div>
                        <div className="grid gap-2 sm:grid-cols-2">
                          <button
                            type="button"
                            onClick={() => updateCadenceType("mixed")}
                            className={cn(
                              "rounded-2xl border p-3 text-left transition-colors",
                              cadenceType === "mixed"
                                ? "border-(--accent) bg-(--bg-surface) text-(--text-primary)"
                                : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--border-subtle)",
                            )}
                          >
                            <p className="text-sm font-semibold">Multicanal</p>
                            <p className="mt-1 text-xs text-(--text-tertiary)">
                              LinkedIn + e-mail na mesma jornada
                            </p>
                          </button>
                          <button
                            type="button"
                            onClick={() => updateCadenceType("email_only")}
                            className={cn(
                              "rounded-2xl border p-3 text-left transition-colors",
                              cadenceType === "email_only"
                                ? "border-(--accent) bg-(--bg-surface) text-(--text-primary)"
                                : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--border-subtle)",
                            )}
                          >
                            <p className="text-sm font-semibold">Só e-mail</p>
                            <p className="mt-1 text-xs text-(--text-tertiary)">
                              Melhor para escala e A/B de assunto
                            </p>
                          </button>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm font-semibold text-(--text-primary)">
                          <ShieldCheck size={16} aria-hidden="true" />
                          Modo de operação
                        </div>
                        <div className="grid gap-2">
                          <button
                            type="button"
                            onClick={() => updateMode("automatic")}
                            className={cn(
                              "rounded-2xl border p-3 text-left transition-colors",
                              mode === "automatic"
                                ? "border-(--accent) bg-(--bg-surface) text-(--text-primary)"
                                : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--border-subtle)",
                            )}
                          >
                            <p className="text-sm font-semibold">Automático</p>
                            <p className="mt-1 text-xs text-(--text-tertiary)">
                              A cadência dispara os passos sem fila manual.
                            </p>
                          </button>
                          <button
                            type="button"
                            onClick={() => updateMode("semi_manual")}
                            disabled={cadenceType === "email_only"}
                            className={cn(
                              "rounded-2xl border p-3 text-left transition-colors disabled:opacity-50",
                              mode === "semi_manual"
                                ? "border-(--accent) bg-(--bg-surface) text-(--text-primary)"
                                : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--border-subtle)",
                            )}
                          >
                            <p className="text-sm font-semibold">Semi-manual</p>
                            <p className="mt-1 text-xs text-(--text-tertiary)">
                              Ideal para networking de ticket alto depois que a conexão é aceita.
                            </p>
                          </button>
                        </div>
                        {cadenceType === "email_only" ? (
                          <p className="text-xs text-(--warning)">
                            Cadências só e-mail permanecem automáticas para não entrar em um modo
                            sem gatilho operacional claro.
                          </p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </section>
          ) : null}

          {activeStep === 1 ? (
            <section className="space-y-6">
              <Card className="rounded-3xl">
                <CardHeader>
                  <CardTitle>Checklist de prontidão</CardTitle>
                  <CardDescription>
                    Antes de investir tempo no copy, vale validar se a operação tem contas, lista e
                    insumos mínimos para rodar com previsibilidade.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 xl:grid-cols-2">
                    {readinessItems.map((item) => (
                      <ReadinessCard key={item.title} item={item} />
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-3xl">
                <CardHeader>
                  <CardTitle>Audiência e contas da cadência</CardTitle>
                  <CardDescription>
                    Escolha a lista de leads e defina as contas preferenciais dessa cadência. Se
                    você não selecionar uma conta, o backend usa o fallback global do tenant.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid gap-5 lg:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="lead-list">Lista de leads</Label>
                      <select
                        id="lead-list"
                        aria-label="Lista de leads"
                        value={leadListId}
                        onChange={(event) => setLeadListId(event.target.value)}
                        className={SELECT_CLASSNAME}
                        disabled={isListsPending || !!leadListsError}
                      >
                        <option value="">Nenhuma lista vinculada</option>
                        {lists?.map((list) => (
                          <option key={list.id} value={list.id}>
                            {list.name} ({list.lead_count} leads)
                          </option>
                        ))}
                      </select>
                      {isListsPending ? (
                        <p className="text-xs text-(--text-tertiary)">
                          Carregando listas disponíveis no tenant atual...
                        </p>
                      ) : leadListsError ? (
                        <p className="text-xs text-(--danger)">
                          Não foi possível carregar as listas agora. Recarregue a página depois de
                          confirmar o backend.
                        </p>
                      ) : lists && lists.length === 0 ? (
                        <p className="text-xs text-(--text-tertiary)">
                          Não existe nenhuma lista no tenant atual. Você ainda pode salvar a
                          cadência e vincular leads depois.
                        </p>
                      ) : (
                        <p className="text-xs text-(--text-tertiary)">
                          Sem lista vinculada, você ainda consegue salvar a cadência, mas a
                          audiência só aparece depois que os leads forem inscritos manualmente.
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="email-account">Conta de e-mail preferencial</Label>
                      <select
                        id="email-account"
                        aria-label="Conta de e-mail preferencial"
                        value={emailAccountId}
                        onChange={(event) => setEmailAccountId(event.target.value)}
                        className={SELECT_CLASSNAME}
                      >
                        <option value="">Usar fallback global</option>
                        {activeEmailAccounts.map((account) => (
                          <option key={account.id} value={account.id}>
                            {account.display_name} ({account.email_address})
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-(--text-tertiary)">
                        Recomendado para qualquer jornada com e-mail, especialmente se você estiver
                        comparando warmup ou reputação entre contas.
                      </p>
                    </div>
                  </div>

                  {cadenceType === "mixed" ? (
                    <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-start">
                      <div className="space-y-2">
                        <Label htmlFor="linkedin-account">Conta LinkedIn preferencial</Label>
                        <select
                          id="linkedin-account"
                          aria-label="Conta LinkedIn preferencial"
                          value={linkedInAccountId}
                          onChange={(event) => setLinkedInAccountId(event.target.value)}
                          className={SELECT_CLASSNAME}
                        >
                          <option value="">Usar fallback global</option>
                          {activeLinkedInAccounts.map((account) => (
                            <option key={account.id} value={account.id}>
                              {account.display_name}
                              {account.linkedin_username ? ` (${account.linkedin_username})` : ""}
                              {account.supports_inmail ? " · InMail" : " · sem InMail"}
                            </option>
                          ))}
                        </select>
                        <p className="text-xs text-(--text-tertiary)">
                          Vale a pena quando você segmenta por persona comercial, perfil de SDR ou
                          quer separar limites de envio entre equipes.
                        </p>
                        {hasInmailSteps && selectedLinkedInAccount && !selectedLinkedInAccount.supports_inmail ? (
                          <p className="text-xs text-(--warning)">
                            A conta selecionada não está habilitada para InMail. Se a cadência usar
                            esse canal, o worker vai pular o step.
                          </p>
                        ) : null}
                      </div>

                      <div className="space-y-2 rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-4 lg:min-w-65">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-(--text-primary)">
                              Fallback de e-mail pessoal
                            </p>
                            <p className="mt-1 text-xs text-(--text-tertiary)">
                              Use quando o lead não tiver e-mail corporativo e esse caminho fizer
                              sentido para a sua operação.
                            </p>
                          </div>
                          <Switch
                            checked={usePersonalEmailFallback}
                            onCheckedChange={setUsePersonalEmailFallback}
                            aria-label="Permitir uso de e-mail pessoal"
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-(--text-primary)">
                            Fallback de e-mail pessoal
                          </p>
                          <p className="mt-1 text-xs text-(--text-tertiary)">
                            Ative se esta cadência puder usar e-mail pessoal quando o lead não tiver
                            e-mail corporativo.
                          </p>
                        </div>
                        <Switch
                          checked={usePersonalEmailFallback}
                          onCheckedChange={setUsePersonalEmailFallback}
                          aria-label="Permitir uso de e-mail pessoal"
                        />
                      </div>
                    </div>
                  )}

                  {selectedLeadList ? (
                    <div className="rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-4">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <p className="text-sm font-semibold text-(--text-primary)">
                            {selectedLeadList.name}
                          </p>
                          <p className="mt-1 text-sm text-(--text-secondary)">
                            {selectedLeadList.description || "Lista vinculada a esta cadência."}
                          </p>
                        </div>
                        <Badge variant="outline">{totalLeads} leads</Badge>
                      </div>

                      {leadListDetail?.leads?.length ? (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {leadListDetail.leads.slice(0, 5).map((lead) => (
                            <span
                              key={lead.id}
                              className="rounded-full border border-(--border-default) bg-(--bg-surface) px-3 py-1 text-xs text-(--text-secondary)"
                            >
                              {lead.name}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </section>
          ) : null}

          {activeStep === 2 ? (
            <section className="space-y-6">
              <Card className="rounded-3xl">
                <CardHeader>
                  <CardTitle>Contexto comercial que alimenta a IA</CardTitle>
                  <CardDescription>
                    Isso melhora muito a consistência do copy e evita prompts genéricos demais no
                    momento do disparo.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-5 lg:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="target-segment">Segmento-alvo</Label>
                    <Input
                      id="target-segment"
                      value={targetSegment}
                      onChange={(event) => setTargetSegment(event.target.value)}
                      placeholder="Ex: SaaS B2B, indústria farmacêutica, varejo premium"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="offer-description">Proposta de valor</Label>
                    <Textarea
                      id="offer-description"
                      value={offerDescription}
                      onChange={(event) => setOfferDescription(event.target.value)}
                      rows={4}
                      placeholder="Resuma o valor entregue e o problema que sua oferta resolve."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="persona-description">Persona ideal</Label>
                    <Textarea
                      id="persona-description"
                      value={personaDescription}
                      onChange={(event) => setPersonaDescription(event.target.value)}
                      rows={4}
                      placeholder="Cargo, dores, prioridades e sinais de timing do decisor."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="tone-instructions">Tom e restrições de linguagem</Label>
                    <Textarea
                      id="tone-instructions"
                      value={toneInstructions}
                      onChange={(event) => setToneInstructions(event.target.value)}
                      rows={4}
                      placeholder="Ex: executivo, direto, sem clichês de SDR e com CTA leve."
                    />
                  </div>
                </CardContent>
              </Card>

              <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <LLMConfigForm
                  value={llmConfig}
                  onChange={(cfg) =>
                    handleLlmConfigChange({
                      ...cfg,
                      llm_provider: cfg.llm_provider as WizardLLMConfig["llm_provider"],
                    })
                  }
                />
                <TTSConfigForm
                  value={ttsConfig}
                  onChange={setTtsConfig}
                  hasVoiceSteps={hasVoiceSteps}
                />
              </div>

              <Card className="rounded-3xl">
                <CardHeader>
                  <CardTitle>Steps da cadência</CardTitle>
                  <CardDescription>
                    Os presets já montam uma sequência inicial. Ajuste canais, delays, variantes de
                    assunto, templates e voice notes aqui.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">
                      {steps.length} passo{steps.length === 1 ? "" : "s"}
                    </Badge>
                    <Badge variant={cadenceType === "email_only" ? "info" : "default"}>
                      {cadenceType === "email_only"
                        ? "Canal único: e-mail"
                        : "Canais mistos liberados"}
                    </Badge>
                    {hasVoiceSteps ? (
                      <Badge variant="warning">Há voice notes na sequência</Badge>
                    ) : null}
                  </div>

                  {steps.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-(--border-default) bg-(--bg-overlay) p-4 text-sm text-(--text-secondary)">
                      Você zerou a estrutura. Adicione passos manualmente ou volte na etapa anterior
                      e escolha um preset para ganhar velocidade.
                    </div>
                  ) : null}

                  <CadenceSteps
                    value={steps}
                    onChange={setSteps}
                    ttsProvider={ttsConfig.tts_provider}
                    ttsVoiceId={ttsConfig.tts_voice_id}
                    ttsSpeed={ttsConfig.tts_speed}
                    ttsPitch={ttsConfig.tts_pitch}
                    leads={leadListDetail?.leads}
                    {...(allowedChannels ? { allowedChannels } : {})}
                  />
                </CardContent>
              </Card>
            </section>
          ) : null}

          {activeStep === 3 ? (
            <section className="space-y-6">
              <Card className="rounded-3xl">
                <CardHeader>
                  <CardTitle>Resumo operacional</CardTitle>
                  <CardDescription>
                    Última checagem antes de salvar. O objetivo aqui é confirmar que estratégia,
                    audiência e infraestrutura fazem sentido juntas.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
                  <div className="space-y-4">
                    <div className="rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">
                          {selectedPreset?.title ?? "Fluxo customizado"}
                        </Badge>
                        <Badge variant={cadenceType === "email_only" ? "info" : "default"}>
                          {cadenceType === "email_only" ? "Só e-mail" : "Multicanal"}
                        </Badge>
                        <Badge variant={mode === "semi_manual" ? "warning" : "outline"}>
                          {mode === "semi_manual" ? "Semi-manual" : "Automática"}
                        </Badge>
                      </div>
                      <h2 className="mt-4 text-lg font-semibold text-(--text-primary)">
                        {name || "Cadência sem nome ainda"}
                      </h2>
                      <p className="mt-2 text-sm leading-6 text-(--text-secondary)">
                        {description ||
                          "Sem descrição definida. Vale registrar a tese comercial antes de ativar."}
                      </p>
                    </div>

                    <div className="rounded-2xl border border-(--border-default) bg-(--bg-surface) p-4">
                      <p className="text-sm font-semibold text-(--text-primary)">
                        Sequência configurada
                      </p>
                      <div className="mt-4 space-y-3">
                        {steps.map((step, index) => (
                          <div
                            key={`${step.channel}-${index}-${step.day_offset}`}
                            className="rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-3"
                          >
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                              <div>
                                <p className="text-sm font-semibold text-(--text-primary)">
                                  Passo {index + 1}
                                </p>
                                <p className="mt-1 text-xs text-(--text-tertiary)">
                                  Dia {step.day_offset} · {channelLabel(step.channel)}
                                  {step.use_voice ? " · voz" : ""}
                                </p>
                              </div>
                              {step.subject_variants?.length ? (
                                <Badge variant="info">
                                  {step.subject_variants.length} assuntos
                                </Badge>
                              ) : null}
                            </div>
                            <p className="mt-3 text-sm leading-6 text-(--text-secondary)">
                              {step.message_template
                                ? step.message_template.slice(0, 180)
                                : "Sem texto manual. O conteúdo será composto a partir do contexto e das instruções do step."}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <Card className="rounded-2xl shadow-none">
                      <CardHeader>
                        <CardTitle>Resumo de recursos</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3 pt-0">
                        <SummaryRow
                          label="Lista"
                          value={
                            selectedLeadList
                              ? `${selectedLeadList.name} · ${totalLeads} leads`
                              : "Sem lista vinculada"
                          }
                        />
                        <SummaryRow
                          label="Conta de e-mail"
                          value={
                            selectedEmailAccount
                              ? selectedEmailAccount.display_name
                              : "Fallback global"
                          }
                        />
                        <SummaryRow
                          label="Conta LinkedIn"
                          value={
                            cadenceType === "email_only"
                              ? "Não se aplica"
                              : selectedLinkedInAccount
                                ? `${selectedLinkedInAccount.display_name}${selectedLinkedInAccount.supports_inmail ? " · InMail habilitado" : " · sem InMail"}`
                                : "Fallback global"
                          }
                        />
                        <SummaryRow
                          label="LLM"
                          value={`${llmConfig.llm_provider === "openai" ? "OpenAI" : "Gemini"} · ${llmConfig.llm_model}`}
                        />
                        <SummaryRow
                          label="TTS"
                          value={
                            hasVoiceSteps
                              ? ttsConfig.tts_provider || "Provider global"
                              : "Sem voice notes"
                          }
                        />
                        <SummaryRow
                          label="E-mail pessoal"
                          value={usePersonalEmailFallback ? "Permitido" : "Bloqueado"}
                        />
                      </CardContent>
                    </Card>

                    <Card className="rounded-2xl shadow-none">
                      <CardHeader>
                        <CardTitle>Atenções antes de salvar</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3 pt-0">
                        {reviewWarnings.length > 0 ? (
                          reviewWarnings.map((warning) => (
                            <div
                              key={warning}
                              className="rounded-2xl border border-(--warning-subtle-fg) bg-(--warning-subtle) px-3 py-3 text-sm text-(--warning-subtle-fg)"
                            >
                              <div className="flex items-start gap-2">
                                <AlertTriangle
                                  size={16}
                                  className="mt-0.5 shrink-0"
                                  aria-hidden="true"
                                />
                                <span>{warning}</span>
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="rounded-2xl border border-(--success-subtle-fg) bg-(--success-subtle) px-3 py-3 text-sm text-(--success-subtle-fg)">
                            A configuração principal está consistente para criar a cadência agora.
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            </section>
          ) : null}

          <div className="flex flex-col gap-3 rounded-2xl border border-(--border-default) bg-(--bg-surface) p-4 sm:flex-row sm:items-center sm:justify-between">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setActiveStep((currentStep) => Math.max(currentStep - 1, 0))}
              disabled={activeStep === 0}
            >
              <ChevronLeft size={16} aria-hidden="true" />
              Voltar
            </Button>

            <div className="flex flex-col-reverse gap-3 sm:flex-row">
              <Button type="button" variant="outline" onClick={() => router.push("/cadencias")}>
                Cancelar
              </Button>
              {activeStep < WIZARD_STEPS.length - 1 ? (
                <Button type="button" onClick={handleNextStep}>
                  Continuar
                  <ChevronRight size={16} aria-hidden="true" />
                </Button>
              ) : (
                <Button type="submit" disabled={createCadence.isPending || !llmConfigReady}>
                  {createCadence.isPending
                    ? "Criando cadência..."
                    : llmConfigReady
                      ? "Criar cadência"
                      : "Carregando IA..."}
                </Button>
              )}
            </div>
          </div>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Resumo vivo</CardTitle>
              <CardDescription>
                Essa coluna fica estável enquanto você avança, para evitar perder contexto da
                operação.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-(--text-tertiary)">
                  Estratégia
                </p>
                <p className="mt-2 text-base font-semibold text-(--text-primary)">
                  {selectedPreset?.title ?? "Fluxo customizado"}
                </p>
                <p className="mt-1 text-sm text-(--text-secondary)">
                  {selectedPreset?.headline ?? "Sequência manual montada do zero."}
                </p>
              </div>

              <div className="space-y-3">
                <SummaryRow
                  label="Tipo"
                  value={cadenceType === "email_only" ? "Só e-mail" : "Multicanal"}
                />
                <SummaryRow
                  label="Modo"
                  value={mode === "semi_manual" ? "Semi-manual" : "Automático"}
                />
                <SummaryRow label="Passos" value={`${steps.length}`} />
                <SummaryRow label="Lista" value={leadListId ? `${totalLeads} leads` : "Pendente"} />
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Distribuição por canal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {channelCounts.length > 0 ? (
                channelCounts.map((item) => (
                  <div
                    key={item.channel}
                    className="flex items-center justify-between rounded-2xl border border-(--border-default) bg-(--bg-overlay) px-3 py-2"
                  >
                    <span className="text-sm text-(--text-secondary)">
                      {channelLabel(item.channel)}
                    </span>
                    <Badge variant="outline">{item.count}</Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-(--text-tertiary)">Nenhum step configurado ainda.</p>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>Próximos checkpoints</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-(--text-secondary)">
              <div className="flex items-start gap-3 rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-3">
                <Bot
                  size={16}
                  className="mt-0.5 shrink-0 text-(--text-tertiary)"
                  aria-hidden="true"
                />
                <span>
                  Use a etapa de conteúdo para calibrar o contexto e evitar mensagens genéricas.
                </span>
              </div>
              <div className="flex items-start gap-3 rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-3">
                <ListChecks
                  size={16}
                  className="mt-0.5 shrink-0 text-(--text-tertiary)"
                  aria-hidden="true"
                />
                <span>
                  Se o sandbox for parte da rotina, vincule uma lista logo agora para ganhar preview
                  real.
                </span>
              </div>
              <div className="flex items-start gap-3 rounded-2xl border border-(--border-default) bg-(--bg-overlay) p-3">
                <FileText
                  size={16}
                  className="mt-0.5 shrink-0 text-(--text-tertiary)"
                  aria-hidden="true"
                />
                <span>
                  Templates ativos e variantes de assunto deixam a operação mais comparável depois
                  nos relatórios.
                </span>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </form>
  )
}

function HeroMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-(--border-default) bg-(--bg-surface) p-3">
      <p className="text-[11px] uppercase tracking-[0.16em] text-(--text-tertiary)">{label}</p>
      <p className="mt-2 line-clamp-2 text-sm font-semibold text-(--text-primary)">{value}</p>
    </div>
  )
}
