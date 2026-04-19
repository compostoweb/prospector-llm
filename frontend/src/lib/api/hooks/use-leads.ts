"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import { env } from "@/env"

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
  emails: LeadEmail[]
  phone: string | null
  enriched_at: string | null
  notes: string | null
  lead_lists: Array<{
    id: string
    name: string
  }>
  active_cadence_count: number
  active_cadences: Array<{
    id: string
    name: string
  }>
  has_multiple_active_cadences: boolean
  origin_key: string
  origin_label: string
  origin_detail: string | null
  created_at: string
  updated_at: string
}

export interface LeadEmail {
  id: string
  email: string
  email_type: "corporate" | "personal" | "unknown"
  source: string | null
  verified: boolean
  is_primary: boolean
  created_at: string
  updated_at: string
}

export interface LeadEmailPayload {
  email: string
  email_type?: "corporate" | "personal" | "unknown"
  source?: string | null
  verified?: boolean
  is_primary?: boolean
}

export interface LeadMergeResponse {
  lead: Lead
  merged_lead_ids: string[]
}

export interface LeadStep {
  id: string
  lead_id: string
  cadence_id: string
  step_number: number
  channel: string
  status:
    | "pending"
    | "sent"
    | "replied"
    | "skipped"
    | "failed"
    | "content_generated"
    | "done_external"
  use_voice: boolean
  item_kind?: "cadence_step" | "manual_task"
  day_offset: number
  scheduled_at: string
  sent_at: string | null
  message_content: string | null
  reply_content: string | null
  intent: string | null
  manual_task_id?: string | null
  manual_task_type?: string | null
  manual_task_detail?: string | null
  notes?: string | null
}

export interface LeadInteraction {
  id: string
  lead_id: string
  tenant_id: string
  cadence_step_id: string | null
  channel: string
  direction: "outbound" | "inbound"
  content_text: string | null
  content_audio_url: string | null
  intent: string | null
  unipile_message_id: string | null
  email_message_id: string | null
  provider_thread_id: string | null
  reply_match_status: "matched" | "ambiguous" | "unmatched" | null
  reply_match_source:
    | "email_message_id"
    | "unipile_message_id"
    | "provider_thread_id"
    | "fallback_single_cadence"
    | null
  reply_match_sent_cadence_count: number | null
  opened: boolean
  created_at: string
}

export interface LeadInteractionListResponse {
  items: LeadInteraction[]
  total: number
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
  emails?: LeadEmailPayload[]
  notes?: string | null
}

export interface UpdateLeadBody {
  id: string
  name?: string
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
  emails?: LeadEmailPayload[]
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
  list_id: string | null
}

export interface GeneratedLeadPreviewItem {
  preview_id: string
  name: string
  first_name: string | null
  last_name: string | null
  job_title: string | null
  company: string | null
  company_domain: string | null
  website: string | null
  industry: string | null
  company_size: string | null
  linkedin_url: string | null
  linkedin_profile_id: string | null
  city: string | null
  location: string | null
  segment: string | null
  phone: string | null
  email_corporate: string | null
  email_personal: string | null
  notes: string | null
  source: string
  origin_key: string
  origin_label: string
}

export interface GenerateLeadsPreviewRequest {
  source: "google_maps" | "b2b_database" | "linkedin_enrichment"
  limit?: number
  search_terms?: string[]
  location_query?: string | null
  categories?: string[]
  job_titles?: string[]
  locations?: string[]
  cities?: string[]
  industries?: string[]
  company_keywords?: string[]
  company_sizes?: string[]
  email_status?: string[]
  linkedin_urls?: string[]
  negative_terms?: string[]
}

export interface GenerateLeadsPreviewResponse {
  source: string
  items: GeneratedLeadPreviewItem[]
  total: number
}

export interface GenerateLeadsImportRequest {
  source: "google_maps" | "b2b_database" | "linkedin_enrichment"
  items: GeneratedLeadPreviewItem[]
  list_id?: string | null
  create_list_name?: string | null
  merge_duplicates?: boolean
}

export interface GenerateLeadsImportResponse {
  created: number
  updated: number
  duplicates: number
  list_id: string | null
  lead_ids: string[]
}

