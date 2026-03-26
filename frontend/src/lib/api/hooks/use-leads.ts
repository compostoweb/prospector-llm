"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface Lead {
  id: string
  tenant_id: string
  name: string
  first_name: string | null
  last_name: string | null
  job_title: string | null
  company: string | null
  company_domain: string | null
  website: string | null
  company_size: string | null
  industry: string | null
  linkedin_url: string | null
  linkedin_profile_id: string | null
  city: string | null
  location: string | null
  segment: string | null
  source: string
  status: "raw" | "enriched" | "in_cadence" | "converted" | "archived"
  score: number | null
  email_corporate: string | null
  email_corporate_source: string | null
  email_corporate_verified: boolean
  email_personal: string | null
  email_personal_source: string | null
  phone: string | null
  enriched_at: string | null
  notes: string | null
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
  use_voice: boolean
  day_offset: number
  scheduled_at: string
  sent_at: string | null
  message_content: string | null
  reply_content: string | null
  intent: string | null
}

export interface CreateLeadBody {
  name: string
  first_name?: string | null
  last_name?: string | null
  job_title?: string | null
  company?: string | null
  company_domain?: string | null
  website?: string | null
  industry?: string | null
  company_size?: string | null
  linkedin_url?: string | null
  city?: string | null
  location?: string | null
  segment?: string | null
  phone?: string | null
  email_corporate?: string | null
  email_personal?: string | null
  notes?: string | null
}

export interface ImportLeadItem {
  name: string
  first_name?: string | null
  last_name?: string | null
  job_title?: string | null
  company?: string | null
  company_domain?: string | null
  website?: string | null
  industry?: string | null
  company_size?: string | null
  linkedin_url?: string | null
  city?: string | null
  location?: string | null
  segment?: string | null
  phone?: string | null
  email_corporate?: string | null
  email_personal?: string | null
  notes?: string | null
}

export interface ImportLeadsResponse {
  imported: number
  duplicates: number
  errors: string[]
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

export function useCreateLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      body,
      enrich = false,
    }: {
      body: CreateLeadBody
      enrich?: boolean
    }): Promise<Lead> => {
      const client = createBrowserClient(session?.accessToken)
      const url = enrich ? "/leads?enrich=true" : "/leads"
      const { data, error } = await client.POST(url as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao criar lead")
      return data as Lead
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

export function useImportLeads() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (items: ImportLeadItem[]): Promise<ImportLeadsResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/leads/import" as never, {
        body: { items } as never,
      })
      if (error) throw new Error("Falha ao importar leads")
      return data as ImportLeadsResponse
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

export function useEnrollLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ leadId, cadenceId }: { leadId: string; cadenceId: string }) => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/leads/${leadId}/enroll` as never, {
        body: { cadence_id: cadenceId } as never,
      })
      if (error) throw new Error("Falha ao inscrever lead na cadência")
      return data as { enrolled: boolean; steps_created: number }
    },
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", vars.leadId] })
      void queryClient.invalidateQueries({
        queryKey: ["leads", vars.leadId, "steps"],
      })
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

// ── LinkedIn Search ───────────────────────────────────────────────────

export interface LinkedInSearchParams {
  keywords: string
  titles?: string[] | undefined
  companies?: string[] | undefined
  location_ids?: string[] | undefined
  industry_ids?: string[] | undefined
  network_distance?: number[] | undefined // [1, 2, 3]
  limit?: number | undefined
  cursor?: string | undefined
}

export interface LinkedInProfile {
  provider_id: string
  name: string
  headline: string | null
  company: string | null
  location: string | null
  profile_url: string | null
  profile_picture_url: string | null
  network_distance: number | null // 1=1º grau, 2=2º grau, 3=3º+
}

export interface LinkedInSearchResult {
  items: LinkedInProfile[]
  cursor: string | null
}

export interface LinkedInImportResult {
  created: number
  skipped: number
  lead_ids: string[]
}

export function useSearchLinkedIn() {
  const { data: session, status } = useSession()

  return useMutation({
    mutationFn: async (params: LinkedInSearchParams): Promise<LinkedInSearchResult> => {
      if (status !== "authenticated" || !session?.accessToken) {
        throw new Error("Sessão não disponível. Recarregue a página.")
      }
      const client = createBrowserClient(session.accessToken)
      const { data, error } = await client.POST("/leads/search-linkedin" as never, {
        body: params as never,
      })
      if (error) throw new Error("Falha na busca LinkedIn")
      return data as LinkedInSearchResult
    },
  })
}

export function useImportLinkedInProfiles() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      profiles,
      list_id,
    }: {
      profiles: LinkedInProfile[]
      list_id?: string
    }): Promise<LinkedInImportResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/leads/import-linkedin" as never, {
        body: { profiles, list_id: list_id ?? null } as never,
      })
      if (error) throw new Error("Falha ao importar leads do LinkedIn")
      return data as LinkedInImportResult
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

export interface LinkedInSearchParamItem {
  id: string
  title: string
}

/**
 * Busca todos os itens de LOCATION ou INDUSTRY disponíveis via Unipile.
 * O endpoint retorna uma lista estática (ignora query), então buscamos
 * uma única vez por tipo e filtramos no cliente.
 */
export function useLinkedInSearchParams(type: "LOCATION" | "INDUSTRY") {
  const { data: session } = useSession()

  return useQuery<LinkedInSearchParamItem[]>({
    queryKey: ["linkedin-search-params", type],
    queryFn: async () => {
      if (!session?.accessToken) return []
      const client = createBrowserClient(session.accessToken)
      const { data, error } = await client.GET("/leads/linkedin-search-params" as never, {
        params: { query: { type } } as never,
      })
      if (error) return []
      const result = data as { items: LinkedInSearchParamItem[] }
      return result.items ?? []
    },
    enabled: !!session?.accessToken,
    staleTime: 30 * 60 * 1000,
  })
}
