"use client"

import { useMemo, useState } from "react"
import { AlertTriangle, Link2Off, Mail, MessageSquare, Send, Users } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { AnalyticsPeriodFilter } from "@/components/shared/analytics-period-filter"
import { Badge } from "@/components/ui/badge"
import { useTeamAnalytics, type TeamUserAnalytics } from "@/lib/api/hooks/use-analytics"
import {
  buildDateFilterValue,
  getRangeQueryFromFilter,
  type AnalyticsDateFilterValue,
} from "@/lib/analytics-period"

function roleLabel(role: string) {
  return role === "tenant_admin" ? "Admin" : "Operador"
}

function formatLastActivity(value: string | null) {
  if (!value) return "Sem atividade"
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

function initialsFor(user: TeamUserAnalytics) {
  const source = user.name || user.email
  return source
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("")
}

export default function EquipeMetricsPage() {
  const [dateFilter, setDateFilter] = useState<AnalyticsDateFilterValue>(() =>
    buildDateFilterValue({ id: "last_30_days", label: "30 dias", days: 30 }),
  )
  const analyticsRange = useMemo(() => getRangeQueryFromFilter(dateFilter), [dateFilter])
  const { data, isLoading, isError } = useTeamAnalytics(analyticsRange)
  const users = data?.users ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Métricas da equipe</h1>
          <p className="text-sm text-(--text-secondary)">
            Performance por usuário a partir das contas conectadas no tenant.
          </p>
        </div>
        <AnalyticsPeriodFilter value={dateFilter} onChange={setDateFilter} />
      </div>

      {isError && (
        <div className="flex items-start gap-3 rounded-lg border border-(--warning) bg-(--warning-subtle) px-4 py-3 text-sm text-(--warning-subtle-fg)">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Não foi possível carregar as métricas da equipe.</p>
            <p className="mt-1 text-(--text-secondary)">
              Verifique se a API está acessível e se o backend está atualizado.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard
          label="Usuários ativos"
          value={isLoading ? "—" : (data?.active_users ?? 0)}
          icon={Users}
        />
        <StatCard label="Envios" value={isLoading ? "—" : (data?.steps_sent ?? 0)} icon={Send} />
        <StatCard
          label="Respostas"
          value={isLoading ? "—" : (data?.replies ?? 0)}
          icon={MessageSquare}
        />
        <StatCard
          label="Taxa de resposta"
          value={isLoading ? "—" : `${(data?.reply_rate ?? 0).toFixed(1)}%`}
          icon={MessageSquare}
        />
        <StatCard
          label="Reconexões"
          value={
            isLoading
              ? "—"
              : users.reduce((total, user) => total + user.reconnect_required_accounts, 0)
          }
          icon={Link2Off}
        />
      </div>

      <div className="overflow-hidden rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
        <div className="flex items-center justify-between border-b border-(--border-subtle) px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-(--text-primary)">Usuários</h2>
            <p className="text-xs text-(--text-tertiary)">
              {isLoading ? "Carregando" : `${users.length} usuários no tenant`}
            </p>
          </div>
          <Mail size={16} className="text-(--text-tertiary)" aria-hidden="true" />
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-(--bg-sunken) text-xs uppercase text-(--text-tertiary)">
              <tr>
                <th className="px-5 py-3 text-left font-medium">Usuário</th>
                <th className="px-4 py-3 text-left font-medium">Contas</th>
                <th className="px-4 py-3 text-right font-medium">Envios</th>
                <th className="px-4 py-3 text-right font-medium">Email</th>
                <th className="px-4 py-3 text-right font-medium">LinkedIn</th>
                <th className="px-4 py-3 text-right font-medium">Respostas</th>
                <th className="px-4 py-3 text-right font-medium">Taxa</th>
                <th className="px-5 py-3 text-left font-medium">Última atividade</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-(--border-subtle)">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-5 py-10 text-center text-sm text-(--text-secondary)"
                  >
                    Carregando métricas
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-5 py-10 text-center text-sm text-(--text-secondary)"
                  >
                    Nenhum usuário encontrado
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.user_id} className="hover:bg-(--bg-overlay)">
                    <td className="px-5 py-4">
                      <div className="flex min-w-56 items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-(--accent-subtle) text-xs font-semibold text-(--accent-subtle-fg)">
                          {initialsFor(user)}
                        </div>
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate font-medium text-(--text-primary)">
                              {user.name || user.email}
                            </p>
                            <Badge variant={user.role === "tenant_admin" ? "default" : "outline"}>
                              {roleLabel(user.role)}
                            </Badge>
                            <Badge variant={user.is_active ? "success" : "outline"}>
                              {user.is_active ? "Ativo" : "Inativo"}
                            </Badge>
                          </div>
                          <p className="truncate text-xs text-(--text-tertiary)">{user.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-(--text-secondary)">
                      <div className="flex flex-wrap gap-1.5">
                        <Badge variant="outline">{user.email_accounts} email</Badge>
                        <Badge variant="outline">{user.linkedin_accounts} LinkedIn</Badge>
                        {user.reconnect_required_accounts > 0 ? (
                          <Badge variant="warning">
                            {user.reconnect_required_accounts} reconectar
                          </Badge>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right font-medium text-(--text-primary)">
                      {user.steps_sent}
                    </td>
                    <td className="px-4 py-4 text-right text-(--text-secondary)">
                      {user.email_sent}
                    </td>
                    <td className="px-4 py-4 text-right text-(--text-secondary)">
                      {user.linkedin_sent}
                    </td>
                    <td className="px-4 py-4 text-right text-(--text-secondary)">
                      {user.replies}
                      {user.interested_replies > 0 ? (
                        <span className="ml-1 text-xs text-(--success)">
                          +{user.interested_replies}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-4 text-right text-(--text-secondary)">
                      {user.reply_rate.toFixed(1)}%
                    </td>
                    <td className="px-5 py-4 text-(--text-secondary)">
                      {formatLastActivity(user.last_activity_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
