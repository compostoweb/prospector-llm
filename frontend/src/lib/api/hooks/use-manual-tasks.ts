"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import type { TaskSlaFilter } from "@/components/tarefas/task-queue-utils"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export type ManualTaskStatus =
  | "pending"
  | "content_generated"
  | "sent"
  | "done_external"
  | "skipped"

export type TaskChannel =
  | "linkedin_connect"
  | "linkedin_dm"
  | "linkedin_post_reaction"
  | "linkedin_post_comment"
  | "linkedin_inmail"
  | "email"
  | "manual_task"

export type ManualTaskType = "call" | "linkedin_post_comment" | "whatsapp" | "other" | string

export interface ManualTaskLead {
  id: string
  name: string
  company: string | null
  job_title: string | null
  linkedin_url: string | null
  status: string
}

export interface ManualTask {
  id: string
  tenant_id: string
  cadence_id: string
  cadence_name: string | null
  lead_id: string
  cadence_step_id: string | null
  channel: TaskChannel
  manual_task_type: ManualTaskType | null
  manual_task_detail: string | null
  step_number: number
  status: ManualTaskStatus
  generated_text: string | null
  generated_audio_url: string | null
  edited_text: string | null
  sent_at: string | null
  unipile_message_id: string | null
  notes: string | null
  created_at: string
  updated_at: string
  lead: ManualTaskLead | null
}

export interface ManualTaskListResponse {
  items: ManualTask[]
  total: number
  page: number
  page_size: number
}

export interface ManualTaskStats {
  pending: number
  content_generated: number
  sent: number
  done_external: number
  skipped: number
}

interface ListTasksParams {
  cadence_id?: string
  status?: ManualTaskStatus | undefined
  statuses?: ManualTaskStatus[] | undefined
  channel?: TaskChannel | undefined
  sla?: Exclude<TaskSlaFilter, "all"> | undefined
  search?: string | undefined
  start_date?: string | undefined
  end_date?: string | undefined
  sort_by?:
    | "created_at"
    | "updated_at"
    | "sent_at"
    | "lead_name"
    | "cadence_name"
    | "step_number"
    | "status"
    | "channel"
    | undefined
  sort_dir?: "asc" | "desc" | undefined
  page?: number
  page_size?: number
}

// ── Queries ───────────────────────────────────────────────────────────

export function useManualTasks(params: ListTasksParams = {}) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["manual-tasks", params],
    queryFn: async (): Promise<ManualTaskListResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const query: Record<string, string | string[]> = {}
      if (params.cadence_id) query.cadence_id = params.cadence_id
      if (params.status) query.status = params.status
      if (params.statuses?.length) query.statuses = params.statuses
      if (params.channel) query.channel = params.channel
      if (params.sla) query.sla = params.sla
      if (params.search) query.search = params.search
      if (params.start_date) query.start_date = params.start_date
      if (params.end_date) query.end_date = params.end_date
      if (params.sort_by) query.sort_by = params.sort_by
      if (params.sort_dir) query.sort_dir = params.sort_dir
      if (params.page) query.page = String(params.page)
      if (params.page_size) query.page_size = String(params.page_size)

      const { data, error } = await client.GET("/tasks" as never, {
        params: { query } as never,
      })
      if (error) throw new Error("Falha ao carregar tarefas")
      return data as ManualTaskListResponse
    },
    staleTime: 30 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useManualTask(id: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["manual-tasks", id],
    queryFn: async (): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/tasks/${id}` as never)
      if (error) throw new Error("Falha ao carregar tarefa")
      return data as ManualTask
    },
    enabled: !!session?.accessToken && !!id,
  })
}

export function useManualTaskStats(params: Pick<ListTasksParams, "start_date" | "end_date"> = {}) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["manual-tasks", "stats", params],
    queryFn: async (): Promise<ManualTaskStats> => {
      const client = createBrowserClient(session?.accessToken)
      const query: Record<string, string> = {}
      if (params.start_date) query.start_date = params.start_date
      if (params.end_date) query.end_date = params.end_date

      const { data, error } = await client.GET("/tasks/stats" as never, {
        params: { query } as never,
      })
      if (error) throw new Error("Falha ao carregar estatísticas")
      return data as ManualTaskStats
    },
    staleTime: 30 * 1000,
    enabled: !!session?.accessToken,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useGenerateTaskContent() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (taskId: string): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/tasks/${taskId}/generate` as never)
      if (error) throw new Error("Falha ao gerar conteúdo")
      return data as ManualTask
    },
    onSuccess: (task) => {
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks"] })
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks", task.id] })
    },
  })
}

export function useRegenerateTaskContent() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (taskId: string): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/tasks/${taskId}/regenerate` as never)
      if (error) throw new Error("Falha ao regerar conteúdo")
      return data as ManualTask
    },
    onSuccess: (task) => {
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks"] })
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks", task.id] })
    },
  })
}

export function useUpdateTaskContent() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      taskId,
      edited_text,
    }: {
      taskId: string
      edited_text: string
    }): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/tasks/${taskId}` as never, {
        body: { edited_text } as never,
      })
      if (error) throw new Error("Falha ao atualizar conteúdo")
      return data as ManualTask
    },
    onSuccess: (task) => {
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks"] })
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks", task.id] })
    },
  })
}

export function useSendTask() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (taskId: string): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/tasks/${taskId}/send` as never)
      if (error) throw new Error("Falha ao enviar mensagem")
      return data as ManualTask
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks"] })
    },
  })
}

export function useMarkTaskDone() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      taskId,
      notes,
    }: {
      taskId: string
      notes?: string
    }): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/tasks/${taskId}/done` as never, {
        body: { notes: notes ?? null } as never,
      })
      if (error) throw new Error("Falha ao marcar como feita")
      return data as ManualTask
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks"] })
    },
  })
}

export function useSkipTask() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (taskId: string): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/tasks/${taskId}/skip` as never)
      if (error) throw new Error("Falha ao pular tarefa")
      return data as ManualTask
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks"] })
    },
  })
}

export function useReopenTask() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (taskId: string): Promise<ManualTask> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(`/tasks/${taskId}/reopen` as never)
      if (error) throw new Error("Falha ao reabrir tarefa")
      return data as ManualTask
    },
    onSuccess: (task) => {
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks"] })
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks", task.id] })
      void queryClient.invalidateQueries({ queryKey: ["manual-tasks", "stats"] })
    },
  })
}
