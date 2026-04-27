"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { toast } from "sonner"

// ── Tipos ─────────────────────────────────────────────────────────────

export type PostPillar = "authority" | "case" | "vision"
export type PostStatus = "draft" | "approved" | "scheduled" | "published" | "failed"
export type ContentGoal = "editorial" | "lead_magnet_launch"
export type LMDistributionType = "comment" | "dm" | "link_bio"
export type HookType =
  | "loop_open"
  | "contrarian"
  | "identification"
  | "shortcut"
  | "benefit"
  | "data"

export interface ContentPost {
  id: string
  tenant_id: string
  title: string
  body: string
  pillar: PostPillar
  status: PostStatus
  hook_type: HookType | null
  hashtags: string | null
  character_count: number | null
  publish_date: string | null
  week_number: number | null
  linkedin_post_urn: string | null
  linkedin_scheduled_id: string | null
  // Mídia: imagem
  image_url: string | null
  image_s3_key: string | null
  image_style: string | null
  image_prompt: string | null
  image_aspect_ratio: string | null
  image_filename: string | null
  image_size_bytes: number | null
  linkedin_image_urn: string | null
  // Mídia: vídeo
  video_url: string | null
  video_s3_key: string | null
  video_filename: string | null
  video_size_bytes: number | null
  linkedin_video_urn: string | null
  impressions: number
  likes: number
  comments: number
  shares: number
  saves: number
  engagement_rate: number | null
  metrics_updated_at: string | null
  published_at: string | null
  error_message: string | null
  notion_page_id: string | null
  created_at: string
  updated_at: string
  linkedin_sync_warning?: string | null
}

export interface ContentTheme {
  id: string
  tenant_id: string
  title: string
  pillar: PostPillar
  used: boolean
  used_at: string | null
  used_in_post_id: string | null
  is_custom: boolean
  created_at: string
  updated_at: string
}

export interface ContentSettings {
  id: string
  tenant_id: string
  default_publish_time: string | null
  posts_per_week: number
  author_name: string | null
  author_voice: string | null
  notion_api_key_set: boolean
  notion_database_id: string | null
  notion_column_mappings: NotionColumnMappings | null
  created_at: string
  updated_at: string
}

