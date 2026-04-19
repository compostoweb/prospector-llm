"use client"

import { useTTSProviders, useTTSVoices, useTestTTS } from "@/lib/api/hooks/use-tts"
import { useTenant, getTenantTTSDefaults } from "@/lib/api/hooks/use-tenant"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { Volume2, Play, Loader2 } from "lucide-react"
import { useMemo, useRef } from "react"

export interface TTSConfig {
  tts_provider: string | null
  tts_voice_id: string | null
  tts_speed: number
  tts_pitch: number
}

interface TTSConfigFormProps {
  value: TTSConfig
  onChange: (config: TTSConfig) => void
  /** Se true, todos os steps são texto — esconde o painel TTS */
  hasVoiceSteps: boolean
}

const PROVIDER_LABELS: Record<string, { label: string; description: string }> = {
  elevenlabs: { label: "ElevenLabs", description: "Cloud — multilíngue, voice cloning" },
  edge: { label: "Edge TTS", description: "Microsoft Neural — gratuito, pt-BR nativo" },
  speechify: { label: "Speechify", description: "Cloud — multilíngue, voice cloning" },
  voicebox: { label: "Voicebox", description: "Self-hosted — voice cloning" },
  xtts: { label: "XTTS v2", description: "Self-hosted — voice cloning ultra-realista" },
}

