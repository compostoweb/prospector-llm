"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { toast } from "sonner"

export type ArticleStatus =
  | "draft"
  | "approved"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed"
  | "deleted"

export interface ContentArticle {
  id: string
  tenant_id: string
  source_url: string
  title: string
  description: string | null
  thumbnail_url: string | null
  thumbnail_s3_key: string | null
  linkedin_image_urn: string | null
  commentary: string | null
  status: ArticleStatus
  scheduled_for: string | null
  published_at: string | null
  linkedin_post_urn: string | null
  source_newsletter_id: string | null
  auto_scraped: boolean
  first_comment_text: string | null
  first_comment_status: string | null
  first_comment_urn: string | null
  first_comment_posted_at: string | null
  first_comment_error: string | null
  impressions: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number | null
  metrics_updated_at: string | null
  error_message: string | null
  processing_at: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface ArticleCreateInput {
  source_url: string
  title: string
  description?: string | null
  thumbnail_url?: string | null
  thumbnail_s3_key?: string | null
  commentary?: string | null
  scheduled_for?: string | null
  source_newsletter_id?: string | null
  auto_scraped?: boolean
  first_comment_text?: string | null
}

export interface ArticleUpdateInput {
  title?: string
  description?: string | null
  thumbnail_url?: string | null
  commentary?: string | null
  scheduled_for?: string | null
  first_comment_text?: string | null
}

export interface ArticleScrapeResponse {
  title: string | null
  description: string | null
  thumbnail_url: string | null
  cached: boolean
}

export const articleKeys = {
  all: ["content-articles"] as const,
  list: (filters?: Record<string, string | undefined>) =>
    [...articleKeys.all, "list", filters] as const,
  one: (id: string) => [...articleKeys.all, id] as const,
}

const apiBase = () => process.env.NEXT_PUBLIC_API_URL ?? ""

async function buildApiError(res: Response, fallback: string): Promise<Error> {
  const payload = (await res.json().catch(() => null)) as { detail?: string } | null
  return new Error(payload?.detail ?? fallback)
}

export function useContentArticles(filters?: { status?: ArticleStatus }) {
  const { data: session } = useSession()
  return useQuery({
    queryKey: articleKeys.list(filters ? { status: filters.status } : undefined),
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (filters?.status) params["status"] = filters.status
      const qs = new URLSearchParams(params).toString()
      const res = await fetch(`${apiBase()}/api/content/articles${qs ? `?${qs}` : ""}`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao listar articles")
      return res.json() as Promise<ContentArticle[]>
    },
    enabled: !!session?.accessToken,
  })
}

export function useScrapeArticleUrl() {
  const { data: session } = useSession()
  return useMutation({
    mutationFn: async (source_url: string) => {
      const res = await fetch(`${apiBase()}/api/content/articles/scrape-url`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify({ source_url }),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao raspar URL")
      return res.json() as Promise<ArticleScrapeResponse>
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useCreateArticle() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: ArticleCreateInput) => {
      const res = await fetch(`${apiBase()}/api/content/articles`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao criar")
      return res.json() as Promise<ContentArticle>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.all })
      toast.success("Article criado")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateArticle() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: ArticleUpdateInput }) => {
      const res = await fetch(`${apiBase()}/api/content/articles/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao atualizar")
      return res.json() as Promise<ContentArticle>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: articleKeys.all }),
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteArticle() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${apiBase()}/api/content/articles/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok && res.status !== 204) throw await buildApiError(res, "Erro ao deletar")
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.all })
      toast.success("Article movido para lixeira")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useApproveArticle() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${apiBase()}/api/content/articles/${id}/approve`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao aprovar")
      return res.json() as Promise<ContentArticle>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.all })
      toast.success("Article aprovado")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useScheduleArticle() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, scheduled_for }: { id: string; scheduled_for: string }) => {
      const res = await fetch(`${apiBase()}/api/content/articles/${id}/schedule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify({ scheduled_for }),
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao agendar")
      return res.json() as Promise<ContentArticle>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.all })
      toast.success("Article agendado")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function usePublishArticleNow() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${apiBase()}/api/content/articles/${id}/publish-now`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao publicar")
      return res.json() as Promise<ContentArticle>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.all })
      toast.success("Article publicado no LinkedIn")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUploadArticleThumbnail() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, file }: { id: string; file: File }) => {
      const fd = new FormData()
      fd.append("file", file)
      const res = await fetch(`${apiBase()}/api/content/articles/${id}/upload-thumbnail`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        body: fd,
      })
      if (!res.ok) throw await buildApiError(res, "Erro ao subir thumbnail")
      return res.json() as Promise<ContentArticle>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.all })
      toast.success("Thumbnail atualizada")
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
