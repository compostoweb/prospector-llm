"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

export type LLMUsageGranularity = "hour" | "day" | "week" | "month"
export type LLMUsageBreakdownDimension = "module" | "task_type" | "provider" | "model" | "feature"

export interface LLMUsageSummary {
  requests: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  estimated_cost_usd: number
  avg_input_tokens_per_request: number
  avg_output_tokens_per_request: number
  avg_total_tokens_per_request: number
}

export interface LLMUsageTimeSeriesPoint {
  bucket_start: string
  requests: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  estimated_cost_usd: number
}

export interface LLMUsageComparison {
  current: LLMUsageSummary
  previous: LLMUsageSummary
  requests_change_pct: number | null
  total_tokens_change_pct: number | null
  estimated_cost_change_pct: number | null
  avg_output_tokens_change_pct: number | null
}

export interface LLMUsageBreakdownItem {
  key: string
  label: string
  provider: string | null
  requests: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  estimated_cost_usd: number
}

export interface LLMUsageFilters {
  provider?: string | undefined
  model?: string | undefined
  endAt?: string | undefined
}

function buildAnalyticsQuery(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue
    query.set(key, String(value))
  }
  return query.toString()
}

export function useLLMUsageSummary(days = 30, filters: LLMUsageFilters = {}) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "llm", "summary", days, filters.provider, filters.model],
    queryFn: async (): Promise<LLMUsageSummary> => {
      const client = createBrowserClient(session?.accessToken)
      const query = buildAnalyticsQuery({
        days,
        provider: filters.provider,
        model: filters.model,
      })
      const { data, error } = await client.GET(`/analytics/llm/summary?${query}` as never)
      if (error) throw new Error("Falha ao carregar resumo de consumo LLM")
      return data as LLMUsageSummary
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useLLMUsageTimeSeries(
  days = 30,
  granularity: LLMUsageGranularity = "day",
  filters: LLMUsageFilters = {},
) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: [
      "analytics",
      "llm",
      "timeseries",
      days,
      granularity,
      filters.provider,
      filters.model,
      filters.endAt,
    ],
    queryFn: async (): Promise<LLMUsageTimeSeriesPoint[]> => {
      const client = createBrowserClient(session?.accessToken)
      const query = buildAnalyticsQuery({
        days,
        granularity,
        provider: filters.provider,
        model: filters.model,
        end_at: filters.endAt,
      })
      const { data, error } = await client.GET(`/analytics/llm/timeseries?${query}` as never)
      if (error) throw new Error("Falha ao carregar série temporal de LLM")
      return (data as LLMUsageTimeSeriesPoint[]) ?? []
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useLLMUsageBreakdown(
  dimension: LLMUsageBreakdownDimension,
  days = 30,
  limit = 8,
  filters: LLMUsageFilters = {},
) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: [
      "analytics",
      "llm",
      "breakdown",
      dimension,
      days,
      limit,
      filters.provider,
      filters.model,
    ],
    queryFn: async (): Promise<LLMUsageBreakdownItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const query = buildAnalyticsQuery({
        days,
        dimension,
        limit,
        provider: filters.provider,
        model: filters.model,
      })
      const { data, error } = await client.GET(`/analytics/llm/breakdown?${query}` as never)
      if (error) throw new Error("Falha ao carregar breakdown de consumo LLM")
      return (data as LLMUsageBreakdownItem[]) ?? []
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useLLMUsageComparison(days = 30, filters: LLMUsageFilters = {}) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "llm", "comparison", days, filters.provider, filters.model],
    queryFn: async (): Promise<LLMUsageComparison> => {
      const client = createBrowserClient(session?.accessToken)
      const query = buildAnalyticsQuery({
        days,
        provider: filters.provider,
        model: filters.model,
      })
      const { data, error } = await client.GET(`/analytics/llm/comparison?${query}` as never)
      if (error) throw new Error("Falha ao carregar comparação de consumo LLM")
      return data as LLMUsageComparison
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}
