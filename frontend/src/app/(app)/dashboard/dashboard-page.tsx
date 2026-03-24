"use client"

import { useState } from "react"
import {
  Users,
  GitBranch,
  CheckCircle,
  Send,
  MessageSquare,
  TrendingUp,
  Archive,
} from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { ChannelChart } from "@/components/dashboard/channel-chart"
import { RecentReplies } from "@/components/dashboard/recent-replies"
import { FunnelChart } from "@/components/dashboard/funnel-chart"
import { IntentChart } from "@/components/dashboard/intent-chart"
import { CadencePerformanceTable } from "@/components/dashboard/cadence-performance"
import { PeriodFilter } from "@/components/dashboard/period-filter"
import {
  useDashboardStats,
  useChannelBreakdown,
  useRecentReplies,
  useIntentBreakdown,
  useFunnel,
  useCadencePerformance,
} from "@/lib/api/hooks/use-analytics"

function trendProps(value: number | undefined): { trend?: { value: number; label: string } } {
  if (value == null || value === 0) return {}
  return { trend: { value, label: "vs período anterior" } }
}

export default function DashboardPage() {
  const [days, setDays] = useState(30)

  const { data: stats, isLoading: loadingStats } = useDashboardStats(days)
  const { data: channels, isLoading: loadingChannels } = useChannelBreakdown(days)
  const { data: replies, isLoading: loadingReplies } = useRecentReplies()
  const { data: intents, isLoading: loadingIntents } = useIntentBreakdown(days)
  const { data: funnel, isLoading: loadingFunnel } = useFunnel()
  const { data: cadences, isLoading: loadingCadences } = useCadencePerformance(days)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Dashboard</h1>
          <p className="text-sm text-(--text-secondary)">Visão geral da prospecção</p>
        </div>
        <PeriodFilter value={days} onChange={setDays} />
      </div>

      {/* Stat cards — 5 itens */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard
          label="Total de leads"
          value={loadingStats ? "—" : (stats?.leads_total ?? 0)}
          icon={Users}
          {...trendProps(stats?.leads_total_trend)}
        />
        <StatCard
          label="Em cadência"
          value={loadingStats ? "—" : (stats?.leads_in_cadence ?? 0)}
          icon={GitBranch}
        />
        <StatCard
          label="Convertidos"
          value={loadingStats ? "—" : (stats?.leads_converted ?? 0)}
          icon={CheckCircle}
          {...(stats ? { description: `${stats.conversion_rate.toFixed(1)}% de conversão` } : {})}
        />
        <StatCard
          label="Envios no período"
          value={loadingStats ? "—" : (stats?.steps_sent_period ?? 0)}
          icon={Send}
          {...trendProps(stats?.steps_sent_trend)}
          {...(stats ? { description: `${stats.steps_sent_today} hoje` } : {})}
        />
        <StatCard
          label="Respostas"
          value={loadingStats ? "—" : (stats?.replies_period ?? 0)}
          icon={MessageSquare}
          {...trendProps(stats?.replies_trend)}
          {...(stats ? { description: `${stats.replies_today} hoje` } : {})}
        />
      </div>

      {/* Funil + Intent donut */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-(--text-primary)">
            <TrendingUp size={15} aria-hidden="true" />
            Funil de conversão
          </h2>
          <FunnelChart data={funnel ?? []} isLoading={loadingFunnel} />
        </div>

        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-(--text-primary)">
            <Archive size={15} aria-hidden="true" />
            Intenção das respostas
          </h2>
          <IntentChart data={intents ?? []} isLoading={loadingIntents} />
        </div>
      </div>

      {/* Gráfico por canal */}
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
        <h2 className="mb-4 text-sm font-semibold text-(--text-primary)">
          Atividade por canal — últimos {days} dias
        </h2>
        <ChannelChart data={channels ?? []} isLoading={loadingChannels} />
      </div>

      {/* Performance cadências + Respostas recentes */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <h2 className="mb-4 text-sm font-semibold text-(--text-primary)">
            Top cadências — últimos {days} dias
          </h2>
          <CadencePerformanceTable data={cadences ?? []} isLoading={loadingCadences} />
        </div>

        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-(--text-primary)">
            <MessageSquare size={15} aria-hidden="true" />
            Respostas recentes
          </h2>
          <RecentReplies replies={replies ?? []} isLoading={loadingReplies} />
        </div>
      </div>
    </div>
  )
}
