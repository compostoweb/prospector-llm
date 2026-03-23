"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface TenantIntegration {
  tenant_id: string
  unipile_linkedin_account_id: string | null
  unipile_gmail_account_id: string | null
  pipedrive_api_token: string | null
  pipedrive_domain: string | null
  pipedrive_stage_interest: string | null
  pipedrive_stage_objection: string | null
  pipedrive_owner_id: string | null
  notify_email: string | null
  notify_on_interest: boolean
  notify_on_objection: boolean
  allow_personal_email: boolean
  limit_linkedin_connect: number
  limit_linkedin_dm: number
  limit_email: number
  created_at: string
}

export interface Tenant {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
  integration: TenantIntegration | null
}

export interface UpdateIntegrationsBody {
  unipile_linkedin_account_id?: string | null
  unipile_gmail_account_id?: string | null
  notify_email?: string | null
  notify_on_interest?: boolean
  notify_on_objection?: boolean
  allow_personal_email?: boolean
  limit_linkedin_connect?: number
  limit_linkedin_dm?: number
  limit_email?: number
}

// ── Hooks ─────────────────────────────────────────────────────────────

/** Dados do tenant atual e suas configurações de integração */
export function useTenant() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["tenant", "me"],
    queryFn: async (): Promise<Tenant> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/tenants/me" as never)
      if (error) throw new Error("Falha ao carregar dados do tenant")
      return data as Tenant
    },
    staleTime: 5 * 60 * 1000, // 5min
    enabled: !!session?.accessToken,
  })
}

/** Atualiza configurações de integração do tenant (PUT /tenants/me/integrations) */
export function useUpdateIntegrations() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: UpdateIntegrationsBody): Promise<TenantIntegration> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PUT("/tenants/me/integrations" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao salvar configurações")
      return data as TenantIntegration
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", "me"] })
    },
  })
}
