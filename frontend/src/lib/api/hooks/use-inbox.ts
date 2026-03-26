"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface ChatAttendee {
  id: string
  name: string
  profile_url: string | null
  profile_picture_url: string | null
}

export interface Conversation {
  chat_id: string
  attendees: ChatAttendee[]
  last_message_text: string | null
  last_message_at: string | null
  unread_count: number
  has_lead: boolean
  lead_id: string | null
  lead_name: string | null
  lead_company: string | null
  lead_status: string | null
}

export interface ConversationListResponse {
  items: Conversation[]
  cursor: string | null
}

export interface ChatMessage {
  id: string
  sender_id: string
  sender_name: string
  text: string
  timestamp: string
  is_own: boolean
  attachments: Record<string, unknown>[]
  reactions?: MessageReaction[]
}

export interface MessageReaction {
  emoji: string
  is_own: boolean
}

export interface ChatMessagesResponse {
  items: ChatMessage[]
  cursor: string | null
}

export interface ConversationLead {
  has_lead: boolean
  lead_id: string | null
  name: string | null
  company: string | null
  job_title: string | null
  linkedin_url: string | null
  email_corporate: string | null
  email_personal: string | null
  phone: string | null
  city: string | null
  segment: string | null
  industry: string | null
  score: number | null
  status: string | null
  notes: string | null
  pending_tasks_count: number
  // Dados do contato Unipile (sempre preenchidos)
  attendee_name: string | null
  attendee_profile_url: string | null
  attendee_profile_picture_url: string | null
  attendee_id: string | null
  attendee_headline: string | null
  attendee_location: string | null
  attendee_email: string | null
  attendee_connections_count: number | null
  attendee_shared_connections_count: number | null
  attendee_is_premium: boolean
  attendee_websites: string[]
}

export interface RecentActivityItem {
  id: string
  channel: string
  direction: string
  content_preview: string | null
  intent: string | null
  created_at: string
}

export interface CadenceHistoryItem {
  cadence_id: string
  cadence_name: string
  mode: string
  total_steps: number
  completed_steps: number
  last_step_at: string | null
  is_active: boolean
}

export interface LeadTag {
  id: string
  name: string
  color: string
}

export type SuggestTone = "formal" | "casual" | "objetiva" | "consultiva"

export type InboxFilter = "all" | "unread"

// ── Queries ───────────────────────────────────────────────────────────

export function useConversations(opts?: {
  cursor?: string
  filter?: InboxFilter
  search?: string
}) {
  const { data: session } = useSession()
  const filter = opts?.filter ?? "all"
  const search = opts?.search ?? ""
  const cursor = opts?.cursor

  return useQuery({
    queryKey: ["inbox", "conversations", filter, search, cursor],
    queryFn: async (): Promise<ConversationListResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const query: Record<string, string> = { limit: "50", filter }
      if (cursor) query.cursor = cursor
      if (search) query.search = search

      const { data, error } = await client.GET("/inbox/conversations" as never, {
        params: { query } as never,
      })
      if (error) throw new Error("Falha ao carregar conversas")
      return data as ConversationListResponse
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useSyncInbox() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.POST("/inbox/sync" as never)
      if (error) throw new Error("Falha ao sincronizar")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["inbox", "conversations"] })
    },
  })
}

export function useChatMessages(chatId: string, cursor?: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["inbox", "messages", chatId, cursor],
    queryFn: async (): Promise<ChatMessagesResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const query: Record<string, string> = {}
      if (cursor) query.cursor = cursor

      const { data, error } = await client.GET(`/inbox/conversations/${chatId}/messages` as never, {
        params: { query } as never,
      })
      if (error) throw new Error("Falha ao carregar mensagens")
      return data as ChatMessagesResponse
    },
    staleTime: 10 * 1000,
    enabled: !!session?.accessToken && !!chatId,
  })
}

export function useConversationLead(chatId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["inbox", "lead", chatId],
    queryFn: async (): Promise<ConversationLead> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/inbox/conversations/${chatId}/lead` as never)
      if (error) throw new Error("Falha ao carregar dados do lead")
      return data as ConversationLead
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken && !!chatId,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useSendMessage() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ chatId, text }: { chatId: string; text: string }) => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/inbox/conversations/${chatId}/send` as never, {
        body: { text } as never,
      })
      if (error) throw new Error("Falha ao enviar mensagem")
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "messages", variables.chatId],
      })
      void queryClient.invalidateQueries({ queryKey: ["inbox", "conversations"] })
    },
  })
}

export function useSendVoiceMessage() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ chatId, audioBlob }: { chatId: string; audioBlob: Blob }) => {
      const accessToken = session?.accessToken
      if (!accessToken) throw new Error("Sessão expirada")

      const formData = new FormData()
      formData.append("audio", audioBlob, "voice-note.webm")

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/inbox/conversations/${encodeURIComponent(chatId)}/send-voice`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: formData,
        },
      )
      if (!res.ok) throw new Error("Falha ao enviar voice note")
      return res.json()
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "messages", variables.chatId],
      })
      void queryClient.invalidateQueries({ queryKey: ["inbox", "conversations"] })
    },
  })
}

export function useSuggestReply() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async ({
      chatId,
      tone,
    }: {
      chatId: string
      tone: SuggestTone
    }): Promise<{ suggested_text: string; tone: string }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/inbox/conversations/${chatId}/suggest` as never, {
        body: { tone } as never,
      })
      if (error) throw new Error("Falha ao gerar sugestão")
      return data as { suggested_text: string; tone: string }
    },
  })
}