export interface ContentReference {
  id: string
  tenant_id: string
  author_name: string | null
  author_title: string | null
  author_company: string | null
  body: string
  hook_type: HookType | null
  pillar: PostPillar | null
  engagement_score: number | null
  source_url: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ContentLinkedInAccount {
  id: string
  tenant_id: string
  person_id: string
  person_urn: string
  display_name: string | null
  is_active: boolean
  scopes: string | null
  connected_at: string
  token_expires_at: string | null
  updated_at: string
  has_unipile: boolean
  last_voyager_sync_at: string | null
}

export interface VoyagerSyncResponse {
  success: boolean
  posts_created: number
  posts_updated: number
  posts_skipped: number
  error: string | null
  synced_at: string
}

export interface GeneratePostVariation {
  text: string
  character_count: number
  hook_type_used: string
  violations: string[]
}

export interface GeneratePostRequest {
  theme: string
  pillar: PostPillar
  content_goal?: ContentGoal
  lead_magnet_id?: string | null
  hook_type?: HookType | null
  launch_distribution_type?: LMDistributionType | null
  launch_trigger_word?: string | null
  variations?: number
  use_references?: boolean
  provider?: string | null
  model?: string | null
  temperature?: number
}

export interface ImprovePostRequest {
  post_id?: string | null
  body?: string | null
  instruction: string
  provider?: string | null
  model?: string | null
}

export interface ThemeSuggestion {
  theme: ContentTheme
  reason: string
  lead_count: number
  sector: string
}

export interface ContentReferenceCreate {
  body: string
  author_name?: string | null
  author_title?: string | null
  author_company?: string | null
  hook_type?: HookType | null
  pillar?: PostPillar | null
  engagement_score?: number | null
  source_url?: string | null
  notes?: string | null
}

// ── Query Keys ────────────────────────────────────────────────────────

export const contentKeys = {
  all: ["content"] as const,
  posts: (filters?: Record<string, string | undefined>) =>
    [...contentKeys.all, "posts", filters] as const,
  post: (id: string) => [...contentKeys.all, "posts", id] as const,
  themes: (filters?: Record<string, string | undefined>) =>
    [...contentKeys.all, "themes", filters] as const,
  settings: () => [...contentKeys.all, "settings"] as const,
  references: () => [...contentKeys.all, "references"] as const,
  linkedinStatus: () => [...contentKeys.all, "linkedin-status"] as const,
  themeSuggestions: () => [...contentKeys.all, "theme-suggestions"] as const,
}

async function buildApiError(res: Response, fallbackMessage: string): Promise<Error> {
  const payload = (await res.json().catch(() => null)) as { detail?: string } | null
  return new Error(payload?.detail ?? fallbackMessage)
}

// ── Posts ─────────────────────────────────────────────────────────────

export function useContentPosts(filters?: {
  status?: PostStatus
  pillar?: PostPillar
  week_number?: number
}) {
  const { data: session } = useSession()
  return useQuery({
    queryKey: contentKeys.posts(
      filters
        ? {
            status: filters.status,
            pillar: filters.pillar,
            week_number: filters.week_number?.toString(),
          }
        : undefined,
    ),
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (filters?.status) params["status"] = filters.status
      if (filters?.pillar) params["pillar"] = filters.pillar
      if (filters?.week_number) params["week_number"] = String(filters.week_number)

      const qs = new URLSearchParams(params).toString()
      const url = `/api/content/posts${qs ? `?${qs}` : ""}`
      // openapi-fetch não tem o schema do Content Hub gerado, usamos fetch direto
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}${url}`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw new Error("Erro ao buscar posts")
      return res.json() as Promise<ContentPost[]>
    },
    enabled: !!session?.accessToken,
    refetchInterval: 5 * 60 * 1000, // 5 min
  })
}

export function useCreateContentPost() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: {
      title: string
      body: string
      pillar: PostPillar
      hook_type?: HookType | null
      hashtags?: string | null
      character_count?: number | null
      publish_date?: string | null
      week_number?: number | null
    }) => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Erro ao criar post")
      return res.json() as Promise<ContentPost>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useApprovePost() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/approve`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw await buildApiError(res, "Erro ao aprovar post")
      return res.json() as Promise<ContentPost>
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Erro ao aprovar post"),
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useSchedulePost() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/schedule`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw await buildApiError(res, "Erro ao agendar post")
      return res.json() as Promise<ContentPost>
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Erro ao agendar post"),
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useCancelSchedule() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/schedule`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw await buildApiError(res, "Erro ao cancelar agendamento")
      return res.json() as Promise<ContentPost>
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Erro ao cancelar agendamento"),
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function usePublishNow() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/publish-now`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw await buildApiError(res, "Erro ao publicar post")
      return res.json() as Promise<ContentPost>
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Erro ao publicar post"),
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useDeletePost() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao deletar post")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export interface ContentPostUpdateBody {
  title?: string | null
  body?: string | null
  pillar?: PostPillar | null
  hook_type?: HookType | null
  hashtags?: string | null
  character_count?: number | null
  publish_date?: string | null
  week_number?: number | null
}

export function useUpdatePost() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ postId, data }: { postId: string; data: ContentPostUpdateBody }) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify(data),
        },
      )
      if (!res.ok) throw new Error("Erro ao atualizar post")
      return res.json() as Promise<ContentPost & { linkedin_sync_warning?: string | null }>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

// ── Temas ─────────────────────────────────────────────────────────────

export function useContentThemes(filters?: { pillar?: PostPillar; used?: boolean }) {
  const { data: session } = useSession()
  return useQuery({
    queryKey: contentKeys.themes(
      filters ? { pillar: filters.pillar, used: filters.used?.toString() } : undefined,
    ),
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (filters?.pillar) params["pillar"] = filters.pillar
      if (filters?.used !== undefined) params["used"] = String(filters.used)
      const qs = new URLSearchParams(params).toString()
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/themes${qs ? `?${qs}` : ""}`,
        { headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` } },
      )
      if (!res.ok) throw new Error("Erro ao buscar temas")
      return res.json() as Promise<ContentTheme[]>
    },
    enabled: !!session?.accessToken,
  })
}

export function useCreateTheme() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { title: string; pillar: PostPillar }) => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/themes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Erro ao criar tema")
      return res.json() as Promise<ContentTheme>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useMarkThemeUsed() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ themeId, postId }: { themeId: string; postId?: string | null }) => {
      const params = new URLSearchParams()
      if (postId) params.set("post_id", postId)
      const qs = params.toString()
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/themes/${themeId}/used${qs ? `?${qs}` : ""}`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao marcar tema como usado")
      return res.json() as Promise<ContentTheme>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useDeleteTheme() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (themeId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/themes/${themeId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao excluir tema")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useThemeSuggestions() {
  const { data: session } = useSession()
  return useQuery({
    queryKey: contentKeys.themeSuggestions(),
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/generate/suggest-themes`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao buscar sugestões de temas")
      return res.json() as Promise<ThemeSuggestion[]>
    },
    enabled: !!session?.accessToken,
  })
}

// ── Settings ──────────────────────────────────────────────────────────

export function useContentSettings() {
  const { data: session } = useSession()
  return useQuery({
    queryKey: contentKeys.settings(),
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/settings`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw new Error("Erro ao buscar configurações")
      return res.json() as Promise<ContentSettings>
    },
    enabled: !!session?.accessToken,
  })
}

export function useUpdateContentSettings() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: {
      default_publish_time?: string | null
      posts_per_week?: number | null
      author_name?: string | null
      author_voice?: string | null
      notion_api_key?: string | null
      notion_database_id?: string | null
    }) => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/settings`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Erro ao atualizar configurações")
      return res.json() as Promise<ContentSettings>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.settings() }),
  })
}

// ── Galeria de Imagens ────────────────────────────────────────────────

export interface GalleryImage {
  post_id: string
  post_title: string
  post_status: string
  post_pillar: string | null
  image_url: string | null
  image_s3_key: string | null
  image_style: string | null
  image_prompt: string | null
  image_aspect_ratio: string | null
  image_filename: string | null
  image_size_bytes: number | null
  source: "generated" | "uploaded"
  created_at: string | null
  updated_at: string | null
}

export interface GalleryImagesResponse {
  images: GalleryImage[]
  total: number
  page: number
  page_size: number
}

export interface GalleryImagesFilters {
  page?: number | undefined
  page_size?: number | undefined
  source?: "generated" | "uploaded" | undefined
  style?: ImageStyle | undefined
  pillar?: PostPillar | undefined
  status?: PostStatus | undefined
  search?: string | undefined
}

export function useContentImages(filters?: GalleryImagesFilters) {
  const { data: session } = useSession()
  const params = new URLSearchParams()
  if (filters?.page) params.set("page", String(filters.page))
  if (filters?.page_size) params.set("page_size", String(filters.page_size))
  if (filters?.source) params.set("source", filters.source)
  if (filters?.style) params.set("style", filters.style)
  if (filters?.pillar) params.set("pillar", filters.pillar)
  if (filters?.status) params.set("status", filters.status)
  if (filters?.search) params.set("search", filters.search)
  const qs = params.toString()
  return useQuery({
    queryKey: [...contentKeys.all, "images", filters],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/images${qs ? `?${qs}` : ""}`,
        {
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao carregar galeria de imagens")
      return res.json() as Promise<GalleryImagesResponse>
    },
  })
}

