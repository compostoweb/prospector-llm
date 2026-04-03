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
  provider_type: "unipile" | "native"
  unipile_account_id: string | null
  is_active: boolean
  last_polled_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateUnipileLinkedInAccountBody {
  display_name: string
  linkedin_username?: string | null
  unipile_account_id: string
}

export interface CreateNativeLinkedInAccountBody {
  display_name: string
  linkedin_username: string
  li_at_cookie: string
}

export interface UpdateLinkedInAccountBody {
  display_name?: string
  linkedin_username?: string | null
  is_active?: boolean
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
