"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

export interface AdminTenant {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
  member_count: number
  admin_count: number
  primary_admin_email: string | null
}

export interface CreateTenantBody {
  name: string
  slug: string
  primary_admin_email?: string | null
  primary_admin_name?: string | null
}

export interface UpdateTenantBody {
  name?: string
  slug?: string
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

export function useAdminTenants() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["admin", "tenants"],
    queryFn: async (): Promise<AdminTenant[]> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/tenants")
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao carregar tenants"))
      }
      return (data as AdminTenant[]) ?? []
    },
    enabled: !!session?.accessToken && session.user.is_superuser,
    staleTime: 30 * 1000,
  })
}

export function useCreateTenant() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateTenantBody): Promise<AdminTenant> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/tenants", { body })
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao criar tenant"))
      }
      return data as AdminTenant
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "tenants"] })
    },
  })
}

export function useUpdateTenant() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ tenantId, body }: { tenantId: string; body: UpdateTenantBody }) => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/tenants/${tenantId}`, { body })
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao atualizar tenant"))
      }
      return data as AdminTenant
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "tenants"] })
    },
  })
}