export interface GenerateStandaloneImageRequest {
  prompt: string
  style: ImageStyle
  aspect_ratio?: ImageAspectRatio
  sub_type?: ImageSubType | null
  visual_direction?: ImageVisualDirection | null
}

export interface GenerateStandaloneImageResponse {
  image_url: string
  image_prompt: string
  post_id: string | null
}

export function useGenerateStandaloneImage() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: GenerateStandaloneImageRequest) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/images/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify(body),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao gerar imagem")
      }
      return res.json() as Promise<GenerateStandaloneImageResponse>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [...contentKeys.all, "images"] }),
  })
}

export interface UploadStandaloneImageResponse {
  image_url: string
  filename: string
  size_bytes: number
  post_id: string
}

export function useUploadStandaloneImage() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/images/upload`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
          body: formData,
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao fazer upload da imagem")
      }
      return res.json() as Promise<UploadStandaloneImageResponse>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [...contentKeys.all, "images"] }),
  })
}

export function useDeleteGalleryImage() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/images/${postId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw await buildApiError(res, "Erro ao excluir imagem")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: [...contentKeys.all, "images"] }),
  })
}

// ── LinkedIn Account ──────────────────────────────────────────────────

export function useLinkedInContentAccount() {
  const { data: session } = useSession()
  return useQuery({
    queryKey: contentKeys.linkedinStatus(),
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/linkedin/status`,
        { headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` } },
      )
      if (res.status === 404) return null
      if (!res.ok) throw new Error("Erro ao buscar status LinkedIn")
      return res.json() as Promise<ContentLinkedInAccount>
    },
    enabled: !!session?.accessToken,
  })
}

export function useSyncVoyager() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/linkedin/sync`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail ?? "Erro ao sincronizar analytics")
      }
      return res.json() as Promise<VoyagerSyncResponse>
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: contentKeys.linkedinStatus() })
      qc.invalidateQueries({ queryKey: contentKeys.all })
    },
  })
}

