import { Mail, Eye, MessageSquare, AlertTriangle } from "lucide-react"
import type { EmailStats } from "@/lib/api/hooks/use-analytics"

interface EmailStatsCardProps {
  data: EmailStats
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
      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${colorClass}`}>
        <Icon size={15} aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-(--text-secondary)">{label}</p>
        <p className="text-sm font-semibold text-(--text-primary)">{value}</p>
      </div>
    </div>
  )
}

export function EmailStatsCard({ data, isLoading }: EmailStatsCardProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2.5 animate-pulse">
            <div className="h-8 w-8 rounded-md bg-(--bg-overlay)" />
            <div className="space-y-1.5">
              <div className="h-2.5 w-16 rounded bg-(--bg-overlay)" />
              <div className="h-3.5 w-10 rounded bg-(--bg-overlay)" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
      <MetricItem
        icon={Mail}
        label="Enviados"
        value={data.sent.toLocaleString("pt-BR")}
        colorClass="bg-(--accent-subtle) text-(--accent)"
      />
      <MetricItem
        icon={Eye}
        label="Taxa de abertura"
        value={`${data.open_rate.toFixed(1)}%`}
        colorClass="bg-(--success-subtle) text-(--success)"
      />
      <MetricItem
        icon={MessageSquare}
        label="Taxa de resposta"
        value={`${data.reply_rate.toFixed(1)}%`}
        colorClass="bg-(--success-subtle) text-(--success)"
      />
      <MetricItem
        icon={AlertTriangle}
        label="Bounce"
        value={`${data.bounce_rate.toFixed(1)}%`}
        colorClass={
          data.bounce_rate > 5
            ? "bg-(--danger-subtle) text-(--danger)"
            : "bg-(--warning-subtle) text-(--warning)"
        }
      />
    </div>
  )
}
