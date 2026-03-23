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
        "rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-sm)]",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
            {label}
          </p>
          <p className="mt-1.5 text-2xl font-semibold text-[var(--text-primary)]">{value}</p>
          {description && (
            <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{description}</p>
          )}
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent-subtle)]">
          <Icon size={18} className="text-[var(--accent)]" aria-hidden="true" />
        </div>
      </div>

      {trend && (
        <p
          className={cn(
            "mt-3 text-xs font-medium",
            trendPositive ? "text-[var(--success)]" : "text-[var(--danger)]",
          )}
        >
          {trendPositive ? "+" : ""}
          {trend.value}% {trend.label}
        </p>
      )}
    </div>
  )
}
