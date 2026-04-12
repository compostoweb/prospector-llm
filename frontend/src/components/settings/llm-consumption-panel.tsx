"use client"

import type { Route as AppRoute } from "next"
import { useMemo } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { Bot, Coins, Cpu, FileText, Layers3, Loader2, Sparkles } from "lucide-react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { StatCard } from "@/components/dashboard/stat-card"
import {
  useLLMUsageBreakdown,
  useLLMUsageComparison,
  useLLMUsageSummary,
  useLLMUsageTimeSeries,
  type LLMUsageBreakdownItem,
  type LLMUsageFilters,
  type LLMUsageGranularity,
} from "@/lib/api/hooks/use-llm-analytics"
import { useLLMModels } from "@/lib/api/hooks/use-llm-models"
import { cn } from "@/lib/utils"

const PERIOD_OPTIONS = [
  { label: "24h", value: 1 },
  { label: "7d", value: 7 },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
  { label: "12m", value: 365 },
] as const

const GRANULARITY_OPTIONS: { label: string; value: LLMUsageGranularity }[] = [
  { label: "Hora", value: "hour" },
  { label: "Dia", value: "day" },
  { label: "Semana", value: "week" },
  { label: "Mês", value: "month" },
]

const PERIOD_VALUES = new Set<number>(PERIOD_OPTIONS.map((option) => option.value))
const GRANULARITY_VALUES = new Set<string>(GRANULARITY_OPTIONS.map((option) => option.value))

