import { cn } from "@/lib/utils"
import type { PostPillar } from "@/lib/content-engagement/types"

const PILLAR_LABELS: Record<PostPillar, string> = {
  authority: "Autoridade",
  case: "Case",
  vision: "Visão",
}

const PILLAR_COLORS: Record<PostPillar, string> = {
  authority: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  case: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  vision: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
}

interface PillarBadgeProps {
  pillar: PostPillar | null | undefined
  className?: string
}

export function PillarBadge({ pillar, className }: PillarBadgeProps) {
  if (!pillar) return null

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        PILLAR_COLORS[pillar],
        className
      )}
    >
      {PILLAR_LABELS[pillar]}
    </span>
  )
}
