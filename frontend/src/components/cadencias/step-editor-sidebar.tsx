"use client"

import { useCallback, useDeferredValue, useEffect, useRef, useState } from "react"
import { motion } from "framer-motion"
import {
  X,
  Mail,
  Linkedin,
  Volume2,
  MousePointerClick,
  MessageSquare,
  ClipboardList,
  Play,
  Loader2,
  Music,
  Sparkles,
  Wand2,
} from "lucide-react"
import {
  useCadence,
  useCadenceTemplateVariables,
  useCadenceStepPreview,
  useComposeCadenceStep,
  useSendCadenceStepTestEmail,
  type CadenceChannel,
  type CadenceStep,
  type StepType,
} from "@/lib/api/hooks/use-cadences"
import type { AudioFile } from "@/lib/api/hooks/use-audio-files"
import { useEmailAccounts } from "@/lib/api/hooks/use-email-accounts"
import type { EmailTemplate } from "@/lib/api/hooks/use-email-templates"
import type { LeadListLeadItem } from "@/lib/api/hooks/use-lead-lists"
import { StepAudioRecorder } from "@/components/cadencias/step-audio-recorder"
import { SendTestEmailDialog } from "@/components/cadencias/send-test-email-dialog"
import { useTestTTS } from "@/lib/api/hooks/use-tts"
import {
  buildTestEmailSuccessMessage,
  buildTestEmailTransportSummary,
} from "@/lib/cadences/test-email-transport"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

// ─── Tipos ────────────────────────────────────────────────────────────

interface StepEditorSidebarProps {
  cadenceId: string
  step: CadenceStep
  index: number
  onUpdate: (field: keyof CadenceStep, value: unknown) => void
  onClose: () => void
  ttsProvider?: string | null
  ttsVoiceId?: string | null
  ttsSpeed?: number
  ttsPitch?: number
  leads?: LeadListLeadItem[]
  emailTemplates: EmailTemplate[]
  audioFiles: AudioFile[]
}

// ─── Constantes visuais ───────────────────────────────────────────────

const CHANNEL_OPTIONS: {
  value: CadenceChannel
  label: string
  icon: React.ReactNode
  colorClass: string
}[] = [
  {
    value: "linkedin_connect",
    label: "Connect",
    icon: <Linkedin size={14} />,
    colorClass: "border-blue-200 bg-blue-50 text-blue-700 hover:border-blue-400",
  },
  {
    value: "linkedin_dm",
    label: "DM",
    icon: <MessageSquare size={14} />,
    colorClass: "border-blue-200 bg-blue-50 text-blue-700 hover:border-blue-400",
  },
  {
    value: "linkedin_inmail",
    label: "InMail",
    icon: <Linkedin size={14} />,
    colorClass: "border-blue-200 bg-blue-50 text-blue-700 hover:border-blue-400",
  },
  {
    value: "linkedin_post_reaction",
    label: "Reação",
    icon: <MousePointerClick size={14} />,
    colorClass: "border-blue-200 bg-blue-50 text-blue-700 hover:border-blue-400",
  },
  {
    value: "linkedin_post_comment",
    label: "Comentário",
    icon: <MessageSquare size={14} />,
    colorClass: "border-blue-200 bg-blue-50 text-blue-700 hover:border-blue-400",
  },
  {
    value: "email",
    label: "E-mail",
    icon: <Mail size={14} />,
    colorClass: "border-green-200 bg-green-50 text-green-700 hover:border-green-400",
  },
  {
    value: "manual_task",
    label: "Manual",
    icon: <ClipboardList size={14} />,
    colorClass: "border-amber-200 bg-amber-50 text-amber-700 hover:border-amber-400",
  },
]

