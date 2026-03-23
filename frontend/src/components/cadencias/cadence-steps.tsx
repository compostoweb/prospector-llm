"use client"

import { Plus, Trash2, GripVertical, Volume2 } from "lucide-react"
import type { CadenceStep } from "@/lib/api/hooks/use-cadences"

const CHANNEL_OPTIONS = [
  { value: "linkedin_connect", label: "LinkedIn Connect" },
  { value: "linkedin_dm", label: "LinkedIn DM" },
  { value: "email", label: "E-mail" },
] as const

interface CadenceStepsProps {
  value: CadenceStep[]
  onChange: (steps: CadenceStep[]) => void
}

export function CadenceSteps({ value, onChange }: CadenceStepsProps) {
  function addStep() {
    const newStep: CadenceStep = {
      channel: "linkedin_dm",
      day_offset: value.length === 0 ? 0 : 3,
      message_template: "",
      use_voice: false,
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
      // Limpa use_voice se canal mudou para algo != linkedin_dm
      if (field === "channel" && val !== "linkedin_dm") {
        next.use_voice = false
      }
      return next
    })
    onChange(updated)
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
                className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) focus:border-(--accent) focus:outline-none"
              />
            </div>
          </div>

          {/* Template da mensagem */}
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-(--text-secondary)">
              Template da mensagem
              <span className="ml-1 text-(--text-tertiary)">
                (use {"{lead_name}"}, {"{company}"}, {"{job_title}"})
              </span>
            </label>
            <textarea
              value={step.message_template}
              onChange={(e) => updateStep(index, "message_template", e.target.value)}
              rows={3}
              placeholder="Olá {lead_name}, vi que você trabalha na {company}…"
              className="w-full resize-none rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) placeholder:text-(--text-tertiary) focus:border-(--accent) focus:outline-none"
            />
          </div>

          {/* Voice note toggle — só para LinkedIn DM */}
          {step.channel === "linkedin_dm" && (
            <label className="mt-3 flex items-center gap-2 cursor-pointer">
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
                Enviar como mensagem de voz (TTS via Speechify)
              </span>
            </label>
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
    </div>
  )
}
