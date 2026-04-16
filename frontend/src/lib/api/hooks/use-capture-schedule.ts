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
  maps_categories: string[] | null

  b2b_job_titles: string[] | null
  b2b_locations: string[] | null
  b2b_cities: string[] | null
  b2b_industries: string[] | null
  b2b_company_keywords: string[] | null
  b2b_company_sizes: string[] | null

  created_at: string
  updated_at: string
}

export interface CaptureScheduleUpsert {
  source: CaptureSource
  is_active?: boolean
  max_items?: number
  maps_search_terms?: string[]
  maps_location?: string | null
  maps_categories?: string[]
  b2b_job_titles?: string[]
  b2b_locations?: string[]
  b2b_cities?: string[]
  b2b_industries?: string[]
  b2b_company_keywords?: string[]
  b2b_company_sizes?: string[]
}

// ── Hooks ──────────────────────────────────────────────────────────────

export function useCaptureSchedule(source: CaptureSource) {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined

  return useQuery<CaptureScheduleConfig | null>({
    queryKey: ["capture-schedule", source],
    queryFn: async () => {
      if (!token) return null
      const client = createBrowserClient(token)
      const res = await client.get(`/capture-schedule/${source}`)
      if (res.status === 404) return null
      return res.data as CaptureScheduleConfig
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
      const client = createBrowserClient(token!)
      const res = await client.put(`/capture-schedule/${source}`, payload)
      return res.data as CaptureScheduleConfig
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capture-schedule", source] })
    },
  })
}

export function useDisableCaptureSchedule(source: CaptureSource) {
  const { data: session } = useSession()
  const token = session?.accessToken as string | undefined
  const queryClient = useQueryClient()

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      const client = createBrowserClient(token!)
      await client.delete(`/capture-schedule/${source}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capture-schedule", source] })
    },
  })
}
