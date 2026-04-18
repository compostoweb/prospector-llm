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

export interface UnipileWebhookStatus {
  url: string
  docs_url: string
  dashboard_url: string
  expected_events: string[]
  expected_sources: UnipileWebhookSourceStatus[]
  secret_configured: boolean
  public_endpoint_healthy: boolean
  public_endpoint_status_code: number | null
  linkedin_account_configured: boolean
  gmail_account_configured: boolean
  api_registration_supported: boolean
  api_registration_ready: boolean
  api_registration_blockers: string[]
  registered_in_unipile: boolean
  registered_webhooks: UnipileRegisteredWebhook[]
  registration_lookup_error: string | null
  supports_signature_auth: boolean
  supports_custom_header_auth: boolean
  auth_headers: Array<"X-Unipile-Signature" | "Unipile-Auth">
  ready: boolean
}

export interface UnipileWebhookSourceStatus {
  source: string
  label: string
  expected_events: string[]
  registered: boolean
  webhook_id: string | null
  enabled: boolean | null
  registered_events: string[]
  missing_events: string[]
  extra_events: string[]
}

export interface UnipileRegisteredWebhook {
  webhook_id: string | null
  source: string | null
  enabled: boolean | null
  events: string[]
}

export interface UnipileWebhookRegistrationItem {
  source: string
  events: string[]
  created: boolean
  already_exists: boolean
  webhook_id: string | null
}

export interface UnipileWebhookRegistrationResult {
  created: boolean
  already_exists: boolean
  request_url: string
  auth_header: "Unipile-Auth"
  webhooks: UnipileWebhookRegistrationItem[]
  message: string
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
  llm_provider: "openai" | "gemini" | "anthropic" | "openrouter"
  llm_model: string
  llm_temperature: number
  llm_max_tokens: number
}

export const DEFAULT_SYSTEM_LLM_CONFIG: TenantLLMConfig = {
  llm_provider: "openai",
  llm_model: "gpt-5.4-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 1024,
}

export const DEFAULT_COLD_EMAIL_LLM_CONFIG: TenantLLMConfig = {
  llm_provider: "openai",
  llm_model: "gpt-5.4-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

function extractApiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") {
    return fallback
  }

  const detail = (error as { detail?: unknown }).detail
  if (typeof detail === "string" && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    return (
      detail
        .map((entry) => {
          if (typeof entry === "string") {
            return entry.trim()
          }
          if (
            entry &&
            typeof entry === "object" &&
            "msg" in entry &&
            typeof entry.msg === "string"
          ) {
            return entry.msg.trim()
          }
          return ""
        })
        .filter(Boolean)
        .join(" ") || fallback
    )
  }

  return fallback
}

function normalizeProvider(
  provider: string | null | undefined,
  fallback: TenantLLMConfig["llm_provider"],
): TenantLLMConfig["llm_provider"] {
  if (
    provider === "openai" ||
    provider === "gemini" ||
    provider === "anthropic" ||
    provider === "openrouter"
  ) {
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

/** Status operacional do webhook da Unipile para o tenant atual */
export function useUnipileWebhookStatus() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["tenant", "me", "unipile-webhook"],
    queryFn: async (): Promise<UnipileWebhookStatus> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/tenants/me/unipile/webhook" as never)
      if (error) throw new Error("Falha ao carregar status do webhook da Unipile")
      return data as UnipileWebhookStatus
    },
    staleTime: 60 * 1000,
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

/** Registra o webhook da Unipile via API usando a configuração atual do backend */
export function useRegisterUnipileWebhook() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<UnipileWebhookRegistrationResult> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/tenants/me/unipile/webhook/register" as never)
      if (error) {
        throw new Error(extractApiErrorMessage(error, "Falha ao registrar webhook da Unipile"))
      }
      return data as UnipileWebhookRegistrationResult
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenant", "me", "unipile-webhook"] })
    },
  })
}
