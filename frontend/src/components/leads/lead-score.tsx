import { cn, scoreVariant } from "@/lib/utils"

interface LeadScoreProps {
  score: number
  size?: "sm" | "md"
  showLabel?: boolean
  className?: string
}

const variantColors: Record<ReturnType<typeof scoreVariant>, string> = {
  success: "text-[var(--success)] bg-[var(--success-subtle)]",
  warning: "text-[var(--warning)] bg-[var(--warning-subtle)]",
  danger: "text-[var(--danger)] bg-[var(--danger-subtle)]",
}

const ringColors: Record<ReturnType<typeof scoreVariant>, string> = {
  success: "stroke-[var(--success)]",
  warning: "stroke-[var(--warning)]",
  danger: "stroke-[var(--danger)]",
}

export function LeadScore({ score, size = "md", showLabel = false, className }: LeadScoreProps) {
  const variant = scoreVariant(score)
  const radius = size === "sm" ? 10 : 14
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference - (score / 100) * circumference

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {/* Anel SVG */}
      <div
        className={cn(
          "relative flex items-center justify-center rounded-full",
          variantColors[variant],
          size === "sm" ? "h-8 w-8" : "h-11 w-11",
        )}
      >
        <svg
          className="absolute inset-0 -rotate-90"
          width="100%"
          height="100%"
          viewBox={`0 0 ${(radius + 4) * 2} ${(radius + 4) * 2}`}
          aria-hidden="true"
        >
          {/* Trilha */}
          <circle
            cx={radius + 4}
            cy={radius + 4}
            r={radius}
            fill="none"
            strokeWidth="2.5"
            className="stroke-current opacity-20"
          />
          {/* Progresso */}
          <circle
            cx={radius + 4}
            cy={radius + 4}
            r={radius}
            fill="none"
            strokeWidth="2.5"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            className={ringColors[variant]}
          />
        </svg>
        <span
          className={cn(
            "relative font-bold tabular-nums",
            size === "sm" ? "text-[10px]" : "text-[11px]",
          )}
        >
          {score}
        </span>
      </div>

      {showLabel && <span className="text-xs text-[var(--text-secondary)]">score</span>}
    </div>
  )
}
