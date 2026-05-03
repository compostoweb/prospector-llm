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
  body_markdown: string | null
  body_html: string | null
  sections_payload: NewsletterFullPayload | Record<string, unknown> | null
  cover_image_url: string | null
  cover_image_s3_key: string | null
  status: NewsletterStatus
  scheduled_for: string | null
  published_at: string | null
  linkedin_pulse_url: string | null
  derived_article_id: string | null
  last_reminder_sent_at: string | null
  created_by: string | null
  notion_page_id: string | null
  pulse_views_count: number | null
  pulse_reactions_count: number | null
  pulse_comments_count: number | null
  pulse_reposts_count: number | null
  deleted_at: string | null
  created_at: string
  updated_at: string
}

export interface NewsletterCreateInput {
  title: string
  subtitle?: string | null
  body_markdown?: string | null
  body_html?: string | null
  sections_payload?: Record<string, unknown> | null
  cover_image_url?: string | null
  cover_image_s3_key?: string | null
  scheduled_for?: string | null
}

export interface NewsletterUpdateInput {
  title?: string
  subtitle?: string | null
  body_markdown?: string | null
  body_html?: string | null
  sections_payload?: Record<string, unknown> | null
  scheduled_for?: string | null
  status?: NewsletterStatus
  linkedin_pulse_url?: string | null
  pulse_views_count?: number | null
  pulse_reactions_count?: number | null
  pulse_comments_count?: number | null
  pulse_reposts_count?: number | null
}

export interface NewsletterGenerateCoverInput {
  prompt?: string | null
  style?: "clean" | "with_text" | "infographic"
  visual_direction?: string
  aspect_ratio?: "4:5" | "1:1" | "16:9"
  image_size?: "512" | "1K" | "2K" | "4K"
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

export function useGenerateNewsletterCover() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, input }: { id: string; input: NewsletterGenerateCoverInput }) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/generate-cover`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(input),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao gerar capa com IA")
      return res.json() as Promise<ContentNewsletter>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: newsletterKeys.all })
      toast.success("Capa gerada com IA")
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
      linkedin_pulse_url,
      create_derived_article,
      published_at,
    }: {
      id: string
      linkedin_pulse_url: string
      create_derived_article?: boolean
      published_at?: string | null
    }) => {
      const res = await fetch(`${apiBase()}/api/content/newsletters/${id}/mark-published`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify({
          linkedin_pulse_url,
          create_derived_article: create_derived_article ?? true,
          ...(published_at ? { published_at } : {}),
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

// ── Notion Newsletter Import ──────────────────────────────────────────

export interface NotionNewsletterPreview {
  page_id: string
  title: string
  subtitle: string | null
  edition_number: number | null
  status_notion: string | null
  scheduled_for: string | null
  body_preview: string
  already_imported: boolean
}

export interface NotionNewsletterImportResult {
  imported: number
  skipped: number
  failed: number
  newsletter_ids: string[]
}

export function useNotionNewsletterPreview(enabled: boolean) {
  const { data: session } = useSession()
  return useQuery({
    queryKey: ["notion", "newsletter-preview"],
    queryFn: async () => {
      const res = await fetch(
        `${apiBase()}/api/content/notion/newsletter-preview`,
        { headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` } },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(
          (err as { detail?: string }).detail ?? "Erro ao buscar newsletters do Notion",
        )
      }
      return res.json() as Promise<NotionNewsletterPreview[]>
    },
    enabled: enabled && !!session?.accessToken,
    staleTime: 0,
  })
}

export function useImportNewslettersFromNotion() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (pageIds: string[]) => {
      const res = await fetch(`${apiBase()}/api/content/notion/newsletter-import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify({ page_ids: pageIds }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(
          (err as { detail?: string }).detail ?? "Erro ao importar newsletters do Notion",
        )
      }
      return res.json() as Promise<NotionNewsletterImportResult>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: newsletterKeys.all }),
  })
}
