"use client"

import { useState } from "react"
import { useCreateCadence, useUpdateCadence } from "@/lib/api/hooks/use-cadences"
import { useLeadLists, useLeadList } from "@/lib/api/hooks/use-lead-lists"
import { CadenceSteps } from "@/components/cadencias/cadence-steps"
import { LLMConfigForm } from "@/components/cadencias/llm-config-form"
import { TTSConfigForm, type TTSConfig } from "@/components/cadencias/tts-config-form"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { FlaskConical } from "lucide-react"
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
  const { data: lists } = useLeadLists()

  const [name, setName] = useState(cadence?.name ?? "")
  const [description, setDescription] = useState(cadence?.description ?? "")
  const [leadListId, setLeadListId] = useState(cadence?.lead_list_id ?? "")
  const { data: leadListDetail } = useLeadList(leadListId)
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
    tts_speed: cadence?.tts_speed ?? 1.0,
    tts_pitch: cadence?.tts_pitch ?? 0.0,
  })
  const [targetSegment, setTargetSegment] = useState(cadence?.target_segment ?? "")
  const [personaDescription, setPersonaDescription] = useState(cadence?.persona_description ?? "")
  const [offerDescription, setOfferDescription] = useState(cadence?.offer_description ?? "")
  const [toneInstructions, setToneInstructions] = useState(cadence?.tone_instructions ?? "")
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
      tts_speed: ttsConfig.tts_speed,
      tts_pitch: ttsConfig.tts_pitch,
      lead_list_id: leadListId || null,
      target_segment: targetSegment.trim() || null,
      persona_description: personaDescription.trim() || null,
      offer_description: offerDescription.trim() || null,
      tone_instructions: toneInstructions.trim() || null,
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

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[2fr_3fr]">
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

          {/* Contexto de prospecção (alimenta a IA) */}
          <details className="group rounded-md border border-(--border) p-4">
            <summary className="cursor-pointer text-sm font-semibold text-(--text-primary) select-none">
              Contexto de prospecção
              <span className="ml-2 text-xs font-normal text-(--text-tertiary)">
                — alimenta a IA com informações do seu negócio
              </span>
            </summary>
            <div className="mt-4 space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="target-segment">Segmento-alvo</Label>
                <Input
                  id="target-segment"
                  value={targetSegment}
                  onChange={(e) => setTargetSegment(e.target.value)}
                  placeholder="Ex: SaaS B2B, indústria farmacêutica, varejo premium"
                  maxLength={300}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="persona-desc">Persona ideal</Label>
                <Textarea
                  id="persona-desc"
                  value={personaDescription}
                  onChange={(e) => setPersonaDescription(e.target.value)}
                  rows={2}
                  placeholder="Ex: CTOs e VPs de Tecnologia de empresas com 200+ funcionários, focados em transformação digital"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="offer-desc">Proposta de valor</Label>
                <Textarea
                  id="offer-desc"
                  value={offerDescription}
                  onChange={(e) => setOfferDescription(e.target.value)}
                  rows={2}
                  placeholder="Ex: Consultoria em automação de processos com IA para reduzir custos operacionais"
                />
                <p className="text-xs text-(--text-tertiary)">
                  A IA mencionará isso sutilmente apenas nos steps avançados.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tone-instructions">Instruções de tom (opcional)</Label>
                <Textarea
                  id="tone-instructions"
                  value={toneInstructions}
                  onChange={(e) => setToneInstructions(e.target.value)}
                  rows={2}
                  placeholder="Ex: Use tom executivo mas descontraído. Evite jargões técnicos."
                />
              </div>
            </div>
          </details>

          {/* Lista de leads */}
          <div className="space-y-1.5">
            <Label htmlFor="cadence-list">Lista de leads</Label>
            <select
              id="cadence-list"
              value={leadListId}
              onChange={(e) => setLeadListId(e.target.value)}
              aria-label="Selecionar lista de leads"
              className="flex h-9 w-full rounded-md border border-(--border) bg-transparent px-3 py-1 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--ring)"
            >
              <option value="">Nenhuma lista</option>
              {lists?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.lead_count} leads)
                </option>
              ))}
            </select>
            <p className="text-xs text-(--text-tertiary)">
              Vincule uma lista para usar os leads desta cadência.
            </p>
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
          <div className="flex flex-wrap gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => router.back()}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar cadência"}
            </Button>
            {isEdit && cadence && (
              <Link href={`/cadencias/${cadence.id}/sandbox`}>
                <Button type="button" variant="outline">
                  <FlaskConical size={14} aria-hidden="true" />
                  Testar no Sandbox
                </Button>
              </Link>
            )}
          </div>
        </div>

        {/* ── Coluna direita: Passos (sticky) ── */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <h2 className="mb-3 text-sm font-semibold text-(--text-primary)">Passos da cadência</h2>
          <CadenceSteps
            value={steps}
            onChange={setSteps}
            ttsProvider={ttsConfig.tts_provider}
            ttsVoiceId={ttsConfig.tts_voice_id}
            ttsSpeed={ttsConfig.tts_speed}
            ttsPitch={ttsConfig.tts_pitch}
            leads={leadListDetail?.leads}
          />
        </div>
      </div>
    </form>
  )
}
