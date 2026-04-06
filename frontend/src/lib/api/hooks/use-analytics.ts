"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface DashboardStats {
  leads_total: number
  leads_in_cadence: number
  leads_converted: number
  leads_archived: number
  steps_sent_today: number
  steps_sent_week: number
  steps_sent_period: number
  replies_today: number
  replies_week: number
  replies_period: number
  conversion_rate: number
  leads_total_trend: number
  leads_in_cadence_trend: number
  leads_converted_trend: number
  steps_sent_trend: number
  replies_trend: number
}

export interface ChannelBreakdown {
  channel: string
  steps_sent: number
  replies: number
  reply_rate: number
}

export interface RecentReply {
  lead_id: string
  lead_name: string
  company_name: string | null
  intent: string
  replied_at: string
  channel: string
}

export interface IntentBreakdown {
  intent: string
  count: number
  percentage: number
}

export interface FunnelItem {
  status: string
  count: number
  percentage: number
}

export interface CadencePerformance {
  cadence_id: string
  cadence_name: string
  leads_active: number
  steps_sent: number
  replies: number
  reply_rate: number
}

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

// ── Hooks ─────────────────────────────────────────────────────────────

export function useDashboardStats(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["dashboard", "stats", days],
    queryFn: async (): Promise<DashboardStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/dashboard?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar estatísticas")
      return data as DashboardStats
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useChannelBreakdown(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "channels", days],
    queryFn: async (): Promise<ChannelBreakdown[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/channels?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar breakdown de canais")
      return (data as ChannelBreakdown[]) ?? []
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useRecentReplies(limit = 10) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "recent-replies", limit],
    queryFn: async (): Promise<RecentReply[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/recent-replies?limit=${limit}` as never)
      if (error) throw new Error("Falha ao carregar respostas recentes")
      return (data as RecentReply[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useIntentBreakdown(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "intents", days],
    queryFn: async (): Promise<IntentBreakdown[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/intents?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar breakdown de intenções")
      return (data as IntentBreakdown[]) ?? []
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useFunnel() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "funnel"],
    queryFn: async (): Promise<FunnelItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/analytics/funnel" as never)
      if (error) throw new Error("Falha ao carregar funil")
      return (data as FunnelItem[]) ?? []
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useCadencePerformance(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "performance", days],
    queryFn: async (): Promise<CadencePerformance[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/performance?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar performance de cadências")
      return (data as CadencePerformance[]) ?? []
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailStats(days = 30) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["analytics", "email", days],
    queryFn: async (): Promise<EmailStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/email/stats?days=${days}` as never)
      if (error) throw new Error("Falha ao carregar estatísticas de e-mail")
      return data as EmailStats
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}
