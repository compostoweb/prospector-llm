"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface DashboardStats {
  leads_total: number
  leads_in_cadence: number
  leads_converted: number
  steps_sent_today: number
  steps_sent_week: number
  replies_today: number
  replies_week: number
  conversion_rate: number
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

// ── Hooks ─────────────────────────────────────────────────────────────

export function useDashboardStats() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: async (): Promise<DashboardStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/analytics/dashboard" as never)
      if (error) throw new Error("Falha ao carregar estatísticas")
      return data as DashboardStats
    },
    staleTime: 60 * 1000, // 1min
    refetchInterval: 5 * 60 * 1000, // revalida a cada 5min
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
    enabled: !!session?.accessToken,
  })
}