export interface QuickCreateLeadBody {
  name: string
  linkedin_url?: string | undefined
  linkedin_profile_id?: string | undefined
  company?: string | undefined
  job_title?: string | undefined
}

export function useQuickCreateLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      chatId,
      body,
    }: {
      chatId: string
      body: QuickCreateLeadBody
    }): Promise<ConversationLead> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(
        `/inbox/conversations/${chatId}/create-lead` as never,
        { body: body as never },
      )
      if (error) throw new Error("Falha ao criar lead")
      return data as ConversationLead
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "lead", variables.chatId],
      })
      void queryClient.invalidateQueries({ queryKey: ["inbox", "conversations"] })
      void queryClient.invalidateQueries({ queryKey: ["leads"] })
    },
  })
}

export function useSendToCRM() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async ({
      chatId,
    }: {
      chatId: string
    }): Promise<{ person_id: number; deal_id: number | null; status: string }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/inbox/conversations/${chatId}/send-crm` as never)
      if (error) throw new Error("Falha ao enviar para CRM")
      return data as { person_id: number; deal_id: number | null; status: string }
    },
  })
}

export function useSendAttachments() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      chatId,
      files,
      text,
    }: {
      chatId: string
      files: File[]
      text?: string | undefined
    }) => {
      const accessToken = session?.accessToken
      if (!accessToken) throw new Error("Sessão expirada")

      const formData = new FormData()
      if (text) formData.append("text", text)
      for (const file of files) {
        formData.append("files", file)
      }

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/inbox/conversations/${encodeURIComponent(chatId)}/send-attachments`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
          body: formData,
        },
      )
      if (!res.ok) throw new Error("Falha ao enviar anexos")
      return res.json()
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "messages", variables.chatId],
      })
      void queryClient.invalidateQueries({ queryKey: ["inbox", "conversations"] })
    },
  })
}

export function useAddReaction() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      chatId,
      messageId,
      emoji,
    }: {
      chatId: string
      messageId: string
      emoji: string
    }) => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(
        `/inbox/conversations/${chatId}/messages/${messageId}/reactions` as never,
        { body: { emoji } as never },
      )
      if (error) throw new Error("Falha ao adicionar reação")
      return data
    },
    onMutate: async ({ chatId, messageId, emoji }) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ["inbox", "messages", chatId] })
      const key = ["inbox", "messages", chatId, undefined]
      const prev = queryClient.getQueryData<ChatMessagesResponse>(key)
      if (prev) {
        queryClient.setQueryData<ChatMessagesResponse>(key, {
          ...prev,
          items: prev.items.map((msg) =>
            msg.id === messageId
              ? { ...msg, reactions: [...(msg.reactions ?? []), { emoji, is_own: true }] }
              : msg,
          ),
        })
      }
      return { prev }
    },
    onError: (_err, { chatId }, context) => {
      if (context?.prev) {
        queryClient.setQueryData(["inbox", "messages", chatId, undefined], context.prev)
      }
    },
    onSettled: (_data, _err, { chatId }) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "messages", chatId],
      })
    },
  })
}

export function useRemoveReaction() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      chatId,
      messageId,
      emoji,
    }: {
      chatId: string
      messageId: string
      emoji: string
    }) => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.DELETE(
        `/inbox/conversations/${chatId}/messages/${messageId}/reactions` as never,
        { body: { emoji } as never },
      )
      if (error) throw new Error("Falha ao remover reação")
      return data
    },
    onSettled: (_data, _err, { chatId }) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "messages", chatId],
      })
    },
  })
}

// ── Recent Activity ───────────────────────────────────────────────────

export function useRecentActivity(chatId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["inbox", "activity", chatId],
    queryFn: async (): Promise<{ items: RecentActivityItem[] }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/inbox/conversations/${chatId}/activity` as never)
      if (error) throw new Error("Falha ao carregar atividade")
      return data as { items: RecentActivityItem[] }
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken && !!chatId,
  })
}

// ── Cadence History ──────────────────────────────────────────────────

export function useCadenceHistory(chatId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["inbox", "cadences", chatId],
    queryFn: async (): Promise<{ items: CadenceHistoryItem[] }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/inbox/conversations/${chatId}/cadences` as never)
      if (error) throw new Error("Falha ao carregar cadências")
      return data as { items: CadenceHistoryItem[] }
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken && !!chatId,
  })
}

// ── Tags ──────────────────────────────────────────────────────────────

export function useLeadTags(chatId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["inbox", "tags", chatId],
    queryFn: async (): Promise<LeadTag[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/inbox/conversations/${chatId}/tags` as never)
      if (error) throw new Error("Falha ao carregar tags")
      return data as LeadTag[]
    },
    staleTime: 30 * 1000,
    enabled: !!session?.accessToken && !!chatId,
  })
}

export function useAddTag() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      chatId,
      name,
      color,
    }: {
      chatId: string
      name: string
      color?: string | undefined
    }): Promise<LeadTag> => {
      const client = createBrowserClient(session?.accessToken)
      const body: Record<string, string> = { name }
      if (color) body.color = color
      const { data, error } = await client.POST(`/inbox/conversations/${chatId}/tags` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao adicionar tag")
      return data as LeadTag
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "tags", variables.chatId],
      })
    },
  })
}

export function useRemoveTag() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ chatId, tagId }: { chatId: string; tagId: string }) => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/inbox/conversations/${chatId}/tags/${tagId}` as never)
      if (error) throw new Error("Falha ao remover tag")
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["inbox", "tags", variables.chatId],
      })
    },
  })
}
