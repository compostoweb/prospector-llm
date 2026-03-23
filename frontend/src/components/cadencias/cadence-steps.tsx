"use client"

import { Plus, Trash2, GripVertical } from "lucide-react"
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
      step_number: value.length + 1,
      channel: "linkedin_dm",
      delay_days: value.length === 0 ? 0 : 3,
      message_template: "",
    }
    onChange([...value, newStep])
  }

  function removeStep(index: number) {
    const updated = value
      .filter((_, i) => i !== index)
      .map((s, i) => ({ ...s, step_number: i + 1 }))
    onChange(updated)
  }

  function updateStep(index: number, field: keyof CadenceStep, val: unknown) {
    const updated = value.map((s, i) => (i === index ? { ...s, [field]: val } : s))
    onChange(updated)
  }

  return (
    <div className="space-y-3">
      {value.map((step, index) => (
        <div
          key={index}
          className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-4"
        >
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GripVertical size={14} className="text-[var(--text-disabled)]" aria-hidden="true" />
              <span className="text-xs font-semibold text-[var(--text-tertiary)]">
                PASSO {step.step_number}
              </span>
            </div>
            <button
              type="button"
              onClick={() => removeStep(index)}
              aria-label={`Remover passo ${step.step_number}`}
              className="text-[var(--text-tertiary)] transition-colors hover:text-[var(--danger)]"
            >
              <Trash2 size={14} aria-hidden="true" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Canal */}
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Canal
              </label>
              <select
                value={step.channel}
                onChange={(e) => updateStep(index, "channel", e.target.value)}
                className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
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
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Dias de espera
              </label>
              <input
                type="number"
                min={0}
                max={90}
                value={step.delay_days}
                onChange={(e) => updateStep(index, "delay_days", Number(e.target.value))}
                className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
              />
            </div>
          </div>

          {/* Template da mensagem */}
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
              Template da mensagem
              <span className="ml-1 text-[var(--text-tertiary)]">
                (use {"{lead_name}"}, {"{company}"}, {"{job_title}"})
              </span>
            </label>
            <textarea
              value={step.message_template}
              onChange={(e) => updateStep(index, "message_template", e.target.value)}
              rows={3}
              placeholder="Olá {lead_name}, vi que você trabalha na {company}…"
              className="w-full resize-none rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent)] focus:outline-none"
            />
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addStep}
        className="flex w-full items-center justify-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] py-3 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
      >
        <Plus size={14} aria-hidden="true" />
        Adicionar passo
      </button>
    </div>
  )
}
