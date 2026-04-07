"use client"

import { useCallback, useRef, useState } from "react"
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
} from "lucide-react"
import type { CadenceChannel, CadenceStep, StepType } from "@/lib/api/hooks/use-cadences"
import type { AudioFile } from "@/lib/api/hooks/use-audio-files"
import type { EmailTemplate } from "@/lib/api/hooks/use-email-templates"
import type { LeadListLeadItem } from "@/lib/api/hooks/use-lead-lists"
import { StepAudioRecorder } from "@/components/cadencias/step-audio-recorder"
import { useTestTTS } from "@/lib/api/hooks/use-tts"
import { cn } from "@/lib/utils"

// ─── Tipos ────────────────────────────────────────────────────────────

interface StepEditorSidebarProps {
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
  { token: "{lead_name}", label: "Nome" },
  { token: "{first_name}", label: "Primeiro nome" },
  { token: "{last_name}", label: "Sobrenome" },
  { token: "{company}", label: "Empresa" },
  { token: "{job_title}", label: "Cargo" },
  { token: "{industry}", label: "Setor" },
  { token: "{city}", label: "Cidade" },
  { token: "{location}", label: "Localização" },
  { token: "{segment}", label: "Segmento" },
] as const

function resolveTemplate(template: string, lead?: LeadListLeadItem): string {
  if (!lead) return template
  const nameParts = (lead.name ?? "").split(" ")
  const replacements: Record<string, string> = {
    "{lead_name}": lead.name ?? "Lead",
    "{first_name}": nameParts[0] ?? "Lead",
    "{last_name}": nameParts.slice(1).join(" ") || "Sobrenome",
    "{company}": lead.company ?? "Empresa",
    "{job_title}": lead.job_title ?? "Cargo",
    "{industry}": "Tecnologia",
    "{city}": "São Paulo",
    "{location}": "Brasil",
    "{segment}": "B2B",
    "{company_domain}": "empresa.com",
    "{website}": "https://empresa.com",
  }
  let resolved = template
  for (const [token, value] of Object.entries(replacements)) {
    resolved = resolved.replaceAll(token, value)
  }
  return resolved
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
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-[--text-secondary]">{label}</label>
      {children}
      {hint && <p className="text-[11px] leading-relaxed text-[--text-tertiary]">{hint}</p>}
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────

export function StepEditorSidebar({
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
  const testTTS = useTestTTS()

  const stepTypeOptions = STEP_TYPE_OPTIONS[step.channel] ?? []
  const previewLead = leads?.[0]
  const resolvedPreview = step.message_template
    ? resolveTemplate(step.message_template, previewLead)
    : ""

  const selectedEmailTemplate =
    step.channel === "email"
      ? (emailTemplates.find((t) => t.id === step.email_template_id) ?? null)
      : null
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

  const handlePreviewTTS = useCallback(async () => {
    if (!step.message_template || !ttsProvider || !ttsVoiceId) return
    setIsPreviewing(true)
    try {
      const resolved = resolveTemplate(step.message_template, previewLead)
      const blob = await testTTS.mutateAsync({
        provider: ttsProvider,
        voice_id: ttsVoiceId,
        text: resolved,
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
  }, [step.message_template, ttsProvider, ttsVoiceId, ttsSpeed, ttsPitch, previewLead, testTTS])

  const handleRecordedAudioUploaded = useCallback(
    (audioFile: AudioFile) => {
      setRecentUploadedAudio(audioFile)
      onUpdate("use_voice", true)
      onUpdate("audio_file_id", audioFile.id)
    },
    [onUpdate],
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
            </SidebarSection>
          </div>
        )}

        {/* ── Seção: Mensagem ── */}
        {step.channel !== "manual_task" && (
          <div className="space-y-4 px-4 py-4">
            <SidebarSection title="Mensagem">
              <SidebarField
                label={
                  step.channel === "email" && selectedEmailTemplate
                    ? "Corpo manual (fallback)"
                    : "Template da mensagem"
                }
                hint={
                  step.channel === "email"
                    ? selectedEmailTemplate
                      ? "Usado se o template salvo for removido"
                      : "Se preencher, o backend usa este corpo e pula a geração por IA"
                    : "Se preencher, substitui a geração por IA"
                }
              >
                <textarea
                  ref={textareaRef}
                  value={step.message_template}
                  onChange={(e) => onUpdate("message_template", e.target.value)}
                  rows={5}
                  placeholder="Olá {first_name}, vi que você trabalha na {company}…"
                  className="w-full resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-[--text-primary] placeholder:text-gray-400 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </SidebarField>

              {/* Pills de variáveis */}
              <div className="flex flex-wrap gap-1">
                {TEMPLATE_VARIABLES.map(({ token, label }) => (
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

              {/* Preview resolvido */}
              {resolvedPreview && previewLead && (
                <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-[11px]">
                  <p className="font-semibold text-blue-800">
                    Prévia com {previewLead.name ?? "lead de exemplo"}
                  </p>
                  <p className="mt-1.5 whitespace-pre-wrap text-blue-700">{resolvedPreview}</p>
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
                              {previewLead && (
                                <span className="text-gray-400">
                                  (com {previewLead.name ?? "lead"})
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
    </motion.aside>
  )
}