const STEP_TYPE_OPTIONS: Record<string, { value: StepType; label: string }[]> = {
  linkedin_connect: [{ value: "linkedin_connect", label: "Convite de Conexão" }],
  linkedin_dm: [
    { value: "linkedin_dm_first", label: "Primeira abordagem" },
    { value: "linkedin_dm_post_connect", label: "Pós-conexão (agradecimento)" },
    { value: "linkedin_dm_post_connect_voice", label: "Pós-conexão com áudio" },
    { value: "linkedin_dm_voice", label: "DM com áudio" },
    { value: "linkedin_dm_followup", label: "Follow-up" },
    { value: "linkedin_dm_breakup", label: "Despedida / Breakup" },
  ],
  linkedin_post_reaction: [{ value: "linkedin_post_reaction", label: "Curtir post recente" }],
  linkedin_post_comment: [{ value: "linkedin_post_comment", label: "Comentar post recente" }],
  linkedin_inmail: [{ value: "linkedin_inmail", label: "InMail (Premium)" }],
  email: [
    { value: "email_first", label: "Primeiro e-mail (cold mail)" },
    { value: "email_followup", label: "Follow-up" },
    { value: "email_breakup", label: "Despedida / Breakup" },
  ],
}

const TEMPLATE_VARIABLES = [
  { token: "{lead_name}", label: "Nome completo" },
  { token: "{name}", label: "Nome completo" },
  { token: "{first_name}", label: "Primeiro nome" },
  { token: "{last_name}", label: "Sobrenome" },
  { token: "{company}", label: "Empresa" },
  { token: "{job_title}", label: "Cargo" },
  { token: "{industry}", label: "Setor" },
  { token: "{city}", label: "Cidade" },
  { token: "{location}", label: "Localização" },
  { token: "{segment}", label: "Segmento" },
  { token: "{company_domain}", label: "Domínio" },
  { token: "{website}", label: "Website" },
  { token: "{email}", label: "Email" },
] as const

const MANUAL_TASK_OPTIONS = [
  { value: "call", label: "Ligação" },
  { value: "linkedin_post_comment", label: "Comentário em post" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "other", label: "Outro" },
] as const

type ComposerCopy = {
  sectionTitle: string
  fieldLabel: string
  fieldHint: string
  placeholder: string
  generateLabel: string
  improveLabel: string
  progressLabel: string
  previewBodyLabel: string
  advisory?: string
}

function findUnknownTokens(template: string, validTokens: Set<string>): string[] {
  const matches = template.match(/\{[a-z_]+\}/gi) ?? []
  return [...new Set(matches.filter((token) => !validTokens.has(token)))]
}

function labelForManualTaskType(value: string | null | undefined): string | null {
  const match = MANUAL_TASK_OPTIONS.find((item) => item.value === value)
  return match?.label ?? value ?? null
}

function serializeSubjectVariants(variants?: string[] | null): string {
  return (variants ?? []).join("\n")
}

function parseSubjectVariants(value: string): string[] | null {
  const items = value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean)
  return items.length > 0 ? items : null
}

function getComposerCopy(channel: CadenceChannel, hasEmailTemplate: boolean): ComposerCopy {
  if (channel === "linkedin_post_comment") {
    return {
      sectionTitle: "Comentário do post",
      fieldLabel: "Rascunho do comentário",
      fieldHint:
        "Use um comentário curto, contextual e sem pitch direto. O ideal é soar como interação natural com o post.",
      placeholder:
        "Excelente ponto sobre distribuição. Curti especialmente a parte de priorizar clareza antes de escalar.",
      generateLabel: "Gerar comentário",
      improveLabel: "Lapidar comentário",
      progressLabel: "Gerando comentário com IA…",
      previewBodyLabel: "Comentário",
      advisory:
        "A prévia abaixo reflete o comentário já renderizado para o lead escolhido. Mantenha 1 a 2 frases e evite CTA agressivo.",
    }
  }

  if (channel === "linkedin_inmail") {
    return {
      sectionTitle: "InMail",
      fieldLabel: "Rascunho do InMail",
      fieldHint:
        "A IA gera assunto e corpo. Se você escrever manualmente, mantenha a abertura curta e uma única proposta de valor.",
      placeholder:
        "Assunto: Ideia rápida para a equipe da {company}\n\nOlá {first_name}, vi seu contexto na {company} e pensei em uma abordagem simples para...",
      generateLabel: "Gerar InMail",
      improveLabel: "Lapidar InMail",
      progressLabel: "Gerando InMail com IA…",
      previewBodyLabel: "Corpo do InMail",
      advisory:
        "Para InMail, o preview mostra assunto e corpo separados quando a IA devolve a estrutura completa do canal.",
    }
  }

  if (channel === "email") {
    return {
      sectionTitle: "Mensagem",
      fieldLabel: hasEmailTemplate ? "Corpo manual (fallback)" : "Template da mensagem",
      fieldHint: hasEmailTemplate
        ? "Usado se o template salvo for removido"
        : "Se preencher, o backend usa este corpo e pula a geração por IA",
      placeholder: "Olá {first_name}, vi que você trabalha na {company}…",
      generateLabel: "Gerar com IA",
      improveLabel: "Melhorar texto",
      progressLabel: "Gerando assunto e corpo com IA…",
      previewBodyLabel: "Corpo",
    }
  }

  return {
    sectionTitle: "Mensagem",
    fieldLabel: "Template da mensagem",
    fieldHint: "Se preencher, substitui a geração por IA",
    placeholder: "Olá {first_name}, vi que você trabalha na {company}…",
    generateLabel: "Gerar com IA",
    improveLabel: "Melhorar texto",
    progressLabel: "Gerando texto com IA…",
    previewBodyLabel: "Corpo",
  }
}

