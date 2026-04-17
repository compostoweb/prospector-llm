"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface ModelInfo {
  id: string
  name: string
  provider: "openai" | "gemini" | "anthropic" | "openrouter"
  context_window: number
  input_cost_per_mtok: number
  output_cost_per_mtok: number
  supports_json: boolean
}

export interface LLMProviderInfo {
  provider: string
  configured: boolean
  models_count: number
}

export interface TestModelParams {
  provider: string
  model: string
  prompt?: string
  temperature?: number
  max_tokens?: number
}

export interface TestModelResult {
  provider: string
  model: string
  response: string
  latency_ms: number
  tokens_used: number
}

function extractProviderMessage(message: string): string {
  const singleQuotedMatch = message.match(/'message':\s*'([^']+)'/)
  if (singleQuotedMatch?.[1]) {
    return singleQuotedMatch[1]
  }

  const doubleQuotedMatch = message.match(/"message":\s*"([^"]+)"/)
  if (doubleQuotedMatch?.[1]) {
    return doubleQuotedMatch[1]
  }

  return message
}

function humanizeTestModelError(message: string, provider: string): string {
  const normalized = extractProviderMessage(message).trim()
  const lower = normalized.toLowerCase()

  if (lower === "failed to fetch") {
    return "Falha de rede ao testar o modelo. Verifique a API e tente novamente."
  }

  if (
    provider === "anthropic" &&
    (lower.includes("credit balance") || lower.includes("plans & billing"))
  ) {
    return "Conta Anthropic sem creditos suficientes. Adicione saldo em Plans & Billing e tente novamente."
  }

  if (lower.includes("invalid api key") || lower.includes("invalid_api_key")) {
    return `Chave de API invalida para ${provider}. Verifique a configuracao e tente novamente.`
  }

  if (lower.includes("not configured") || lower.includes("nao configurado")) {
    return `Provider ${provider} nao configurado no backend.`
  }

  return normalized || "Falha ao testar modelo"
}

function extractApiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") {
    return fallback
  }

  const detail = (error as { detail?: unknown }).detail

  if (typeof detail === "string" && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const firstError = detail[0]
    if (
      firstError &&
      typeof firstError === "object" &&
      "msg" in firstError &&
      typeof firstError.msg === "string" &&
      firstError.msg.trim()
    ) {
      return firstError.msg
    }
  }

  return fallback
}

// ── Hooks ─────────────────────────────────────────────────────────────

/** Lista todos os modelos disponíveis — staleTime 1h (igual ao cache Redis) */
export function useLLMModels() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["llm", "models"],
    queryFn: async (): Promise<ModelInfo[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/llm/models" as never)
      if (error) throw new Error("Falha ao carregar modelos LLM")
      return (data as ModelInfo[]) ?? []
    },
    staleTime: 60 * 60 * 1000, // 1h
    enabled: !!session?.accessToken,
    select: (models) => ({
      models,
      providers: [...new Set(models.map((m) => m.provider))],
      byProvider: models.reduce<Record<string, ModelInfo[]>>((acc, m) => {
        if (!acc[m.provider]) acc[m.provider] = []
        // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
        acc[m.provider]!.push(m)
        return acc
      }, {}),
    }),
  })
}

/** Providers configurados no backend */
export function useLLMProviders() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["llm", "providers"],
    queryFn: async (): Promise<LLMProviderInfo[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/llm/providers" as never)
      if (error) throw new Error("Falha ao carregar providers LLM")
      return (data as LLMProviderInfo[]) ?? []
    },
    staleTime: 60 * 60 * 1000,
    enabled: !!session?.accessToken,
    select: (providers) => ({
      providers: providers.map((p) => p.provider),
      details: providers,
    }),
  })
}

/** Mutation para forçar re-sincronização dos modelos (force_refresh=true) */
export function useSyncLLMModels() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<ModelInfo[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/llm/models?force_refresh=true" as never)
      if (error) throw new Error("Falha ao sincronizar modelos")
      return (data as ModelInfo[]) ?? []
    },
    onSuccess: (fresh) => {
      // Atualiza o cache local com os dados recém-buscados da API
      queryClient.setQueryData(["llm", "models"], fresh)
      void queryClient.invalidateQueries({ queryKey: ["llm", "providers"] })
    },
  })
}
export function useTestModel() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: TestModelParams): Promise<TestModelResult> => {
      try {
        const client = createBrowserClient(session?.accessToken)
        const { data, error } = await client.POST("/llm/test" as never, {
          body: params as never,
        })
        if (error) {
          throw new Error(
            humanizeTestModelError(
              extractApiErrorMessage(error, "Falha ao testar modelo"),
              params.provider,
            ),
          )
        }
        return data as TestModelResult
      } catch (error: unknown) {
        if (error instanceof Error) {
          const message = error.message.trim()
          if (message) {
            throw new Error(humanizeTestModelError(message, params.provider))
          }
        }

        throw new Error("Falha ao testar modelo")
      }
    },
    onSuccess: () => {
      // Invalida cache de provedores para refletir estado atualizado
      void queryClient.invalidateQueries({ queryKey: ["llm", "providers"] })
    },
  })
}
