"use client"

import { useCallback, useRef, useState } from "react"
import { Plus, Trash2, GripVertical, Volume2, Music, Play, Loader2 } from "lucide-react"
import type { CadenceStep, StepType } from "@/lib/api/hooks/use-cadences"
import { useAudioFiles } from "@/lib/api/hooks/use-audio-files"
import { useTestTTS } from "@/lib/api/hooks/use-tts"
import type { LeadListLeadItem } from "@/lib/api/hooks/use-lead-lists"

const CHANNEL_OPTIONS = [
  { value: "linkedin_connect", label: "LinkedIn Connect" },
  { value: "linkedin_dm", label: "LinkedIn DM" },
  { value: "email", label: "E-mail" },
  { value: "manual_task", label: "Tarefa Manual" },
] as const

/** Tipos de step disponíveis por canal */
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
  { token: "{company_domain}", label: "Domínio" },
  { token: "{website}", label: "Website" },
] as const

interface CadenceStepsProps {
  value: CadenceStep[]
  onChange: (steps: CadenceStep[]) => void
  ttsProvider?: string | null
  ttsVoiceId?: string | null
  ttsSpeed?: number
  ttsPitch?: number
  leads?: LeadListLeadItem[]
}

/** Resolve variáveis do template com dados do lead */
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

