"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface LinkedInAccount {
  id: string
  tenant_id: string
  display_name: string
  linkedin_username: string | null
  owner_user_id: string | null
  owner_email: string | null
  owner_name: string | null
  created_by_user_id: string | null
  provider_type: "unipile" | "native"
  unipile_account_id: string | null
  is_active: boolean
  supports_inmail: boolean
  provider_status: string | null
  last_status_at: string | null
  last_health_check_at: string | null
  health_error: string | null
  connected_at: string | null
  disconnected_at: string | null
  reconnect_required_at: string | null
  last_polled_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateUnipileLinkedInAccountBody {
  display_name: string
  linkedin_username?: string | null
  supports_inmail?: boolean
  unipile_account_id: string
}

export interface CreateUnipileHostedAuthBody {
  display_name: string
  linkedin_username?: string | null
  supports_inmail?: boolean
}

export interface CreateNativeLinkedInAccountBody {
  display_name: string
  linkedin_username: string
  supports_inmail?: boolean
  li_at_cookie: string
}

export interface UpdateLinkedInAccountBody {
  display_name?: string
  linkedin_username?: string | null
  is_active?: boolean
  supports_inmail?: boolean
}

export interface LinkedInAccountStatus {
  account_id: string
  is_active: boolean
  provider_type: string
  ping_ok: boolean
  error: string | null
}

// ── Query hooks ───────────────────────────────────────────────────────

export function useLinkedInAccounts() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["linkedin-accounts"],
    queryFn: async (): Promise<{ accounts: LinkedInAccount[]; total: number }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/linkedin-accounts" as never)
      if (error) throw new Error("Falha ao carregar contas LinkedIn")
      return data as { accounts: LinkedInAccount[]; total: number }
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useLinkedInAccountStatus(accountId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["linkedin-account-status", accountId],
    queryFn: async (): Promise<LinkedInAccountStatus> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/linkedin-accounts/${accountId}/status` as never)
      if (error) throw new Error("Falha ao verificar status")
      return data as LinkedInAccountStatus
    },
    enabled: !!session?.accessToken && !!accountId,
    staleTime: 30 * 1000,
  })
}

// ── Mutation hooks ────────────────────────────────────────────────────

export function useCreateUnipileLinkedInAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateUnipileLinkedInAccountBody): Promise<LinkedInAccount> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/linkedin-accounts/unipile" as never, {
        body: body as never,
      })
      if (error) {
        const errMsg = (error as { detail?: string }).detail ?? "Falha ao criar conta Unipile"
        throw new Error(errMsg)
      }
      return data as LinkedInAccount
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["linkedin-accounts"] }),
  })
}

export function useCreateUnipileHostedAuthLink() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async (body: CreateUnipileHostedAuthBody): Promise<{ auth_url: string }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/linkedin-accounts/unipile/hosted-auth" as never, {
        body: body as never,
      })
      if (error) {
        const errMsg = (error as { detail?: string }).detail ?? "Falha ao iniciar conexão Unipile"
        throw new Error(errMsg)
      }
      return data as { auth_url: string }
    },
  })
}

export function useCreateUnipileReconnectLink() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async (accountId: string): Promise<{ auth_url: string }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST(
        `/linkedin-accounts/${accountId}/unipile/reconnect-link` as never,
      )
      if (error) {
        const errMsg = (error as { detail?: string }).detail ?? "Falha ao iniciar reconexão Unipile"
        throw new Error(errMsg)
      }
      return data as { auth_url: string }
    },
  })
}

export function useCreateNativeLinkedInAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateNativeLinkedInAccountBody): Promise<LinkedInAccount> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/linkedin-accounts/native" as never, {
        body: body as never,
      })
      if (error) {
        const errMsg = (error as { detail?: string }).detail ?? "Cookie li_at inválido ou expirado"
        throw new Error(errMsg)
      }
      return data as LinkedInAccount
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["linkedin-accounts"] }),
  })
}

export function useUpdateLinkedInAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      body,
    }: {
      id: string
      body: UpdateLinkedInAccountBody
    }): Promise<LinkedInAccount> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/linkedin-accounts/${id}` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao atualizar conta LinkedIn")
      return data as LinkedInAccount
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["linkedin-accounts"] }),
  })
}

export function useDeleteLinkedInAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/linkedin-accounts/${id}` as never)
      if (error) throw new Error("Falha ao remover conta LinkedIn")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["linkedin-accounts"] }),
  })
}
