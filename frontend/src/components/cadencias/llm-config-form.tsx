"use client"

import { useState } from "react"
import { useLLMModels } from "@/lib/api/hooks/use-llm-models"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandItem,
} from "@/components/ui/command"
import { Check, ChevronsUpDown } from "lucide-react"
import { cn } from "@/lib/utils"

export interface LLMConfig {
  llm_provider: "openai" | "gemini" | "anthropic" | "openrouter"
  llm_model: string
  llm_temperature: number
  llm_max_tokens: number
}

interface LLMConfigFormProps {
  value: LLMConfig
  onChange: (config: LLMConfig) => void
}

const PROVIDER_OPTIONS: LLMConfig["llm_provider"][] = [
  "openai",
  "gemini",
  "anthropic",
  "openrouter",
]

const PROVIDER_LABELS: Record<LLMConfig["llm_provider"], string> = {
  openai: "OpenAI",
  gemini: "Gemini",
  anthropic: "Anthropic",
  openrouter: "OpenRouter",
}

export function LLMConfigForm({ value, onChange }: LLMConfigFormProps) {
  const { data, isLoading } = useLLMModels()
  const [open, setOpen] = useState(false)

  const configuredProviders = new Set(
    PROVIDER_OPTIONS.filter((provider) => (data?.providers ?? ([] as string[])).includes(provider)),
  )
  const currentProviderModels = data?.byProvider[value.llm_provider] ?? []
  const selectedModel = currentProviderModels.find((m) => m.id === value.llm_model)

  function update<K extends keyof LLMConfig>(key: K, val: LLMConfig[K]) {
    const updated = { ...value, [key]: val }
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

      {/* Provider + Modelo */}
      <div className="grid grid-cols-2 gap-3">
        {/* Provider */}
        <div>
          <label className="mb-1 block text-xs font-medium text-(--text-secondary)">Provider</label>
          <div className="flex gap-2">
            {PROVIDER_OPTIONS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => update("llm_provider", p)}
                disabled={configuredProviders.size > 0 && !configuredProviders.has(p)}
                className={cn(
                  "flex-1 rounded-md border py-2 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                  value.llm_provider === p
                    ? "border-(--accent) bg-(--accent) text-white"
                    : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:text-(--text-primary) hover:bg-(--bg-overlay)",
                )}
              >
                {PROVIDER_LABELS[p]}
              </button>
            ))}
          </div>
        </div>

        {/* Modelo — Combobox com busca */}
        <div>
          <Label className="mb-1 block text-xs">Modelo</Label>
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <button
                type="button"
                title="Selecionar modelo"
                disabled={isLoading || currentProviderModels.length === 0}
                className={cn(
                  "flex h-8 w-full items-center justify-between rounded-md border border-(--border-default)",
                  "bg-(--bg-surface) px-3 text-xs text-(--text-primary) transition-colors",
                  "hover:bg-(--bg-overlay) disabled:cursor-not-allowed disabled:opacity-50",
                  "focus:outline-none focus:ring-2 focus:ring-(--accent)",
                )}
              >
                <span className="truncate">
                  {isLoading
                    ? "Carregando…"
                    : (selectedModel?.name ?? value.llm_model) || "Selecione…"}
                </span>
                <ChevronsUpDown size={12} className="ml-1 shrink-0 text-(--text-disabled)" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-72 p-0">
              <Command>
                <CommandInput placeholder="Buscar modelo…" />
                <CommandList>
                  <CommandEmpty>Nenhum modelo encontrado.</CommandEmpty>
                  {currentProviderModels.map((m) => (
                    <CommandItem
                      key={m.id}
                      value={m.id}
                      keywords={[m.name, m.id]}
                      onSelect={() => {
                        update("llm_model", m.id)
                        setOpen(false)
                      }}
                    >
                      <Check
                        size={12}
                        className={cn(
                          "shrink-0",
                          m.id === value.llm_model ? "opacity-100" : "opacity-0",
                        )}
                      />
                      <span className="flex-1 truncate font-mono">{m.id}</span>
                    </CommandItem>
                  ))}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
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
        <p className="mt-1.5 text-[10px] text-(--text-disabled) leading-snug">
          ≈{" "}
          <span className="font-medium text-(--text-tertiary)">
            {Math.round(value.llm_max_tokens * 0.75).toLocaleString("pt-BR")}
          </span>{" "}
          palavras &nbsp;·&nbsp;
          <span className="font-medium text-(--text-tertiary)">
            {Math.round(value.llm_max_tokens * 4).toLocaleString("pt-BR")}
          </span>{" "}
          caracteres por resposta
        </p>
      </div>
    </div>
  )
}
