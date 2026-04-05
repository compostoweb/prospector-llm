"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface FictitiousLeadData {
  name: string
  company: string
  job_title: string
  email?: string | null
  linkedin_url?: string | null
  industry?: string | null
  city?: string | null
  website?: string | null
}

export interface SandboxCompositionContext {
  generation_mode: string
  step_key: string
  copy_method: string | null
  playbook_sector: string | null
  playbook_role: string | null
  matched_role: string | null
  few_shot_applied: boolean
  few_shot_key: string | null
  few_shot_method: string | null
  has_site_summary: boolean
  has_recent_posts: boolean
}

export interface SandboxStep {
  id: string
  sandbox_run_id: string
  lead_id: string | null
  fictitious_lead_data: FictitiousLeadData | null
  step_number: number
  channel: "linkedin_connect" | "linkedin_dm" | "email" | "manual_task"
  day_offset: number
  use_voice: boolean
  step_type: string | null
  scheduled_at_preview: string
  message_content: string | null
  audio_preview_url: string | null
  email_subject: string | null
  status: "pending" | "generating" | "generated" | "approved" | "rejected"
  llm_provider: string | null
  llm_model: string | null
  tokens_in: number | null
  tokens_out: number | null
  composition_context: SandboxCompositionContext | null
  simulated_reply: string | null
  simulated_intent: "interest" | "objection" | "not_interested" | "neutral" | "out_of_office" | null
  simulated_confidence: number | null
  simulated_reply_summary: string | null
  is_rate_limited: boolean
  rate_limit_reason: string | null
  adjusted_scheduled_at: string | null
  created_at: string
  updated_at: string
}

export interface SandboxRun {
  id: string
  cadence_id: string
  status: "running" | "completed" | "approved" | "rejected"
  lead_source: "real" | "sample" | "fictitious"
  pipedrive_dry_run: Record<string, unknown> | null
  steps: SandboxStep[]
  created_at: string
  updated_at: string
}

export interface SandboxRunListItem {
  id: string
  cadence_id: string
  status: "running" | "completed" | "approved" | "rejected"
  lead_source: "real" | "sample" | "fictitious"
  steps_count: number
  created_at: string
}

export interface SandboxCreateBody {
  lead_ids?: string[] | null
  lead_count?: number
  use_fictitious?: boolean
}

export interface SandboxApproveResult {
  sandbox_run_id: string
  status: string
  steps_approved: number
}

export interface SandboxStartResult {
  sandbox_run_id: string
  cadence_id: string
  leads_enrolled: number
  steps_created: number
}

export interface PipedriveLeadPreview {
  lead_name: string
  lead_company: string | null
  intent: string | null
  person: {
    name: string
    email: string | null
    person_exists: boolean
    person_id: number | null
  }
  deal: {
    title: string
    stage: string
    value: number
  }
  note_preview: string
}

export interface PipedriveDryRunResult {
  sandbox_run_id: string
  leads: PipedriveLeadPreview[]
}

export interface PipedrivePushLeadResult {
  lead_name: string
  person_id: number | null
  deal_id: number | null
  note_added: boolean
  error: string | null
}

export interface PipedrivePushResult {
  sandbox_run_id: string
  pushed: number
  errors: number
  results: PipedrivePushLeadResult[]
}

// ── Queries ───────────────────────────────────────────────────────────

export function useSandboxRuns(cadenceId: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["sandbox-runs", cadenceId],
    queryFn: async (): Promise<SandboxRunListItem[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/cadences/${cadenceId}/sandbox` as never)
      if (error) throw new Error("Falha ao carregar sandbox runs")
      return (data as SandboxRunListItem[]) ?? []
    },
    staleTime: 30 * 1000,
    enabled: !!session?.accessToken && !!cadenceId,
  })
}

export function useSandboxRun(runId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["sandbox-run", runId],
    queryFn: async (): Promise<SandboxRun> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/sandbox/${runId}` as never)
      if (error) throw new Error("Falha ao carregar sandbox run")
      return data as SandboxRun
    },
    staleTime: 15 * 1000,
    enabled: !!session?.accessToken && !!runId,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useCreateSandbox(cadenceId: string) {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: SandboxCreateBody): Promise<SandboxRun> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/cadences/${cadenceId}/sandbox` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao criar sandbox")
      return data as SandboxRun
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sandbox-runs", cadenceId] })
    },
  })
}

export function useGenerateSandbox() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string): Promise<SandboxRun> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/sandbox/${runId}/generate` as never)
      if (error) throw new Error("Falha ao gerar mensagens")
      return data as SandboxRun
    },
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: ["sandbox-run", run.id] })
    },
  })
}

