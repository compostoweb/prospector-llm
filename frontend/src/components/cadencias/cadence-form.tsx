"use client"

import { useState } from "react"
import { useCreateCadence, useUpdateCadence } from "@/lib/api/hooks/use-cadences"
import { CadenceSteps } from "@/components/cadencias/cadence-steps"
import { LLMConfigForm } from "@/components/cadencias/llm-config-form"
import { useRouter } from "next/navigation"
import type { Cadence, CreateCadenceBody, CadenceStep } from "@/lib/api/hooks/use-cadences"

interface CadenceFormProps {
  cadence?: Cadence
}

const DEFAULT_LLM = {
  llm_provider: "openai" as const,
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

export function CadenceForm({ cadence }: CadenceFormProps) {
  const router = useRouter()
  const createCadence = useCreateCadence()
  const updateCadence = useUpdateCadence()

  const [name, setName] = useState(cadence?.name ?? "")
  const [description, setDescription] = useState(cadence?.description ?? "")
  const [llmConfig, setLlmConfig] = useState({
    llm_provider: cadence?.llm_provider ?? DEFAULT_LLM.llm_provider,
    llm_model: cadence?.llm_model ?? DEFAULT_LLM.llm_model,
    llm_temperature: cadence?.llm_temperature ?? DEFAULT_LLM.llm_temperature,
    llm_max_tokens: cadence?.llm_max_tokens ?? DEFAULT_LLM.llm_max_tokens,
  })
  const [steps, setSteps] = useState<CadenceStep[]>(cadence?.steps ?? [])
  const [error, setError] = useState<string | null>(null)

  const isLoading = createCadence.isPending || updateCadence.isPending
  const isEdit = !!cadence

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError("Nome é obrigatório")
      return
    }
    if (steps.length === 0) {
      setError("Adicione pelo menos um passo")
      return
    }

    const body: CreateCadenceBody = {
      name: name.trim(),
      ...(description.trim() ? { description: description.trim() } : {}),
      ...llmConfig,
      steps,
    }

    try {
      if (isEdit) {
        await updateCadence.mutateAsync({ id: cadence.id, ...body })
        router.push(`/cadencias/${cadence.id}`)
      } else {
        const created = await createCadence.mutateAsync(body)
        router.push(`/cadencias/${created.id}`)
      }
    } catch {
      setError("Erro ao salvar cadência. Tente novamente.")
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div
          role="alert"
          className="rounded-[var(--radius-md)] bg-[var(--danger-subtle)] px-4 py-3 text-sm text-[var(--danger-subtle-fg)]"
        >
          {error}
        </div>
      )}

      {/* Nome */}
      <div>
        <label
          htmlFor="cadence-name"
          className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
        >
          Nome da cadência *
        </label>
        <input
          id="cadence-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ex: Prospecção SaaS B2B"
          required
          className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent)] focus:outline-none"
        />
      </div>

      {/* Descrição */}
      <div>
        <label
          htmlFor="cadence-desc"
          className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
        >
          Descrição
        </label>
        <textarea
          id="cadence-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          placeholder="Descreva o público-alvo e objetivo desta cadência…"
          className="w-full resize-none rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:border-[var(--accent)] focus:outline-none"
        />
      </div>

      {/* LLM Config */}
      <LLMConfigForm value={llmConfig} onChange={setLlmConfig} />

      {/* Passos */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
          Passos da cadência
        </h2>
        <CadenceSteps value={steps} onChange={setSteps} />
      </div>

      {/* Ações */}
      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={() => router.back()}
          className="rounded-[var(--radius-md)] border border-[var(--border-default)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-overlay)]"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-[var(--radius-md)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar cadência"}
        </button>
      </div>
    </form>
  )
}
