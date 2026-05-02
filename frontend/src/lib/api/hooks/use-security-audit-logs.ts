"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import type { components } from "@/lib/api/schema"

export type SecurityAuditLogItem = components["schemas"]["SecurityAuditLogResponse"]
export type SecurityAuditLogListResponse = components["schemas"]["SecurityAuditLogListResponse"]

export interface SecurityAuditLogFilters {
  scopeTenantId?: string
  eventType?: string
  resourceType?: string
  status?: string
  limit?: number
  offset?: number
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

export function useSecurityAuditLogs(filters: SecurityAuditLogFilters) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["admin", "security-audit-logs", filters],
    queryFn: async (): Promise<SecurityAuditLogListResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET<SecurityAuditLogListResponse>(
        "/security-audit-logs",
        {
          params: {
            query: {
              scope_tenant_id: filters.scopeTenantId,
              event_type: filters.eventType,
              resource_type: filters.resourceType,
              status: filters.status,
              limit: filters.limit ?? 25,
              offset: filters.offset ?? 0,
            },
          },
        },
      )

      if (error) {
        throw new Error(
          extractApiErrorMessage(error, "Falha ao carregar a trilha de auditoria."),
        )
      }

      return data ?? { items: [], total: 0 }
    },
    enabled: !!session?.accessToken && session.user.is_superuser,
    staleTime: 15 * 1000,
  })
}