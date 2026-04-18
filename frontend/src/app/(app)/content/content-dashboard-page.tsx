"use client"

import { useState, useMemo } from "react"
import {
  endOfDay,
  format,
  isAfter,
  isWithinInterval,
  parseISO,
  startOfDay,
  startOfWeek,
  subDays,
  subWeeks,
} from "date-fns"
import { ptBR } from "date-fns/locale"
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts"
import {
  Eye,
  Heart,
  TrendingUp,
  FileText,
  Send,
  Loader2,
  CalendarClock,
  Award,
  Zap,
  BarChart2,
  ExternalLink,
  MessageCircle,
  Calendar,
  Bookmark,
  RefreshCw,
} from "lucide-react"
import { useContentPosts, useContentSettings, useSyncVoyager, type ContentPost } from "@/lib/api/hooks/use-content"
import { PillarBadge } from "@/components/content/post-badges"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

// ── Paleta consistente com o design system ──────────────────────────
const COLORS = {
  published: "#22c55e",
  scheduled: "#f59e0b",
  approved: "#3b82f6",
  draft: "#9ca3af",
  failed: "#ef4444",
  authority: "#6366f1",
  case: "#22c55e",
  vision: "#f59e0b",
  charBelow: "#f59e0b",
  charIdeal: "#22c55e",
  charGood: "#3b82f6",
  charOver: "#9ca3af",
}

// ── Helpers ──────────────────────────────────────────────────────────
function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—"
  return `${n.toFixed(1)}%`
}

// ── Sub-components ────────────────────────────────────────────────────

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string
  sub?: string
  accent?: boolean
}

function StatCard({ icon, label, value, sub, accent }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 flex flex-col gap-2 shadow-sm",
        accent && "border-(--accent)/30 bg-(--accent)/5",
      )}
    >
      <div className="flex items-center gap-2 text-(--text-tertiary)">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold text-(--text-primary) leading-none">{value}</p>
      {sub && <p className="text-xs text-(--text-tertiary)">{sub}</p>}
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold text-(--text-primary) flex items-center gap-2">
      {children}
    </h2>
  )
}

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-sm flex flex-col gap-4",
        className,
      )}
    >
      {children}
    </div>
  )
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-40 text-xs text-(--text-tertiary)">
      {message}
    </div>
  )
}

// ── Tooltip custom ────────────────────────────────────────────────────
function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-md border border-(--border-default) bg-(--bg-surface) shadow-lg px-3 py-2 text-xs">
      {label && <p className="font-medium text-(--text-secondary) mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name}:{" "}
          <span className="font-semibold">
            {typeof p.value === "number" && p.value >= 1000 ? fmt(p.value) : p.value}
          </span>
        </p>
      ))}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────
type PeriodKey = "all" | "today" | "yesterday" | "7d" | "30d" | "60d" | "90d" | "180d" | "365d"

const PERIOD_OPTIONS: { key: PeriodKey; label: string }[] = [
  { key: "all", label: "Todo o período" },
  { key: "today", label: "Hoje" },
  { key: "yesterday", label: "Ontem" },
  { key: "7d", label: "7 dias" },
  { key: "30d", label: "30 dias" },
  { key: "60d", label: "60 dias" },
  { key: "90d", label: "90 dias" },
  { key: "180d", label: "180 dias" },
  { key: "365d", label: "365 dias" },
]

function filterByPeriod(posts: ContentPost[], period: PeriodKey): ContentPost[] {
  if (period === "all") return posts

  const now = new Date()

  if (period === "today") {
    return posts.filter((post) => {
      const publishedAt = post.published_at ?? post.created_at
      return isWithinInterval(parseISO(publishedAt), {
        start: startOfDay(now),
        end: endOfDay(now),
      })
    })
  }

  if (period === "yesterday") {
    const yesterday = subDays(now, 1)
    return posts.filter((post) => {
      const publishedAt = post.published_at ?? post.created_at
      return isWithinInterval(parseISO(publishedAt), {
        start: startOfDay(yesterday),
        end: endOfDay(yesterday),
      })
    })
  }

  const days = parseInt(period, 10)
  const cutoff = subDays(new Date(), days)
  return posts.filter((p) => {
    const d = p.published_at ?? p.created_at
    return isAfter(parseISO(d), cutoff)
  })
}