// ─── Componentes de suporte ───────────────────────────────────────────

function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold text-[--text-tertiary]">{title}</p>
      {children}
    </div>
  )
}

function SidebarField({
  label,
  hint,
  action,
  children,
}: {
  label: string
  hint?: string
  action?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <label className="block text-xs font-medium text-[--text-secondary]">{label}</label>
        {action}
      </div>
      {children}
      {hint && <p className="text-[11px] leading-relaxed text-[--text-tertiary]">{hint}</p>}
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────

export function StepEditorSidebar({
  cadenceId,
  step,
  index,
  onUpdate,
  onClose,
  ttsProvider,
  ttsVoiceId,
  ttsSpeed,
  ttsPitch,
  leads,
  emailTemplates,
  audioFiles,
}: StepEditorSidebarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [recentUploadedAudio, setRecentUploadedAudio] = useState<AudioFile | null>(null)
  const [selectedPreviewLeadId, setSelectedPreviewLeadId] = useState<string>("")
  const [testEmailOpen, setTestEmailOpen] = useState(false)
  const testTTS = useTestTTS()
  const cadenceQuery = useCadence(cadenceId)
  const composeStep = useComposeCadenceStep()
  const emailAccountsQuery = useEmailAccounts()
  const sendTestEmail = useSendCadenceStepTestEmail()
  const templateVariablesQuery = useCadenceTemplateVariables()

  const stepTypeOptions = STEP_TYPE_OPTIONS[step.channel] ?? []
  const templateVariables =
    templateVariablesQuery.data && templateVariablesQuery.data.length > 0
      ? templateVariablesQuery.data
      : TEMPLATE_VARIABLES
  const validTemplateTokens = new Set(templateVariables.map((item) => item.token))
  const unknownTokens = step.message_template
    ? findUnknownTokens(step.message_template, validTemplateTokens)
    : []
  const isComposableChannel =
    step.channel !== "manual_task" && step.channel !== "linkedin_post_reaction"
  const previewLead = leads?.find((lead) => lead.id === selectedPreviewLeadId) ?? leads?.[0] ?? null
  const deferredPreviewLeadId = useDeferredValue(selectedPreviewLeadId || previewLead?.id || "")
  const deferredMessageTemplate = useDeferredValue(step.message_template)
  const deferredPreviewSubject = useDeferredValue(step.subject_variants?.[0] ?? null)
  const deferredEmailTemplateId = useDeferredValue(step.email_template_id ?? null)

  useEffect(() => {
    if (!leads || leads.length === 0) {
      if (selectedPreviewLeadId) {
        setSelectedPreviewLeadId("")
      }
      return
    }

    const stillExists = leads.some((lead) => lead.id === selectedPreviewLeadId)
    if (!selectedPreviewLeadId || !stillExists) {
      setSelectedPreviewLeadId(leads[0]?.id ?? "")
    }
  }, [leads, selectedPreviewLeadId])

  const previewQuery = useCadenceStepPreview({
    cadenceId,
    stepIndex: index,
    channel: step.channel,
    leadId: deferredPreviewLeadId || null,
    currentText: deferredMessageTemplate,
    currentSubject: deferredPreviewSubject,
    currentEmailTemplateId: deferredEmailTemplateId,
  })

  const selectedEmailTemplate =
    step.channel === "email"
      ? (emailTemplates.find((t) => t.id === step.email_template_id) ?? null)
      : null
  const composerCopy = getComposerCopy(step.channel, Boolean(selectedEmailTemplate))
  const testEmailTransport = buildTestEmailTransportSummary({
    cadence: cadenceQuery.data,
    emailAccounts: emailAccountsQuery.data?.accounts,
    isCadenceLoading: cadenceQuery.isLoading,
    isEmailAccountsLoading: emailAccountsQuery.isLoading,
  })
  const availableAudioFiles = recentUploadedAudio
    ? [
        recentUploadedAudio,
        ...audioFiles.filter((audioFile) => audioFile.id !== recentUploadedAudio.id),
      ]
    : audioFiles
  const defaultRecordedAudioName = `Passo ${index + 1} - LinkedIn DM`

  function handleChannelChange(ch: CadenceChannel) {
    onUpdate("channel", ch)
    // reset campos dependentes do canal
    if (ch !== "linkedin_dm") {
      onUpdate("use_voice", false)
      onUpdate("audio_file_id", null)
    }
    if (ch !== "email") {
      onUpdate("email_template_id", null)
      onUpdate("subject_variants", null)
    }
    onUpdate("step_type", null)
  }

  function insertVariable(token: string) {
    const ta = textareaRef.current
    const current = step.message_template ?? ""
    if (ta) {
      const start = ta.selectionStart
      const end = ta.selectionEnd
      onUpdate("message_template", current.slice(0, start) + token + current.slice(end))
      requestAnimationFrame(() => {
        ta.focus()
        const pos = start + token.length
        ta.setSelectionRange(pos, pos)
      })
    } else {
      onUpdate("message_template", current + token)
    }
  }

  const handleCompose = useCallback(
    async (action: "generate" | "improve") => {
      const result = await composeStep.mutateAsync({
        cadenceId,
        stepIndex: index,
        action,
        currentText: step.message_template,
        currentSubject: step.subject_variants?.[0] ?? null,
      })

      onUpdate("message_template", result.message_template)
      if (step.channel === "email") {
        onUpdate("email_template_id", null)
        onUpdate("subject_variants", result.subject ? [result.subject] : null)
      }
    },
    [
      cadenceId,
      composeStep,
      index,
      onUpdate,
      step.channel,
      step.message_template,
      step.subject_variants,
    ],
  )

  const handlePreviewTTS = useCallback(async () => {
    if (!ttsProvider || !ttsVoiceId) return
    const previewText = previewQuery.data?.body || step.message_template
    if (!previewText) return
    setIsPreviewing(true)
    try {
      const blob = await testTTS.mutateAsync({
        provider: ttsProvider,
        voice_id: ttsVoiceId,
        text: previewText,
        speed: ttsSpeed ?? 1.0,
        pitch: ttsPitch ?? 0.0,
      })
      const url = URL.createObjectURL(blob)
      if (!audioRef.current) audioRef.current = new Audio()
      audioRef.current.src = url
      await audioRef.current.play()
    } catch {
      // silent
    } finally {
      setIsPreviewing(false)
    }
  }, [
    previewQuery.data?.body,
    step.message_template,
    ttsProvider,
    ttsVoiceId,
    ttsSpeed,
    ttsPitch,
    testTTS,
  ])

  const handleRecordedAudioUploaded = useCallback(
    (audioFile: AudioFile) => {
      setRecentUploadedAudio(audioFile)
      onUpdate("use_voice", true)
      onUpdate("audio_file_id", audioFile.id)
    },
    [onUpdate],
  )

  const handleSendTestEmail = useCallback(
    (toEmail: string) => {
      sendTestEmail.mutate(
        {
          cadenceId,
          stepIndex: index,
          to_email: toEmail,
          leadId: selectedPreviewLeadId || previewLead?.id || null,
          currentText: step.message_template,
          currentSubject: step.subject_variants?.[0] ?? null,
          currentEmailTemplateId: step.email_template_id ?? null,
        },
        {
          onSuccess: (result) => {
            setTestEmailOpen(false)
            toast.success(
              buildTestEmailSuccessMessage({
                toEmail: result.to_email,
                summary: testEmailTransport,
                providerType: result.provider_type,
              }),
            )
          },
          onError: (error) => {
            toast.error(error instanceof Error ? error.message : "Falha ao enviar teste")
          },
        },
      )
    },
    [
      cadenceId,
      index,
      previewLead?.id,
      selectedPreviewLeadId,
      sendTestEmail,
      step.email_template_id,
      step.message_template,
      step.subject_variants,
      testEmailTransport,
    ],
  )

  return (
    <motion.aside
      initial={{ x: 380, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 380, opacity: 0 }}
      transition={{ type: "spring", stiffness: 400, damping: 35 }}
      className="flex h-full w-90 shrink-0 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg"
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-100 px-4 py-3">
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold",
            CHANNEL_OPTIONS.find((c) => c.value === step.channel)?.colorClass.includes("blue")
              ? "bg-blue-100 text-blue-700"
              : CHANNEL_OPTIONS.find((c) => c.value === step.channel)?.colorClass.includes("green")
                ? "bg-green-100 text-green-700"
                : "bg-amber-100 text-amber-700",
          )}
        >
          {index + 1}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-[--text-primary]">Passo {index + 1}</p>
          <p className="truncate text-[11px] text-[--text-tertiary]">
            {CHANNEL_OPTIONS.find((c) => c.value === step.channel)?.label ?? step.channel}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-[--text-tertiary] transition-colors hover:bg-gray-100 hover:text-[--text-primary]"
          aria-label="Fechar editor"
        >
          <X size={16} />
        </button>
      </div>

      {/* Conteúdo scrollável */}
      <div className="flex-1 divide-y divide-[--border-subtle] overflow-y-auto">
        {/* ── Seção: Canal + Delay ── */}
        <div className="space-y-4 px-4 py-4">
          <SidebarSection title="Canal">
            <div className="grid grid-cols-3 gap-1.5">
              {CHANNEL_OPTIONS.map(({ value, label, icon }) => {
                const isActive = step.channel === value
                const isLinkedin = value.startsWith("linkedin")
                const isEmail = value === "email"
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => handleChannelChange(value)}
                    className={cn(
                      "flex flex-col items-center gap-1 rounded-lg border px-2 py-2.5 text-[11px] font-medium transition-all",
                      isActive
                        ? isLinkedin
                          ? "border-blue-300 bg-blue-50 text-blue-700 shadow-sm"
                          : isEmail
                            ? "border-green-300 bg-green-50 text-green-700 shadow-sm"
                            : "border-amber-300 bg-amber-50 text-amber-700 shadow-sm"
                        : "border-gray-200 bg-white text-gray-500 hover:border-gray-300 hover:bg-gray-50",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-md",
                        isActive
                          ? isLinkedin
                            ? "bg-blue-100"
                            : isEmail
                              ? "bg-green-100"
                              : "bg-amber-100"
                          : "bg-gray-100",
                      )}
                    >
                      {icon}
                    </span>
                    {label}
                  </button>
                )
              })}
            </div>
          </SidebarSection>

          <SidebarField
            label="Dias de espera"
            hint="Número de dias após o passo anterior (0 = envio imediato)"
          >
            <input
              type="number"
              min={0}
              max={90}
              value={step.day_offset}
              onChange={(e) => onUpdate("day_offset", Number(e.target.value))}
              aria-label="Dias de espera antes deste passo"
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </SidebarField>

          {/* Tipo do passo */}
          {stepTypeOptions.length > 1 && (
            <SidebarField
              label="Tipo do passo"
              hint="Define qual instrução a IA usa para gerar o conteúdo"
            >
              <select
                value={step.step_type ?? ""}
                onChange={(e) => onUpdate("step_type", e.target.value || null)}
                aria-label="Tipo do passo"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Automático (inferir pela posição)</option>
                {stepTypeOptions.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </SidebarField>
          )}
        </div>

        {/* ── Seção: E-mail ── */}
        {step.channel === "email" && (
          <div className="space-y-4 px-4 py-4">
            <SidebarSection title="E-mail">
              <SidebarField
                label="Template salvo"
                hint="Se selecionado, usa o assunto e corpo do template com personalização por lead"
              >
                <select
                  value={step.email_template_id ?? ""}
                  onChange={(e) => onUpdate("email_template_id", e.target.value || null)}
                  aria-label="Template salvo de e-mail"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                >
                  <option value="">Nenhum — gerar com IA ou corpo manual</option>
                  {emailTemplates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
                {emailTemplates.length === 0 && (
                  <p className="text-[11px] text-amber-600">
                    Nenhum template ativo. Crie na área de cold email.
                  </p>
                )}
                {selectedEmailTemplate && (
                  <div className="mt-1.5 rounded-lg border border-green-100 bg-green-50 p-2.5 text-[11px]">
                    <p className="font-semibold text-green-800">
                      Assunto: {selectedEmailTemplate.subject}
                    </p>
                    {selectedEmailTemplate.description && (
                      <p className="mt-1 text-green-700">{selectedEmailTemplate.description}</p>
                    )}
                  </div>
                )}
              </SidebarField>

              <SidebarField
                label="Variações de assunto"
                hint="Uma linha por variação. Têm prioridade sobre o assunto gerado pela IA."
              >
                <textarea
                  value={serializeSubjectVariants(step.subject_variants)}
                  onChange={(e) =>
                    onUpdate("subject_variants", parseSubjectVariants(e.target.value))
                  }
                  rows={3}
                  placeholder={"Vi uma oportunidade na {company}\nIdeia rápida para {first_name}"}
                  className="w-full resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] placeholder:text-gray-400 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </SidebarField>

              {composeStep.isPending && step.channel === "email" && (
                <p className="text-[11px] text-blue-600">{composerCopy.progressLabel}</p>
              )}
            </SidebarSection>
          </div>
        )}

        {step.channel === "manual_task" && (
          <div className="space-y-4 px-4 py-4">
            <SidebarSection title="Tarefa manual">
              <SidebarField
                label="Tipo da tarefa"
                hint="Esse tipo aparece no canvas e no histórico do lead após a execução"
              >
                <select
                  value={step.manual_task_type ?? ""}
                  onChange={(e) => onUpdate("manual_task_type", e.target.value || null)}
                  aria-label="Tipo da tarefa manual"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                >
                  <option value="">Selecione um tipo</option>
                  {MANUAL_TASK_OPTIONS.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </SidebarField>

              <SidebarField
                label="Detalhamento"
                hint="Instruções operacionais para quem vai executar esse passo"
              >
                <textarea
                  value={step.manual_task_detail ?? ""}
                  onChange={(e) => onUpdate("manual_task_detail", e.target.value || null)}
                  rows={4}
                  placeholder="Ex.: ligar entre 10h e 12h, citar o último post do lead e convidar para conversar."
                  className="w-full resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] placeholder:text-gray-400 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </SidebarField>

              {(step.manual_task_type || step.manual_task_detail) && (
                <div className="rounded-lg border border-amber-100 bg-amber-50 p-3 text-[11px] text-amber-800">
                  <p className="font-semibold">
                    {labelForManualTaskType(step.manual_task_type) ?? "Tarefa manual"}
                  </p>
                  {step.manual_task_detail && (
                    <p className="mt-1 whitespace-pre-wrap text-amber-700">
                      {step.manual_task_detail}
                    </p>
                  )}
                </div>
              )}
            </SidebarSection>
          </div>
        )}

        {/* ── Seção: Mensagem ── */}
        {step.channel === "linkedin_post_reaction" && (
          <div className="space-y-4 px-4 py-4">
            <SidebarSection title="Reação em post">
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-[11px] text-blue-800">
                <p className="font-semibold">Este passo não gera texto.</p>
                <p className="mt-1 text-blue-700">
                  O dispatch só registra a reação no post recente do lead. Use comentário ou InMail
                  quando precisar de copy editorial neste ponto da cadência.
                </p>
              </div>
            </SidebarSection>
          </div>
        )}

        {step.channel !== "manual_task" && step.channel !== "linkedin_post_reaction" && (
          <div className="space-y-4 px-4 py-4">
            <SidebarSection title={composerCopy.sectionTitle}>
              {composerCopy.advisory && (
                <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-[11px] text-blue-800">
                  {composerCopy.advisory}
                </div>
              )}

              <SidebarField
                label={composerCopy.fieldLabel}
                hint={composerCopy.fieldHint}
                action={
                  isComposableChannel ? (
                    <button
                      type="button"
                      onClick={() =>
                        void handleCompose(step.message_template.trim() ? "improve" : "generate")
                      }
                      disabled={composeStep.isPending}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-600 transition-colors hover:text-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {composeStep.isPending ? (
                        <Loader2 size={11} className="animate-spin" />
                      ) : step.message_template.trim() ? (
                        <Wand2 size={11} />
                      ) : (
                        <Sparkles size={11} />
                      )}
                      {step.message_template.trim()
                        ? composerCopy.improveLabel
                        : composerCopy.generateLabel}
                    </button>
                  ) : undefined
                }
              >
                <textarea
                  ref={textareaRef}
                  value={step.message_template}
                  onChange={(e) => onUpdate("message_template", e.target.value)}
                  rows={5}
                  placeholder={composerCopy.placeholder}
                  className="w-full resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] placeholder:text-gray-400 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </SidebarField>

              {step.channel === "email" && selectedEmailTemplate && (
                <p className="text-[11px] text-amber-600">
                  Gerar com IA remove o template salvo deste passo e passa a usar o texto manual
                  gerado.
                </p>
              )}

              {composeStep.error instanceof Error && (
                <p className="text-[11px] text-rose-600">{composeStep.error.message}</p>
              )}

              {/* Pills de variáveis */}
              <div className="flex flex-wrap gap-1">
                {templateVariables.map(({ token, label }) => (
                  <button
                    key={token}
                    type="button"
                    onClick={() => insertVariable(token)}
                    className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-[11px] font-medium text-gray-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                  >
                    {label}
                  </button>
                ))}
              </div>

              {unknownTokens.length > 0 && (
                <div className="rounded-lg border border-rose-100 bg-rose-50 p-3 text-[11px] text-rose-700">
                  <p className="font-semibold">Variáveis não reconhecidas</p>
                  <p className="mt-1">{unknownTokens.join(", ")}</p>
                </div>
              )}

              <SidebarField
                label="Lead da prévia"
                hint="A prévia agora é renderizada pelo backend com o mesmo motor usado no envio"
              >
                <select
                  value={selectedPreviewLeadId}
                  onChange={(e) => setSelectedPreviewLeadId(e.target.value)}
                  aria-label="Lead usado na prévia do passo"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                >
                  {leads && leads.length > 0 ? (
                    leads.map((lead) => (
                      <option key={lead.id} value={lead.id}>
                        {lead.name} {lead.company ? `· ${lead.company}` : ""}
                      </option>
                    ))
                  ) : (
                    <option value="">Lead de exemplo do sistema</option>
                  )}
                </select>
              </SidebarField>

              {previewQuery.isPending && (
                <p className="text-[11px] text-blue-600">Renderizando prévia real…</p>
              )}

              {previewQuery.error instanceof Error && (
                <p className="text-[11px] text-rose-600">{previewQuery.error.message}</p>
              )}

              {previewQuery.data && (previewQuery.data.body || previewQuery.data.subject) && (
                <div className="overflow-hidden rounded-lg border border-blue-100 bg-blue-50 text-[11px]">
                  {/* Cabeçalho da prévia */}
                  <div className="border-b border-blue-100 bg-blue-100/60 px-3 py-2">
                    <p className="font-semibold text-blue-800">
                      Prévia real com {previewQuery.data.lead_name ?? "lead de exemplo"}
                    </p>
                  </div>

                  <div className="space-y-2 p-3">
                    {previewQuery.data.subject && (
                      <div className="rounded-md border border-blue-200 bg-white/80 px-2.5 py-2 text-blue-900">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-blue-400">
                          Assunto
                        </p>
                        <p className="mt-1 whitespace-pre-wrap font-medium">
                          {previewQuery.data.subject}
                        </p>
                      </div>
                    )}

                    <div className="rounded-md border border-blue-200 bg-white/80 px-2.5 py-2 text-blue-800">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-blue-400">
                        {composerCopy.previewBodyLabel}
                      </p>
                      {previewQuery.data.body_is_html ? (
                        <div
                          className="prose prose-sm mt-1 max-w-none text-blue-800"
                          dangerouslySetInnerHTML={{ __html: previewQuery.data.body }}
                        />
                      ) : (
                        <p className="mt-1 whitespace-pre-wrap text-blue-700">
                          {previewQuery.data.body}
                        </p>
                      )}
                    </div>

                    {step.channel === "email" && (
                      <div className="space-y-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setTestEmailOpen(true)}
                          disabled={sendTestEmail.isPending}
                          className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-medium text-blue-700 transition-colors hover:border-blue-300 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {sendTestEmail.isPending ? (
                            <Loader2 size={13} className="animate-spin" />
                          ) : (
                            <Mail size={13} />
                          )}
                          Enviar teste por e-mail
                        </button>
                        <div className="rounded-md border border-blue-200 bg-white/80 px-2.5 py-2 text-[11px]">
                          <p className="font-medium text-blue-800">
                            Conta: {testEmailTransport.shortLabel}
                          </p>
                          <p className="mt-0.5 text-blue-600">{testEmailTransport.hint}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </SidebarSection>
          </div>
        )}

        {/* ── Seção: Voz (só LinkedIn DM) ── */}
        {step.channel === "linkedin_dm" && (
          <div className="space-y-4 px-4 py-4">
            <SidebarSection title="Mensagem de Voz">
              <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 transition-colors hover:border-blue-300 hover:bg-blue-50">
                <input
                  type="checkbox"
                  checked={step.use_voice}
                  onChange={(e) => onUpdate("use_voice", e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 accent-blue-600"
                />
                <Volume2 size={14} className="text-blue-600" />
                <span className="text-sm font-medium text-gray-700">
                  Enviar como mensagem de voz
                </span>
              </label>

              {step.use_voice && (
                <div className="space-y-3 pl-1">
                  <SidebarField label="Fonte do áudio">
                    <select
                      value={step.audio_file_id ?? ""}
                      onChange={(e) => onUpdate("audio_file_id", e.target.value || null)}
                      aria-label="Fonte do áudio para mensagem de voz"
                      className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    >
                      <option value="">
                        🎙️ Gerar via TTS{ttsProvider ? ` (${ttsProvider})` : ""}
                      </option>
                      {availableAudioFiles.map((af) => (
                        <option key={af.id} value={af.id}>
                          🎵 {af.name} {af.language ? `(${af.language})` : ""}
                        </option>
                      ))}
                    </select>
                  </SidebarField>

                  {step.audio_file_id ? (
                    <div className="space-y-3">
                      <p className="flex items-center gap-1.5 text-[11px] text-gray-500">
                        <Music size={11} />
                        Áudio pré-gravado — o template de texto será ignorado para voz
                      </p>

                      <StepAudioRecorder
                        defaultName={defaultRecordedAudioName}
                        onUploaded={handleRecordedAudioUploaded}
                      />
                    </div>
                  ) : (
                    <>
                      <p className="text-[11px] text-gray-500">
                        O texto do template será convertido em áudio via TTS
                      </p>
                      {ttsProvider && ttsVoiceId && (
                        <button
                          type="button"
                          onClick={handlePreviewTTS}
                          disabled={isPreviewing || !step.message_template}
                          className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 transition-colors hover:border-blue-300 hover:text-blue-700 disabled:opacity-50"
                        >
                          {isPreviewing ? (
                            <>
                              <Loader2 size={13} className="animate-spin" />
                              Gerando prévia…
                            </>
                          ) : (
                            <>
                              <Play size={13} />
                              Testar TTS
                              {(previewQuery.data?.lead_name || previewLead?.name) && (
                                <span className="text-gray-400">
                                  (com {previewQuery.data?.lead_name ?? previewLead?.name ?? "lead"}
                                  )
                                </span>
                              )}
                            </>
                          )}
                        </button>
                      )}

                      <StepAudioRecorder
                        defaultName={defaultRecordedAudioName}
                        onUploaded={handleRecordedAudioUploaded}
                      />
                    </>
                  )}
                </div>
              )}
            </SidebarSection>
          </div>
        )}
      </div>

      <SendTestEmailDialog
        open={testEmailOpen}
        onOpenChange={setTestEmailOpen}
        onSubmit={handleSendTestEmail}
        isPending={sendTestEmail.isPending}
        contextLabel={`Passo ${index + 1}${previewQuery.data?.lead_name ? ` · ${previewQuery.data.lead_name}` : ""}`}
        subjectPreview={previewQuery.data?.subject ?? null}
        suggestedEmails={previewLead?.email_corporate ? [previewLead.email_corporate] : []}
        transportLabel={testEmailTransport.label}
        transportHint={testEmailTransport.hint}
      />
    </motion.aside>
  )
}
