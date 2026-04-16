"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

export type TenantRole = "tenant_admin" | "tenant_user"

export interface TenantMember {
  membership_id: string
  user_id: string
  tenant_id: string
  email: string
  name: string | null
  role: TenantRole
  is_active: boolean
  is_superuser: boolean
  joined_at: string
  invited_by_email: string | null
  created_at: string
  updated_at: string
}

export interface InviteTenantMemberBody {
  email: string
  name?: string | null
  role: TenantRole
}

export interface UpdateTenantMemberBody {
  role: TenantRole
  is_active?: boolean
}

function extractApiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") {
    return fallback
  }

  const detail = (error as { detail?: unknown }).detail
  if (typeof detail === "string" && detail.trim()) {
    return detail
  }

  return fallback
}

export function useTenantMembers() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["tenant", "members"],
    queryFn: async (): Promise<TenantMember[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/tenants/me/members")
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao carregar membros"))
      }
      return (data as TenantMember[]) ?? []
    },
    enabled:
      !!session?.accessToken &&
      (session.user.is_superuser || session.user.tenant_role === "tenant_admin"),
    staleTime: 30 * 1000,
  })
}

export function useInviteTenantMember() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: InviteTenantMemberBody): Promise<TenantMember> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/tenants/me/members", { body })
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao convidar membro"))
      }
      return data as TenantMember
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", "members"] })
    },
  })
}

export function useUpdateTenantMember() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      membershipId,
      body,
    }: {
      membershipId: string
      body: UpdateTenantMemberBody
    }): Promise<TenantMember> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/tenants/me/members/${membershipId}`, { body })
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao atualizar membro"))
      }
      return data as TenantMember
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", "members"] })
    },
  })
}

export function useRemoveTenantMember() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (membershipId: string): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/tenants/me/members/${membershipId}`)
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao remover membro"))
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", "members"] })
    },
  })
}
