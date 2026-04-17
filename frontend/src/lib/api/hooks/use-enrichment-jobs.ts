"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ──────────────────────────────────────────────────────────────

export type EnrichmentJobStatus = "pending" | "running" | "done" | "failed"

export interface EnrichmentJob {
  id: string
  tenant_id: string
  target_list_id: string | null
  target_list_name: string | null
  total_count: number
  processed_count: number
  batch_size: number
  status: EnrichmentJobStatus
  progress_pct: number
  remaining_count: number
  batches_remaining: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface EnrichmentJobCreate {
  linkedin_urls: string[]
  batch_size?: number
  target_list_id?: string | null
  target_list_name?: string | null
}

// ── Chaves de query ────────────────────────────────────────────────────

export const enrichmentJobKeys = {
  all: ["enrichment-jobs"] as const,
  detail: (id: string) => ["enrichment-jobs", id] as const,
}

function getAuthorizedClient(token?: string) {
  if (!token) {
    throw new Error("Sessão expirada. Faça login novamente.")
  }
  return createBrowserClient(token)
}

// ── Hooks ──────────────────────────────────────────────────────────────

export function useEnrichmentJobs() {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined

  return useQuery<EnrichmentJob[]>({
    queryKey: enrichmentJobKeys.all,
    enabled: !!token,
    queryFn: async () => {
      const client = getAuthorizedClient(token)
      const res = await client.GET("/enrichment-jobs" as never)
      if (res.error) throw res.error
      return (res.data as EnrichmentJob[]) ?? []
    },
    refetchInterval: (query) => {
      // Polling automático enquanto houver job pendente ou rodando
      const jobs = query.state.data as EnrichmentJob[] | undefined
      const hasActive = jobs?.some((j) => j.status === "pending" || j.status === "running")
      return hasActive ? 30_000 : false
    },
  })
}

export function useCreateEnrichmentJob() {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined
  const qc = useQueryClient()

  return useMutation<EnrichmentJob, Error, EnrichmentJobCreate>({
    mutationFn: async (payload) => {
      const client = getAuthorizedClient(token)
      const res = await client.POST("/enrichment-jobs" as never, {
        body: payload as never,
      })
      if (res.error) throw res.error
      return res.data as EnrichmentJob
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: enrichmentJobKeys.all })
    },
  })
}

export function useDeleteEnrichmentJob() {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined
  const qc = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: async (jobId) => {
      const client = getAuthorizedClient(token)
      const res = await client.DELETE(`/enrichment-jobs/${jobId}` as never)
      if (res.error) throw res.error
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: enrichmentJobKeys.all })
    },
  })
}