export function TTSConfigForm({ value, onChange, hasVoiceSteps }: TTSConfigFormProps) {
  // Busca lista de providers via endpoint leve (não carrega 1800+ vozes)
  const { data: providersData } = useTTSProviders()
  const { data: tenant } = useTenant()
  // Busca vozes só do provider selecionado
  const { data, isLoading } = useTTSVoices(value.tts_provider ?? undefined)
  const testTTS = useTestTTS()
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const availableProviders = providersData?.providers ?? []

  // Ordena: clonadas primeiro, depois pt-BR, depois resto
  const currentVoices = useMemo(() => {
    const raw = value.tts_provider ? (data?.byProvider[value.tts_provider] ?? []) : []
    return [...raw].sort((a, b) => {
      // Clonadas primeiro
      if (a.is_cloned && !b.is_cloned) return -1
      if (!a.is_cloned && b.is_cloned) return 1
      // Depois pt-BR antes de outros idiomas
      const aPt = a.language?.startsWith("pt") ? 0 : 1
      const bPt = b.language?.startsWith("pt") ? 0 : 1
      if (aPt !== bPt) return aPt - bPt
      // Alfabético
      return a.name.localeCompare(b.name)
    })
  }, [value.tts_provider, data?.byProvider])

  if (!hasVoiceSteps) return null

  function update<K extends keyof TTSConfig>(key: K, val: TTSConfig[K]) {
    const updated = { ...value, [key]: val }
    if (key === "tts_provider" && val !== value.tts_provider) {
      // Auto-seleciona a voz padrão salva para este provider (se houver)
      const { voiceId } = getTenantTTSDefaults(tenant?.integration ?? null, val as string)
      updated.tts_voice_id = voiceId ?? null
    }
    onChange(updated)
  }

  async function handleTest() {
    if (!value.tts_provider || !value.tts_voice_id) return
    const blob = await testTTS.mutateAsync({
      provider: value.tts_provider,
      voice_id: value.tts_voice_id,
      speed: value.tts_speed,
      pitch: value.tts_pitch,
    })
    const url = URL.createObjectURL(blob)
    if (audioRef.current) {
      audioRef.current.src = url
      await audioRef.current.play()
    }
  }

  return (
    <div className="space-y-4 rounded-md border border-(--border-default) bg-(--bg-overlay) p-4">
      <div className="flex items-center gap-2">
        <Volume2 className="h-4 w-4 text-(--text-tertiary)" />
        <p className="text-xs font-semibold uppercase tracking-wider text-(--text-tertiary)">
          Configuração de Voz (TTS)
        </p>
      </div>

      {/* Provider */}
      <div>
        <label className="mb-1 block text-xs font-medium text-(--text-secondary)">
          Provider TTS
        </label>
        <div className="flex gap-2">
          {(availableProviders.length > 0 ? availableProviders : ["edge"]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => update("tts_provider", p)}
              className={cn(
                "flex-1 rounded-md border py-2 text-xs font-medium transition-colors",
                value.tts_provider === p
                  ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                  : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:bg-(--bg-overlay)",
              )}
              title={PROVIDER_LABELS[p]?.description ?? p}
            >
              {PROVIDER_LABELS[p]?.label ?? p}
            </button>
          ))}
        </div>
      </div>

      {/* Voice selector */}
      {value.tts_provider && (
        <div>
          <Label className="mb-1 block text-xs">Voz</Label>
          <div className="flex gap-2">
            <Select
              value={value.tts_voice_id ?? ""}
              onValueChange={(v) => update("tts_voice_id", v || null)}
              disabled={isLoading || currentVoices.length === 0}
            >
              <SelectTrigger className="h-8 flex-1 text-xs">
                <SelectValue placeholder={isLoading ? "Carregando…" : "Selecione uma voz"} />
              </SelectTrigger>
              <SelectContent>
                {currentVoices.map((v, i) => {
                  // Separador visual entre clonadas e built-in
                  const prevCloned = i > 0 ? currentVoices[i - 1]?.is_cloned : undefined
                  const showSep = prevCloned === true && !v.is_cloned
                  return (
                    <SelectItem
                      key={v.id}
                      value={v.id}
                      className={cn(
                        "text-xs",
                        showSep && "border-t border-(--border-default) mt-1 pt-1",
                      )}
                    >
                      {v.name}
                      <span className="ml-1 text-(--text-disabled)">
                        {v.is_cloned ? "(clone)" : v.language}
                      </span>
                    </SelectItem>
                  )
                })}
              </SelectContent>
            </Select>

            {/* Teste */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!value.tts_voice_id || testTTS.isPending}
              onClick={handleTest}
              className="h-8 px-2"
            >
              {testTTS.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
          {currentVoices.length === 0 && !isLoading && (
            <p className="mt-1 text-[10px] text-(--text-disabled)">
              Nenhuma voz disponível.{" "}
              <a href="/configuracoes/vozes-tts" className="underline">
                Gerenciar vozes
              </a>
            </p>
          )}
        </div>
      )}

      {/* Velocidade */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <Label className="text-xs">Velocidade</Label>
          <span className="text-xs tabular-nums text-(--text-tertiary)">
            {value.tts_speed.toFixed(1)}x
          </span>
        </div>
        <input
          type="range"
          min={0.5}
          max={2.0}
          step={0.1}
          value={value.tts_speed}
          onChange={(e) => update("tts_speed", parseFloat(e.target.value))}
          title="Velocidade da fala TTS"
          className="w-full accent-(--accent)"
        />
        <div className="flex justify-between text-[10px] text-(--text-disabled)">
          <span>Lento (0.5x)</span>
          <span>Normal</span>
          <span>Rápido (2.0x)</span>
        </div>
      </div>

      {/* Entonação / Pitch */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <Label className="text-xs">Entonação</Label>
          <span className="text-xs tabular-nums text-(--text-tertiary)">
            {value.tts_pitch > 0 ? "+" : ""}
            {value.tts_pitch.toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min={-50}
          max={50}
          step={5}
          value={value.tts_pitch}
          onChange={(e) => update("tts_pitch", parseFloat(e.target.value))}
          title="Entonação da voz TTS"
          className="w-full accent-(--accent)"
        />
        <div className="flex justify-between text-[10px] text-(--text-disabled)">
          <span>Grave (-50%)</span>
          <span>Normal</span>
          <span>Agudo (+50%)</span>
        </div>
      </div>

      {/* Hidden audio element for playback */}
      <audio ref={audioRef} className="hidden" />
    </div>
  )
}
