"use client"

import { useTTSVoices, useTestTTS } from "@/lib/api/hooks/use-tts"
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
import { useRef } from "react"

export interface TTSConfig {
  tts_provider: string | null
  tts_voice_id: string | null
}

interface TTSConfigFormProps {
  value: TTSConfig
  onChange: (config: TTSConfig) => void
  /** Se true, todos os steps são texto — esconde o painel TTS */
  hasVoiceSteps: boolean
}

export function TTSConfigForm({ value, onChange, hasVoiceSteps }: TTSConfigFormProps) {
  const { data, isLoading } = useTTSVoices(value.tts_provider ?? undefined)
  const testTTS = useTestTTS()
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const availableProviders = data?.providers ?? []
  const currentVoices = value.tts_provider ? (data?.byProvider[value.tts_provider] ?? []) : []

  if (!hasVoiceSteps) return null

  function update<K extends keyof TTSConfig>(key: K, val: TTSConfig[K]) {
    const updated = { ...value, [key]: val }
    if (key === "tts_provider" && val !== value.tts_provider) {
      updated.tts_voice_id = null
    }
    onChange(updated)
  }

  async function handleTest() {
    if (!value.tts_provider || !value.tts_voice_id) return
    const blob = await testTTS.mutateAsync({
      provider: value.tts_provider,
      voice_id: value.tts_voice_id,
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
          {(availableProviders.length > 0 ? availableProviders : ["speechify"]).map((p) => (
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
            >
              {p === "speechify" ? "Speechify" : p === "voicebox" ? "Voicebox" : p}
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
                {currentVoices.map((v) => (
                  <SelectItem key={v.id} value={v.id} className="text-xs">
                    {v.name}
                    {v.is_cloned && <span className="ml-1 text-(--text-disabled)">(clone)</span>}
                  </SelectItem>
                ))}
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
              <a href="/configuracoes/voz" className="underline">
                Gerenciar vozes
              </a>
            </p>
          )}
        </div>
      )}

      {/* Hidden audio element for playback */}
      <audio ref={audioRef} className="hidden" />
    </div>
  )
}