// ── Geração com IA ────────────────────────────────────────────────────

export function useGeneratePost() {
  const { data: session } = useSession()
  return useMutation({
    mutationFn: async (body: GeneratePostRequest) => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Erro ao gerar post")
      return res.json() as Promise<{ variations: GeneratePostVariation[] }>
    },
  })
}

export function useImprovePost() {
  const { data: session } = useSession()
  return useMutation({
    mutationFn: async (body: ImprovePostRequest) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/generate/improve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify(body),
        },
      )
      if (!res.ok) throw new Error("Erro ao melhorar post")
      return res.json() as Promise<{ text: string; character_count: number; violations: string[] }>
    },
  })
}

export function useDetectHookType() {
  const { data: session } = useSession()
  return useMutation({
    mutationFn: async (body: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/generate/detect-hook`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify({ body }),
        },
      )
      if (!res.ok) throw new Error("Não foi possível detectar o tipo de gancho")
      return res.json() as Promise<{ hook_type: string }>
    },
  })
}

export function useVaryTheme() {
  const { data: session } = useSession()
  return useMutation({
    mutationFn: async (body: { theme_title: string; pillar: string }) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/generate/vary-theme`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify(body),
        },
      )
      if (!res.ok) throw new Error("Erro ao gerar variação")
      return res.json() as Promise<{ variation: string }>
    },
  })
}

// ── Referências ───────────────────────────────────────────────────────

export function useContentReferences() {
  const { data: session } = useSession()
  return useQuery({
    queryKey: contentKeys.references(),
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/references`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw new Error("Erro ao buscar referências")
      return res.json() as Promise<ContentReference[]>
    },
    enabled: !!session?.accessToken,
  })
}

export function useCreateContentReference() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ContentReferenceCreate) => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/references`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.accessToken ?? ""}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Erro ao criar referência")
      return res.json() as Promise<ContentReference>
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentKeys.references() })
    },
  })
}

export function useDeleteContentReference() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/references/${id}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao excluir referência")
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentKeys.references() })
    },
  })
}

// ── Analyze Reference URL with AI ────────────────────────────────────────────

export interface AnalyzeUrlResult {
  body: string
  author_name: string | null
  author_title: string | null
  author_company: string | null
  hook_type: HookType | null
  pillar: PostPillar | null
  engagement_score: number | null
  notes: string | null
}

