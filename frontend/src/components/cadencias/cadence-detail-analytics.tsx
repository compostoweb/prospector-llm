"use client"

import type { Route } from "next"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { AlertTriangle, Clock3, Gauge, MessageSquare, Send, Users } from "lucide-react"
import { AnalyticsPeriodFilter } from "@/components/shared/analytics-period-filter"
import { StatCard } from "@/components/dashboard/stat-card"
import { BadgeChannel } from "@/components/shared/badge-channel"
import type { Cadence } from "@/lib/api/hooks/use-cadences"
import {
  buildDateFilterValue,
  formatSelectedRangeLabel,
  getRangeQueryFromFilter,
  resolveDateFilterValue,
  type AnalyticsDateFilterValue,
} from "@/lib/analytics-period"
import {
  useCadenceABTestResults,
  useCadenceAnalytics,
  useCadenceDeliveryBudget,
  type CadenceDeliveryBudgetItem,
} from "@/lib/api/hooks/use-cadence-analytics"

interface CadenceDetailAnalyticsProps {
  cadence: Cadence
}

const PERIOD_OPTIONS = new Map([
  [7, { id: "last_7_days", label: "7 dias", days: 7 }],
  [15, { id: "last_15_days", label: "15 dias", days: 15 }],
  [30, { id: "last_30_days", label: "30 dias", days: 30 }],
  [60, { id: "last_60_days", label: "60 dias", days: 60 }],
  [90, { id: "last_90_days", label: "90 dias", days: 90 }],
] as const)

