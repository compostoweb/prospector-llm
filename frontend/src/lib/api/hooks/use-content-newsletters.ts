"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { toast } from "sonner"

// ── Types ─────────────────────────────────────────────────────────────

export type NewsletterStatus =
  | "draft"
  | "validated"
  | "approved"
  | "scheduled"
  | "published"
  | "failed"
  | "deleted"

export interface NewsletterSectionTemaQuinzena {
  hook: string
  body_md: string
}
export interface NewsletterSectionVisao {
  body_md: string
}
export interface NewsletterSectionTutorial {
  steps: string[]
}
export interface NewsletterRadarToolItem {
  name: string
  what: string
  when: string
  limitation: string
}
export interface NewsletterRadarDataItem {
  fact: string
  source_label: string
  source_url: string
}
export interface NewsletterSectionRadar {
  intro: string
  tools: NewsletterRadarToolItem[]
  data: NewsletterRadarDataItem[]
}
export interface NewsletterSectionPergunta {
  body_md: string
}

export interface NewsletterFullPayload {
  edition_number: number
  title: string
  subtitle: string
  central_theme: string
  read_time_min: number
  tema_quinzena: NewsletterSectionTemaQuinzena
  visao_opiniao: NewsletterSectionVisao
  mini_tutorial: NewsletterSectionTutorial
  radar: NewsletterSectionRadar
  pergunta_quinzena: NewsletterSectionPergunta
  word_count: number | null
  violations: string[] | null
}

export interface ContentNewsletter {
  id: string
  tenant_id: string
  edition_number: number
  title: string
  subtitle: string | null
  central_theme: string | null
  status: NewsletterStatus
  payload: NewsletterFullPayload | null
  cover_url: string | null
  cover_s3_key: string | null
  read_time_min: number | null
  word_count: number | null
  scheduled_for: string | null
  published_at: string | null
  published_url: string | null
  derived_article_id: string | null
  last_reminder_sent_at: string | null
  llm_provider: string | null
  llm_model: string | null
  llm_temperature: number | null
  generation_violations: string[] | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface NewsletterCreateInput {
  edition_number?: number | null
  title: string
  subtitle?: string | null
  central_theme?: string | null
  payload?: NewsletterFullPayload | null
  cover_url?: string | null
  cover_s3_key?: string | null
  scheduled_for?: string | null
}

export interface NewsletterUpdateInput {
  title?: string
  subtitle?: string | null
  central_theme?: string | null
  payload?: NewsletterFullPayload | null
  scheduled_for?: string | null
  status?: NewsletterStatus
}

export interface NewsletterGenerateDraftInput {
  central_theme?: string | null
  edition_number?: number | null
  provider?: string | null
  model?: string | null
  temperature?: number | null
}

export interface NewsletterImproveSectionInput {
  section: string
  instruction: string
  current_content: string
  provider?: string | null
  model?: string | null
}

export interface NewsletterBanksPayload {
  themes_central: string[]
  vision_themes: string[]
  tutorials: string[]
  tools: { name: string; what: string; when: string; limitation: string }[]
  data_points: { fact: string; source_label: string; source_url: string }[]
  opening_templates: string[]
  forbidden_words: string[]
  link_whitelist: string[]
}

// ── Query Keys ────────────────────────────────────────────────────────

export const newsletterKeys = {
  all: ["content-newsletters"] as const,
  list: (filters?: Record<string, string | undefined>) =>
    [...newsletterKeys.all, "list", filters] as const,
  one: (id: string) => [...newsletterKeys.all, id] as const,
  banks: () => [...newsletterKeys.all, "banks"] as const,
}

const apiBase = () => process.env.NEXT_PUBLIC_API_URL ?? ""

async function buildApiError(res: Response, fallback: string): Promise<Error> {
  const payload = (await res.json().catch(() => null)) as { detail?: string } | null
  return new Error(payload?.detail ?? fallback)
}

// ── Queries ───────────────────────────────────────────────────────────

export function useContentNewsletters(filters?: {
  status?: NewsletterStatus
  include_deleted?: boolean
}) {
  const { data: session } = useSession()
  return useQuery({
    queryKey: newsletterKeys.list(
      filters
        ? {
            status: filters.status,
            include_deleted: filters.include_deleted ? "1" : undefined,
          }
        : undefined,
    ),
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (filters?.status) params["status"] = filters.status
      if (filters?.include_deleted) params["include_deleted"] = "true"
      const qs = new URLSearchParams(params).toString()
      const res = await fetch(`${apiBase()}/api/content/newsletters${qs ? `?${qs}` : ""}`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao listar newsletters")
      return res.json() as Promise<ContentNewsletter[]>
    },
    enabled: !!session?.accessToken,
  })
}

export function useContentNewsletter(id: string | null) {
  const { data: session } = useSession()
  return useQuery({
    queryKey: newsletterKeys.one(id ?? ""),
    queryFn: async () => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao buscar newsletter")
      return res.json() as Promise<ContentNewsletter>
    },
    enabled: !!session?.accessToken && !!id,
  })
}