export function LLMConsumptionPanel() {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()

  const { data: modelsData } = useLLMModels()
  const availableModels = modelsData?.models ?? []
  const rawDays = Number(searchParams.get("consumo_days") ?? "30")
  const days = PERIOD_VALUES.has(rawDays) ? rawDays : 30
  const rawGranularity = searchParams.get("consumo_granularity")
  const granularity: LLMUsageGranularity = GRANULARITY_VALUES.has(
    rawGranularity as LLMUsageGranularity,
  )
    ? (rawGranularity as LLMUsageGranularity)
    : "day"
  const rawProvider = searchParams.get("consumo_provider") ?? "all"
  const knownProviders = new Set<string>(availableModels.map((item) => item.provider))
  const provider = rawProvider === "all" || knownProviders.has(rawProvider) ? rawProvider : "all"
  const visibleModelOptions =
    provider === "all"
      ? availableModels
      : availableModels.filter((item) => item.provider === provider)
  const rawModel = searchParams.get("consumo_model") ?? "all"
  const model =
    rawModel === "all" || visibleModelOptions.some((item) => item.id === rawModel)
      ? rawModel
      : "all"

  function updateFilters(next: {
    days?: number
    granularity?: LLMUsageGranularity
    provider?: string
    model?: string
  }) {
    const params = new URLSearchParams(searchParams.toString())
    const nextDays = next.days ?? days
    const nextGranularity = next.granularity ?? granularity
    const nextProvider = next.provider ?? provider
    const nextModel = next.model ?? model

    if (nextDays === 30) {
      params.delete("consumo_days")
    } else {
      params.set("consumo_days", String(nextDays))
    }

    if (nextGranularity === "day") {
      params.delete("consumo_granularity")
    } else {
      params.set("consumo_granularity", nextGranularity)
    }

    if (nextProvider === "all") {
      params.delete("consumo_provider")
    } else {
      params.set("consumo_provider", nextProvider)
    }

    if (nextModel === "all") {
      params.delete("consumo_model")
    } else {
      params.set("consumo_model", nextModel)
    }

    const query = params.toString()
    const nextUrl = query ? `${pathname}?${query}` : pathname
    router.replace(nextUrl as AppRoute, { scroll: false })
  }

  const filters = useMemo<LLMUsageFilters>(() => {
    const next: LLMUsageFilters = {}
    if (provider !== "all") {
      next.provider = provider
    }
    if (model !== "all") {
      next.model = model
    }
    return next
  }, [model, provider])

  const comparisonEndAt = useMemo(() => {
    const anchor = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
    return anchor.toISOString()
  }, [days])

  const summary = useLLMUsageSummary(days, filters)
  const comparison = useLLMUsageComparison(days, filters)
  const series = useLLMUsageTimeSeries(days, granularity, filters)
  const previousSeries = useLLMUsageTimeSeries(days, granularity, {
    ...filters,
    endAt: comparisonEndAt,
  })
  const modules = useLLMUsageBreakdown("module", days, 6, filters)
  const tasks = useLLMUsageBreakdown("task_type", days, 6, filters)
  const features = useLLMUsageBreakdown("feature", days, 6, filters)
  const models = useLLMUsageBreakdown("model", days, 6, filters)
  const providers = useLLMUsageBreakdown("provider", days, 4, filters)

  const chartData = useMemo(
    () =>
      (series.data ?? []).map((point, index) => ({
        ...point,
        label: formatBucket(point.bucket_start, granularity),
        previous_total_tokens: previousSeries.data?.[index]?.total_tokens ?? 0,
        previous_estimated_cost_usd: previousSeries.data?.[index]?.estimated_cost_usd ?? 0,
      })),
    [granularity, previousSeries.data, series.data],
  )

  const isLoading =
    summary.isLoading ||
    comparison.isLoading ||
    series.isLoading ||
    previousSeries.isLoading ||
    modules.isLoading ||
    tasks.isLoading ||
    features.isLoading ||
    models.isLoading ||
    providers.isLoading

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-(--text-primary)">
              Consumo e custo estimado
            </h2>
            <p className="mt-1 text-xs text-(--text-secondary)">
              Acompanha uso por hora, dia, semana e mês com ranking por módulo, tarefa, provider e
              modelo.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <SegmentedControl
              value={days}
              onChange={(value) => updateFilters({ days: value })}
              options={PERIOD_OPTIONS}
            />
            <SegmentedControl
              value={granularity}
              onChange={(value) => updateFilters({ granularity: value as LLMUsageGranularity })}
              options={GRANULARITY_OPTIONS}
            />
            <FilterSelect
              value={provider}
              onChange={(value) => updateFilters({ provider: value, model: "all" })}
              options={buildProviderOptions(availableModels)}
              ariaLabel="Filtrar provider"
            />
            <FilterSelect
              value={model}
              onChange={(value) => updateFilters({ model: value })}
              options={buildModelOptions(visibleModelOptions)}
              ariaLabel="Filtrar modelo"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex min-h-56 items-center justify-center gap-2 text-sm text-(--text-secondary)">
            <Loader2 size={16} className="animate-spin" />
            Carregando consumo de LLM...
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Tokens totais"
                value={formatNumber(summary.data?.total_tokens ?? 0)}
                icon={Bot}
                description={formatSplit(
                  summary.data?.input_tokens ?? 0,
                  summary.data?.output_tokens ?? 0,
                )}
                {...withTrend(toTrend(comparison.data?.total_tokens_change_pct))}
              />
              <StatCard
                label="Custo estimado"
                value={formatCurrency(summary.data?.estimated_cost_usd ?? 0)}
                icon={Coins}
                description="Estimativa agregada entre todos os providers"
                {...withTrend(toTrend(comparison.data?.estimated_cost_change_pct))}
              />
              <StatCard
                label="Chamadas"
                value={formatNumber(summary.data?.requests ?? 0)}
                icon={Cpu}
                description={`Média ${formatNumber(summary.data?.avg_total_tokens_per_request ?? 0)} tokens/chamada`}
                {...withTrend(toTrend(comparison.data?.requests_change_pct))}
              />
              <StatCard
                label="Saída média"
                value={formatNumber(summary.data?.avg_output_tokens_per_request ?? 0)}
                icon={FileText}
                description="Tokens médios de resposta por execução"
                {...withTrend(toTrend(comparison.data?.avg_output_tokens_change_pct))}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <ComparisonCard
                title="Período atual"
                value={formatNumber(comparison.data?.current.total_tokens ?? 0)}
                subtitle={`${formatCurrency(comparison.data?.current.estimated_cost_usd ?? 0)} em custo estimado`}
              />
              <ComparisonCard
                title="Período anterior"
                value={formatNumber(comparison.data?.previous.total_tokens ?? 0)}
                subtitle={`${formatCurrency(comparison.data?.previous.estimated_cost_usd ?? 0)} em custo estimado`}
              />
              <ComparisonCard
                title="Leitura rápida"
                value={formatDeltaLabel(comparison.data?.total_tokens_change_pct)}
                subtitle="Variação de tokens totais versus a janela anterior equivalente"
                highlight
              />
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
              <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-4">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-(--text-primary)">
                      Evolução do consumo
                    </p>
                    <p className="text-xs text-(--text-secondary)">
                      Tokens totais e custo estimado por{" "}
                      {labelForGranularity(granularity).toLowerCase()}.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="rounded-md border border-(--border-default) bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-secondary)">
                      Atual
                    </div>
                    <div className="rounded-md border border-(--border-default) bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-secondary)">
                      Anterior
                    </div>
                    <div className="rounded-md bg-(--accent-subtle) px-2.5 py-1 text-xs font-medium text-(--accent)">
                      {formatNumber(summary.data?.requests ?? 0)} chamadas
                    </div>
                  </div>
                </div>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="llmTokensFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="var(--border-subtle)" vertical={false} />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: "var(--text-tertiary)", fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        yAxisId="tokens"
                        tick={{ fill: "var(--text-tertiary)", fontSize: 12 }}
                        tickFormatter={(value: number) => compactNumber(value)}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        yAxisId="cost"
                        orientation="right"
                        tick={{ fill: "var(--text-tertiary)", fontSize: 12 }}
                        tickFormatter={(value: number) => `$${value.toFixed(2)}`}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border-default)",
                          borderRadius: "var(--radius-md)",
                        }}
                        formatter={(value: number, name: string) => {
                          if (name === "estimated_cost_usd") return [formatCurrency(value), "Custo"]
                          if (name === "requests") return [formatNumber(value), "Chamadas"]
                          return [formatNumber(value), "Tokens"]
                        }}
                      />
                      <Area
                        yAxisId="tokens"
                        type="monotone"
                        dataKey="total_tokens"
                        stroke="var(--accent)"
                        fill="url(#llmTokensFill)"
                        strokeWidth={2.5}
                      />
                      <Line
                        yAxisId="tokens"
                        type="monotone"
                        dataKey="previous_total_tokens"
                        stroke="var(--text-tertiary)"
                        strokeWidth={1.75}
                        strokeDasharray="6 4"
                        dot={false}
                      />
                      <Line
                        yAxisId="cost"
                        type="monotone"
                        dataKey="estimated_cost_usd"
                        stroke="var(--warning)"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        yAxisId="cost"
                        type="monotone"
                        dataKey="previous_estimated_cost_usd"
                        stroke="var(--text-tertiary)"
                        strokeWidth={1.5}
                        strokeDasharray="3 3"
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-3 text-xs text-(--text-secondary)">
                  Linha sólida representa a janela atual; linha tracejada representa a janela
                  anterior equivalente.
                </p>
              </div>

              <BreakdownCard
                title="Providers mais caros"
                description="Comparativo agregado do período selecionado"
                items={providers.data ?? []}
                emptyLabel="Nenhum consumo registrado no período."
              />
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2 2xl:grid-cols-4">
              <BreakdownCard
                title="Módulos"
                description="Onde os tokens estão sendo consumidos"
                items={modules.data ?? []}
                emptyLabel="Sem módulos com consumo no período."
              />
              <BreakdownCard
                title="Tarefas"
                description="Jobs e operações mais intensivos"
                items={tasks.data ?? []}
                emptyLabel="Sem tarefas registradas no período."
              />
              <BreakdownCard
                title="Features"
                description="Ranking das features mais custosas"
                items={features.data ?? []}
                emptyLabel="Sem features registradas no período."
                icon={Sparkles}
              />
              <BreakdownCard
                title="Modelos"
                description="Comparativo por provider/modelo"
                items={models.data ?? []}
                emptyLabel="Sem modelos registrados no período."
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface SegmentedControlProps<T extends string | number> {
  value: T
  onChange: (value: T) => void
  options: ReadonlyArray<{ label: string; value: T }>
}