export function useRegenerateStep() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      stepId,
      temperature,
    }: {
      stepId: string
      temperature?: number
    }): Promise<SandboxStep> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/sandbox/steps/${stepId}/regenerate` as never, {
        body: temperature != null ? ({ temperature } as never) : undefined,
      })
      if (error) throw new Error("Falha ao regenerar step")
      return data as SandboxStep
    },
    onSuccess: (step) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", step.sandbox_run_id],
      })
    },
  })
}

export function useApproveStep() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (stepId: string): Promise<SandboxStep> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/sandbox/steps/${stepId}/approve` as never)
      if (error) throw new Error("Falha ao aprovar step")
      return data as SandboxStep
    },
    onSuccess: (step) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", step.sandbox_run_id],
      })
    },
  })
}

export function useRejectStep() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (stepId: string): Promise<SandboxStep> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/sandbox/steps/${stepId}/reject` as never)
      if (error) throw new Error("Falha ao rejeitar step")
      return data as SandboxStep
    },
    onSuccess: (step) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", step.sandbox_run_id],
      })
    },
  })
}

export function useApproveRun() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string): Promise<SandboxApproveResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/sandbox/${runId}/approve` as never)
      if (error) throw new Error("Falha ao aprovar run")
      return data as SandboxApproveResult
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", result.sandbox_run_id],
      })
    },
  })
}

export function useStartFromSandbox() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string): Promise<SandboxStartResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/sandbox/${runId}/start` as never)
      if (error) throw new Error("Falha ao iniciar cadência")
      return data as SandboxStartResult
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", result.sandbox_run_id],
      })
      void queryClient.invalidateQueries({ queryKey: ["cadences"] })
    },
  })
}

export function useSimulateReply() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      stepId,
      mode,
      reply_text,
    }: {
      stepId: string
      mode: "auto" | "manual"
      reply_text?: string
    }): Promise<SandboxStep> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(
        `/sandbox/steps/${stepId}/simulate-reply` as never,
        { body: { mode, reply_text } as never },
      )
      if (error) throw new Error("Falha ao simular reply")
      return data as SandboxStep
    },
    onSuccess: (step) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", step.sandbox_run_id],
      })
    },
  })
}

export function useSandboxTimeline(runId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["sandbox-timeline", runId],
    queryFn: async (): Promise<SandboxRun> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/sandbox/${runId}/timeline` as never)
      if (error) throw new Error("Falha ao carregar timeline")
      return data as SandboxRun
    },
    enabled: !!session?.accessToken && !!runId,
    staleTime: 30 * 1000,
  })
}

export function usePipedriveDryRun() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string): Promise<PipedriveDryRunResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/sandbox/${runId}/pipedrive-dry-run` as never)
      if (error) throw new Error("Falha no dry-run Pipedrive")
      return data as PipedriveDryRunResult
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", result.sandbox_run_id],
      })
    },
  })
}

export function usePipedrivePush() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string): Promise<PipedrivePushResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/sandbox/${runId}/pipedrive-push` as never)
      if (error) throw new Error("Falha ao enviar para Pipedrive")
      return data as PipedrivePushResult
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({
        queryKey: ["sandbox-run", result.sandbox_run_id],
      })
    },
  })
}

export function useDeleteSandboxRun(cadenceId: string) {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string) => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/sandbox/${runId}` as never)
      if (error) throw new Error("Falha ao excluir sandbox run")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sandbox-runs", cadenceId] })
    },
  })
}
