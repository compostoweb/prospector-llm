"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export type StepType =
  | "linkedin_connect"
  | "linkedin_dm_first"
  | "linkedin_dm_post_connect"
  | "linkedin_dm_post_connect_voice"
  | "linkedin_dm_voice"
  | "linkedin_dm_followup"
  | "linkedin_dm_breakup"
  | "email_first"
  | "email_followup"
  | "email_breakup"

export interface CadenceStep {
  channel: "linkedin_connect" | "linkedin_dm" | "email"
  day_offset: number
  message_template: string
  use_voice: boolean
  audio_file_id: string | null
  step_type: StepType | null
}

export interface Cadence {
  id: string
  tenant_id: string
  name: string
  description: string | null
  is_active: boolean
  llm_provider: "openai" | "gemini"
  llm_model: string
  llm_temperature: number
  llm_max_tokens: number
  tts_provider: string | null
  tts_voice_id: string | null
  tts_speed: number
  tts_pitch: number
  lead_list_id: string | null
  target_segment: string | null
  persona_description: string | null
  offer_description: string | null
  tone_instructions: string | null
  steps_template: CadenceStep[] | null
  created_at: string
  updated_at: string
}

export interface CreateCadenceBody {
  name: string
  description?: string
  llm: {
    provider: "openai" | "gemini"
    model: string
    temperature: number
    max_tokens: number
  }
  tts_provider?: string | null
  tts_voice_id?: string | null
  tts_speed?: number
  tts_pitch?: number
  lead_list_id?: string | null
  target_segment?: string | null
  persona_description?: string | null
  offer_description?: string | null
  tone_instructions?: string | null
  steps_template: CadenceStep[]
}

// ── Hooks de query ────────────────────────────────────────────────────

export function useCadences() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["cadences"],
    queryFn: async (): Promise<Cadence[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/cadences" as never)
      if (error) throw new Error("Falha ao carregar cadências")
      return (data as Cadence[]) ?? []
    },
    staleTime: 60 * 1000, // 1min
    enabled: !!session?.accessToken,
  })
}

export function useCadence(id: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["cadences", id],
    queryFn: async (): Promise<Cadence> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/cadences/${id}` as never)
      if (error) throw new Error("Falha ao carregar cadência")
      return data as Cadence
    },
    enabled: !!session?.accessToken && !!id,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useCreateCadence() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateCadenceBody): Promise<Cadence> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/cadences" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao criar cadência")
      return data as Cadence
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cadences"] })
    },
  })
}

export function useUpdateCadence() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: Partial<CreateCadenceBody> & { id: string }): Promise<Cadence> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/cadences/${id}` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao atualizar cadência")
      return data as Cadence
    },
    onSuccess: (cadence) => {
      void queryClient.invalidateQueries({ queryKey: ["cadences", cadence.id] })
      void queryClient.invalidateQueries({ queryKey: ["cadences"] })
    },
  })
}

export function useToggleCadence() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }): Promise<Cadence> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/cadences/${id}` as never, {
        body: { is_active } as never,
      })
      if (error) throw new Error("Falha ao alterar status da cadência")
      return data as Cadence
    },
    onSuccess: (cadence) => {
      void queryClient.invalidateQueries({ queryKey: ["cadences", cadence.id] })
      void queryClient.invalidateQueries({ queryKey: ["cadences"] })
    },
  })
}

export function useDeleteCadence() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/cadences/${id}` as never)
      if (error) throw new Error("Falha ao excluir cadência")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cadences"] })
    },
  })
}
