"use client"

import { useMemo, useState, useTransition } from "react"
import { Activity, ChevronLeft, ChevronRight, Loader2, RefreshCw, ShieldAlert } from "lucide-react"
import { EmptyState } from "@/components/shared/empty-state"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { SettingsCallout, SettingsPageShell, SettingsPanel } from "@/components/settings/settings-shell"
import { useAdminTenants } from "@/lib/api/hooks/use-admin-tenants"
import {
  useSecurityAuditLogs,
  type SecurityAuditLogItem,
} from "@/lib/api/hooks/use-security-audit-logs"
import { formatRelativeTime, truncate } from "@/lib/utils"

const PAGE_SIZE = 25

type AuditStatusFilter = "all" | "success" | "failure"

interface DraftFilters {
  tenantId: string
  status: AuditStatusFilter
  resourceType: string
  eventType: string
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value))
}

function getStatusVariant(status: string) {
  switch (status) {
    case "success":
      return "success" as const
    case "failure":
      return "danger" as const
    case "denied":
      return "warning" as const
    default:
      return "outline" as const
  }
}

function buildMetadataPreview(item: SecurityAuditLogItem): string | null {
  if (!item.event_metadata) {
    return null
  }

  return truncate(JSON.stringify(item.event_metadata), 280)
}

