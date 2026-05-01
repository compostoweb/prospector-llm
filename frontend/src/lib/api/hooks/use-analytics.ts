"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import { buildAnalyticsQueryString, type AnalyticsRangeQuery } from "@/lib/analytics-period"

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
  total_leads: number
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

export interface LinkedInStats {
  connect_sent: number
  connect_accepted: number
  connect_acceptance_rate: number
  dm_sent: number
  dm_replied: number
  dm_reply_rate: number
}

export interface TeamUserAnalytics {
  user_id: string
  email: string
  name: string | null
  role: string
  is_active: boolean
  email_accounts: number
  linkedin_accounts: number
  reconnect_required_accounts: number
  steps_sent: number
  email_sent: number
  linkedin_sent: number
  manual_tasks_sent: number
  replies: number
  interested_replies: number
  reply_rate: number
  last_activity_at: string | null
}

export interface TeamAnalytics {
  users: TeamUserAnalytics[]
  total_users: number
  active_users: number
  steps_sent: number
  replies: number
  reply_rate: number
}

// ── Hooks ─────────────────────────────────────────────────────────────

export function useDashboardStats(range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "dashboard",
      "stats",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<DashboardStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/dashboard${query}` as never)
      if (error) throw new Error("Falha ao carregar estatísticas")
      return data as DashboardStats
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useChannelBreakdown(range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "analytics",
      "channels",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<ChannelBreakdown[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/channels${query}` as never)
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

export function useIntentBreakdown(range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "analytics",
      "intents",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<IntentBreakdown[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/intents${query}` as never)
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

export function useCadencePerformance(range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "analytics",
      "performance",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<CadencePerformance[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/performance${query}` as never)
      if (error) throw new Error("Falha ao carregar performance de cadências")
      return (data as CadencePerformance[]) ?? []
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailStats(range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "analytics",
      "email",
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
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useLinkedInStats(range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "analytics",
      "linkedin",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<LinkedInStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/linkedin/stats${query}` as never)
      if (error) throw new Error("Falha ao carregar estatísticas de LinkedIn")
      return data as LinkedInStats
    },
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useTeamAnalytics(range: AnalyticsRangeQuery = { days: 30 }) {
  const { data: session } = useSession()
  const query = buildAnalyticsQueryString(range)

  return useQuery({
    queryKey: [
      "analytics",
      "team",
      range.days ?? null,
      range.startDate ?? null,
      range.endDate ?? null,
    ],
    queryFn: async (): Promise<TeamAnalytics> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/analytics/team/users${query}` as never)
      if (error) throw new Error("Falha ao carregar métricas da equipe")
      return data as TeamAnalytics
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}
