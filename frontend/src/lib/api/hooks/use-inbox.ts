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
}

export type SuggestTone = "formal" | "casual" | "objetiva" | "consultiva"

// ── Queries ───────────────────────────────────────────────────────────

export function useConversations(cursor?: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["inbox", "conversations", cursor],
    queryFn: async (): Promise<ConversationListResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const query: Record<string, string> = {}
      if (cursor) query.cursor = cursor

      const { data, error } = await client.GET("/inbox/conversations" as never, {
        params: { query } as never,
      })
      if (error) throw new Error("Falha ao carregar conversas")
      return data as ConversationListResponse
    },
    staleTime: 15 * 1000,
    enabled: !!session?.accessToken,
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

      const { data, error } = await client.GET(
        `/inbox/conversations/${chatId}/messages` as never,
        { params: { query } as never },
      )
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
      const { data, error } = await client.GET(
        `/inbox/conversations/${chatId}/lead` as never,
      )
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
    mutationFn: async ({
      chatId,
      text,
    }: {
      chatId: string
      text: string
    }) => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(
        `/inbox/conversations/${chatId}/send` as never,
        { body: { text } as never },
      )
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
    mutationFn: async ({
      chatId,
      audioBlob,
    }: {
      chatId: string
      audioBlob: Blob
    }) => {
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
      const { data, error } = await client.POST(
        `/inbox/conversations/${chatId}/suggest` as never,
        { body: { tone } as never },
      )
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
      const { data, error } = await client.POST(
        `/inbox/conversations/${chatId}/send-crm` as never,
      )
      if (error) throw new Error("Falha ao enviar para CRM")
      return data as { person_id: number; deal_id: number | null; status: string }
    },
  })
}
