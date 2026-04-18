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
  manual_task_type?: "call" | "linkedin_post_comment" | "whatsapp" | "other" | null
  manual_task_detail?: string | null
}

export interface CadenceTemplateVariable {
  key: string
  token: string
  label: string
}

export interface ComposeCadenceStepResult {
  action: "generate" | "improve"
  channel: CadenceChannel
  step_number: number
  step_type: StepType | null
  message_template: string
  subject: string | null
  variables: string[]
  method: string
}

export interface CadenceStepPreviewResult {
  channel: CadenceChannel
  step_number: number
  lead_id: string | null
  lead_name: string | null
  subject: string | null
  body: string
  body_is_html: boolean
  variables: string[]
  method: string
}

export interface Cadence {
  id: string
  tenant_id: string
  name: string
  description: string | null
  is_active: boolean
  mode: "automatic" | "semi_manual"
  cadence_type: "mixed" | "email_only"
  llm_provider: "openai" | "gemini" | "anthropic" | "openrouter"
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
    provider: "openai" | "gemini" | "anthropic" | "openrouter"
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

export function useCadenceTemplateVariables() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["cadences", "template-variables"],
    queryFn: async (): Promise<CadenceTemplateVariable[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/cadences/template-variables" as never)
      if (error) throw new Error("Falha ao carregar variáveis do template")
      return (data as CadenceTemplateVariable[]) ?? []
    },
    staleTime: 5 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useCadenceStepPreview({
  cadenceId,
  stepIndex,
  channel,
  leadId,
  currentText,
  currentSubject,
  currentEmailTemplateId,
}: {
  cadenceId: string
  stepIndex: number
  channel: CadenceChannel
  leadId?: string | null
  currentText?: string | null
  currentSubject?: string | null
  currentEmailTemplateId?: string | null
}) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: [
      "cadences",
      cadenceId,
      "step-preview",
      stepIndex,
      channel,
      leadId ?? "template",
      currentText ?? "",
      currentSubject ?? "",
      currentEmailTemplateId ?? "",
    ],
    queryFn: async (): Promise<CadenceStepPreviewResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(
        `/cadences/${cadenceId}/steps/${stepIndex}/preview` as never,
        {
          body: {
            lead_id: leadId ?? null,
            current_text: currentText ?? null,
            current_subject: currentSubject ?? null,
            current_email_template_id: currentEmailTemplateId ?? null,
          } as never,
        },
      )
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao renderizar prévia do passo"))
      }
      return data as CadenceStepPreviewResult
    },
    enabled:
      !!session?.accessToken &&
      !!cadenceId &&
      stepIndex >= 0 &&
      channel !== "manual_task" &&
      channel !== "linkedin_post_reaction",
    staleTime: 0,
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
      void queryClient.invalidateQueries({ queryKey: ["analytics", "cadences"] })
    },
  })
}

export function useComposeCadenceStep() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async ({
      cadenceId,
      stepIndex,
      action,
      currentText,
      currentSubject,
    }: {
      cadenceId: string
      stepIndex: number
      action: "generate" | "improve"
      currentText?: string | null
      currentSubject?: string | null
    }): Promise<ComposeCadenceStepResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(
        `/cadences/${cadenceId}/steps/${stepIndex}/compose` as never,
        {
          body: {
            action,
            current_text: currentText ?? null,
            current_subject: currentSubject ?? null,
          } as never,
        },
      )
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao gerar conteúdo do passo"))
      }
      return data as ComposeCadenceStepResult
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
      void queryClient.invalidateQueries({ queryKey: ["analytics", "cadences"] })
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
      if (error) throw new Error(extractApiErrorMessage(error, "Falha ao excluir cadência"))
      return id
    },
    onMutate: async (id: string) => {
      await queryClient.cancelQueries({ queryKey: ["cadences"] })
      await queryClient.cancelQueries({ queryKey: ["analytics", "cadences", "overview"] })

      const previousCadenceQueries = queryClient.getQueriesData({ queryKey: ["cadences"] })
      const previousOverview = queryClient.getQueryData(["analytics", "cadences", "overview"])

      queryClient.setQueriesData({ queryKey: ["cadences"] }, (old: unknown) => {
        if (!Array.isArray(old)) {
          return old
        }
        return old.filter(
          (item) =>
            typeof item === "object" &&
            item !== null &&
            "id" in item &&
            (item as { id: string }).id !== id,
        )
      })

      queryClient.setQueryData(["analytics", "cadences", "overview"], (old: unknown) => {
        if (!Array.isArray(old)) {
          return old
        }
        return old.filter(
          (item) =>
            typeof item === "object" &&
            item !== null &&
            "cadence_id" in item &&
            (item as { cadence_id: string }).cadence_id !== id,
        )
      })

      return { previousCadenceQueries, previousOverview }
    },
    onError: (_error, _id, context) => {
      if (context?.previousCadenceQueries) {
        for (const [queryKey, data] of context.previousCadenceQueries) {
          queryClient.setQueryData(queryKey, data)
        }
      }
      if (context?.previousOverview !== undefined) {
        queryClient.setQueryData(["analytics", "cadences", "overview"], context.previousOverview)
      }
    },
    onSuccess: (id) => {
      queryClient.removeQueries({ queryKey: ["cadences", id] })
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["cadences"] })
      void queryClient.invalidateQueries({ queryKey: ["analytics", "cadences", "overview"] })
    },
  })
}
