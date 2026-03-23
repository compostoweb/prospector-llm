"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface Lead {
  id: string
  tenant_id: string
  full_name: string
  first_name: string | null
  last_name: string | null
  email: string | null
  linkedin_url: string | null
  job_title: string | null
  company_name: string | null
  company_domain: string | null
  company_size: string | null
  industry: string | null
  location: string | null
  score: number
  status: "raw" | "enriched" | "in_cadence" | "converted" | "archived"
  last_intent: string | null
  current_cadence_id: string | null
  created_at: string
  updated_at: string
}

export interface LeadStep {
  id: string
  lead_id: string
  cadence_id: string
  step_number: number
  channel: string
  status: "pending" | "sent" | "replied" | "skipped" | "failed"
  sent_at: string | null
  replied_at: string | null
  message_content: string | null
  reply_content: string | null
  intent: string | null
  created_at: string
}

export interface LeadListParams {
  page?: number
  page_size?: number
  status?: string
  cadence_id?: string
  search?: string
  score_min?: number
  score_max?: number
}

export interface PaginatedLeads {
  items: Lead[]
  total: number
  page: number
  page_size: number
  pages: number
}

// ── Hooks de query ────────────────────────────────────────────────────

export function useLeads(params: LeadListParams = {}) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["leads", params],
    queryFn: async (): Promise<PaginatedLeads> => {
      const client = createBrowserClient(session?.accessToken)
      const searchParams = new URLSearchParams()
      if (params.page) searchParams.set("page", String(params.page))
      if (params.page_size) searchParams.set("page_size", String(params.page_size))
      if (params.status) searchParams.set("status", params.status)
      if (params.cadence_id) searchParams.set("cadence_id", params.cadence_id)
      if (params.search) searchParams.set("search", params.search)
      if (params.score_min != null) searchParams.set("score_min", String(params.score_min))
      if (params.score_max != null) searchParams.set("score_max", String(params.score_max))

      const url = `/leads?${searchParams.toString()}` as never
      const { data, error } = await client.GET(url)
      if (error) throw new Error("Falha ao carregar leads")
      return data as PaginatedLeads
    },
    staleTime: 30 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useLead(id: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["leads", id],
    queryFn: async (): Promise<Lead> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/leads/${id}` as never)
      if (error) throw new Error("Falha ao carregar lead")
      return data as Lead
    },
    enabled: !!session?.accessToken && !!id,
  })
}

export function useLeadSteps(leadId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["leads", leadId, "steps"],
    queryFn: async (): Promise<LeadStep[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/leads/${leadId}/steps` as never)
      if (error) throw new Error("Falha ao carregar histórico do lead")
      return (data as LeadStep[]) ?? []
    },
    enabled: !!session?.accessToken && !!leadId,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useUpdateLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, ...body }: Partial<Lead> & { id: string }) => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/leads/${id}` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao atualizar lead")
      return data as Lead
    },
    onSuccess: (lead) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", lead.id] })
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

export function useArchiveLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/leads/${id}` as never)
      if (error) throw new Error("Falha ao arquivar lead")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}
