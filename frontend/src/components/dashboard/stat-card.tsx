import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface StatCardProps {
  label: string
  value: number | string
  icon: LucideIcon
  description?: string
  trend?: { value: number; label: string }
  className?: string
}

export function StatCard({
  label,
  value,
  icon: Icon,
  description,
  trend,
  className,
}: StatCardProps) {
  const trendPositive = trend && trend.value >= 0

  return (
    <div
      className={cn(
        "rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
            {label}
          </p>
          <p className="mt-1.5 text-2xl font-semibold text-(--text-primary)">{value}</p>
          {description && (
            <p className="mt-0.5 text-xs text-(--text-secondary)">{description}</p>
          )}
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-(--accent-subtle)">
          <Icon size={18} className="text-(--accent)" aria-hidden="true" />
        </div>
      </div>

      {trend && (
        <p
          className={cn(
            "mt-3 text-xs font-medium",
            trendPositive ? "text-(--success)" : "text-(--danger)",
          )}
        >
          {trendPositive ? "+" : ""}
          {trend.value}% {trend.label}
        </p>
      )}
    </div>
  )
}
