"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

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

// ── Hooks ─────────────────────────────────────────────────────────────

export function useEmailStats(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-analytics", "stats", days],
    queryFn: async (): Promise<EmailStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/email/stats?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar estatísticas de e-mail")
      return data as EmailStats
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailCadences(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-analytics", "cadences", days],
    queryFn: async (): Promise<EmailCadenceItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/email/cadences?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar cadências de e-mail")
      return (data as EmailCadenceItem[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailOverTime(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-analytics", "over-time", days],
    queryFn: async (): Promise<EmailOverTimeItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/email/over-time?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar série temporal")
      return (data as EmailOverTimeItem[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailABResults(cadenceId: string, stepNumber: number) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-analytics", "ab-results", cadenceId, stepNumber],
    queryFn: async (): Promise<EmailABResultItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(
        `/analytics/email/ab-results?cadence_id=${cadenceId}&step_number=${stepNumber}` as never,
      )
      if (error) throw new Error("Falha ao carregar resultados A/B")
      return (data as EmailABResultItem[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken && !!cadenceId && stepNumber > 0,
  })
}
