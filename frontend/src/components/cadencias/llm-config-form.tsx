"use client"

import { useState } from "react"
import { useLLMModels } from "@/lib/api/hooks/use-llm-models"
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
    <div className="space-y-4 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-overlay)] p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
        Configuração LLM
      </p>

      {/* Provider */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
            Provider
          </label>
          <div className="flex gap-2">
            {["openai", "gemini"].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => update("llm_provider", p as "openai" | "gemini")}
                className={cn(
                  "flex-1 rounded-[var(--radius-md)] border py-2 text-xs font-medium transition-colors",
                  value.llm_provider === p
                    ? "border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent-subtle-fg)]"
                    : "border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-overlay)]",
                )}
              >
                {p === "openai" ? "OpenAI" : "Gemini"}
              </button>
            ))}
          </div>
        </div>

        {/* Modelo */}
        <div>
          <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
            Modelo
          </label>
          <select
            value={value.llm_model}
            onChange={(e) => update("llm_model", e.target.value)}
            disabled={isLoading || currentProviderModels.length === 0}
            className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none disabled:opacity-50"
          >
            {isLoading ? (
              <option>Carregando…</option>
            ) : (
              currentProviderModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Temperature */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="text-xs font-medium text-[var(--text-secondary)]">Temperature</label>
          <span className="text-xs tabular-nums text-[var(--text-tertiary)]">
            {value.llm_temperature.toFixed(1)}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={value.llm_temperature}
          onChange={(e) => update("llm_temperature", Number(e.target.value))}
          className="w-full accent-[var(--accent)]"
        />
        <div className="mt-0.5 flex justify-between text-[10px] text-[var(--text-disabled)]">
          <span>Preciso</span>
          <span>Criativo</span>
        </div>
      </div>

      {/* Max tokens */}
      <div>
        <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
          Máx. tokens de saída
        </label>
        <input
          type="number"
          min={64}
          max={8192}
          step={64}
          value={value.llm_max_tokens}
          onChange={(e) => update("llm_max_tokens", Number(e.target.value))}
          className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
        />
      </div>
    </div>
  )
}