export function useNewsletterBanks() {
  const { data: session } = useSession()
  return useQuery({
    queryKey: newsletterKeys.banks(),
    queryFn: async () => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/banks`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao buscar bancos")
      return res.json() as Promise<NewsletterBanksPayload>
    },
    enabled: !!session?.accessToken,
    staleTime: 60 * 60 * 1000,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useCreateNewsletter() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: NewsletterCreateInput) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao criar newsletter")
      return res.json() as Promise<ContentNewsletter>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: newsletterKeys.all })
      toast.success("Newsletter criada")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateNewsletter() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: NewsletterUpdateInput }) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao atualizar")
      return res.json() as Promise<ContentNewsletter>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: newsletterKeys.all })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteNewsletter() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok && res.status !== 204) throw await buildApiError(res, "Erro ao deletar")
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: newsletterKeys.all })
      toast.success("Newsletter movida para lixeira")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useGenerateNewsletterDraft() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, input }: { id: string; input: NewsletterGenerateDraftInput }) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/generate-draft`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(input),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao gerar rascunho")
      return res.json() as Promise<ContentNewsletter>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: newsletterKeys.all })
      toast.success("Rascunho gerado")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useImproveNewsletterSection() {
  const { data: session } = useSession()
  return useMutation({
    mutationFn: async ({ id, input }: { id: string; input: NewsletterImproveSectionInput }) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/improve-section`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(input),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao melhorar")
      return res.json() as Promise<{ improved_content: string }>
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUploadNewsletterCover() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const fd = new FormData()
      fd.append("file", file)
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/upload-cover`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        body: fd,
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao subir capa")
      return res.json() as Promise<ContentNewsletter>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: newsletterKeys.all })
      toast.success("Capa atualizada")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useScheduleNewsletter() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, scheduled_for }: { id: string; scheduled_for: string }) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/schedule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify({ scheduled_for }),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao agendar")
      return res.json() as Promise<ContentNewsletter>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: newsletterKeys.all })
      toast.success("Newsletter agendada")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useMarkNewsletterPublished() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      published_url,
      create_article,
    }: {
      id: string
      published_url?: string | null
      create_article?: boolean
    }) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/mark-published`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify({
          published_url: published_url ?? null,
          create_article: create_article ?? true,
        }),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao marcar publicado")
      return res.json() as Promise<ContentNewsletter>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["content-newsletters"] })
      qc.invalidateQueries({ queryKey: ["content-articles"] })
      toast.success("Newsletter marcada como publicada")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export async function exportNewsletter(
  id: string,
  format: "markdown" | "html",
  accessToken: string,
): Promise<string> {
  const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/export?format=${format}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) throw new Error("Erro ao exportar")
  return res.text()
}