interface FilterSelectProps {
  value: string
  onChange: (value: string) => void
  options: Array<{ label: string; value: string }>
  ariaLabel: string
}

function FilterSelect({ value, onChange, options, ariaLabel }: FilterSelectProps) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={ariaLabel}
      className="rounded-md border border-(--border-default) bg-(--bg-overlay) px-3 py-1.5 text-xs text-(--text-primary) outline-none"
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}

function SegmentedControl<T extends string | number>({
  value,
  onChange,
  options,
}: SegmentedControlProps<T>) {
  return (
    <div className="inline-flex rounded-md border border-(--border-default) bg-(--bg-overlay) p-0.5">
      {options.map((option) => (
        <button
          key={String(option.value)}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-sm px-3 py-1 text-xs font-medium transition-colors",
            value === option.value
              ? "bg-(--bg-surface) text-(--text-primary) shadow-(--shadow-sm)"
              : "text-(--text-secondary) hover:text-(--text-primary)",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

interface BreakdownCardProps {
  title: string
  description: string
  items: LLMUsageBreakdownItem[]
  emptyLabel: string
  icon?: typeof Layers3
}

function BreakdownCard({
  title,
  description,
  items,
  emptyLabel,
  icon: Icon = Layers3,
}: BreakdownCardProps) {
  const maxTokens = Math.max(...items.map((item) => item.total_tokens), 0)

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-4">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-(--accent-subtle)">
          <Icon size={18} className="text-(--accent)" />
        </div>
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">{title}</p>
          <p className="text-xs text-(--text-secondary)">{description}</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="flex min-h-48 items-center justify-center rounded-md border border-dashed border-(--border-default) text-sm text-(--text-secondary)">
          {emptyLabel}
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const width = maxTokens > 0 ? (item.total_tokens / maxTokens) * 100 : 0
            return (
              <div key={`${item.label}-${item.provider ?? "none"}`} className="space-y-1.5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-(--text-primary)">{item.label}</p>
                    <p className="text-xs text-(--text-secondary)">
                      {formatNumber(item.requests)} chamadas ·{" "}
                      {formatCurrency(item.estimated_cost_usd)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-(--text-primary)">
                      {formatNumber(item.total_tokens)}
                    </p>
                    <p className="text-xs text-(--text-secondary)">tokens</p>
                  </div>
                </div>
                <div className="flex items-center justify-between rounded-md bg-(--bg-overlay) px-2.5 py-1.5 text-xs text-(--text-secondary)">
                  <span>Participação relativa</span>
                  <span className="font-medium text-(--text-primary)">{width.toFixed(1)}%</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

interface ComparisonCardProps {
  title: string
  value: string
  subtitle: string
  highlight?: boolean
}

function ComparisonCard({ title, value, subtitle, highlight = false }: ComparisonCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        highlight
          ? "border-(--accent) bg-(--accent-subtle)"
          : "border-(--border-default) bg-(--bg-page)",
      )}
    >
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
        {title}
      </p>
      <p className="mt-2 text-2xl font-semibold text-(--text-primary)">{value}</p>
      <p className="mt-1 text-xs text-(--text-secondary)">{subtitle}</p>
    </div>
  )
}

function labelForGranularity(granularity: LLMUsageGranularity): string {
  return GRANULARITY_OPTIONS.find((option) => option.value === granularity)?.label ?? "Dia"
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value)
}

function compactNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 1 ? 3 : 2,
    maximumFractionDigits: value < 1 ? 3 : 2,
  }).format(value)
}

function formatSplit(inputTokens: number, outputTokens: number): string {
  return `${formatNumber(inputTokens)} entrada · ${formatNumber(outputTokens)} saída`
}

function formatBucket(value: string, granularity: LLMUsageGranularity): string {
  const date = new Date(value)
  if (granularity === "hour") {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
    }).format(date)
  }
  if (granularity === "day") {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
    }).format(date)
  }
  if (granularity === "week") {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
    }).format(date)
  }
  return new Intl.DateTimeFormat("pt-BR", {
    month: "short",
    year: "2-digit",
  }).format(date)
}

function toTrend(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return undefined
  }
  return {
    value,
    label: "vs período anterior",
  }
}

function formatDeltaLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Sem base anterior"
  }
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`
}

function withTrend(trend: { value: number; label: string } | undefined) {
  return trend ? { trend } : {}
}

function buildProviderOptions(models: Array<{ provider: string }>) {
  return [
    { label: "Todos os providers", value: "all" },
    ...Array.from(new Set(models.map((item) => item.provider))).map((item) => ({
      label: item,
      value: item,
    })),
  ]
}

function buildModelOptions(models: Array<{ id: string; name: string; provider: string }>) {
  return [
    { label: "Todos os modelos", value: "all" },
    ...models.map((item) => ({
      label: `${item.provider} / ${item.name}`,
      value: item.id,
    })),
  ]
}