export default function AuditoriaSegurancaPage() {
  const { data: tenants = [] } = useAdminTenants()
  const [page, setPage] = useState(1)
  const [isApplyingFilters, startTransition] = useTransition()
  const [draftFilters, setDraftFilters] = useState<DraftFilters>({
    tenantId: "all",
    status: "all",
    resourceType: "",
    eventType: "",
  })
  const [appliedFilters, setAppliedFilters] = useState<DraftFilters>({
    tenantId: "all",
    status: "all",
    resourceType: "",
    eventType: "",
  })

  const auditLogsQuery = useSecurityAuditLogs({
    ...(appliedFilters.tenantId !== "all" ? { scopeTenantId: appliedFilters.tenantId } : {}),
    ...(appliedFilters.status !== "all" ? { status: appliedFilters.status } : {}),
    ...(appliedFilters.resourceType.trim()
      ? { resourceType: appliedFilters.resourceType.trim() }
      : {}),
    ...(appliedFilters.eventType.trim() ? { eventType: appliedFilters.eventType.trim() } : {}),
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })

  const tenantNameById = useMemo(() => {
    return new Map(tenants.map((tenant) => [tenant.id, tenant.name]))
  }, [tenants])

  const totalItems = auditLogsQuery.data?.total ?? 0
  const auditItems = useMemo(() => auditLogsQuery.data?.items ?? [], [auditLogsQuery.data?.items])
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE))

  const visibleCounts = useMemo(() => {
    return auditItems.reduce(
      (accumulator, item) => {
        accumulator.total += 1
        if (item.status === "success") {
          accumulator.success += 1
        }
        if (item.status === "failure") {
          accumulator.failure += 1
        }
        if (!item.scope_tenant_id) {
          accumulator.global += 1
        }
        return accumulator
      },
      { total: 0, success: 0, failure: 0, global: 0 },
    )
  }, [auditItems])

  function applyFilters() {
    startTransition(() => {
      setPage(1)
      setAppliedFilters(draftFilters)
    })
  }

  function clearFilters() {
    const cleared = { tenantId: "all", status: "all", resourceType: "", eventType: "" } satisfies DraftFilters
    startTransition(() => {
      setPage(1)
      setDraftFilters(cleared)
      setAppliedFilters(cleared)
    })
  }

  return (
    <SettingsPageShell
      title="Auditoria de segurança"
      description="Consulte eventos sensíveis e administrativos do sistema, com escopo por tenant, status e tipo de recurso."
      actions={
        <Button
          variant="outline"
          onClick={() => void auditLogsQuery.refetch()}
          disabled={auditLogsQuery.isFetching}
        >
          <RefreshCw size={14} className={auditLogsQuery.isFetching ? "animate-spin" : undefined} />
          Atualizar
        </Button>
      }
    >
      <SettingsCallout icon={<ShieldAlert size={16} />} title="Escopo da consulta">
        Esta tela usa a trilha persistida do backend e exibe eventos globais de superadmin e
        eventos por tenant conforme os filtros aplicados.
      </SettingsCallout>

      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-4">
          <SettingsPanel
            title="Filtros"
            description="Refine a consulta antes de disparar a leitura no backend."
            contentClassName="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="audit-tenant">Tenant</Label>
              <Select
                value={draftFilters.tenantId}
                onValueChange={(value) => setDraftFilters((current) => ({ ...current, tenantId: value }))}
              >
                <SelectTrigger id="audit-tenant">
                  <SelectValue placeholder="Todos os tenants" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os tenants</SelectItem>
                  {tenants.map((tenant) => (
                    <SelectItem key={tenant.id} value={tenant.id}>
                      {tenant.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="audit-status">Status</Label>
              <Select
                value={draftFilters.status}
                onValueChange={(value) =>
                  setDraftFilters((current) => ({
                    ...current,
                    status: value as AuditStatusFilter,
                  }))
                }
              >
                <SelectTrigger id="audit-status">
                  <SelectValue placeholder="Todos os status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os status</SelectItem>
                  <SelectItem value="success">Sucesso</SelectItem>
                  <SelectItem value="failure">Falha</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="audit-resource-type">Tipo de recurso</Label>
              <Input
                id="audit-resource-type"
                value={draftFilters.resourceType}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    resourceType: event.target.value,
                  }))
                }
                placeholder="Ex.: user, content_post"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="audit-event-type">Evento</Label>
              <Input
                id="audit-event-type"
                value={draftFilters.eventType}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    eventType: event.target.value,
                  }))
                }
                placeholder="Ex.: auth.login, admin.user_create"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={applyFilters} disabled={isApplyingFilters}>
                {isApplyingFilters ? <Loader2 size={14} className="animate-spin" /> : null}
                Aplicar filtros
              </Button>
              <Button variant="outline" onClick={clearFilters} disabled={isApplyingFilters}>
                Limpar
              </Button>
            </div>
          </SettingsPanel>

          <SettingsPanel
            title="Resumo da página"
            description="Contagens calculadas sobre os eventos retornados na página atual."
          >
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-(--text-tertiary)">Eventos</p>
                <p className="mt-2 text-2xl font-semibold text-(--text-primary)">
                  {visibleCounts.total}
                </p>
              </div>
              <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-(--text-tertiary)">Sucessos</p>
                <p className="mt-2 text-2xl font-semibold text-(--text-primary)">
                  {visibleCounts.success}
                </p>
              </div>
              <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-(--text-tertiary)">Falhas</p>
                <p className="mt-2 text-2xl font-semibold text-(--text-primary)">
                  {visibleCounts.failure}
                </p>
              </div>
              <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-(--text-tertiary)">Globais</p>
                <p className="mt-2 text-2xl font-semibold text-(--text-primary)">
                  {visibleCounts.global}
                </p>
              </div>
            </div>
          </SettingsPanel>
        </div>

        <SettingsPanel
          title="Eventos"
          description={`${totalItems.toLocaleString("pt-BR")} eventos encontrados no total.`}
          contentClassName="space-y-4"
          headerAside={
            <Badge variant="outline">
              Página {page} de {totalPages}
            </Badge>
          }
        >
          {auditLogsQuery.isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <Loader2 size={18} className="animate-spin text-(--text-tertiary)" />
            </div>
          ) : auditLogsQuery.isError ? (
            <EmptyState
              icon={ShieldAlert}
              title="Falha ao carregar auditoria"
              description={auditLogsQuery.error.message}
              action={
                <Button variant="outline" onClick={() => void auditLogsQuery.refetch()}>
                  Tentar novamente
                </Button>
              }
            />
          ) : auditItems.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="Nenhum evento encontrado"
              description="Ajuste os filtros ou amplie o escopo para visualizar eventos persistidos." 
            />
          ) : (
            <>
              <div className="space-y-3">
                {auditItems.map((item) => {
                  const metadataPreview = buildMetadataPreview(item)
                  const tenantLabel = item.scope_tenant_id
                    ? tenantNameById.get(item.scope_tenant_id) ?? item.scope_tenant_id
                    : "Global"

                  return (
                    <article
                      key={item.id}
                      className="rounded-xl border border-(--border-default) bg-(--bg-page) p-4"
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={getStatusVariant(item.status)}>{item.status}</Badge>
                            <Badge variant="outline">{item.event_type}</Badge>
                            <Badge variant="neutral">{item.resource_type}</Badge>
                            <Badge variant="outline">{item.action}</Badge>
                          </div>
                          <div className="space-y-1">
                            <p className="text-sm font-medium text-(--text-primary)">
                              {item.message ?? "Evento sem mensagem detalhada."}
                            </p>
                            <p className="text-xs text-(--text-secondary)">
                              Tenant: {tenantLabel}
                              {item.resource_id ? ` · Recurso: ${truncate(item.resource_id, 48)}` : ""}
                              {item.actor_user_id
                                ? ` · Usuário: ${truncate(item.actor_user_id, 18)}`
                                : ""}
                            </p>
                          </div>
                        </div>

                        <div className="text-left text-xs text-(--text-tertiary) lg:text-right">
                          <time dateTime={item.created_at}>{formatRelativeTime(item.created_at)}</time>
                          <p>{formatTimestamp(item.created_at)}</p>
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_280px]">
                        <div className="grid gap-2 sm:grid-cols-2">
                          <div className="rounded-lg border border-(--border-subtle) bg-(--bg-surface) p-3">
                            <p className="text-[11px] uppercase tracking-[0.16em] text-(--text-tertiary)">
                              IP
                            </p>
                            <p className="mt-1 break-all text-sm text-(--text-primary)">
                              {item.ip_address ?? "Não registrado"}
                            </p>
                          </div>
                          <div className="rounded-lg border border-(--border-subtle) bg-(--bg-surface) p-3">
                            <p className="text-[11px] uppercase tracking-[0.16em] text-(--text-tertiary)">
                              User-Agent
                            </p>
                            <p className="mt-1 text-sm text-(--text-primary)">
                              {item.user_agent ? truncate(item.user_agent, 82) : "Não registrado"}
                            </p>
                          </div>
                        </div>

                        <div className="rounded-lg border border-(--border-subtle) bg-(--bg-surface) p-3">
                          <p className="text-[11px] uppercase tracking-[0.16em] text-(--text-tertiary)">
                            Metadata
                          </p>
                          <p className="mt-1 wrap-break-word text-sm text-(--text-primary)">
                            {metadataPreview ?? "Sem metadata associada."}
                          </p>
                        </div>
                      </div>
                    </article>
                  )
                })}
              </div>

              <div className="flex flex-col gap-3 border-t border-(--border-subtle) pt-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-(--text-secondary)">
                  Exibindo {(page - 1) * PAGE_SIZE + 1}–
                  {Math.min(page * PAGE_SIZE, totalItems)} de {totalItems.toLocaleString("pt-BR")}
                  .
                </p>
                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                    disabled={page <= 1 || auditLogsQuery.isFetching}
                  >
                    <ChevronLeft size={14} />
                    Anterior
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                    disabled={page >= totalPages || auditLogsQuery.isFetching}
                  >
                    Próxima
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            </>
          )}
        </SettingsPanel>
      </div>
    </SettingsPageShell>
  )
}