export interface LeadListParams {
  page?: number
  page_size?: number
  status?: string
  source?: string
  cadence_id?: string
  list_id?: string
  segment?: string
  search?: string
  min_score?: number
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
      if (params.source) searchParams.set("source", params.source)
      if (params.cadence_id) searchParams.set("cadence_id", params.cadence_id)
      if (params.list_id) searchParams.set("list_id", params.list_id)
      if (params.segment) searchParams.set("segment", params.segment)
      if (params.search) searchParams.set("search", params.search)
      const minScore = params.min_score ?? params.score_min
      if (minScore != null) searchParams.set("min_score", String(minScore))
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

export function useLeadInteractions(leadId: string, pageSize = 50) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["leads", leadId, "interactions", pageSize],
    queryFn: async (): Promise<LeadInteractionListResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(
        `/leads/${leadId}/interactions?page=1&page_size=${pageSize}` as never,
      )
      if (error) throw new Error("Falha ao carregar auditoria de interações")
      return data as LeadInteractionListResponse
    },
    enabled: !!session?.accessToken && !!leadId,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useUpdateLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, ...body }: UpdateLeadBody) => {
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

export function usePermanentDeleteLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/leads/${id}/permanent` as never)
      if (error) throw new Error("Falha ao excluir lead definitivamente")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

export function useMergeLeads() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      primary_lead_id,
      secondary_lead_ids,
    }: {
      primary_lead_id: string
      secondary_lead_ids: string[]
    }): Promise<LeadMergeResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/leads/merge" as never, {
        body: { primary_lead_id, secondary_lead_ids } as never,
      })
      if (error) throw new Error("Falha ao mesclar leads")
      return data as LeadMergeResponse
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
      void queryClient.invalidateQueries({ queryKey: ["leads", result.lead.id] })
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

export interface ImportLeadsPayload {
  items: ImportLeadItem[]
  list_id?: string | null
  list_name?: string | null
}

export function useImportLeads() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ImportLeadsPayload): Promise<ImportLeadsResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/leads/import" as never, {
        body: payload as never,
      })
      if (error) throw new Error("Falha ao importar leads")
      return data as ImportLeadsResponse
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
      void queryClient.invalidateQueries({ queryKey: ["lead-lists"] })
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

export function useEnrichLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (leadId: string): Promise<{ status: string; lead_id: string }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/leads/${leadId}/enrich` as never)
      if (error) throw new Error("Falha ao iniciar enriquecimento")
      return data as { status: string; lead_id: string }
    },
    onSuccess: (_data, leadId) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", leadId] })
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

// ── LinkedIn Search ───────────────────────────────────────────────────

export interface LinkedInSearchParams {
  keywords: string
  titles?: string[] | undefined
  companies?: string[] | undefined
  company_ids?: string[] | undefined // IDs nativos (filtro COMPANY do LinkedIn)
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
  industry: string | null
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

export function useGenerateLeadsPreview() {
  const { data: session, status } = useSession()

  return useMutation({
    mutationFn: async (
      body: GenerateLeadsPreviewRequest,
    ): Promise<GenerateLeadsPreviewResponse> => {
      if (status !== "authenticated" || !session?.accessToken) {
        throw new Error("Sessão não disponível. Recarregue a página.")
      }
      const client = createBrowserClient(session.accessToken)
      const { data, error } = await client.POST("/leads/generate-preview" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao gerar preview de leads")
      return data as GenerateLeadsPreviewResponse
    },
  })
}

export function useGenerateLeadsImport() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: GenerateLeadsImportRequest): Promise<GenerateLeadsImportResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/leads/generate-import" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao importar leads gerados")
      return data as GenerateLeadsImportResponse
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
      void queryClient.invalidateQueries({ queryKey: ["lead-lists"] })
    },
  })
}

export interface LinkedInSearchParamItem {
  id: string
  title: string
}

/**
 * Busca todos os itens de LOCATION ou INDUSTRY disponíveis via Unipile.
 * Usa fetch direto (evita problemas de serialização do openapi-fetch com paths não tipados).
 */
export function useLinkedInSearchParams(type: "LOCATION" | "INDUSTRY") {
  const { data: session } = useSession()

  return useQuery<LinkedInSearchParamItem[]>({
    queryKey: ["linkedin-search-params", type],
    queryFn: async () => {
      if (!session?.accessToken) throw new Error("No session")
      const url = `${env.NEXT_PUBLIC_API_URL}/leads/linkedin-search-params?type=${encodeURIComponent(type)}`
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${session.accessToken}` },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = (await res.json()) as { items?: LinkedInSearchParamItem[] }
      return json.items ?? []
    },
    enabled: !!session?.accessToken,
    staleTime: 24 * 60 * 60 * 1000, // 24h — dados servidos do cache BD
    retry: 2,
  })
}

export interface LinkedInEnrichResult {
  provider_id: string
  company: string | null
}

/**
 * Enriquece uma lista de perfis LinkedIn com a empresa atual.
 * Faz POST /leads/linkedin-enrich-companies com os provider_ids.
 * Retorna um map provider_id → company_name.
 */
export function useLinkedInEnrichCompanies() {
  const { data: session } = useSession()

  return useMutation<Map<string, string>, Error, string[]>({
    mutationFn: async (providerIds: string[]) => {
      const map = new Map<string, string>()
      if (!session?.accessToken || providerIds.length === 0) return map
      const client = createBrowserClient(session.accessToken)
      const { data, error } = await client.POST("/leads/linkedin-enrich-companies" as never, {
        body: { provider_ids: providerIds } as never,
      })
      if (error) return map
      const result = data as { results: LinkedInEnrichResult[] }
      for (const r of result.results ?? []) {
        if (r.company) map.set(r.provider_id, r.company)
      }
      return map
    },
  })
}
