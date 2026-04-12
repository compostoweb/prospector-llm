"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface TenantIntegration {
  tenant_id: string
  unipile_linkedin_account_id: string | null
  unipile_gmail_account_id: string | null
  pipedrive_api_token_set: boolean
  pipedrive_domain: string | null
  pipedrive_owner_id: number | null
  pipedrive_stage_interest: number | null
  pipedrive_stage_objection: number | null
  notify_email: string | null
  notify_on_interest: boolean
  notify_on_objection: boolean
  allow_personal_email: boolean
  limit_linkedin_connect: number
  limit_linkedin_dm: number
  limit_email: number
  // LLM — padrão do sistema
  llm_default_provider: string
  llm_default_model: string
  llm_default_temperature: number
  llm_default_max_tokens: number
  // LLM — padrão Cold Email
  cold_email_llm_provider: string
  cold_email_llm_model: string
  cold_email_llm_temperature: number
  cold_email_llm_max_tokens: number
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
  pipedrive_api_token?: string | null
  pipedrive_domain?: string | null
  pipedrive_stage_interest?: number | null
  pipedrive_stage_objection?: number | null
  pipedrive_owner_id?: number | null
  notify_email?: string | null
  notify_on_interest?: boolean
  notify_on_objection?: boolean
  allow_personal_email?: boolean
  limit_linkedin_connect?: number
  limit_linkedin_dm?: number
  limit_email?: number
  // LLM — padrão do sistema
  llm_default_provider?: string
  llm_default_model?: string
  llm_default_temperature?: number
  llm_default_max_tokens?: number
  // LLM — padrão Cold Email
  cold_email_llm_provider?: string
  cold_email_llm_model?: string
  cold_email_llm_temperature?: number
  cold_email_llm_max_tokens?: number
}

export interface TenantLLMConfig {
  llm_provider: "openai" | "gemini" | "anthropic"
  llm_model: string
  llm_temperature: number
  llm_max_tokens: number
}

export const DEFAULT_SYSTEM_LLM_CONFIG: TenantLLMConfig = {
  llm_provider: "openai",
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 1024,
}

export const DEFAULT_COLD_EMAIL_LLM_CONFIG: TenantLLMConfig = {
  llm_provider: "openai",
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

function normalizeProvider(
  provider: string | null | undefined,
  fallback: TenantLLMConfig["llm_provider"],
): TenantLLMConfig["llm_provider"] {
  if (provider === "openai" || provider === "gemini" || provider === "anthropic") {
    return provider
  }
  return fallback
}

export function getTenantLLMConfig(
  integration: TenantIntegration | null | undefined,
  scope: "system" | "cold_email" = "system",
): TenantLLMConfig {
  const fallback =
    scope === "cold_email" ? DEFAULT_COLD_EMAIL_LLM_CONFIG : DEFAULT_SYSTEM_LLM_CONFIG

  if (!integration) {
    return fallback
  }

  if (scope === "cold_email") {
    return {
      llm_provider: normalizeProvider(integration.cold_email_llm_provider, fallback.llm_provider),
      llm_model: integration.cold_email_llm_model || fallback.llm_model,
      llm_temperature: integration.cold_email_llm_temperature ?? fallback.llm_temperature,
      llm_max_tokens: integration.cold_email_llm_max_tokens ?? fallback.llm_max_tokens,
    }
  }

  return {
    llm_provider: normalizeProvider(integration.llm_default_provider, fallback.llm_provider),
    llm_model: integration.llm_default_model || fallback.llm_model,
    llm_temperature: integration.llm_default_temperature ?? fallback.llm_temperature,
    llm_max_tokens: integration.llm_default_max_tokens ?? fallback.llm_max_tokens,
  }
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
