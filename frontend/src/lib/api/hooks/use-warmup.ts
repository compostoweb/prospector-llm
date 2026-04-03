"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface WarmupCampaign {
  id: string
  tenant_id: string
  email_account_id: string
  status: "active" | "paused" | "completed"
  current_day: number
  ramp_days: number
  daily_volume_start: number
  daily_volume_target: number
  total_sent: number
  total_replied: number
  spam_count: number
  created_at: string
  updated_at: string
}

export interface WarmupStats {
  campaign_id: string
  status: string
  current_day: number
  ramp_days: number
  progress_pct: number
  daily_volume_today: number
  daily_volume_target: number
  total_sent: number
  total_replied: number
  spam_count: number
  reply_rate_pct: number
  spam_rate_pct: number
  log_counts: Record<string, number>
}

export interface WarmupLog {
  id: string
  direction: "sent" | "received"
  status: "delivered" | "opened" | "replied" | "spam" | "failed"
  partner_email: string
  message_id_sent: string | null
  sent_at: string | null
  replied_at: string | null
}

export interface CreateWarmupBody {
  email_account_id: string
  daily_volume_start?: number
  daily_volume_target?: number
  ramp_days?: number
}

// ── Query hooks ───────────────────────────────────────────────────────

export function useWarmupCampaigns() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["warmup-campaigns"],
    queryFn: async (): Promise<WarmupCampaign[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/warmup" as never)
      if (error) throw new Error("Falha ao carregar campanhas de warmup")
      return (data as WarmupCampaign[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useWarmupStats(campaignId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["warmup-stats", campaignId],
    queryFn: async (): Promise<WarmupStats> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/warmup/${campaignId}/stats` as never)
      if (error) throw new Error("Falha ao carregar estatísticas")
      return data as WarmupStats
    },
    enabled: !!session?.accessToken && !!campaignId,
    refetchInterval: 5 * 60 * 1000,
  })
}

export function useWarmupLogs(campaignId: string | null, direction?: "sent" | "received") {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["warmup-logs", campaignId, direction],
    queryFn: async (): Promise<WarmupLog[]> => {
      const client = createBrowserClient(session?.accessToken)
      const params = new URLSearchParams()
      if (direction) params.set("direction", direction)
      params.set("limit", "100")
      const url = `/warmup/${campaignId}/logs?${params.toString()}`
      const { data, error } = await client.GET(url as never)
      if (error) throw new Error("Falha ao carregar logs")
      return (data as WarmupLog[]) ?? []
    },
    enabled: !!session?.accessToken && !!campaignId,
    staleTime: 2 * 60 * 1000,
  })
}

// ── Mutation hooks ────────────────────────────────────────────────────

export function useCreateWarmupCampaign() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateWarmupBody): Promise<WarmupCampaign> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/warmup" as never, {
        body: body as never,
      })
      if (error) {
        const msg = (error as { detail?: string }).detail ?? "Falha ao criar campanha"
        throw new Error(msg)
      }
      return data as WarmupCampaign
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["warmup-campaigns"] }),
  })
}

export function useStartWarmup() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (campaignId: string): Promise<WarmupCampaign> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/warmup/${campaignId}/start` as never)
      if (error) throw new Error("Falha ao iniciar campanha")
      return data as WarmupCampaign
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["warmup-campaigns"] }),
  })
}

export function usePauseWarmup() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (campaignId: string): Promise<WarmupCampaign> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/warmup/${campaignId}/pause` as never)
      if (error) throw new Error("Falha ao pausar campanha")
      return data as WarmupCampaign
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["warmup-campaigns"] }),
  })
}

export function useDeleteWarmupCampaign() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (campaignId: string): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/warmup/${campaignId}` as never)
      if (error) throw new Error("Falha ao remover campanha")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["warmup-campaigns"] }),
  })
}
