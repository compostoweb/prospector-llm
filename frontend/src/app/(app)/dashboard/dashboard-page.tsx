"use client"

import { useMemo, useState } from "react"
import {
  Users,
  GitBranch,
  CheckCircle,
  Send,
  MessageSquare,
  TrendingUp,
  Archive,
  ClipboardList,
  Mail,
  AlertTriangle,
} from "lucide-react"
import { StatCard } from "@/components/dashboard/stat-card"
import { ChannelChart } from "@/components/dashboard/channel-chart"
import { RecentReplies } from "@/components/dashboard/recent-replies"
import { FunnelChart } from "@/components/dashboard/funnel-chart"
import { IntentChart } from "@/components/dashboard/intent-chart"
import { CadencePerformanceTable } from "@/components/dashboard/cadence-performance"
import { AnalyticsPeriodFilter } from "@/components/shared/analytics-period-filter"
import { EmailStatsCard } from "@/components/dashboard/email-stats-card"
import { LinkedInStatsCard } from "@/components/dashboard/linkedin-stats-card"
import {
  useDashboardStats,
  useChannelBreakdown,
  useRecentReplies,
  useIntentBreakdown,
  useFunnel,
  useCadencePerformance,
  useEmailStats,
  useLinkedInStats,
  type EmailStats,
} from "@/lib/api/hooks/use-analytics"
import { useManualTaskStats } from "@/lib/api/hooks/use-manual-tasks"
import {
  buildDateFilterValue,
  getRangeQueryFromFilter,
  type AnalyticsDateFilterValue,
} from "@/lib/analytics-period"

const EMPTY_EMAIL_STATS: EmailStats = {
  sent: 0,
  opened: 0,
  replied: 0,
  unsubscribed: 0,
  bounced: 0,
  open_rate: 0,
  reply_rate: 0,
  bounce_rate: 0,
  unsubscribe_rate: 0,
}

function trendProps(value: number | undefined): { trend?: { value: number; label: string } } {
  if (value == null || value === 0) return {}
  return { trend: { value, label: "vs período anterior" } }
}

export default function DashboardPage() {
  const [dateFilter, setDateFilter] = useState<AnalyticsDateFilterValue>(() =>
    buildDateFilterValue({ id: "last_30_days", label: "30 dias", days: 30 }),
  )
  const analyticsRange = useMemo(() => getRangeQueryFromFilter(dateFilter), [dateFilter])

  const {
    data: stats,
    isLoading: loadingStats,
    isError: statsError,
  } = useDashboardStats(analyticsRange)
  const {
    data: channels,
    isLoading: loadingChannels,
    isError: channelsError,
  } = useChannelBreakdown(analyticsRange)
  const { data: replies, isLoading: loadingReplies, isError: repliesError } = useRecentReplies()
  const {
    data: intents,
    isLoading: loadingIntents,
    isError: intentsError,
  } = useIntentBreakdown(analyticsRange)
  const { data: funnel, isLoading: loadingFunnel, isError: funnelError } = useFunnel()
  const {
    data: cadences,
    isLoading: loadingCadences,
    isError: cadencesError,
  } = useCadencePerformance(analyticsRange)
  const {
    data: emailStats,
    isLoading: loadingEmail,
    isError: emailError,
  } = useEmailStats(analyticsRange)
  const {
    data: linkedInStats,
    isLoading: loadingLinkedIn,
    isError: linkedInError,
  } = useLinkedInStats(analyticsRange)
  const { data: taskStats } = useManualTaskStats()
  const hasAnalyticsError =
    statsError ||
    channelsError ||
    repliesError ||
    intentsError ||
    funnelError ||
    cadencesError ||
    emailError ||
    linkedInError

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Dashboard</h1>
          <p className="text-sm text-(--text-secondary)">Visão geral da prospecção</p>
        </div>
        <AnalyticsPeriodFilter value={dateFilter} onChange={setDateFilter} />
      </div>

      {hasAnalyticsError && (
        <div className="flex items-start gap-3 rounded-lg border border-(--warning) bg-(--warning-subtle) px-4 py-3 text-sm text-(--warning-subtle-fg)">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Não foi possível carregar o dashboard completo.</p>
            <p className="mt-1 text-(--text-secondary)">
              Verifique se a API e o WebSocket do backend estão acessíveis no ambiente atual.
            </p>
          </div>
        </div>
      )}

      {/* Stat cards — 6 itens */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
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
          {...trendProps(stats?.leads_in_cadence_trend)}
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
        <StatCard
          label="Tarefas pendentes"
          value={taskStats?.pending ?? 0}
          icon={ClipboardList}
          {...(taskStats
            ? { description: `${taskStats.content_generated} prontas para envio` }
            : {})}
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
          Atividade por canal — período selecionado
        </h2>
        <ChannelChart data={channels ?? []} isLoading={loadingChannels} />
      </div>

      {/* Email stats — só exibe se houver envios */}
      {(loadingEmail || (emailStats?.sent ?? 0) > 0) && (
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-(--text-primary)">
            <Mail size={15} aria-hidden="true" />
            Desempenho de e-mail — período selecionado
          </h2>
          <EmailStatsCard data={emailStats ?? EMPTY_EMAIL_STATS} isLoading={loadingEmail} />
        </div>
      )}

      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
        <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-(--text-primary)">
          <MessageSquare size={15} aria-hidden="true" />
          Desempenho de LinkedIn — período selecionado
        </h2>
        <LinkedInStatsCard
          data={
            linkedInStats ?? {
              connect_sent: 0,
              connect_accepted: 0,
              connect_acceptance_rate: 0,
              dm_sent: 0,
              dm_replied: 0,
              dm_reply_rate: 0,
            }
          }
          isLoading={loadingLinkedIn}
        />
      </div>

      {/* Performance cadências + Respostas recentes */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
          <h2 className="mb-4 text-sm font-semibold text-(--text-primary)">
            Top cadências — período selecionado
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
