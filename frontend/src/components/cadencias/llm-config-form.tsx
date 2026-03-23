"use client"

import { useState } from "react"
import { useLLMModels } from "@/lib/api/hooks/use-llm-models"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

interface LLMConfig {
  llm_provider: "openai" | "gemini"
  llm_model: string
  llm_temperature: number
  llm_max_tokens: number
}

interface LLMConfigFormProps {
  value: LLMConfig
  onChange: (config: LLMConfig) => void
}

export function LLMConfigForm({ value, onChange }: LLMConfigFormProps) {
  const { data, isLoading } = useLLMModels()

  const providers = data?.providers ?? []
  const currentProviderModels = data?.byProvider[value.llm_provider] ?? []

  function update<K extends keyof LLMConfig>(key: K, val: LLMConfig[K]) {
    const updated = { ...value, [key]: val }
    // Se mudou o provider, reset do modelo
    if (key === "llm_provider" && val !== value.llm_provider) {
      const firstModel = data?.byProvider[val as string]?.[0]?.id
      updated.llm_model = firstModel ?? ""
    }
    onChange(updated)
  }

  return (
    <div className="space-y-4 rounded-md border border-(--border-default) bg-(--bg-overlay) p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-(--text-tertiary)">
        Configuração LLM
      </p>

      {/* Provider */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-(--text-secondary)">Provider</label>
          <div className="flex gap-2">
            {["openai", "gemini"].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => update("llm_provider", p as "openai" | "gemini")}
                className={cn(
                  "flex-1 rounded-md border py-2 text-xs font-medium transition-colors",
                  value.llm_provider === p
                    ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                    : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:bg-(--bg-overlay)",
                )}
              >
                {p === "openai" ? "OpenAI" : "Gemini"}
              </button>
            ))}
          </div>
        </div>

        {/* Modelo */}
        <div>
          <Label className="mb-1 block text-xs">Modelo</Label>
          <Select
            value={value.llm_model}
            onValueChange={(v) => update("llm_model", v)}
            disabled={isLoading || currentProviderModels.length === 0}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder={isLoading ? "Carregando…" : "Selecione"} />
            </SelectTrigger>
            <SelectContent>
              {currentProviderModels.map((m) => (
                <SelectItem key={m.id} value={m.id} className="text-xs">
                  {m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Temperature */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <Label className="text-xs">Temperature</Label>
          <span className="text-xs tabular-nums text-(--text-tertiary)">
            {value.llm_temperature.toFixed(1)}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={value.llm_temperature}
          aria-label="Temperature"
          onChange={(e) => update("llm_temperature", Number(e.target.value))}
          className="w-full accent-(--accent)"
        />
        <div className="mt-0.5 flex justify-between text-[10px] text-(--text-disabled)">
          <span>Preciso</span>
          <span>Criativo</span>
        </div>
      </div>

      {/* Max tokens */}
      <div>
        <Label className="mb-1 block text-xs">Máx. tokens de saída</Label>
        <Input
          type="number"
          min={64}
          max={8192}
          step={64}
          value={value.llm_max_tokens}
          onChange={(e) => update("llm_max_tokens", Number(e.target.value))}
          className="h-8 text-xs"
        />
      </div>
    </div>
  )
}