export function CadenceDetailAnalytics({ cadence }: CadenceDetailAnalyticsProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const rawDays = Number(searchParams.get("days") ?? "30")
  const rawStartDate = searchParams.get("start_date")
  const rawEndDate = searchParams.get("end_date")
  const selectedPeriod = (() => {
    if (rawStartDate && rawEndDate) {
      return resolveDateFilterValue({ startDate: rawStartDate, endDate: rawEndDate })
    }

    const preset = PERIOD_OPTIONS.get(rawDays) ?? PERIOD_OPTIONS.get(30)
    return buildDateFilterValue(preset ?? { id: "last_30_days", label: "30 dias", days: 30 })
  })()

  function handlePeriodChange(nextPeriod: AnalyticsDateFilterValue) {
    const params = new URLSearchParams(searchParams.toString())

    const preset = Array.from(PERIOD_OPTIONS.values()).find((option) => option.id === nextPeriod.id)

    if (preset?.days) {
      if (preset.days === 30) {
        params.delete("days")
      } else {
        params.set("days", String(preset.days))
      }
      params.delete("start_date")
      params.delete("end_date")
    } else {
      params.delete("days")
      params.set("start_date", nextPeriod.startDate)
      params.set("end_date", nextPeriod.endDate)
    }

    const query = params.toString()
    const nextUrl = query ? `${pathname}?${query}` : pathname
    router.replace(nextUrl as Route, { scroll: false })
  }

  const analyticsRange = getRangeQueryFromFilter(selectedPeriod)
  const { data, isLoading, isError } = useCadenceAnalytics(cadence.id, analyticsRange)
  const deliveryBudgetQuery = useCadenceDeliveryBudget(cadence.id)
  const abResults = useCadenceABTestResults(cadence.id, cadence.steps_template, analyticsRange)
  const deliveryBudgetItems = deliveryBudgetQuery.data?.items ?? []
  const deliveryBudgetSummaries = summarizeBudgetByAction(deliveryBudgetItems).filter(
    (item) => item.scope_count > 1,
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm) sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">Janela de análise</p>
          <p className="text-xs text-(--text-secondary)">
            Envios, respostas e A/B usam o período selecionado: {selectedPeriod.label} (
            {formatSelectedRangeLabel(selectedPeriod.startDate, selectedPeriod.endDate)}). Base de
            leads e backlog seguem o estado atual.
          </p>
        </div>
        <AnalyticsPeriodFilter value={selectedPeriod} onChange={handlePeriodChange} />
      </div>

      {isError ? (
        <div className="rounded-lg border border-(--danger-subtle-fg) bg-(--danger-subtle) px-4 py-3 text-sm text-(--danger)">
          Não foi possível carregar os indicadores desta cadência agora.
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Leads na cadência"
          value={isLoading ? "..." : (data?.total_leads ?? 0)}
          icon={Users}
          description={
            isLoading ? "Carregando base ativa" : `${data?.leads_active ?? 0} ativos neste momento`
          }
        />
        <StatCard
          label="Envios concluídos"
          value={isLoading ? "..." : (data?.steps_sent ?? 0)}
          icon={Send}
          description={`Steps enviados ou respondidos no período selecionado`}
        />
        <StatCard
          label="Respostas"
          value={isLoading ? "..." : (data?.replies ?? 0)}
          icon={MessageSquare}
          description={
            isLoading ? "Calculando taxa" : `${data?.reply_rate ?? 0}% de taxa de resposta`
          }
        />
        <StatCard
          label="Fila atual"
          value={isLoading ? "..." : (data?.pending_steps ?? 0)}
          icon={Clock3}
          description={
            isLoading
              ? "Lendo backlog"
              : `${data?.failed_steps ?? 0} falhas · ${data?.skipped_steps ?? 0} pulados`
          }
        />
      </div>

      <section className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Gauge size={16} className="text-(--accent)" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-semibold text-(--text-primary)">
                Limite operacional de hoje
              </h2>
              <p className="text-xs text-(--text-secondary)">
                Limite diário por conta e por ação. Comentário, reação e InMail aparecem separados
                quando a cadência usa esses canais.
              </p>
            </div>
          </div>
          {deliveryBudgetQuery.data?.generated_at ? (
            <span className="text-[11px] text-(--text-tertiary)">
              Atualizado às{" "}
              {new Date(deliveryBudgetQuery.data.generated_at).toLocaleTimeString("pt-BR", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          ) : null}
        </div>

        {deliveryBudgetQuery.isLoading ? (
          <div className="flex flex-wrap gap-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div
                key={index}
                className="h-32 w-full animate-pulse rounded-lg bg-(--bg-overlay) sm:w-80"
              />
            ))}
          </div>
        ) : deliveryBudgetQuery.isError ? (
          <div className="rounded-lg border border-(--warning-subtle-fg) bg-(--warning-subtle) px-4 py-3 text-sm text-(--warning)">
            Não foi possível carregar o limite operacional agora.
          </div>
        ) : deliveryBudgetItems.length > 0 ? (
          <div className="flex flex-wrap items-start gap-3">
            {deliveryBudgetSummaries.map((item) => (
              <OperationalBudgetSummaryCard key={item.channel} item={item} />
            ))}
            {deliveryBudgetItems.map((item) => (
              <OperationalBudgetCard key={`${item.channel}-${item.scope_label}`} item={item} />
            ))}
          </div>
        ) : (
          <p className="py-6 text-sm text-(--text-tertiary)">
            Esta cadência ainda não tem canais elegíveis para budget operacional diário.
          </p>
        )}
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <section className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Send size={16} className="text-(--accent)" aria-hidden="true" />
              <div>
                <h2 className="text-sm font-semibold text-(--text-primary)">
                  Desempenho por canal
                </h2>
                <p className="text-xs text-(--text-secondary)">
                  Envios, respostas, abertura de e-mail e aceites de conexão no período selecionado
                </p>
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-24 animate-pulse rounded-lg bg-(--bg-overlay)" />
              ))}
            </div>
          ) : data && data.channel_breakdown.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {data.channel_breakdown.map((row) => (
                <div
                  key={row.channel}
                  className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4"
                >
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <BadgeChannel channel={row.channel} />
                    <div className="text-right text-xs font-medium text-(--text-tertiary)">
                      <p>{row.reply_rate}% resp./envio</p>
                      {row.channel === "email" ? <p>{row.open_rate}% abertura</p> : null}
                      {row.channel === "linkedin_connect" ? (
                        <p>{row.acceptance_rate}% aceite</p>
                      ) : null}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <MetricMini label="Enviados" value={row.sent} />
                    <MetricMini label="Respondidos" value={row.replied} />
                    <MetricMini label="Tx. resp./envio" value={`${row.reply_rate}%`} />
                    {row.channel === "email" ? (
                      <>
                        <MetricMini label="Abertos" value={row.opened} />
                        <MetricMini label="Tx. abertura" value={`${row.open_rate}%`} />
                      </>
                    ) : null}
                    {row.channel === "linkedin_connect" ? (
                      <>
                        <MetricMini label="Aceites" value={row.accepted} />
                        <MetricMini label="Tx. aceite" value={`${row.acceptance_rate}%`} />
                      </>
                    ) : null}
                    <MetricMini label="Pendentes" value={row.pending} />
                    <MetricMini label="Falhas" value={row.failed + row.skipped} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-(--text-tertiary)">
              Esta cadência ainda não tem movimentação por canal.
            </p>
          )}
        </section>

        <section className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <div className="mb-4 flex items-center gap-2">
            <Clock3 size={16} className="text-(--accent)" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-semibold text-(--text-primary)">Leitura por step</h2>
              <p className="text-xs text-(--text-secondary)">
                Base por etapa, taxa de resposta sobre envios, abertura, bounce e aceites por canal
              </p>
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-11 animate-pulse rounded-lg bg-(--bg-overlay)" />
              ))}
            </div>
          ) : data && data.step_breakdown.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-(--border-subtle)">
                    <th className="pb-2 pr-3 font-medium text-(--text-tertiary)">Step</th>
                    <th className="pb-2 pr-3 font-medium text-(--text-tertiary)">Canal</th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Leads
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Envios
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Respostas
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Tx. resp./envio
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Tx. abertura
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Bounce
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Aceites
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Tx. aceite
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Pendentes
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Falhas
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.step_breakdown.map((row) => (
                    <tr
                      key={`${row.step_number}-${row.channel}`}
                      className="border-b border-(--border-subtle) last:border-0"
                    >
                      <td className="py-3 pr-3 font-medium text-(--text-primary)">
                        #{row.step_number}
                      </td>
                      <td className="py-3 pr-3">
                        <BadgeChannel channel={row.channel} />
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.lead_count}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.sent}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.replied}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums font-medium text-(--text-primary)">
                        {row.reply_rate}%
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.channel === "email" ? `${row.open_rate}%` : "—"}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.channel === "email" ? row.bounced : "—"}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.channel === "linkedin_connect" ? row.accepted : "—"}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.channel === "linkedin_connect" ? `${row.acceptance_rate}%` : "—"}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.pending}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.failed + row.skipped}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-(--text-tertiary)">
              Ainda não existem steps processados nesta cadência.
            </p>
          )}
        </section>
      </div>

      {abResults.length > 0 ? (
        <section className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle size={16} className="text-(--accent)" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-semibold text-(--text-primary)">A/B de assuntos</h2>
              <p className="text-xs text-(--text-secondary)">
                Comparativo das variantes usadas nos steps de e-mail com subject variants no período
                selecionado.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {abResults.map((group) => (
              <div
                key={group.stepNumber}
                className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4"
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-(--text-primary)">
                      Step #{group.stepNumber}
                    </p>
                    <p className="mt-1 text-xs text-(--text-secondary)">
                      Variantes configuradas: {group.subjectVariants.join(" • ")}
                    </p>
                  </div>
                  <BadgeChannel channel="email" />
                </div>

                {group.isLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 3 }).map((_, index) => (
                      <div key={index} className="h-9 animate-pulse rounded bg-(--bg-surface)" />
                    ))}
                  </div>
                ) : group.isError ? (
                  <p className="text-sm text-(--danger)">
                    Não foi possível carregar o comparativo deste step.
                  </p>
                ) : group.data && group.data.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-(--border-subtle)">
                          <th className="pb-2 pr-3 font-medium text-(--text-tertiary)">Assunto</th>
                          <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                            Envios
                          </th>
                          <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                            Abertos
                          </th>
                          <th className="pb-2 text-right font-medium text-(--text-tertiary)">
                            Open rate
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.data.map((row) => (
                          <tr
                            key={row.subject}
                            className="border-b border-(--border-subtle) last:border-0"
                          >
                            <td className="py-2 pr-3 text-(--text-primary)">{row.subject}</td>
                            <td className="py-2 pr-3 text-right tabular-nums text-(--text-secondary)">
                              {row.sent}
                            </td>
                            <td className="py-2 pr-3 text-right tabular-nums text-(--text-secondary)">
                              {row.opened}
                            </td>
                            <td className="py-2 text-right tabular-nums font-medium text-(--text-primary)">
                              {row.open_rate}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-(--text-tertiary)">
                    Sem volume suficiente para comparar variantes neste step.
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}

function MetricMini({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-(--text-tertiary)">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-(--text-primary)">{value}</p>
    </div>
  )
}

function OperationalBudgetCard({ item }: { item: CadenceDeliveryBudgetItem }) {
  const tone =
    item.remaining_today <= 0
      ? {
          badge: "bg-(--danger-subtle) text-(--danger-subtle-fg)",
          label: "Esgotado",
          bar: "var(--danger)",
        }
      : item.usage_pct >= 80
        ? {
            badge: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
            label: "No limite",
            bar: "var(--warning)",
          }
        : {
            badge: "bg-(--success-subtle) text-(--success-subtle-fg)",
            label: "Saudável",
            bar: "var(--success)",
          }

  return (
    <div className="w-full rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4 sm:w-80">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <BadgeChannel channel={item.channel} />
          <div>
            <p className="text-sm font-semibold text-(--text-primary)">{item.scope_label}</p>
            <p className="text-xs text-(--text-secondary)">
              Uso de {item.usage_pct}% · limite configurado {item.configured_limit}/dia · escopo{" "}
              {formatScopeType(item.scope_type)}
            </p>
          </div>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${tone.badge}`}>
          {tone.label}
        </span>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-(--bg-surface)">
        <div
          className="h-full rounded-full transition-[width]"
          style={{ width: `${Math.min(item.usage_pct, 100)}%`, backgroundColor: tone.bar }}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <MetricMini label="Config." value={item.configured_limit} />
        <MetricMini label="Usados" value={item.used_today} />
        <MetricMini label="Limite" value={item.daily_budget} />
        <MetricMini label="Saldo" value={item.remaining_today} />
      </div>
    </div>
  )
}

interface OperationalBudgetActionSummary {
  channel: string
  scope_count: number
  configured_limit: number
  daily_budget: number
  used_today: number
  remaining_today: number
  usage_pct: number
}

function OperationalBudgetSummaryCard({ item }: { item: OperationalBudgetActionSummary }) {
  const tone =
    item.remaining_today <= 0
      ? "text-(--danger)"
      : item.usage_pct >= 80
        ? "text-(--warning)"
        : "text-(--success)"

  return (
    <div className="w-full rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4 sm:w-80">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <BadgeChannel channel={item.channel} />
          <p className="text-xs text-(--text-secondary)">
            {item.scope_count} escopo{item.scope_count === 1 ? "" : "s"} com limite hoje
          </p>
        </div>
        <span className={`text-sm font-semibold ${tone}`}>{item.remaining_today} livres</span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <MetricMini label="Config." value={item.configured_limit} />
        <MetricMini label="Limite" value={item.daily_budget} />
        <MetricMini label="Usados" value={item.used_today} />
        <MetricMini label="Saldo" value={item.remaining_today} />
      </div>
    </div>
  )
}

function summarizeBudgetByAction(
  items: CadenceDeliveryBudgetItem[],
): OperationalBudgetActionSummary[] {
  const grouped = new Map<string, OperationalBudgetActionSummary>()

  for (const item of items) {
    const current = grouped.get(item.channel)
    if (current) {
      current.scope_count += 1
      current.configured_limit += item.configured_limit
      current.daily_budget += item.daily_budget
      current.used_today += item.used_today
      current.remaining_today += item.remaining_today
      current.usage_pct = current.daily_budget
        ? Number(((current.used_today / current.daily_budget) * 100).toFixed(1))
        : 0
      continue
    }

    grouped.set(item.channel, {
      channel: item.channel,
      scope_count: 1,
      configured_limit: item.configured_limit,
      daily_budget: item.daily_budget,
      used_today: item.used_today,
      remaining_today: item.remaining_today,
      usage_pct: item.daily_budget
        ? Number(((item.used_today / item.daily_budget) * 100).toFixed(1))
        : 0,
    })
  }

  return Array.from(grouped.values())
}

function formatScopeType(value: string) {
  switch (value) {
    case "email_account":
      return "conta de e-mail"
    case "linkedin_account":
      return "conta LinkedIn"
    default:
      return "fallback do tenant"
  }
}