export function CadenceSteps({
  value,
  onChange,
  ttsProvider,
  ttsVoiceId,
  ttsSpeed,
  ttsPitch,
  leads,
}: CadenceStepsProps) {
  const textareaRefs = useRef<Map<number, HTMLTextAreaElement>>(new Map())
  const { data: audioFilesData } = useAudioFiles()
  const audioFiles = audioFilesData?.items ?? []
  const testTTS = useTestTTS()
  const previewAudioRef = useRef<HTMLAudioElement | null>(null)
  const [previewingStep, setPreviewingStep] = useState<number | null>(null)

  const setRef = useCallback(
    (index: number) => (el: HTMLTextAreaElement | null) => {
      if (el) textareaRefs.current.set(index, el)
      else textareaRefs.current.delete(index)
    },
    [],
  )

  function addStep() {
    const newStep: CadenceStep = {
      channel: "linkedin_dm",
      day_offset: value.length === 0 ? 0 : 3,
      message_template: "",
      use_voice: false,
      audio_file_id: null,
      step_type: null,
    }
    onChange([...value, newStep])
  }

  function removeStep(index: number) {
    const updated = value.filter((_, i) => i !== index)
    onChange(updated)
  }

  function updateStep(index: number, field: keyof CadenceStep, val: unknown) {
    const updated = value.map((s, i) => {
      if (i !== index) return s
      const next = { ...s, [field]: val }
      // Limpa use_voice, audio_file_id e step_type se canal mudou
      if (field === "channel") {
        if (val !== "linkedin_dm") {
          next.use_voice = false
          next.audio_file_id = null
        }
        next.step_type = null // reset ao trocar canal
      }
      // Limpa audio_file_id se desmarcou use_voice
      if (field === "use_voice" && val === false) {
        next.audio_file_id = null
      }
      return next
    })
    onChange(updated)
  }

  function insertVariable(index: number, token: string) {
    const ta = textareaRefs.current.get(index)
    const current = value[index]?.message_template ?? ""

    if (ta) {
      const start = ta.selectionStart
      const end = ta.selectionEnd
      const newValue = current.slice(0, start) + token + current.slice(end)
      updateStep(index, "message_template", newValue)
      // Restaura cursor após o token inserido
      requestAnimationFrame(() => {
        ta.focus()
        const pos = start + token.length
        ta.setSelectionRange(pos, pos)
      })
    } else {
      updateStep(index, "message_template", current + token)
    }
  }

  async function handlePreviewTTS(index: number) {
    const step = value[index]
    if (!step?.message_template || !ttsProvider || !ttsVoiceId) return

    setPreviewingStep(index)
    try {
      const firstLead = leads?.[0]
      const resolvedText = resolveTemplate(step.message_template, firstLead)

      const blob = await testTTS.mutateAsync({
        provider: ttsProvider,
        voice_id: ttsVoiceId,
        text: resolvedText,
        speed: ttsSpeed ?? 1.0,
        pitch: ttsPitch ?? 0.0,
      })
      const url = URL.createObjectURL(blob)
      if (previewAudioRef.current) {
        previewAudioRef.current.src = url
        await previewAudioRef.current.play()
      }
    } catch {
      // silently handle
    } finally {
      setPreviewingStep(null)
    }
  }

  return (
    <div className="space-y-3">
      {value.map((step, index) => (
        <div
          key={index}
          className="rounded-md border border-(--border-default) bg-(--bg-surface) p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GripVertical size={14} className="text-(--text-disabled)" aria-hidden="true" />
              <span className="text-xs font-semibold text-(--text-tertiary)">
                PASSO {index + 1}
              </span>
            </div>
            <button
              type="button"
              onClick={() => removeStep(index)}
              aria-label={`Remover passo ${index + 1}`}
              className="text-(--text-tertiary) transition-colors hover:text-(--danger)"
            >
              <Trash2 size={14} aria-hidden="true" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Canal */}
            <div>
              <label className="mb-1 block text-xs font-medium text-(--text-secondary)">
                Canal
              </label>
              <select
                value={step.channel}
                onChange={(e) => updateStep(index, "channel", e.target.value)}
                aria-label={`Canal do passo ${index + 1}`}
                className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:border-(--accent) focus:outline-none"
              >
                {CHANNEL_OPTIONS.map(({ value: v, label }) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* Delay */}
            <div>
              <label className="mb-1 block text-xs font-medium text-(--text-secondary)">
                Dias de espera
              </label>
              <input
                type="number"
                min={0}
                max={90}
                value={step.day_offset}
                onChange={(e) => updateStep(index, "day_offset", Number(e.target.value))}
                aria-label={`Dias de espera do passo ${index + 1}`}
                className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:border-(--accent) focus:outline-none"
              />
            </div>
          </div>

          {/* Tipo do passo — filtrado pelo canal */}
          {STEP_TYPE_OPTIONS[step.channel] && STEP_TYPE_OPTIONS[step.channel].length > 1 && (
            <div className="mt-3">
              <label className="mb-1 block text-xs font-medium text-(--text-secondary)">
                Tipo do passo
              </label>
              <select
                value={step.step_type ?? ""}
                onChange={(e) => updateStep(index, "step_type", e.target.value || null)}
                aria-label={`Tipo do passo ${index + 1}`}
                className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:border-(--accent) focus:outline-none"
              >
                <option value="">Automático (inferir pela posição)</option>
                {STEP_TYPE_OPTIONS[step.channel].map(({ value: v, label }) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-[11px] text-(--text-tertiary)">
                Define qual instrução a IA vai usar para gerar o conteúdo deste passo
              </p>
            </div>
          )}

          {/* Template da mensagem */}
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-(--text-secondary)">
              Template da mensagem
            </label>
            <textarea
              ref={setRef(index)}
              value={step.message_template}
              onChange={(e) => updateStep(index, "message_template", e.target.value)}
              rows={3}
              placeholder="Olá {lead_name}, vi que você trabalha na {company}…"
              className="w-full resize-none rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) placeholder:text-(--text-tertiary) focus:border-(--accent) focus:outline-none"
            />

            {/* Variable pills */}
            <div className="mt-1.5 flex flex-wrap gap-1">
              {TEMPLATE_VARIABLES.map(({ token, label }) => (
                <button
                  key={token}
                  type="button"
                  onClick={() => insertVariable(index, token)}
                  className="rounded-full border border-(--border-subtle) bg-(--bg-overlay) px-2 py-0.5 text-[11px] font-medium text-(--text-secondary) transition-colors hover:border-(--accent) hover:text-(--accent)"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Voice note toggle — só para LinkedIn DM */}
          {step.channel === "linkedin_dm" && (
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={step.use_voice}
                  onChange={(e) => updateStep(index, "use_voice", e.target.checked)}
                  aria-label="Enviar como mensagem de voz"
                  title="Enviar como mensagem de voz"
                  className="h-4 w-4 rounded border-(--border-default) accent-(--accent)"
                />
                <Volume2 size={14} className="text-(--text-secondary)" aria-hidden="true" />
                <span className="text-xs font-medium text-(--text-secondary)">
                  Enviar como mensagem de voz
                </span>
              </label>

              {/* Seletor de fonte de áudio */}
              {step.use_voice && (
                <div className="ml-6">
                  <label className="mb-1 block text-xs font-medium text-(--text-secondary)">
                    Fonte do áudio
                  </label>
                  <select
                    value={step.audio_file_id ?? ""}
                    onChange={(e) => updateStep(index, "audio_file_id", e.target.value || null)}
                    aria-label={`Fonte de áudio do passo ${index + 1}`}
                    className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:border-(--accent) focus:outline-none"
                  >
                    <option value="">
                      🎙️ Gerar via TTS
                      {ttsProvider
                        ? ` (${ttsProvider === "edge" ? "Edge TTS" : ttsProvider === "speechify" ? "Speechify" : ttsProvider})`
                        : ""}
                    </option>
                    {audioFiles.map((af) => (
                      <option key={af.id} value={af.id}>
                        🎵 {af.name} {af.language ? `(${af.language})` : ""}
                      </option>
                    ))}
                  </select>
                  {step.audio_file_id && (
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-(--text-tertiary)">
                      <Music size={11} aria-hidden="true" />
                      Áudio pré-gravado — o template de texto será ignorado para voz
                    </p>
                  )}
                  {!step.audio_file_id && (
                    <p className="mt-1 text-[11px] text-(--text-tertiary)">
                      O texto do template será convertido em áudio via TTS
                    </p>
                  )}

                  {/* Botão de preview TTS — só se não tem áudio pré-gravado */}
                  {!step.audio_file_id && ttsProvider && ttsVoiceId && (
                    <button
                      type="button"
                      onClick={() => handlePreviewTTS(index)}
                      disabled={previewingStep === index || !step.message_template}
                      className="mt-2 flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 text-xs font-medium text-(--text-secondary) transition-colors hover:border-(--accent) hover:text-(--accent) disabled:opacity-50"
                    >
                      {previewingStep === index ? (
                        <>
                          <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                          Gerando prévia…
                        </>
                      ) : (
                        <>
                          <Play size={12} aria-hidden="true" />
                          Testar TTS deste passo
                          {leads && leads.length > 0 && (
                            <span className="text-(--text-disabled)">
                              (com {leads[0]?.name ?? "lead"})
                            </span>
                          )}
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      <button
        type="button"
        onClick={addStep}
        className="flex w-full items-center justify-center gap-2 rounded-md border border-dashed border-(--border-default) py-3 text-sm text-(--text-secondary) transition-colors hover:border-(--accent) hover:text-(--accent)"
      >
        <Plus size={14} aria-hidden="true" />
        Adicionar passo
      </button>

      {/* Hidden audio for TTS preview */}
      <audio ref={previewAudioRef} className="hidden" />
    </div>
  )
}