export function useAnalyzeReferenceUrl() {
  const { data: session } = useSession()
  return useMutation({
    mutationFn: async (url: string): Promise<AnalyzeUrlResult> => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/references/analyze-url`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify({ url }),
        },
      )
      if (!res.ok) throw new Error("Não foi possível analisar a URL")
      return res.json()
    },
  })
}

// ── Imagem gerada por IA ──────────────────────────────────────────────

export type ImageStyle = "clean" | "with_text" | "infographic"
export type ImageSubType = "metrics" | "steps" | "comparison"
export type ImageAspectRatio = "4:5" | "1:1" | "16:9"
export type ImageVisualDirection = "auto" | "editorial" | "minimal" | "bold" | "organic"

export interface GeneratePostImageRequest {
  post_id: string
  style: ImageStyle
  aspect_ratio?: ImageAspectRatio
  sub_type?: ImageSubType | null
  visual_direction?: ImageVisualDirection | null
  custom_prompt?: string | null
}

export function useGeneratePostImage() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: GeneratePostImageRequest) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/generate/image`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify(body),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao gerar imagem")
      }
      return res.json() as Promise<{ image_url: string; image_prompt: string }>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useDeletePostImage() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/image`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao excluir imagem")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useUploadPostImage() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ postId, file }: { postId: string; file: File }) => {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/upload-image`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
          body: formData,
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao fazer upload da imagem")
      }
      return res.json() as Promise<ContentPost>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

// ── Upload de vídeo ───────────────────────────────────────────────────

export function useUploadPostVideo() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ postId, file }: { postId: string; file: File }) => {
      const formData = new FormData()
      formData.append("file", file)
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/upload-video`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
          body: formData,
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao fazer upload do vídeo")
      }
      return res.json() as Promise<ContentPost>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useDeletePostVideo() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/posts/${postId}/video`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
        },
      )
      if (!res.ok) throw new Error("Erro ao excluir vídeo")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

// ── Notion Import ─────────────────────────────────────────────────
export interface NotionDatabaseColumn {
  name: string
  type: string
}

export interface NotionColumnMappings {
  title: string
  body: string
  pillar?: string | null
  status?: string | null
  publish_date?: string | null
  week_number?: string | null
  hashtags?: string | null
}
export interface NotionPostPreview {
  page_id: string
  title: string
  pillar: string | null
  status_notion: string | null
  publish_date: string | null
  week_number: number | null
  hashtags: string | null
  body_preview: string
  body: string
  already_imported: boolean
}

export interface NotionImportResult {
  imported: number
  skipped: number
  failed: number
  post_ids: string[]
}

export function useNotionPreview(enabled: boolean) {
  const { data: session } = useSession()
  return useQuery({
    queryKey: ["notion", "preview"],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/notion/preview`,
        { headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` } },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao buscar posts do Notion")
      }
      return res.json() as Promise<NotionPostPreview[]>
    },
    enabled: enabled && !!session?.accessToken,
    staleTime: 0, // sempre busca ao abrir o modal
  })
}

export function useImportFromNotion() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (pageIds: string[]) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/notion/import`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify({ page_ids: pageIds }),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao importar posts do Notion")
      }
      return res.json() as Promise<NotionImportResult>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.all }),
  })
}

export function useNotionColumns() {
  const { data: session } = useSession()
  return useQuery({
    queryKey: ["notion", "columns"],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/notion/columns`,
        { headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` } },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao buscar colunas do Notion")
      }
      return res.json() as Promise<NotionDatabaseColumn[]>
    },
    enabled: false, // só executa via refetch()
    staleTime: 5 * 60 * 1000, // 5 min
  })
}

export function useSaveNotionMappings() {
  const { data: session } = useSession()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: NotionColumnMappings) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/notion/mappings`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.accessToken ?? ""}`,
          },
          body: JSON.stringify(body),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail ?? "Erro ao salvar mapeamento")
      }
      return res.json() as Promise<{ ok: boolean; fields_mapped: string[] }>
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: contentKeys.settings() }),
  })
}
