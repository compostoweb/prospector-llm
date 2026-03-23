"use client"

import { Users, GitBranch, CheckCircle, Send, MessageSquare } from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { ChannelChart } from "@/components/dashboard/channel-chart"
import { RecentReplies } from "@/components/dashboard/recent-replies"
import {
  useDashboardStats,
  useChannelBreakdown,
  useRecentReplies,
} from "@/lib/api/hooks/use-analytics"

export default function DashboardPage() {
  const { data: stats, isLoading: loadingStats } = useDashboardStats()
  const { data: channels, isLoading: loadingChannels } = useChannelBreakdown()
  const { data: replies, isLoading: loadingReplies } = useRecentReplies()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-[var(--text-primary)]">Dashboard</h1>
        <p className="text-sm text-[var(--text-secondary)]">Visão geral da prospecção</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total de leads"
          value={loadingStats ? "—" : (stats?.leads_total ?? 0)}
          icon={Users}
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
          label="Enviados hoje"
          value={loadingStats ? "—" : (stats?.steps_sent_today ?? 0)}
          icon={Send}
          {...(stats ? { description: `${stats.replies_today} respostas hoje` } : {})}
        />
      </div>

      {/* Gráfico + Respostas recentes */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-sm)]">
          <h2 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">
            Atividade por canal — últimos 30 dias
          </h2>
          <ChannelChart data={channels ?? []} isLoading={loadingChannels} />
        </div>

        <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-sm)]">
          <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-[var(--text-primary)]">
            <MessageSquare size={15} aria-hidden="true" />
            Respostas recentes
          </h2>
          <RecentReplies replies={replies ?? []} isLoading={loadingReplies} />
        </div>
      </div>
    </div>
  )
}
