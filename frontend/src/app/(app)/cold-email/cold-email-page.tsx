"use client"

import Link from "next/link"
import { useState, useMemo } from "react"
import { useSearchParams } from "next/navigation"
import {
  Mail,
  Send,
  Eye,
  MessageSquare,
  AlertCircle,
  Loader2,
  Pause,
  Play,
  ExternalLink,
  FlaskConical,
  ChevronDown,
  AlertTriangle,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import {
  useEmailStats,
  useEmailCadences,
  useEmailOverTime,
  useEmailABResults,
} from "@/lib/api/hooks/use-email-analytics"
import type { EmailAnalyticsRange, EmailOverTimeItem } from "@/lib/api/hooks/use-email-analytics"
import { useCadences } from "@/lib/api/hooks/use-cadences"
import { useCadenceOverview } from "@/lib/api/hooks/use-cadence-analytics"
import { cn } from "@/lib/utils"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import { useQueryClient } from "@tanstack/react-query"
import {
  buildDateFilterValue,
  getRangeQueryFromFilter,
  parseInputDate,
  resolveDateFilterValue,
  type AnalyticsDateFilterValue,
} from "@/lib/analytics-period"
import { toast } from "sonner"

const coldEmailAxisDateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
})

const coldEmailTooltipDateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
})

function formatColdEmailDate(value: string, mode: "axis" | "tooltip" = "axis"): string {
  const parsed = new Date(`${value}T00:00:00`)

  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return mode === "tooltip"
    ? coldEmailTooltipDateFormatter.format(parsed)
    : coldEmailAxisDateFormatter.format(parsed)
}

function buildColdEmailChartData(
  startDate: string,
  endDate: string,
  data: EmailOverTimeItem[] | undefined,
): EmailOverTimeItem[] {
  const byDate = new Map((data ?? []).map((item) => [item.date, item]))
  const timeline: EmailOverTimeItem[] = []
  const current = parseInputDate(startDate)
  const end = parseInputDate(endDate)

  while (current <= end) {
    const dateKey = current.toISOString().slice(0, 10)
    const existing = byDate.get(dateKey)

    timeline.push({
      date: dateKey,
      sent: existing?.sent ?? 0,
      opened: existing?.opened ?? 0,
      replied: existing?.replied ?? 0,
    })

    current.setUTCDate(current.getUTCDate() + 1)
  }

  return timeline
}

function KPICard({
  icon: Icon,
  label,
  value,
  sub,
  variant = "default",
}: {
  icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: "true" }>
  label: string
  value: string | number
  sub?: string | undefined
  variant?: "default" | "accent" | "danger" | "success" | "info" | "warning"
}) {
  const styles: Record<
    NonNullable<typeof variant>,
    {
      card: string
      badge: string
      dot: string
      value: string
      icon: string
      sub: string
    }
  > = {
    default: {
      card: "border-(--border-default) bg-(--bg-surface)",
      badge: "bg-(--bg-overlay) text-(--text-secondary)",
      dot: "bg-(--text-tertiary)",
      value: "text-(--text-primary)",
      icon: "text-(--text-secondary)",
      sub: "text-(--text-tertiary)",
    },
    accent: {
      card: "border-(--accent-subtle-fg)/15 bg-(--bg-surface)",
      badge: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
      dot: "bg-(--accent)",
      value: "text-(--accent)",
      icon: "text-(--accent)",
      sub: "text-(--text-tertiary)",
    },
    success: {
      card: "border-(--success)/15 bg-(--bg-surface)",
      badge: "bg-(--success-subtle) text-(--success-subtle-fg)",
      dot: "bg-(--success)",
      value: "text-(--success)",
      icon: "text-(--success)",
      sub: "text-(--text-tertiary)",
    },
    info: {
      card: "border-(--info)/15 bg-(--bg-surface)",
      badge: "bg-(--info-subtle) text-(--info-subtle-fg)",
      dot: "bg-(--info)",
      value: "text-(--info)",
      icon: "text-(--info)",
      sub: "text-(--text-tertiary)",
    },
    warning: {
      card: "border-(--warning)/15 bg-(--bg-surface)",
      badge: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
      dot: "bg-(--warning)",
      value: "text-(--warning)",
      icon: "text-(--warning)",
      sub: "text-(--text-tertiary)",
    },
    danger: {
      card: "border-(--danger-subtle-fg)/15 bg-(--bg-surface)",
      badge: "bg-(--danger-subtle) text-(--danger-subtle-fg)",
      dot: "bg-(--danger-subtle-fg)",
      value: "text-(--danger-subtle-fg)",
      icon: "text-(--danger-subtle-fg)",
      sub: "text-(--text-tertiary)",
    },
  }

  const tone = styles[variant]

  return (
    <div className={cn("rounded-lg border px-4 py-3 shadow-(--shadow-sm)", tone.card)}>
      <div className="flex items-start justify-between gap-3">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-semibold",
            tone.badge,
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", tone.dot)} />
          <Icon size={12} aria-hidden="true" className={tone.icon} />
          {label}
        </span>
      </div>
      <p className={cn("mt-3 text-2xl font-semibold tracking-tight", tone.value)}>{value}</p>
      {sub ? <p className={cn("mt-1 text-xs", tone.sub)}>{sub}</p> : null}
    </div>
  )
}

