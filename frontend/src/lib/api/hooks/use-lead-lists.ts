"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface LeadListLeadItem {
  id: string
  name: string
  job_title: string | null
  company: string | null
  email_corporate: string | null
  linkedin_url: string | null
  status: string
}

export interface LeadList {
  id: string
  tenant_id: string
  name: string
  description: string | null
  lead_count: number
  created_at: string
  updated_at: string
}

export interface LeadListDetail extends LeadList {
  leads: LeadListLeadItem[]
}

export interface CreateLeadListBody {
  name: string
  description?: string | null
}

export interface UpdateLeadListBody {
  name?: string
  description?: string | null
}

// ── Hooks de query ────────────────────────────────────────────────────

export function useLeadLists() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["lead-lists"],
    queryFn: async (): Promise<LeadList[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/lead-lists" as never)
      if (error) throw new Error("Falha ao carregar listas de leads")
      return data as LeadList[]
    },
    staleTime: 30_000,
    enabled: !!session?.accessToken,
  })
}

export function useLeadList(id: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["lead-lists", id],
    queryFn: async (): Promise<LeadListDetail> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/lead-lists/${id}` as never)
      if (error) throw new Error("Falha ao carregar lista")
      return data as LeadListDetail
    },
    staleTime: 30_000,
    enabled: !!session?.accessToken && !!id,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useCreateLeadList() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateLeadListBody): Promise<LeadList> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/lead-lists" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao criar lista")
      return data as LeadList
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["lead-lists"] })
    },
  })
}

export function useUpdateLeadList() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      body,
    }: {
      id: string
      body: UpdateLeadListBody
    }): Promise<LeadList> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PUT(`/lead-lists/${id}` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao atualizar lista")
      return data as LeadList
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["lead-lists"] })
    },
  })
}

export function useDeleteLeadList() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/lead-lists/${id}` as never)
      if (error) throw new Error("Falha ao excluir lista")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["lead-lists"] })
    },
  })
}

export function useAddLeadListMembers() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      listId,
      leadIds,
    }: {
      listId: string
      leadIds: string[]
    }): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.POST(`/lead-lists/${listId}/members` as never, {
        body: { lead_ids: leadIds } as never,
      })
      if (error) throw new Error("Falha ao adicionar leads à lista")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["lead-lists"] })
    },
  })
}

export function useRemoveLeadListMembers() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      listId,
      leadIds,
    }: {
      listId: string
      leadIds: string[]
    }): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/lead-lists/${listId}/members` as never, {
        body: { lead_ids: leadIds } as never,
      })
      if (error) throw new Error("Falha ao remover leads da lista")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["lead-lists"] })
    },
  })
}
