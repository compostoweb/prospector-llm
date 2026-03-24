"use client"

import { useState } from "react"
import { useCreateCadence, useUpdateCadence } from "@/lib/api/hooks/use-cadences"
import { CadenceSteps } from "@/components/cadencias/cadence-steps"
import { LLMConfigForm } from "@/components/cadencias/llm-config-form"
import { TTSConfigForm, type TTSConfig } from "@/components/cadencias/tts-config-form"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
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
  const [steps, setSteps] = useState<CadenceStep[]>(cadence?.steps_template ?? [])
  const [ttsConfig, setTtsConfig] = useState<TTSConfig>({
    tts_provider: cadence?.tts_provider ?? null,
    tts_voice_id: cadence?.tts_voice_id ?? null,
  })
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
      llm: {
        provider: llmConfig.llm_provider,
        model: llmConfig.llm_model,
        temperature: llmConfig.llm_temperature,
        max_tokens: llmConfig.llm_max_tokens,
      },
      tts_provider: ttsConfig.tts_provider,
      tts_voice_id: ttsConfig.tts_voice_id,
      steps_template: steps,
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
    <form onSubmit={handleSubmit}>
      {error && (
        <div
          role="alert"
          className="mb-5 rounded-md bg-(--danger-subtle) px-4 py-3 text-sm text-(--danger-subtle-fg)"
        >
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ── Coluna esquerda: Configurações ── */}
        <div className="space-y-5">
          {/* Nome */}
          <div className="space-y-1.5">
            <Label htmlFor="cadence-name">Nome da cadência *</Label>
            <Input
              id="cadence-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Prospecção SaaS B2B"
              required
            />
          </div>

          {/* Descrição */}
          <div className="space-y-1.5">
            <Label htmlFor="cadence-desc">Descrição</Label>
            <Textarea
              id="cadence-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Descreva o público-alvo e objetivo desta cadência…"
            />
          </div>

          {/* LLM Config */}
          <LLMConfigForm value={llmConfig} onChange={setLlmConfig} />

          {/* TTS Config — só aparece se houver steps com use_voice */}
          <TTSConfigForm
            value={ttsConfig}
            onChange={setTtsConfig}
            hasVoiceSteps={steps.some((s) => s.use_voice)}
          />

          {/* Ações */}
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => router.back()}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar cadência"}
            </Button>
          </div>
        </div>

        {/* ── Coluna direita: Passos (sticky) ── */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <h2 className="mb-3 text-sm font-semibold text-(--text-primary)">Passos da cadência</h2>
          <CadenceSteps value={steps} onChange={setSteps} />
        </div>
      </div>
    </form>
  )
}
