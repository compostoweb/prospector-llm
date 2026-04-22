"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import {
  buildAnalyticsQueryString,
  type AnalyticsRangeQuery,
} from "@/lib/analytics-period"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface EmailStats {
  sent: number
  opened: number
  replied: number
  unsubscribed: number
  bounced: number
  open_rate: number
  reply_rate: number
  bounce_rate: number
  unsubscribe_rate: number
}

export interface EmailCadenceItem {
  cadence_id: string
  cadence_name: string
  sent: number
  opened: number
  replied: number
  bounced: number
  open_rate: number
  reply_rate: number
}

export interface EmailOverTimeItem {
  date: string
  sent: number
  opened: number
  replied: number
}

export interface EmailABResultItem {
  subject: string
  sent: number
  opened: number
  open_rate: number
}

export type EmailAnalyticsRange = AnalyticsRangeQuery

// ── Hooks ─────────────────────────────────────────────────────────────

export function useEmailStats(range: EmailAnalyticsRange = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "email-analytics",
      "stats",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<EmailStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/email/stats${query}` as never)
      if (error) throw new Error("Falha ao carregar estatísticas de e-mail")
      return data as EmailStats
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailCadences(range: EmailAnalyticsRange = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "email-analytics",
      "cadences",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<EmailCadenceItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/email/cadences${query}` as never)
      if (error) throw new Error("Falha ao carregar cadências de e-mail")
      return (data as EmailCadenceItem[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailOverTime(range: EmailAnalyticsRange = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "email-analytics",
      "over-time",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<EmailOverTimeItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/email/over-time${query}` as never)
      if (error) throw new Error("Falha ao carregar série temporal")
      return (data as EmailOverTimeItem[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailABResults(
  cadenceId: string,
  stepNumber: number,
  range: EmailAnalyticsRange = { days: 30 },
) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "email-analytics",
      "ab-results",
      cadenceId,
      stepNumber,
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<EmailABResultItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(
        `/analytics/email/ab-results?cadence_id=${cadenceId}&step_number=${stepNumber}${query ? `&${query.slice(1)}` : ""}` as never,
      )
      if (error) throw new Error("Falha ao carregar resultados A/B")
      return (data as EmailABResultItem[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken && !!cadenceId && stepNumber > 0,
  })
}
