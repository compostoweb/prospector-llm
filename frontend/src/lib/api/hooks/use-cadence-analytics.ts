"use client"

import { useQueries, useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import { buildAnalyticsQueryString, type AnalyticsRangeQuery } from "@/lib/analytics-period"
import type { CadenceStep } from "@/lib/api/hooks/use-cadences"
import type { Lead } from "@/lib/api/hooks/use-leads"

export interface CadenceAnalyticsChannel {
  channel: string
  sent: number
  replied: number
  opened: number
  accepted: number
  pending: number
  skipped: number
  failed: number
  open_rate: number
  acceptance_rate: number
  reply_rate: number
}

export interface CadenceAnalyticsStep {
  step_number: number
  channel: string
  lead_count: number
  sent: number
  replied: number
  opened: number
  bounced: number
  accepted: number
  pending: number
  skipped: number
  failed: number
  open_rate: number
  acceptance_rate: number
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

export interface CadenceReplyEvent {
  interaction_id: string
  lead: Lead
  channel: string
  step_number: number | null
  replied_at: string
  intent: string | null
  reply_text: string | null
  reply_match_source: string | null
  pipedrive_sync_status: string | null
  pipedrive_person_id: number | null
  pipedrive_deal_id: number | null
  pipedrive_synced_at: string | null
  pipedrive_sync_error: string | null
}

export interface CadenceReplyAuditItem {
  interaction_id: string
  lead: Lead
  channel: string
  created_at: string
  reply_match_status: "ambiguous" | "unmatched" | "low_confidence"
  reply_match_source: string | null
  reply_match_sent_cadence_count: number | null
  content_text: string | null
  candidate_steps: CadenceReplyAuditCandidateStep[]
}

export interface CadenceReplyAuditCandidateStep {
  id: string
  cadence_id: string
  cadence_name: string | null
  step_number: number
  channel: string
  status: string
  scheduled_at: string
  sent_at: string | null
}

export interface CadenceReplyManagement {
  replies: CadenceReplyEvent[]
  audit_items: CadenceReplyAuditItem[]
}

export function useCadenceAnalytics(cadenceId: string, range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "analytics",
      "cadences",
      cadenceId,
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<CadenceAnalytics> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/cadences/${cadenceId}${query}` as never)
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
  range: AnalyticsRangeQuery = { days: 30 },
): CadenceABStepResult[] {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

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
      queryKey: [
        "analytics",
        "cadences",
        cadenceId,
        "ab-results",
        step.stepNumber,
        range.days ?? null,
        range.startDate ?? null,
        range.endDate ?? null,
      ],
      queryFn: async (): Promise<CadenceABResult[]> => {
        const client = createBrowserClient(session?.accessToken)
        const { data, error } = await client.GET(
          `/analytics/email/ab-results?cadence_id=${cadenceId}&step_number=${step.stepNumber}${query ? `&${query.slice(1)}` : ""}` as never,
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

export function useCadenceReplyManagement(cadenceId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["cadences", cadenceId, "reply-management"],
    queryFn: async (): Promise<CadenceReplyManagement> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/cadences/${cadenceId}/reply-management` as never)
      if (error) throw new Error("Falha ao carregar respostas da cadência")
      return data as CadenceReplyManagement
    },
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
    enabled: !!session?.accessToken && !!cadenceId,
  })
}
