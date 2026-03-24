"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface PipedrivePipeline {
  id: number
  name: string
}

export interface PipedriveStage {
  id: number
  name: string
  pipeline_id: number
  order_nr: number
}

export interface PipedriveUser {
  id: number
  name: string
  email: string
}

// ── Hooks ─────────────────────────────────────────────────────────────

export function usePipedrivePipelines(enabled = true) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["pipedrive", "pipelines"],
    queryFn: async (): Promise<PipedrivePipeline[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/pipedrive/pipelines" as never)
      if (error) throw new Error("Falha ao carregar pipelines")
      return data as PipedrivePipeline[]
    },
    staleTime: 10 * 60 * 1000, // 10min
    enabled: enabled && !!session?.accessToken,
  })
}

export function usePipedriveStages(pipelineId: number | null, enabled = true) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["pipedrive", "stages", pipelineId],
    queryFn: async (): Promise<PipedriveStage[]> => {
      const client = createBrowserClient(session?.accessToken)
      const url = pipelineId ? `/pipedrive/stages?pipeline_id=${pipelineId}` : "/pipedrive/stages"
      const { data, error } = await client.GET(url as never)
      if (error) throw new Error("Falha ao carregar stages")
      return data as PipedriveStage[]
    },
    staleTime: 10 * 60 * 1000,
    enabled: enabled && !!session?.accessToken,
  })
}

export function usePipedriveUsers(enabled = true) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["pipedrive", "users"],
    queryFn: async (): Promise<PipedriveUser[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/pipedrive/users" as never)
      if (error) throw new Error("Falha ao carregar usuários")
      return data as PipedriveUser[]
    },
    staleTime: 10 * 60 * 1000,
    enabled: enabled && !!session?.accessToken,
  })
}
