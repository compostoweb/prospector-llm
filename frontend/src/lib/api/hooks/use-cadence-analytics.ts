"use client"

import { useQueries, useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import type { CadenceStep } from "@/lib/api/hooks/use-cadences"

export interface CadenceAnalyticsChannel {
  channel: string
  sent: number
  replied: number
  pending: number
  skipped: number
  failed: number
  reply_rate: number
}

export interface CadenceAnalyticsStep {
  step_number: number
  channel: string
  sent: number
  replied: number
  pending: number
  skipped: number
  failed: number
  reply_rate: number
}

export interface CadenceAnalytics {
  cadence_id: string
  cadence_name: string
  cadence_type: "mixed" | "email_only"
  is_active: boolean
  total_leads: number
  leads_active: number
  steps_sent: number
  replies: number
  pending_steps: number
  skipped_steps: number
  failed_steps: number
  reply_rate: number
  channel_breakdown: CadenceAnalyticsChannel[]
  step_breakdown: CadenceAnalyticsStep[]
}

export interface CadenceOverview {
  cadence_id: string
  total_leads: number
  leads_active: number
  leads_converted: number
  leads_finished: number
  replies: number
  leads_paused: number
}

export interface CadenceABResult {
  subject: string
  sent: number
  opened: number
  open_rate: number
}

export interface CadenceABStepResult {
  stepNumber: number
  subjectVariants: string[]
  data: CadenceABResult[] | undefined
  isLoading: boolean
  isError: boolean
}

export interface CadenceDeliveryBudgetItem {
  channel: string
  scope_type: string
  scope_label: string
  configured_limit: number
  daily_budget: number
  used_today: number
  remaining_today: number
  usage_pct: number
}

export interface CadenceDeliveryBudget {
  cadence_id: string
  generated_at: string
  items: CadenceDeliveryBudgetItem[]
}

export function useCadenceAnalytics(cadenceId: string, days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "cadences", cadenceId, days],
    queryFn: async (): Promise<CadenceAnalytics> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(
        `/analytics/cadences/${cadenceId}?days=${days}` as never,
      )
      if (error) throw new Error("Falha ao carregar analytics da cadência")
      return data as CadenceAnalytics
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken && !!cadenceId,
  })
}

export function useCadenceABTestResults(
  cadenceId: string,
  stepsTemplate: CadenceStep[] | null | undefined,
  days = 30,
): CadenceABStepResult[] {
  const { data: session } = useSession()

  const abSteps = (stepsTemplate ?? []).flatMap((step, index) => {
    const subjectVariants =
      step.channel === "email"
        ? (step.subject_variants ?? [])
            .map((variant) => variant.trim())
            .filter((variant) => variant.length > 0)
        : []

    if (subjectVariants.length === 0) {
      return []
    }

    return [{ stepNumber: index + 1, subjectVariants }]
  })

  const queryResults = useQueries({
    queries: abSteps.map((step) => ({
      queryKey: ["analytics", "cadences", cadenceId, "ab-results", step.stepNumber, days],
      queryFn: async (): Promise<CadenceABResult[]> => {
        const client = createBrowserClient(session?.accessToken)
        const { data, error } = await client.GET(
          `/analytics/email/ab-results?cadence_id=${cadenceId}&step_number=${step.stepNumber}&days=${days}` as never,
        )
        if (error) throw new Error("Falha ao carregar resultados A/B da cadência")
        return (data as CadenceABResult[]) ?? []
      },
      staleTime: 5 * 60 * 1000,
      enabled: !!session?.accessToken && !!cadenceId,
    })),
  })

  return abSteps.map((step, index) => ({
    stepNumber: step.stepNumber,
    subjectVariants: step.subjectVariants,
    data: queryResults[index]?.data,
    isLoading: queryResults[index]?.isLoading ?? false,
    isError: queryResults[index]?.isError ?? false,
  }))
}

export function useCadenceOverview() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "cadences", "overview"],
    queryFn: async (): Promise<CadenceOverview[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/analytics/cadences" as never)
      if (error) throw new Error("Falha ao carregar resumo das cadências")
      return (data as CadenceOverview[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useCadenceDeliveryBudget(cadenceId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["cadences", cadenceId, "delivery-budget"],
    queryFn: async (): Promise<CadenceDeliveryBudget> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/cadences/${cadenceId}/delivery-budget` as never)
      if (error) throw new Error("Falha ao carregar limite operacional da cadência")
      return data as CadenceDeliveryBudget
    },
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
    enabled: !!session?.accessToken && !!cadenceId,
  })
}