// ── Status e ações inline ────────────────────────────────────────────

function CadenceStatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
        isActive
          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
          : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
      )}
    >
      {isActive ? <Play size={9} /> : <Pause size={9} />}
      {isActive ? "Ativa" : "Pausada"}
    </span>
  )
}

function CadenceToggleButton({
  cadenceId,
  isActive,
  iconOnly = false,
}: {
  cadenceId: string
  isActive: boolean
  iconOnly?: boolean
}) {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  const [loading, setLoading] = useState(false)
  const [active, setActive] = useState(isActive)

  async function handleToggle() {
    setLoading(true)
    try {
      const client = createBrowserClient(session?.accessToken)
      await client.PATCH(`/cadences/${cadenceId}` as never, {
        body: { is_active: !active } as never,
      })
      setActive((prev) => !prev)
      toast.success(active ? "Cadência pausada." : "Cadência ativada.")
      await queryClient.invalidateQueries({ queryKey: ["email-analytics"] })
    } catch {
      toast.error("Erro ao alterar status da cadência.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={loading}
      title={active ? "Pausar campanha" : "Ativar campanha"}
      className={cn(
        iconOnly
          ? "inline-flex h-7 w-7 items-center justify-center rounded-md border border-(--border-default) text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) disabled:opacity-50"
          : "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors disabled:opacity-50",
        !iconOnly &&
          (active
            ? "bg-green-100 text-green-700 hover:opacity-75 dark:bg-green-900/30 dark:text-green-400"
            : "bg-yellow-100 text-yellow-700 hover:opacity-75 dark:bg-yellow-900/30 dark:text-yellow-400"),
      )}
      aria-label={active ? "Pausar campanha" : "Ativar campanha"}
    >
      {loading ? (
        <Loader2 size={9} className="animate-spin" />
      ) : active ? (
        <Pause size={9} />
      ) : (
        <Play size={9} />
      )}
      {!iconOnly ? (active ? "Ativa" : "Pausada") : null}
    </button>
  )
}

// ── Seção A/B ─────────────────────────────────────────────────────────

function ABResultsSection({
  cadences,
  range,
}: {
  cadences: { cadence_id: string; cadence_name: string }[]
  range: EmailAnalyticsRange
}) {
  const [selectedCadenceId, setSelectedCadenceId] = useState("")
  const [stepNumber, setStepNumber] = useState(1)
  const { data: abResults, isLoading } = useEmailABResults(selectedCadenceId, stepNumber, range)

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface)">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-(--border-default) px-4 py-3">
        <div className="flex items-center gap-2">
          <FlaskConical size={14} className="text-(--text-secondary)" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-(--text-primary)">Resultados A/B de assunto</h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <select
              value={selectedCadenceId}
              onChange={(e) => setSelectedCadenceId(e.target.value)}
              aria-label="Selecione a cadência"
              className="appearance-none rounded-md border border-(--border-default) bg-(--bg-overlay) pl-3 pr-7 py-1.5 text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
            >
              <option value="">Selecione a cadência…</option>
              {cadences.map((c) => (
                <option key={c.cadence_id} value={c.cadence_id}>
                  {c.cadence_name}
                </option>
              ))}
            </select>
            <ChevronDown
              size={11}
              className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            />
          </div>
          <div className="relative">
            <select
              value={stepNumber}
              onChange={(e) => setStepNumber(Number(e.target.value))}
              aria-label="Número do step"
              className="appearance-none rounded-md border border-(--border-default) bg-(--bg-overlay) pl-3 pr-7 py-1.5 text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  Step {n}
                </option>
              ))}
            </select>
            <ChevronDown
              size={11}
              className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            />
          </div>
        </div>
      </div>

      {!selectedCadenceId ? (
        <p className="px-4 py-8 text-center text-sm text-(--text-tertiary)">
          Selecione uma cadência para ver os resultados A/B dos assuntos.
        </p>
      ) : isLoading ? (
        <div className="flex items-center justify-center gap-2 px-4 py-8 text-sm text-(--text-secondary)">
          <Loader2 size={14} className="animate-spin" />
          Carregando…
        </div>
      ) : !abResults || abResults.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-(--text-tertiary)">
          Sem dados A/B para este step. Configure variantes de assunto na cadência.
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-(--border-subtle) text-left text-xs text-(--text-tertiary)">
              <th className="px-4 py-2">Assunto</th>
              <th className="px-4 py-2 text-right">Enviados</th>
              <th className="px-4 py-2 text-right">Abertos</th>
              <th className="px-4 py-2 text-right">Taxa abertura</th>
            </tr>
          </thead>
          <tbody>
            {abResults.map((r, i) => (
              <tr
                key={i}
                className="border-b border-(--border-subtle) last:border-0 hover:bg-(--bg-overlay)"
              >
                <td className="px-4 py-2.5 text-(--text-primary)">{r.subject || "—"}</td>
                <td className="px-4 py-2.5 text-right text-(--text-secondary)">{r.sent}</td>
                <td className="px-4 py-2.5 text-right text-(--text-secondary)">{r.opened}</td>
                <td className="px-4 py-2.5 text-right">
                  <span
                    className={cn(
                      "font-semibold",
                      r.open_rate >= 40
                        ? "text-green-600 dark:text-green-400"
                        : r.open_rate >= 20
                          ? "text-(--accent)"
                          : "text-(--text-secondary)",
                    )}
                  >
                    {r.open_rate}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────

export default function ColdEmailPage() {
  const searchParams = useSearchParams()
  const dateFilter = useMemo<AnalyticsDateFilterValue>(() => {
    const startDate = searchParams.get("start_date")
    const endDate = searchParams.get("end_date")

    if (startDate && endDate) {
      return resolveDateFilterValue({ startDate, endDate })
    }

    return buildDateFilterValue({ id: "last_30_days", label: "30 dias", days: 30 })
  }, [searchParams])
  const analyticsRange = useMemo<EmailAnalyticsRange>(
    () => getRangeQueryFromFilter(dateFilter),
    [dateFilter],
  )
  const {
    data: stats,
    isLoading: loadingStats,
    isError: statsError,
  } = useEmailStats(analyticsRange)
  const {
    data: cadenceOverview,
    isLoading: loadingOverview,
    isError: cadenceOverviewError,
  } = useCadenceOverview()
  const {
    data: analyticsData,
    isLoading: loadingCadences,
    isError: analyticsError,
  } = useEmailCadences(analyticsRange)
  const {
    data: allEmailCadences,
    isLoading: loadingAllCadences,
    isError: allCadencesError,
  } = useCadences("email_only")
  const { data: overTime, isError: overTimeError } = useEmailOverTime(analyticsRange)
  const hasColdEmailError =
    statsError || analyticsError || allCadencesError || overTimeError || cadenceOverviewError
  const chartData = useMemo(
    () => buildColdEmailChartData(dateFilter.startDate, dateFilter.endDate, overTime),
    [dateFilter.endDate, dateFilter.startDate, overTime],
  )

  // Merge: show all email_only cadences, with analytics when available
  const analyticsMap = new Map((analyticsData ?? []).map((c) => [c.cadence_id, c]))
  const overviewMap = new Map((cadenceOverview ?? []).map((c) => [c.cadence_id, c]))
  const mergedCadences = (allEmailCadences ?? []).map((c) => ({
    cadence_id: c.id,
    cadence_name: c.name,
    lead_count: overviewMap.get(c.id)?.total_leads ?? 0,
    sent: analyticsMap.get(c.id)?.sent ?? 0,
    opened: analyticsMap.get(c.id)?.opened ?? 0,
    replied: analyticsMap.get(c.id)?.replied ?? overviewMap.get(c.id)?.replies ?? 0,
    bounced: analyticsMap.get(c.id)?.bounced ?? 0,
    open_rate: analyticsMap.get(c.id)?.open_rate ?? 0,
    reply_rate: analyticsMap.get(c.id)?.reply_rate ?? 0,
    is_active: c.is_active,
  }))

  return (
    <div className="space-y-3">
      {hasColdEmailError ? (
        <div className="flex items-start gap-3 rounded-lg border border-(--warning) bg-(--warning-subtle) px-4 py-3 text-sm text-(--warning-subtle-fg)">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Não foi possível carregar toda a área de Cold Email.</p>
            <p className="mt-1 text-(--text-secondary)">
              Verifique se a API do backend está acessível antes de revisar métricas e campanhas.
            </p>
          </div>
        </div>
      ) : null}
      {/* KPIs */}
      {loadingStats ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-(--bg-overlay)" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <KPICard icon={Send} label="Enviados" value={stats?.sent ?? 0} variant="default" />
          <KPICard
            icon={Eye}
            label="Taxa de abertura"
            value={`${stats?.open_rate ?? 0}%`}
            sub={`${stats?.opened ?? 0} abertos`}
            variant="accent"
          />
          <KPICard
            icon={MessageSquare}
            label="Taxa de resposta"
            value={`${stats?.reply_rate ?? 0}%`}
            sub={`${stats?.replied ?? 0} respostas`}
            variant="success"
          />
          <KPICard
            icon={Mail}
            label="Total de respostas"
            value={stats?.replied ?? 0}
            sub="Todas as cadências de email puro"
            variant="info"
          />
          <KPICard
            icon={AlertCircle}
            label="Bounce rate"
            value={`${stats?.bounce_rate ?? 0}%`}
            sub={`${stats?.bounced ?? 0} bounces`}
            variant="danger"
          />
        </div>
      )}

      {!loadingStats && (stats?.sent ?? 0) > 0 && (stats?.opened ?? 0) === 0 ? (
        <div className="flex items-start gap-3 rounded-lg border border-(--warning) bg-(--warning-subtle) px-4 py-3 text-sm text-(--warning-subtle-fg)">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Aberturas ainda não foram registradas.</p>
            <p className="mt-1 text-(--text-secondary)">
              Se você já abriu emails dessa campanha, valide no backend uma TRACKING_BASE_URL
              pública. Em ambiente local, pixels apontando para localhost não conseguem registrar
              abertura fora da sua máquina.
            </p>
          </div>
        </div>
      ) : null}

      {/* Gráfico ao longo do tempo */}
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
        <h2 className="mb-4 text-sm font-semibold text-(--text-primary)">
          Evolução no período selecionado
        </h2>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
            <XAxis
              dataKey="date"
              tickFormatter={(value: string) => formatColdEmailDate(value, "axis")}
              tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip
              labelFormatter={(value) => formatColdEmailDate(String(value), "tooltip")}
              contentStyle={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-md)",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="sent"
              name="Enviados"
              stroke="var(--accent)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="opened"
              name="Abertos"
              stroke="var(--success)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="replied"
              name="Respondidos"
              stroke="var(--info)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Tabela de cadências */}
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface)">
        <div className="flex items-center justify-between border-b border-(--border-default) px-4 py-3">
          <h2 className="text-sm font-semibold text-(--text-primary)">Performance por cadência</h2>
          <Link
            href="/cadencias?cadence_type=email_only"
            className="text-xs text-(--accent) hover:underline"
          >
            Ver todas →
          </Link>
        </div>
        {loadingCadences || loadingAllCadences || loadingOverview ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-(--bg-overlay)" />
            ))}
          </div>
        ) : mergedCadences.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-245 w-full text-sm">
              <thead>
                <tr className="border-b border-(--border-subtle) text-left text-xs text-(--text-tertiary)">
                  <th className="px-4 py-2">Cadência</th>
                  <th className="px-4 py-2 text-right">Qtd Leads</th>
                  <th className="px-4 py-2 text-right">Enviados</th>
                  <th className="px-4 py-2 text-right">Qtd Respostas</th>
                  <th className="px-4 py-2 text-right">T. Abertura</th>
                  <th className="px-4 py-2 text-right">T. Resposta</th>
                  <th className="px-4 py-2 text-right">Bounce</th>
                  <th className="px-4 py-2 text-center">Status</th>
                  <th className="px-4 py-2 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {mergedCadences.map((c) => (
                  <tr
                    key={c.cadence_id}
                    className="border-b border-(--border-subtle) last:border-0 hover:bg-(--bg-overlay)"
                  >
                    <td className="px-4 py-2.5">
                      <Link
                        href={`/cadencias/${c.cadence_id}`}
                        className="font-medium text-(--text-primary) hover:underline"
                      >
                        {c.cadence_name}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-right text-(--text-secondary)">
                      {c.lead_count}
                    </td>
                    <td className="px-4 py-2.5 text-right text-(--text-secondary)">
                      {c.sent > 0 ? c.sent : <span className="text-(--text-disabled)">—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right text-(--text-secondary)">{c.replied}</td>
                    <td className="px-4 py-2.5 text-right font-medium text-(--accent)">
                      {c.sent > 0 ? (
                        `${c.open_rate}%`
                      ) : (
                        <span className="text-(--text-disabled)">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium text-green-600 dark:text-green-400">
                      {c.sent > 0 ? (
                        `${c.reply_rate}%`
                      ) : (
                        <span className="text-(--text-disabled)">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          c.bounced > 0 ? "text-red-500" : "text-(--text-tertiary)",
                        )}
                      >
                        {c.bounced}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center align-middle whitespace-nowrap">
                      <CadenceStatusBadge isActive={c.is_active} />
                    </td>
                    <td className="px-4 py-2.5 align-middle">
                      <div className="flex items-center justify-end gap-2">
                        <CadenceToggleButton
                          cadenceId={c.cadence_id}
                          isActive={c.is_active}
                          iconOnly
                        />
                        <Link
                          href={`/cadencias/${c.cadence_id}`}
                          title="Ver cadência"
                          className="flex justify-end text-(--text-tertiary) hover:text-(--text-primary)"
                        >
                          <ExternalLink size={13} />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-center">
            <Mail size={28} className="text-(--text-disabled)" aria-hidden="true" />
            <p className="text-sm text-(--text-secondary)">
              Nenhuma cadência de e-mail criada ainda.
            </p>
            <Link
              href="/cold-email/nova-campanha"
              className="text-sm text-(--accent) hover:underline"
            >
              Criar campanha de e-mail
            </Link>
          </div>
        )}
      </div>

      {/* A/B Results */}
      {mergedCadences.length > 0 && (
        <ABResultsSection cadences={mergedCadences} range={analyticsRange} />
      )}
    </div>
  )
}
