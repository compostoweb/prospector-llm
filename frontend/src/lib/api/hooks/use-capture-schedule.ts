"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Types ──────────────────────────────────────────────────────────────

export type CaptureSource = "google_maps" | "b2b_database"

export interface CaptureScheduleConfig {
  id: string
  tenant_id: string
  source: CaptureSource
  is_active: boolean
  max_items: number

  maps_search_terms: string[] | null
  maps_location: string | null
  maps_locations: string[] | null
  maps_categories: string[] | null

  b2b_job_titles: string[] | null
  b2b_locations: string[] | null
  b2b_cities: string[] | null
  b2b_industries: string[] | null
  b2b_company_keywords: string[] | null
  b2b_company_sizes: string[] | null

  maps_combo_index: number
  b2b_rotation_index: number
  last_run_at: string | null
  last_list_id: string | null

  created_at: string
  updated_at: string
}

export interface CaptureScheduleUpsert {
  source: CaptureSource
  is_active?: boolean
  max_items?: number
  maps_search_terms?: string[]
  maps_location?: string | null
  maps_locations?: string[]
  maps_categories?: string[]
  b2b_job_titles?: string[]
  b2b_locations?: string[]
  b2b_cities?: string[]
  b2b_industries?: string[]
  b2b_company_keywords?: string[]
  b2b_company_sizes?: string[]
}

// ── Hooks ──────────────────────────────────────────────────────────────

export function useCaptureSchedules() {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined

  return useQuery<CaptureScheduleConfig[]>({
    queryKey: ["capture-schedules"],
    queryFn: async () => {
      if (!token) return []
      const client = createBrowserClient(token)
      const { data, error } = await client.GET("/capture-schedule" as never)
      if (error) throw new Error("Falha ao buscar capturas automáticas")
      return data as CaptureScheduleConfig[]
    },
    enabled: !!token,
  })
}

export function useCaptureSchedule(source: CaptureSource) {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined

  return useQuery<CaptureScheduleConfig | null>({
    queryKey: ["capture-schedule", source],
    queryFn: async () => {
      if (!token) return null
      const client = createBrowserClient(token)
      const { data, error } = await client.GET(`/capture-schedule/${source}` as never)
      if (error) return null
      return data as CaptureScheduleConfig
    },
    enabled: !!token,
    retry: false,
  })
}

export function useUpsertCaptureSchedule(source: CaptureSource) {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined
  const queryClient = useQueryClient()

  return useMutation<CaptureScheduleConfig, Error, CaptureScheduleUpsert>({
    mutationFn: async (payload) => {
      const client = createBrowserClient(token ?? "")
      const { data, error } = await client.PUT(
        `/capture-schedule/${source}` as never,
        {
          body: payload,
        } as never,
      )
      if (error) throw new Error("Falha ao salvar configuração")
      return data as CaptureScheduleConfig
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capture-schedule", source] })
      queryClient.invalidateQueries({ queryKey: ["capture-schedules"] })
    },
  })
}

export function useDeleteCaptureSchedule(source: CaptureSource) {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined
  const queryClient = useQueryClient()

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      const client = createBrowserClient(token ?? "")
      const { error } = await client.DELETE(`/capture-schedule/${source}` as never)
      if (error) throw new Error("Falha ao excluir automação")
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capture-schedule", source] })
      queryClient.invalidateQueries({ queryKey: ["capture-schedules"] })
    },
  })
}

export function useToggleCaptureSchedule(source: CaptureSource) {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined
  const queryClient = useQueryClient()

  return useMutation<CaptureScheduleConfig, Error, { config: CaptureScheduleConfig }>({
    mutationFn: async ({ config }) => {
      const client = createBrowserClient(token ?? "")
      const { data, error } = await client.PUT(
        `/capture-schedule/${source}` as never,
        {
          body: {
            source: config.source,
            is_active: !config.is_active,
            max_items: config.max_items,
            maps_search_terms: config.maps_search_terms ?? [],
            maps_location: config.maps_location,
            maps_locations: config.maps_locations ?? [],
            maps_categories: config.maps_categories ?? [],
            b2b_job_titles: config.b2b_job_titles ?? [],
            b2b_locations: config.b2b_locations ?? [],
            b2b_cities: config.b2b_cities ?? [],
            b2b_industries: config.b2b_industries ?? [],
            b2b_company_keywords: config.b2b_company_keywords ?? [],
            b2b_company_sizes: config.b2b_company_sizes ?? [],
          },
        } as never,
      )
      if (error) throw new Error("Falha ao alterar estado da captura")
      return data as CaptureScheduleConfig
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capture-schedule", source] })
      queryClient.invalidateQueries({ queryKey: ["capture-schedules"] })
    },
  })
}

// ── Execution history ──────────────────────────────────────────────────

export interface CaptureExecutionLog {
  id: string
  capture_config_id: string
  source: CaptureSource
  list_id: string | null
  list_name: string | null
  combo_label: string | null
  leads_received: number
  leads_inserted: number
  leads_skipped: number
  status: "success" | "failed"
  error_message: string | null
  executed_at: string
}

export function useCaptureExecutionHistory(source: CaptureSource | null) {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined

  return useQuery<CaptureExecutionLog[]>({
    queryKey: ["capture-execution-history", source],
    queryFn: async () => {
      if (!token || !source) return []
      const client = createBrowserClient(token)
      const { data, error } = await client.GET(`/capture-schedule/${source}/history` as never)
      if (error) throw new Error("Falha ao buscar histórico de execuções")
      return data as CaptureExecutionLog[]
    },
    enabled: !!token && !!source,
  })
}
