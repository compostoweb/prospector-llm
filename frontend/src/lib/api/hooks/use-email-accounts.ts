"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

interface EmailAccountsQueryData {
  accounts: EmailAccount[]
  total: number
}

function mergeEmailAccountIntoCache(
  current: EmailAccountsQueryData | undefined,
  updated: EmailAccount,
): EmailAccountsQueryData | undefined {
  if (!current) return current

  return {
    ...current,
    accounts: current.accounts.map((account) => (account.id === updated.id ? updated : account)),
  }
}

// ── Tipos ─────────────────────────────────────────────────────────────

export interface EmailAccount {
  id: string
  tenant_id: string
  display_name: string
  email_address: string
  owner_user_id: string | null
  owner_email: string | null
  owner_name: string | null
  created_by_user_id: string | null
  from_name: string | null
  provider_type: "unipile_gmail" | "google_oauth" | "smtp"
  effective_provider_type: "unipile_gmail" | "google_oauth" | "smtp"
  outbound_uses_fallback: boolean
  unipile_account_id: string | null
  smtp_host: string | null
  smtp_port: number | null
  smtp_username: string | null
  smtp_use_tls: boolean
  imap_host: string | null
  imap_port: number | null
  imap_use_ssl: boolean
  daily_send_limit: number
  is_active: boolean
  provider_status: string | null
  last_status_at: string | null
  last_health_check_at: string | null
  health_error: string | null
  connected_at: string | null
  disconnected_at: string | null
  reconnect_required_at: string | null
  is_warmup_enabled: boolean
  email_signature: string | null
  created_at: string
  updated_at: string
}

export interface CreateUnipileAccountBody {
  display_name: string
  email_address: string
  from_name?: string | null
  unipile_account_id: string
  daily_send_limit?: number
}

export interface CreateSMTPAccountBody {
  display_name: string
  email_address: string
  from_name?: string | null
  smtp_host: string
  smtp_port?: number
  smtp_username: string
  smtp_password: string
  smtp_use_tls?: boolean
  daily_send_limit?: number
  imap_host?: string
  imap_port?: number
  imap_use_ssl?: boolean
  imap_password?: string
}

export interface SMTPTestBody {
  smtp_host: string
  smtp_port: number
  smtp_username: string
  smtp_password: string
  smtp_use_tls: boolean
}

export interface UpdateAccountBody {
  display_name?: string
  from_name?: string | null
  daily_send_limit?: number
  is_active?: boolean
  is_warmup_enabled?: boolean
  email_signature?: string | null
  imap_host?: string | null
  imap_port?: number | null
  imap_use_ssl?: boolean
  imap_password?: string | null
}

// ── Query hooks ───────────────────────────────────────────────────────

export function useEmailAccounts() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-accounts"],
    queryFn: async (): Promise<{ accounts: EmailAccount[]; total: number }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/email-accounts" as never)
      if (error) throw new Error("Falha ao carregar contas de e-mail")
      return data as { accounts: EmailAccount[]; total: number }
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailAccountStatus(accountId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-account-status", accountId],
    queryFn: async () => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/email-accounts/${accountId}/status` as never)
      if (error) throw new Error("Falha ao verificar status")
      return data as { is_reachable: boolean; error: string | null }
    },
    enabled: !!session?.accessToken && !!accountId,
    staleTime: 30 * 1000,
  })
}

export function useGoogleOAuthUrl() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["google-oauth-url"],
    queryFn: async (): Promise<string> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/email-accounts/google/authorize" as never)
      if (error) throw new Error("Falha ao obter URL OAuth")
      return (data as { auth_url: string }).auth_url
    },
    enabled: !!session?.accessToken,
    staleTime: 5 * 60 * 1000,
  })
}

// ── Mutation hooks ────────────────────────────────────────────────────

export function useCreateUnipileAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateUnipileAccountBody): Promise<EmailAccount> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/email-accounts/unipile" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao criar conta Unipile")
      return data as EmailAccount
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["email-accounts"] }),
  })
}

export function useCreateSMTPAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateSMTPAccountBody): Promise<EmailAccount> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/email-accounts/smtp" as never, {
        body: body as never,
      })
      if (error) {
        const errMsg = (error as { detail?: string }).detail ?? "Falha ao criar conta SMTP"
        throw new Error(errMsg)
      }
      return data as EmailAccount
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["email-accounts"] }),
  })
}

export function useTestSMTP() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async (body: SMTPTestBody): Promise<{ ok: boolean; error: string | null }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/email-accounts/smtp/test" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao testar SMTP")
      return data as { ok: boolean; error: string | null }
    },
  })
}

export function useUpdateEmailAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      body,
    }: {
      id: string
      body: UpdateAccountBody
    }): Promise<EmailAccount> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/email-accounts/${id}` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao atualizar conta")
      return data as EmailAccount
    },
    onSuccess: (updated) => {
      qc.setQueryData<EmailAccountsQueryData | undefined>(["email-accounts"], (current) =>
        mergeEmailAccountIntoCache(current, updated),
      )
      void qc.invalidateQueries({ queryKey: ["email-accounts"] })
    },
  })
}

export function useDeleteEmailAccount() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/email-accounts/${id}` as never)
      if (error) throw new Error("Falha ao remover conta")
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["email-accounts"] }),
  })
}

export function useFetchGmailSignature() {
  const { data: session } = useSession()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({
      accountId,
      save,
    }: {
      accountId: string
      save: boolean
    }): Promise<{ signature: string | null; send_as_email: string }> => {
      const client = createBrowserClient(session?.accessToken)
      const url = `/email-accounts/${accountId}/gmail-signature?save=${save}` as never
      const { data, error } = await client.GET(url)
      if (error) {
        const detail = (error as { detail?: string }).detail ?? "Erro ao buscar assinatura"
        throw new Error(detail)
      }
      return data as { signature: string | null; send_as_email: string }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["email-accounts"] }),
  })
}
