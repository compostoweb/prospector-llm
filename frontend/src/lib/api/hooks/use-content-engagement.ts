"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { env } from "@/env"
import type {
  AddManualEngagementPostRequest,
  EngagementComment,
  EngagementPost,
  EngagementSession,
  EngagementSessionDetail,
  GoogleDiscoveryComposeRequest,
  GoogleDiscoveryQuery,
  ImportExternalPostsRequest,
  ImportExternalPostsResponse,
  RunScanRequest,
  RunScanResponse,
} from "@/lib/content-engagement/types"
import { contentKeys } from "@/lib/api/hooks/use-content"

function buildAuthHeaders(accessToken?: string, includeJson = false): HeadersInit {
  const headers: HeadersInit = {}
  if (includeJson) headers["Content-Type"] = "application/json"
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`
  return headers
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : "Falha na requisição de Engajamento"
    throw new Error(detail)
  }
  return payload as T
}

const BASE = () => `${env.NEXT_PUBLIC_API_URL}/api/content/engagement`

export const engagementKeys = {
  all: ["content", "engagement"] as const,
  sessions: (page?: number, limit?: number) =>
    [...engagementKeys.all, "sessions", page ?? "all", limit ?? "all"] as const,
  session: (id: string) => [...engagementKeys.all, "sessions", id] as const,
  posts: (sessionId?: string, postType?: string) =>
    [...engagementKeys.all, "posts", sessionId ?? "all", postType ?? "all"] as const,
  comments: (sessionId?: string, postId?: string) =>
    [...engagementKeys.all, "comments", sessionId ?? "all", postId ?? "all"] as const,
  googleDiscoveryHistory: (limit?: number) =>
    [...engagementKeys.all, "google-discovery", "history", limit ?? "all"] as const,
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export function useEngagementSessions(params?: { page?: number; limit?: number }) {
  const { data: session } = useSession()
  const page = params?.page
  const limit = params?.limit

  return useQuery({
    queryKey: engagementKeys.sessions(page, limit),
    queryFn: async () => {
      const searchParams = new URLSearchParams()
      if (page) searchParams.set("page", String(page))
      if (limit) searchParams.set("limit", String(limit))
      const query = searchParams.toString()
      const res = await fetch(`${BASE()}/sessions${query ? `?${query}` : ""}`, {
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementSession[]>(res)
    },
    enabled: !!session?.accessToken,
  })
}

export function useEngagementSession(id: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: engagementKeys.session(id ?? ""),
    queryFn: async () => {
      const res = await fetch(`${BASE()}/sessions/${id}`, {
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementSessionDetail>(res)
    },
    enabled: !!session?.accessToken && !!id,
    staleTime: 0,
    refetchOnMount: "always",
    // Para de pôllar se passaram mais de 15 minutos (worker morto/timeout)
    refetchInterval: (query) => {
      const data = query.state.data as EngagementSessionDetail | undefined
      if (data?.status !== "running") return false
      const createdAt = data?.created_at ? new Date(data.created_at).getTime() : 0
      const elapsed = Date.now() - createdAt
      if (elapsed > 5 * 60 * 1000) return false // 5 min timeout
      return 3000
    },
  })
}

// ── Run scan ──────────────────────────────────────────────────────────────────

export function useRunScan() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: RunScanRequest) => {
      const res = await fetch(`${BASE()}/run`, {
        method: "POST",
        headers: buildAuthHeaders(session?.accessToken, true),
        body: JSON.stringify(body),
      })
      return parseApiResponse<RunScanResponse>(res)
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.all })
      queryClient.invalidateQueries({ queryKey: engagementKeys.sessions() })
      queryClient.invalidateQueries({ queryKey: engagementKeys.session(result.session_id) })
    },
  })
}

export function useComposeGoogleDiscoveryQueries() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: GoogleDiscoveryComposeRequest) => {
      const res = await fetch(`${BASE()}/discovery/google/compose`, {
        method: "POST",
        headers: buildAuthHeaders(session?.accessToken, true),
        body: JSON.stringify(body),
      })
      return parseApiResponse<GoogleDiscoveryQuery[]>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.googleDiscoveryHistory() })
    },
  })
}

export function useGoogleDiscoveryHistory(limit = 20) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: engagementKeys.googleDiscoveryHistory(limit),
    queryFn: async () => {
      const res = await fetch(`${BASE()}/discovery/google/history?limit=${limit}`, {
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<GoogleDiscoveryQuery[]>(res)
    },
    enabled: !!session?.accessToken,
  })
}

// ── Posts ─────────────────────────────────────────────────────────────────────

export function useEngagementPosts(sessionId?: string, postType?: "reference" | "icp") {
  const { data: session } = useSession()

  return useQuery({
    queryKey: engagementKeys.posts(sessionId, postType),
    queryFn: async () => {
      const params = new URLSearchParams()
      if (sessionId) params.set("session_id", sessionId)
      if (postType) params.set("post_type", postType)
      const res = await fetch(`${BASE()}/posts?${params.toString()}`, {
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementPost[]>(res)
    },
    enabled: !!session?.accessToken,
  })
}

export function useAddManualPost() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      sessionId,
      body,
    }: {
      sessionId: string
      body: AddManualEngagementPostRequest
    }) => {
      const res = await fetch(`${BASE()}/posts?session_id=${sessionId}`, {
        method: "POST",
        headers: buildAuthHeaders(session?.accessToken, true),
        body: JSON.stringify(body),
      })
      return parseApiResponse<EngagementPost>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.posts() })
    },
  })
}

export function useImportExternalPosts() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      sessionId,
      body,
    }: {
      sessionId: string
      body: ImportExternalPostsRequest
    }) => {
      const res = await fetch(`${BASE()}/posts/import?session_id=${sessionId}`, {
        method: "POST",
        headers: buildAuthHeaders(session?.accessToken, true),
        body: JSON.stringify(body),
      })
      return parseApiResponse<ImportExternalPostsResponse>(res)
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.all })
      queryClient.invalidateQueries({ queryKey: engagementKeys.session(result.session_id) })
      queryClient.invalidateQueries({ queryKey: engagementKeys.posts(result.session_id) })
      queryClient.invalidateQueries({ queryKey: engagementKeys.sessions() })
    },
  })
}

export function useSaveEngagementPost() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ postId, is_saved }: { postId: string; is_saved: boolean }) => {
      const res = await fetch(`${BASE()}/posts/${postId}/save`, {
        method: "PATCH",
        headers: buildAuthHeaders(session?.accessToken, true),
        body: JSON.stringify({ is_saved }),
      })
      return parseApiResponse<EngagementPost>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.posts() })
      queryClient.invalidateQueries({ queryKey: engagementKeys.sessions() })
      queryClient.invalidateQueries({ queryKey: contentKeys.references() })
    },
  })
}

export function useDeleteEngagementPost() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (postId: string) => {
      const res = await fetch(`${BASE()}/posts/${postId}`, {
        method: "DELETE",
        headers: buildAuthHeaders(session?.accessToken),
      })
      if (!res.ok) {
        const payload = await res.json().catch(() => null)
        throw new Error(payload?.detail ?? "Erro ao excluir post")
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.posts() })
    },
  })
}

// ── Comments ──────────────────────────────────────────────────────────────────

export function useEngagementComments(sessionId?: string, postId?: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: engagementKeys.comments(sessionId, postId),
    queryFn: async () => {
      const params = new URLSearchParams()
      if (sessionId) params.set("session_id", sessionId)
      if (postId) params.set("post_id", postId)
      const res = await fetch(`${BASE()}/comments?${params.toString()}`, {
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementComment[]>(res)
    },
    enabled: !!session?.accessToken,
  })
}

export function useSelectComment() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (commentId: string) => {
      const res = await fetch(`${BASE()}/comments/${commentId}/select`, {
        method: "PATCH",
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementComment>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.comments() })
    },
  })
}

export function useMarkCommentPosted() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (commentId: string) => {
      const res = await fetch(`${BASE()}/comments/${commentId}/posted`, {
        method: "PATCH",
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementComment>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.all })
    },
  })
}

export function useUnmarkCommentPosted() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (commentId: string) => {
      const res = await fetch(`${BASE()}/comments/${commentId}/unpost`, {
        method: "PATCH",
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementComment>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.all })
    },
  })
}

export function useDiscardComment() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (commentId: string) => {
      const res = await fetch(`${BASE()}/comments/${commentId}/discard`, {
        method: "PATCH",
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<EngagementComment>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.comments() })
    },
  })
}

export function useRegenerateComment() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (commentId: string) => {
      const res = await fetch(`${BASE()}/comments/${commentId}/regenerate`, {
        method: "POST",
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<{ comment_1: EngagementComment; comment_2: EngagementComment }>(res)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: engagementKeys.all })
    },
  })
}
