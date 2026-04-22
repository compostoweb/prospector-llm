import { MessageSquare, UserPlus, CheckCircle2, Send } from "lucide-react"
import type { LinkedInStats } from "@/lib/api/hooks/use-analytics"

interface LinkedInStatsCardProps {
  data: LinkedInStats
  isLoading?: boolean
}

interface MetricItemProps {
  icon: React.ElementType
  label: string
  value: string | number
  colorClass: string
}

function MetricItem({ icon: Icon, label, value, colorClass }: MetricItemProps) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md ${colorClass}`}
      >
        <Icon size={20} aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-(--text-secondary)">{label}</p>
        <p className="text-lg font-semibold text-(--text-primary)">{value}</p>
      </div>
    </div>
  )
}

export function LinkedInStatsCard({ data, isLoading }: LinkedInStatsCardProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2.5 animate-pulse">
            <div className="h-8 w-8 rounded-md bg-(--bg-overlay)" />
            <div className="space-y-1.5">
              <div className="h-2.5 w-20 rounded bg-(--bg-overlay)" />
              <div className="h-3.5 w-10 rounded bg-(--bg-overlay)" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 lg:grid-cols-6">
      <MetricItem
        icon={UserPlus}
        label="Conexões enviadas"
        value={data.connect_sent.toLocaleString("pt-BR")}
        colorClass="bg-(--accent-subtle) text-(--accent)"
      />
      <MetricItem
        icon={CheckCircle2}
        label="Conexões aceitas"
        value={data.connect_accepted.toLocaleString("pt-BR")}
        colorClass="bg-(--success-subtle) text-(--success)"
      />
      <MetricItem
        icon={CheckCircle2}
        label="Taxa de aceite"
        value={`${data.connect_acceptance_rate.toFixed(1)}%`}
        colorClass="bg-(--success-subtle) text-(--success)"
      />
      <MetricItem
        icon={Send}
        label="DMs enviadas"
        value={data.dm_sent.toLocaleString("pt-BR")}
        colorClass="bg-(--info-subtle) text-(--info)"
      />
      <MetricItem
        icon={MessageSquare}
        label="Respostas em DM"
        value={data.dm_replied.toLocaleString("pt-BR")}
        colorClass="bg-(--accent-subtle) text-(--accent)"
      />
      <MetricItem
        icon={MessageSquare}
        label="Taxa de resposta DM"
        value={`${data.dm_reply_rate.toFixed(1)}%`}
        colorClass="bg-(--success-subtle) text-(--success)"
      />
    </div>
  )
}
