"use client"

import type { Route } from "next"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { AlertTriangle, Clock3, MessageSquare, Send, Users } from "lucide-react"
import { PeriodFilter } from "@/components/dashboard/period-filter"
import { StatCard } from "@/components/dashboard/stat-card"
import { BadgeChannel } from "@/components/shared/badge-channel"
import type { Cadence } from "@/lib/api/hooks/use-cadences"
import { useCadenceABTestResults, useCadenceAnalytics } from "@/lib/api/hooks/use-cadence-analytics"

interface CadenceDetailAnalyticsProps {
  cadence: Cadence
}

const PERIOD_OPTIONS = new Set([7, 30, 90])

export function CadenceDetailAnalytics({ cadence }: CadenceDetailAnalyticsProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const rawDays = Number(searchParams.get("days") ?? "30")
  const days = PERIOD_OPTIONS.has(rawDays) ? rawDays : 30

  function handlePeriodChange(nextDays: number) {
    const params = new URLSearchParams(searchParams.toString())

    if (nextDays === 30) {
      params.delete("days")
    } else {
      params.set("days", String(nextDays))
    }

    const query = params.toString()
    const nextUrl = query ? `${pathname}?${query}` : pathname
    router.replace(nextUrl as Route, { scroll: false })
  }

  const { data, isLoading, isError } = useCadenceAnalytics(cadence.id, days)
  const abResults = useCadenceABTestResults(cadence.id, cadence.steps_template, days)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm) sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">Janela de análise</p>
          <p className="text-xs text-(--text-secondary)">
            Envios, respostas e A/B usam os últimos {days} dias. Base de leads e backlog seguem o
            estado atual.
          </p>
        </div>
        <PeriodFilter value={days} onChange={handlePeriodChange} />
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
          description={`Steps enviados ou respondidos nos últimos ${days} dias`}
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
                  Envios e respostas nos últimos {days} dias
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
                    <span className="text-xs font-medium text-(--text-tertiary)">
                      {row.reply_rate}% resposta
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <MetricMini label="Enviados" value={row.sent} />
                    <MetricMini label="Respondidos" value={row.replied} />
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
                Desempenho recente por etapa e pendências atuais
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
                      Envios
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Respostas
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Pendentes
                    </th>
                    <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">
                      Falhas
                    </th>
                    <th className="pb-2 text-right font-medium text-(--text-tertiary)">Taxa</th>
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
                        {row.sent}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.replied}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.pending}
                      </td>
                      <td className="py-3 pr-3 text-right tabular-nums text-(--text-secondary)">
                        {row.failed + row.skipped}
                      </td>
                      <td className="py-3 text-right tabular-nums font-medium text-(--text-primary)">
                        {row.reply_rate}%
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
                Comparativo das variantes usadas nos steps de e-mail com subject variants nos
                últimos {days} dias.
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

function MetricMini({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-(--text-tertiary)">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-(--text-primary)">{value}</p>
    </div>
  )
}