export default function ContentDashboardPage() {
  const { data: allPosts = [], isLoading } = useContentPosts()
  const { data: settings } = useContentSettings()
  const [period, setPeriod] = useState<PeriodKey>("all")
  const syncVoyager = useSyncVoyager()

  const posts = useMemo(() => filterByPeriod(allPosts, period), [allPosts, period])

  const stats = useMemo(() => {
    const published = posts.filter((p) => p.status === "published")
    const scheduled = posts.filter((p) => p.status === "scheduled")
    const withMetrics = published.filter((p) => p.engagement_rate != null)

    const totalImpressions = published.reduce((s, p) => s + p.impressions, 0)
    const totalLikes = published.reduce((s, p) => s + p.likes, 0)
    const totalComments = published.reduce((s, p) => s + p.comments, 0)
    const avgEngagement =
      withMetrics.length > 0
        ? withMetrics.reduce((s, p) => s + (p.engagement_rate ?? 0), 0) / withMetrics.length
        : null

    const topByImpressions =
      published.filter((p) => p.impressions > 0).sort((a, b) => b.impressions - a.impressions)[0] ??
      null

    const engagements = (p: ContentPost) => p.likes + p.comments + p.shares + p.saves
    const topByEngagement =
      published
        .filter((p) => engagements(p) > 0)
        .sort((a, b) => engagements(b) - engagements(a))[0] ?? null

    const top3 = published
      .filter((p) => p.impressions > 0)
      .sort((a, b) => b.impressions - a.impressions)
      .slice(0, 3)

    const nextScheduled = scheduled
      .filter((p) => p.publish_date)
      .sort(
        (a, b) =>
          new Date(a.publish_date ?? "").getTime() - new Date(b.publish_date ?? "").getTime(),
      )
      .slice(0, 5)

    // by status
    const byStatus = {
      draft: posts.filter((p) => p.status === "draft").length,
      approved: posts.filter((p) => p.status === "approved").length,
      scheduled: scheduled.length,
      published: published.length,
      failed: posts.filter((p) => p.status === "failed").length,
    }

    // by pillar (todos os posts)
    const pillarMap: Record<string, number> = {}
    for (const p of posts) {
      pillarMap[p.pillar] = (pillarMap[p.pillar] ?? 0) + 1
    }
    const byPillar = [
      { name: "Autoridade", value: pillarMap["authority"] ?? 0, color: COLORS.authority },
      { name: "Caso", value: pillarMap["case"] ?? 0, color: COLORS.case },
      { name: "Visão", value: pillarMap["vision"] ?? 0, color: COLORS.vision },
    ]

    // impressions over time (published)
    const impressionsLine = published
      .filter((p) => p.published_at && p.impressions > 0)
      .sort(
        (a, b) =>
          new Date(a.published_at ?? "").getTime() - new Date(b.published_at ?? "").getTime(),
      )
      .map((p) => ({
        date: format(parseISO(p.published_at ?? ""), "dd/MM", { locale: ptBR }),
        impressions: p.impressions,
        likes: p.likes,
        comments: p.comments,
      }))

    // weekly cadence (last 8 calendar weeks based on published_at)
    const weeklyCadence: Array<{ week: string; posts: number }> = []
    for (let i = 7; i >= 0; i--) {
      const weekStart = startOfWeek(subWeeks(new Date(), i), { weekStartsOn: 1 })
      const weekEnd = new Date(weekStart.getTime() + 7 * 86400_000)
      const count = published.filter((p) => {
        if (!p.published_at) return false
        const d = parseISO(p.published_at)
        return d >= weekStart && d < weekEnd
      }).length
      weeklyCadence.push({
        week: format(weekStart, "dd/MM", { locale: ptBR }),
        posts: count,
      })
    }

    // engagement by hook_type
    const hookMap: Record<string, number[]> = {}
    for (const p of published) {
      if (p.hook_type && p.engagement_rate != null) {
        ;(hookMap[p.hook_type] ??= []).push(p.engagement_rate)
      }
    }
    const HOOK_LABELS: Record<string, string> = {
      loop_open: "Loop aberto",
      contrarian: "Contrário",
      identification: "Identificação",
      shortcut: "Atalho",
      benefit: "Benefício",
      data: "Dado",
    }
    const byHook = Object.entries(hookMap)
      .map(([k, vals]) => ({
        name: HOOK_LABELS[k] ?? k,
        avg: parseFloat((vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(2)),
      }))
      .sort((a, b) => b.avg - a.avg)

    // char quality (todos os posts com character_count)
    const charBuckets = { below: 0, ideal: 0, good: 0, over: 0 }
    for (const p of posts) {
      const c = p.character_count ?? p.body.length
      if (c < 900) charBuckets.below++
      else if (c <= 1500) charBuckets.ideal++
      else if (c <= 3000) charBuckets.good++
      else charBuckets.over++
    }
    const charData = [
      { name: "< 900", value: charBuckets.below, color: COLORS.charBelow },
      { name: "900–1500", value: charBuckets.ideal, color: COLORS.charIdeal },
      { name: "1500–3000", value: charBuckets.good, color: COLORS.charGood },
      { name: "> 3000", value: charBuckets.over, color: COLORS.charOver },
    ]

    return {
      totalPosts: posts.length,
      totalPublished: published.length,
      totalScheduled: scheduled.length,
      totalImpressions,
      totalLikes,
      totalComments,
      avgEngagement,
      topByImpressions,
      topByEngagement,
      top3,
      nextScheduled,
      byStatus,
      byPillar,
      impressionsLine,
      weeklyCadence,
      byHook,
      charData,
    }
  }, [posts])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-(--text-tertiary)" />
      </div>
    )
  }

  const postsPerWeekGoal = settings?.posts_per_week ?? 3

  return (
    <div className="flex flex-col gap-6 pb-8">
      {/* ── Filtro de período ────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-(--border-default) bg-(--accent-subtle) text-(--accent-subtle-fg)">
            <Calendar className="h-4 w-4" />
          </div>
          <div className="flex h-8 items-center overflow-hidden rounded-md border border-(--border-default) bg-(--bg-surface)">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setPeriod(opt.key)}
                className={cn(
                  "h-full bg-(--bg-surface) px-3 text-xs font-medium transition-colors",
                  period === opt.key
                    ? "bg-(--accent) text-white"
                    : "text-(--text-secondary) hover:bg-(--bg-overlay)",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-8 text-xs gap-1.5"
          disabled={syncVoyager.isPending}
          onClick={() =>
            syncVoyager.mutate(undefined, {
              onSuccess: () => toast.success("Métricas sincronizadas"),
              onError: (err) => toast.error(err instanceof Error ? err.message : "Erro ao sincronizar"),
            })
          }
        >
          <RefreshCw className={`h-3.5 w-3.5 ${syncVoyager.isPending ? "animate-spin" : ""}`} />
          {syncVoyager.isPending ? "Sincronizando…" : "Sincronizar métricas"}
        </Button>
      </div>

      {/* ── Row 1: Stat cards ──────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 2xl:grid-cols-7 gap-3">
        <StatCard
          icon={<FileText className="h-3.5 w-3.5" />}
          label="Total de posts"
          value={String(stats.totalPosts)}
          sub="criados"
        />
        <StatCard
          icon={<Send className="h-3.5 w-3.5" />}
          label="Publicados"
          value={String(stats.totalPublished)}
          sub={`de ${stats.totalPosts} posts`}
          accent
        />
        <StatCard
          icon={<CalendarClock className="h-3.5 w-3.5" />}
          label="Agendados"
          value={String(stats.totalScheduled)}
          sub="para publicar"
        />
        <StatCard
          icon={<Eye className="h-3.5 w-3.5" />}
          label="Impressões"
          value={fmt(stats.totalImpressions)}
          sub="total acumulado"
        />
        <StatCard
          icon={<Heart className="h-3.5 w-3.5" />}
          label="Likes"
          value={fmt(stats.totalLikes)}
          sub="total acumulado"
        />
        <StatCard
          icon={<MessageCircle className="h-3.5 w-3.5" />}
          label="Comentários"
          value={fmt(stats.totalComments)}
          sub="total acumulado"
        />
        <StatCard
          icon={<TrendingUp className="h-3.5 w-3.5" />}
          label="Eng. Rate médio"
          value={fmtPct(stats.avgEngagement)}
          sub="posts publicados"
          accent={stats.avgEngagement != null && stats.avgEngagement > 3}
        />
      </div>

      {/* ── Row 2: Destaques ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <HighlightPostCard
          title="Post mais visto"
          icon={<Eye className="h-3.5 w-3.5" />}
          post={stats.topByImpressions}
          metric={
            stats.topByImpressions ? fmt(stats.topByImpressions.impressions) + " impressões" : null
          }
          emptyMessage="Nenhum post publicado com impressões ainda."
        />
        <HighlightPostCard
          title="Post mais engajado"
          icon={<Award className="h-3.5 w-3.5" />}
          post={stats.topByEngagement}
          metric={
            stats.topByEngagement
              ? String(
                  stats.topByEngagement.likes +
                    stats.topByEngagement.comments +
                    stats.topByEngagement.shares,
                ) + " engajamentos"
              : null
          }
          hint="Reações + comentários + compartilhamentos + salvamentos"
          emptyMessage="Nenhum post publicado com engajamento ainda."
        />
      </div>

      {/* ── Row 3: Tendências ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <SectionTitle>
            <TrendingUp className="h-3.5 w-3.5 text-(--accent)" />
            Impressões ao longo do tempo
          </SectionTitle>
          {stats.impressionsLine.length < 2 ? (
            <EmptyChart message="Publique ao menos 2 posts com métricas para ver a tendência." />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart
                data={stats.impressionsLine}
                margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" opacity={0.5} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={fmt}
                  width={40}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="impressions"
                  name="Impressões"
                  stroke={COLORS.authority}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="likes"
                  name="Likes"
                  stroke={COLORS.case}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="comments"
                  name="Comentários"
                  stroke={COLORS.scheduled}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <SectionTitle>
            <BarChart2 className="h-3.5 w-3.5 text-(--accent)" />
            Cadência semanal
          </SectionTitle>
          <p className="text-xs text-(--text-tertiary) -mt-2">
            Posts publicados por semana · meta: {postsPerWeekGoal}/sem
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.weeklyCadence} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--border-default)"
                opacity={0.5}
                vertical={false}
              />
              <XAxis dataKey="week" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={20}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={postsPerWeekGoal}
                stroke={COLORS.scheduled}
                strokeDasharray="6 3"
                strokeWidth={1.5}
              />
              <Bar
                dataKey="posts"
                name="Posts"
                fill={COLORS.authority}
                radius={[3, 3, 0, 0]}
                maxBarSize={32}
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* ── Row 4: Distribuições ──────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <SectionTitle>Pipeline de status</SectionTitle>
          <div className="flex flex-col gap-2">
            {[
              { label: "Rascunho", key: "draft", color: COLORS.draft },
              { label: "Aprovado", key: "approved", color: COLORS.approved },
              { label: "Agendado", key: "scheduled", color: COLORS.scheduled },
              { label: "Publicado", key: "published", color: COLORS.published },
              { label: "Falhou", key: "failed", color: COLORS.failed },
            ].map(({ label, key, color }) => {
              const count = stats.byStatus[key as keyof typeof stats.byStatus]
              const pct = stats.totalPosts > 0 ? (count / stats.totalPosts) * 100 : 0
              return (
                <div key={key} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-(--text-secondary)">{label}</span>
                    <span className="font-medium text-(--text-primary)">{count}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-(--bg-overlay) overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>

        <Card>
          <SectionTitle>Posts por pilar</SectionTitle>
          {stats.totalPosts === 0 ? (
            <EmptyChart message="Nenhum post criado ainda." />
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={stats.byPillar}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {stats.byPillar.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number, name: string) => [value, name]}
                  contentStyle={{ fontSize: 12 }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => <span className="text-[11px]">{value as string}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <SectionTitle>Engajamento por gancho</SectionTitle>
          {stats.byHook.length === 0 ? (
            <EmptyChart message="Sem dados de engajamento por gancho ainda." />
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart
                data={stats.byHook}
                layout="vertical"
                margin={{ top: 0, right: 24, left: 0, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border-default)"
                  opacity={0.5}
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${v}%`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  width={72}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar
                  dataKey="avg"
                  name="Eng. Rate %"
                  fill={COLORS.authority}
                  radius={[0, 3, 3, 0]}
                  maxBarSize={18}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* ── Row 5: Top posts + Qualidade + Próximos ──────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top 3 posts */}
        <Card>
          <SectionTitle>
            <Zap className="h-3.5 w-3.5 text-(--accent)" />
            Top 3 posts por impressões
          </SectionTitle>
          {stats.top3.length === 0 ? (
            <EmptyChart message="Nenhum post publicado com impressões ainda." />
          ) : (
            <div className="flex flex-col gap-3">
              {stats.top3.map((p, i) => (
                <Top3Card key={p.id} post={p} rank={i + 1} />
              ))}
            </div>
          )}
        </Card>

        {/* Qualidade do conteúdo */}
        <Card>
          <SectionTitle>Qualidade do conteúdo</SectionTitle>
          <p className="text-xs text-(--text-tertiary) -mt-2">
            Distribuição por faixa de caracteres
          </p>
          {stats.totalPosts === 0 ? (
            <EmptyChart message="Nenhum post criado ainda." />
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={stats.charData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border-default)"
                  opacity={0.5}
                  vertical={false}
                />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={20}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" name="Posts" radius={[3, 3, 0, 0]} maxBarSize={40}>
                  {stats.charData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          <div className="flex flex-wrap gap-2 mt-1">
            {stats.charData.map((d) => (
              <span key={d.name} className="flex items-center gap-1 text-xs text-(--text-tertiary)">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: d.color }}
                />
                {d.name}: <span className="font-medium text-(--text-primary)">{d.value}</span>
              </span>
            ))}
          </div>
        </Card>

        {/* Próximos agendados */}
        <Card>
          <SectionTitle>
            <CalendarClock className="h-3.5 w-3.5 text-(--accent)" />
            Próximos agendados
          </SectionTitle>
          {stats.nextScheduled.length === 0 ? (
            <EmptyChart message="Nenhum post agendado." />
          ) : (
            <div className="flex flex-col divide-y divide-(--border-default)">
              {stats.nextScheduled.map((p) => (
                <div key={p.id} className="py-2.5 flex flex-col gap-1 first:pt-0 last:pb-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-medium text-(--text-primary) truncate flex-1">
                      {p.title}
                    </p>
                    <PillarBadge pillar={p.pillar} />
                  </div>
                  {p.publish_date && (
                    <p className="text-xs text-(--text-tertiary)">
                      {format(parseISO(p.publish_date), "dd MMM yyyy 'às' HH:mm", { locale: ptBR })}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

// ── Highlight Post Card ───────────────────────────────────────────────
function HighlightPostCard({
  title,
  icon,
  post,
  metric,
  emptyMessage,
  hint,
}: {
  title: string
  icon: React.ReactNode
  post: ContentPost | null
  metric: string | null
  emptyMessage: string
  hint?: string
}) {
  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2 text-(--text-tertiary)">
            {icon}
            <span className="text-xs font-semibold uppercase tracking-wide">{title}</span>
          </div>
          {hint && <p className="text-xs text-(--text-tertiary) ml-5.5">{hint}</p>}
        </div>
        {metric && <span className="text-sm font-bold text-(--accent)">{metric}</span>}
      </div>
      {post == null ? (
        <p className="text-xs text-(--text-tertiary)">{emptyMessage}</p>
      ) : (
        <>
          <p className="text-sm font-medium text-(--text-primary)">{post.title}</p>
          <p className="text-xs text-(--text-secondary) line-clamp-2 whitespace-pre-wrap">
            {post.body}
          </p>
          <div className="flex items-center gap-3 text-xs text-(--text-tertiary) pt-1 border-t border-(--border-default)">
            {post.published_at && (
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />{" "}
                {format(parseISO(post.published_at), "dd MMM yyyy", { locale: ptBR })}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Eye className="h-3 w-3" /> {fmt(post.impressions)}
            </span>
            <span className="flex items-center gap-1">
              <Heart className="h-3 w-3" /> {fmt(post.likes)}
            </span>
            <span className="flex items-center gap-1">
              <MessageCircle className="h-3 w-3" /> {fmt(post.comments)}
            </span>
            <span className="flex items-center gap-1">
              <Bookmark className="h-3 w-3" /> {fmt(post.saves)}
            </span>
            {post.engagement_rate != null && (
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" /> {fmtPct(post.engagement_rate)}
              </span>
            )}
            <PillarBadge pillar={post.pillar} />
            {post.linkedin_post_urn && (
              <a
                href={`https://www.linkedin.com/feed/update/${post.linkedin_post_urn}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-(--accent) transition-colors ml-auto"
                title="Abrir no LinkedIn"
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// ── Top 3 Card ────────────────────────────────────────────────────────
function Top3Card({ post, rank }: { post: ContentPost; rank: number }) {
  const rankColors = ["#f59e0b", "#9ca3af", "#cd7c3f"]
  const linkedInUrl = post.linkedin_post_urn
    ? `https://www.linkedin.com/feed/update/${post.linkedin_post_urn}`
    : null
  return (
    <div className="flex items-start gap-3">
      <span
        className="shrink-0 h-5 w-5 rounded-full flex items-center justify-center text-xs font-bold text-white"
        style={{ backgroundColor: rankColors[rank - 1] ?? "#9ca3af" }}
      >
        {rank}
      </span>
      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <p className="text-xs font-medium text-(--text-primary) truncate flex-1">{post.title}</p>
          {linkedInUrl && (
            <a
              href={linkedInUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 text-(--text-tertiary) hover:text-(--accent) transition-colors"
              title="Abrir no LinkedIn"
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-(--text-tertiary)">
          <span>
            <Eye className="h-3 w-3 inline mr-0.5" />
            {fmt(post.impressions)}
          </span>
          {post.engagement_rate != null && (
            <span>
              <TrendingUp className="h-3 w-3 inline mr-0.5" />
              {fmtPct(post.engagement_rate)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
