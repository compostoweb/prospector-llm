"use client"

import { useState } from "react"
import { useUpdateCadence, type Cadence, type CadenceStep } from "@/lib/api/hooks/use-cadences"
import { useLeadList } from "@/lib/api/hooks/use-lead-lists"
import { CadenceSteps } from "@/components/cadencias/cadence-steps"
import { Button } from "@/components/ui/button"
import { ListTodo, AlertCircle, CheckCircle2 } from "lucide-react"
import Link from "next/link"
import { FlaskConical } from "lucide-react"

interface CadenceStepsEditorProps {
  cadence: Cadence
}

export function CadenceStepsEditor({ cadence }: CadenceStepsEditorProps) {
  const updateCadence = useUpdateCadence()
  const [steps, setSteps] = useState<CadenceStep[]>(cadence.steps_template ?? [])
  const { data: leadListDetail } = useLeadList(cadence.lead_list_id ?? "")
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

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

  return (
    <div className="overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-(--border-subtle) bg-(--bg-overlay) px-5 py-3.5">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-(--accent-subtle)">
          <ListTodo size={13} className="text-(--accent)" />
        </span>
        <div className="flex-1">
          <p className="text-sm font-semibold text-(--text-primary)">Passos da cadência</p>
          <p className="text-xs text-(--text-tertiary)">
            {steps.length === 0
              ? "Nenhum passo adicionado"
              : `${steps.length} passo${steps.length > 1 ? "s" : ""} configurado${steps.length > 1 ? "s" : ""}`}
          </p>
        </div>
      </div>

      {/* Steps editor */}
      <div className="p-5">
        <CadenceSteps
          value={steps}
          onChange={setSteps}
          ttsProvider={cadence.tts_provider}
          ttsVoiceId={cadence.tts_voice_id}
          ttsSpeed={cadence.tts_speed}
          ttsPitch={cadence.tts_pitch}
          leads={leadListDetail?.leads}
        />
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center gap-3 border-t border-(--border-subtle) px-5 py-4">
        <Button
          type="button"
          onClick={handleSave}
          disabled={updateCadence.isPending}
          className="min-w-32"
        >
          {updateCadence.isPending ? "Salvando…" : "Salvar passos"}
        </Button>
        <Link href={`/cadencias/${cadence.id}/sandbox`}>
          <Button type="button" variant="outline">
            <FlaskConical size={14} aria-hidden="true" />
            Testar no Sandbox
          </Button>
        </Link>

        {error && (
          <span className="flex items-center gap-1.5 text-sm text-(--danger)">
            <AlertCircle size={14} />
            {error}
          </span>
        )}
        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-(--success)">
            <CheckCircle2 size={14} />
            Passos salvos com sucesso!
          </span>
        )}
      </div>
    </div>
  )
}
