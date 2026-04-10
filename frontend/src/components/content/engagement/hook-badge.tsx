import { cn } from "@/lib/utils"
import type { HookType } from "@/lib/content-engagement/types"

const HOOK_LABELS: Record<HookType, string> = {
  loop_open: "Loop Aberto",
  contrarian: "Contrarian",
  identification: "Identificação",
  shortcut: "Atalho",
  benefit: "Benefício",
  data: "Dado",
}

const HOOK_COLORS: Record<HookType, string> = {
  loop_open: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  contrarian: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  identification: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  shortcut: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  benefit: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  data: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
}

interface HookBadgeProps {
  hookType: HookType | null | undefined
  className?: string
}

export function HookBadge({ hookType, className }: HookBadgeProps) {
  if (!hookType) return null

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        HOOK_COLORS[hookType],
        className
      )}
    >
      {HOOK_LABELS[hookType]}
    </span>
  )
}
