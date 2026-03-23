import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-(--border-default) bg-(--bg-surface) px-6 py-16 text-center",
        className,
      )}
    >
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-(--bg-overlay)">
          <Icon size={24} className="text-(--text-tertiary)" aria-hidden="true" />
        </div>
      )}
      <div>
        <p className="text-sm font-medium text-(--text-primary)">{title}</p>
        {description && <p className="mt-1 text-sm text-(--text-secondary)">{description}</p>}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}
