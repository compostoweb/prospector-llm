import { cn, scoreVariant } from "@/lib/utils"

interface LeadScoreProps {
  score: number | null
  size?: "sm" | "md"
  showLabel?: boolean
  className?: string
}

const variantColors: Record<ReturnType<typeof scoreVariant>, string> = {
  success: "text-(--success) bg-(--success-subtle)",
  warning: "text-(--warning) bg-(--warning-subtle)",
  danger: "text-(--danger) bg-(--danger-subtle)",
}

const ringColors: Record<ReturnType<typeof scoreVariant>, string> = {
  success: "stroke-(--success)",
  warning: "stroke-(--warning)",
  danger: "stroke-(--danger)",
}

export function LeadScore({ score, size = "md", showLabel = false, className }: LeadScoreProps) {
  const normalizedScore = Math.max(0, Math.min(score ?? 0, 100))
  const variant = scoreVariant(normalizedScore)
  const radius = size === "sm" ? 10 : 14
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference - (normalizedScore / 100) * circumference

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
          {normalizedScore}
        </span>
      </div>

      {showLabel && <span className="text-xs text-(--text-secondary)">score</span>}
    </div>
  )
}
