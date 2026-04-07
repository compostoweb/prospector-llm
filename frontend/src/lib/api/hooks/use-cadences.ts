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
  | "linkedin_post_reaction"
  | "linkedin_post_comment"
  | "linkedin_inmail"
  | "email_first"
  | "email_followup"
  | "email_breakup"

export type CadenceChannel =
  | "linkedin_connect"
  | "linkedin_dm"
  | "linkedin_post_reaction"
  | "linkedin_post_comment"
  | "linkedin_inmail"
  | "email"
  | "manual_task"

export interface CadenceStepLayout {
  x: number
  y: number
}

export interface CadenceStep {
  channel: CadenceChannel
  day_offset: number
  message_template: string
  use_voice: boolean
  audio_file_id: string | null
  step_type: StepType | null
  subject_variants?: string[] | null
  email_template_id?: string | null
  layout?: CadenceStepLayout | null
}

export interface Cadence {
  id: string
  tenant_id: string
  name: string
  description: string | null
  is_active: boolean
  mode: "automatic" | "semi_manual"
  cadence_type: "mixed" | "email_only"
  llm_provider: "openai" | "gemini"
  llm_model: string
  llm_temperature: number
  llm_max_tokens: number
  tts_provider: string | null
  tts_voice_id: string | null
  tts_speed: number
  tts_pitch: number
  lead_list_id: string | null
  email_account_id: string | null
  linkedin_account_id: string | null
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
  mode?: "automatic" | "semi_manual"
  cadence_type?: "mixed" | "email_only"
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
  email_account_id?: string | null
  linkedin_account_id?: string | null
  target_segment?: string | null
  persona_description?: string | null
  offer_description?: string | null
  tone_instructions?: string | null
  steps_template: CadenceStep[]
}

function extractApiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") {
    return fallback
  }

  const detail = (error as { detail?: unknown }).detail

  if (typeof detail === "string" && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const firstError = detail[0]
    if (
      firstError &&
      typeof firstError === "object" &&
      "msg" in firstError &&
      typeof firstError.msg === "string" &&
      firstError.msg.trim()
    ) {
      return firstError.msg
    }
  }

  return fallback
}

// ── Hooks de query ────────────────────────────────────────────────────

export function useCadences(cadenceType?: "mixed" | "email_only") {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["cadences", cadenceType],
    queryFn: async (): Promise<Cadence[]> => {
      const client = createBrowserClient(session?.accessToken)
      const url = cadenceType ? `/cadences?cadence_type=${cadenceType}` : "/cadences"
      const { data, error } = await client.GET(url as never)
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
    refetchInterval: 5 * 60 * 1000,
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
      if (error) throw new Error(extractApiErrorMessage(error, "Falha ao criar cadência"))
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
      if (error) throw new Error(extractApiErrorMessage(error, "Falha ao atualizar cadência"))
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
