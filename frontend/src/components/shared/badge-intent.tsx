import { cn, intentConfig } from "@/lib/utils"

interface BadgeIntentProps {
  intent: string
  className?: string
}

const variantClasses: Record<string, string> = {
  success:
    "bg-[var(--success-subtle)] text-[var(--success-subtle-fg)] border-[var(--success-subtle)]",
  warning:
    "bg-[var(--warning-subtle)] text-[var(--warning-subtle-fg)] border-[var(--warning-subtle)]",
  danger: "bg-[var(--danger-subtle)] text-[var(--danger-subtle-fg)] border-[var(--danger-subtle)]",
  neutral:
    "bg-[var(--neutral-subtle)] text-[var(--neutral-subtle-fg)] border-[var(--neutral-subtle)]",
  info: "bg-[var(--info-subtle)] text-[var(--info-subtle-fg)] border-[var(--info-subtle)]",
}

export function BadgeIntent({ intent, className }: BadgeIntentProps) {
  const config = intentConfig(intent)

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-[var(--radius-full)] border px-2 py-0.5 text-xs font-medium",
        variantClasses[config.variant] ?? variantClasses["neutral"],
        className,
      )}
    >
      {config.label}
    </span>
  )
}
