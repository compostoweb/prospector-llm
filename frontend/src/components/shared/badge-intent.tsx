import { cn, intentConfig } from "@/lib/utils"

interface BadgeIntentProps {
  intent: string
  className?: string
}

const variantClasses: Record<string, string> = {
  success:
    "bg-(--success-subtle) text-(--success-subtle-fg) border-(--success-subtle)",
  warning:
    "bg-(--warning-subtle) text-(--warning-subtle-fg) border-(--warning-subtle)",
  danger: "bg-(--danger-subtle) text-(--danger-subtle-fg) border-(--danger-subtle)",
  neutral:
    "bg-(--neutral-subtle) text-(--neutral-subtle-fg) border-(--neutral-subtle)",
  info: "bg-(--info-subtle) text-(--info-subtle-fg) border-(--info-subtle)",
}

export function BadgeIntent({ intent, className }: BadgeIntentProps) {
  const config = intentConfig(intent)

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-(--radius-full) border px-2 py-0.5 text-xs font-medium",
        variantClasses[config.variant] ?? variantClasses["neutral"],
        className,
      )}
    >
      {config.label}
    </span>
  )
}
