"use client"

import { useCallback, useState } from "react"
import { AnimatePresence } from "framer-motion"
import {
  useUpdateCadence,
  type Cadence,
  type CadenceStep,
  type CadenceChannel,
  type CadenceStepLayout,
} from "@/lib/api/hooks/use-cadences"
import { useLeadList } from "@/lib/api/hooks/use-lead-lists"
import { useAudioFiles } from "@/lib/api/hooks/use-audio-files"
import { useEmailTemplates } from "@/lib/api/hooks/use-email-templates"
import { CadenceFlowCanvas } from "@/components/cadencias/cadence-flow-canvas"
import { StepEditorSidebar } from "@/components/cadencias/step-editor-sidebar"
import { Button } from "@/components/ui/button"
import { AlertCircle, CheckCircle2, FlaskConical } from "lucide-react"
import Link from "next/link"

interface CadenceStepsEditorProps {
  cadence: Cadence
}

export function CadenceStepsEditor({ cadence }: CadenceStepsEditorProps) {
  const updateCadence = useUpdateCadence()

  const [steps, setSteps] = useState<CadenceStep[]>(cadence.steps_template ?? [])
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  // Dados para o editor de passos
  const { data: leadListDetail } = useLeadList(cadence.lead_list_id ?? "")
  const { data: audioFilesData } = useAudioFiles()
  const { data: emailTemplatesData } = useEmailTemplates(undefined, true)

  const leads = leadListDetail?.leads
  const audioFiles = audioFilesData?.items ?? []
  const emailTemplates = emailTemplatesData ?? []

  // ─── Handlers de mutação de passos ───────────────────────────────

  const handleAddStep = useCallback(
    (channel?: CadenceChannel) => {
      const defaultChannel: CadenceChannel =
        cadence.cadence_type === "email_only" ? "email" : "linkedin_dm"
      const newStep: CadenceStep = {
        channel: channel ?? defaultChannel,
        day_offset: steps.length === 0 ? 0 : 3,
        message_template: "",
        use_voice: false,
        audio_file_id: null,
        step_type: null,
        subject_variants: null,
        email_template_id: null,
        layout: null,
        manual_task_type: null,
        manual_task_detail: null,
      }
      const updated = [...steps, newStep]
      setSteps(updated)
      setSelectedIndex(updated.length - 1)
    },
    [steps, cadence.cadence_type],
  )

  const handleInsertAfter = useCallback(
    (afterIndex: number) => {
      const newStep: CadenceStep = {
        channel: cadence.cadence_type === "email_only" ? "email" : "linkedin_dm",
        day_offset: 1,
        message_template: "",
        use_voice: false,
        audio_file_id: null,
        step_type: null,
        subject_variants: null,
        email_template_id: null,
        layout: null,
        manual_task_type: null,
        manual_task_detail: null,
      }
      const updated = [...steps.slice(0, afterIndex + 1), newStep, ...steps.slice(afterIndex + 1)]
      setSteps(updated)
      setSelectedIndex(afterIndex + 1)
    },
    [steps, cadence.cadence_type],
  )

  const handleDeleteStep = useCallback(
    (index: number) => {
      const updated = steps.filter((_, i) => i !== index)
      setSteps(updated)
      if (selectedIndex === index) setSelectedIndex(null)
      else if (selectedIndex !== null && selectedIndex > index) setSelectedIndex(selectedIndex - 1)
    },
    [steps, selectedIndex],
  )

  const handleDuplicateStep = useCallback(
    (index: number) => {
      const src = steps[index]
      if (!src) return
      const copy: CadenceStep = {
        ...src,
        layout: src.layout ? { x: src.layout.x + 40, y: src.layout.y + 40 } : null,
      }
      const updated = [...steps.slice(0, index + 1), copy, ...steps.slice(index + 1)]
      setSteps(updated)
      setSelectedIndex(index + 1)
    },
    [steps],
  )

  const handleMoveUp = useCallback(
    (index: number) => {
      if (index === 0) return
      const updated = [...steps]
      const tmp = updated[index - 1] as CadenceStep
      updated[index - 1] = updated[index] as CadenceStep
      updated[index] = tmp
      setSteps(updated)
      setSelectedIndex(index - 1)
    },
    [steps],
  )

  const handleMoveDown = useCallback(
    (index: number) => {
      if (index >= steps.length - 1) return
      const updated = [...steps]
      const tmp = updated[index] as CadenceStep
      updated[index] = updated[index + 1] as CadenceStep
      updated[index + 1] = tmp
      setSteps(updated)
      setSelectedIndex(index + 1)
    },
    [steps],
  )

  const handleUpdateStep = useCallback(
    (field: keyof CadenceStep, value: unknown) => {
      if (selectedIndex === null) return
      setSteps((prev) =>
        prev.map((s, i) => {
          if (i !== selectedIndex) return s
          const next = { ...s, [field]: value }
          // Reset dependências ao trocar canal
          if (field === "channel") {
            if (value !== "linkedin_dm") {
              next.use_voice = false
              next.audio_file_id = null
            }
            if (value !== "email") {
              next.email_template_id = null
              next.subject_variants = null
            }
            if (value !== "manual_task") {
              next.manual_task_type = null
              next.manual_task_detail = null
            }
            next.step_type = null
          }
          if (field === "use_voice" && value === false) next.audio_file_id = null
          return next
        }),
      )
    },
    [selectedIndex],
  )

  const handleStepPositionChange = useCallback((index: number, layout: CadenceStepLayout) => {
    setSteps((prev) =>
      prev.map((step, currentIndex) => (currentIndex === index ? { ...step, layout } : step)),
    )
  }, [])

  // ─── Save ─────────────────────────────────────────────────────────

  async function handleSave() {
    setError(null)
    setSaved(false)

    if (steps.length === 0) {
      setError("Adicione pelo menos um passo antes de salvar.")
      return
    }
    if (cadence.cadence_type === "email_only" && steps.some((s) => s.channel !== "email")) {
      setError("Cadências do tipo Só E-mail aceitam apenas passos com canal E-mail.")
      return
    }

    try {
      await updateCadence.mutateAsync({
        id: cadence.id,
        name: cadence.name,
        ...(cadence.description ? { description: cadence.description } : {}),
        mode: cadence.mode,
        cadence_type: cadence.cadence_type,
        llm: {
          provider: cadence.llm_provider,
          model: cadence.llm_model,
          temperature: cadence.llm_temperature,
          max_tokens: cadence.llm_max_tokens,
        },
        tts_provider: cadence.tts_provider,
        tts_voice_id: cadence.tts_voice_id,
        tts_speed: cadence.tts_speed,
        tts_pitch: cadence.tts_pitch,
        lead_list_id: cadence.lead_list_id,
        email_account_id: cadence.email_account_id,
        linkedin_account_id: cadence.linkedin_account_id,
        target_segment: cadence.target_segment,
        persona_description: cadence.persona_description,
        offer_description: cadence.offer_description,
        tone_instructions: cadence.tone_instructions,
        steps_template: steps,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar passos. Tente novamente.")
    }
  }

  const selectedStep = selectedIndex !== null ? (steps[selectedIndex] ?? null) : null

  // ─── Render ───────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-0">
      {/* Toolbar superior */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[--text-primary]">
            {steps.length === 0
              ? "Nenhum passo adicionado"
              : `${steps.length} passo${steps.length > 1 ? "s" : ""}`}
          </p>
          <p className="text-xs text-[--text-tertiary]">
            Clique num nó para editar · use ↑↓ para reordenar
          </p>
        </div>

        <div className="flex items-center gap-2">
          {error && (
            <span className="flex items-center gap-1.5 text-sm text-[--danger]">
              <AlertCircle size={14} />
              {error}
            </span>
          )}
          {saved && (
            <span className="flex items-center gap-1.5 text-sm text-[--success]">
              <CheckCircle2 size={14} />
              Salvo!
            </span>
          )}

          <Link href={`/cadencias/${cadence.id}/sandbox`}>
            <Button type="button" variant="outline" className="gap-1.5">
              <FlaskConical size={14} />
              Sandbox
            </Button>
          </Link>

          <Button
            type="button"
            onClick={handleSave}
            disabled={updateCadence.isPending}
            className="min-w-28"
          >
            {updateCadence.isPending ? "Salvando…" : "Salvar passos"}
          </Button>
        </div>
      </div>

      {/* Área canvas + sidebar */}
      <div className="flex h-[calc(100vh-240px)] min-h-125 items-stretch gap-4">
        {/* Canvas — encolhe quando sidebar aberta */}
        <div
          className={
            selectedStep !== null
              ? "min-w-0 flex-1 h-full overflow-hidden"
              : "w-full h-full overflow-hidden"
          }
        >
          <CadenceFlowCanvas
            steps={steps}
            selectedIndex={selectedIndex}
            onSelectStep={setSelectedIndex}
            onStepPositionChange={handleStepPositionChange}
            onAddStep={handleAddStep}
            onInsertAfter={handleInsertAfter}
            onDeleteStep={handleDeleteStep}
            onDuplicateStep={handleDuplicateStep}
            onMoveUp={handleMoveUp}
            onMoveDown={handleMoveDown}
          />
        </div>

        {/* Sidebar de edição */}
        <AnimatePresence>
          {selectedStep !== null && selectedIndex !== null && (
            <StepEditorSidebar
              key={`sidebar-${selectedIndex}`}
              cadenceId={cadence.id}
              step={selectedStep}
              index={selectedIndex}
              onUpdate={handleUpdateStep}
              onClose={() => setSelectedIndex(null)}
              ttsProvider={cadence.tts_provider}
              ttsVoiceId={cadence.tts_voice_id}
              ttsSpeed={cadence.tts_speed}
              ttsPitch={cadence.tts_pitch}
              leads={leads ?? []}
              emailTemplates={emailTemplates}
              audioFiles={audioFiles}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
