"use client"

import { cn } from "@/lib/utils"

interface PeriodFilterProps {
  value: number
  onChange: (days: number) => void
  className?: string
}

const OPTIONS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
] as const

export function PeriodFilter({ value, onChange, className }: PeriodFilterProps) {
  return (
    <div className={cn("inline-flex rounded-md border border-(--border-default) p-0.5", className)}>
      {OPTIONS.map(({ label, days }) => (
        <button
          key={days}
          type="button"
          onClick={() => onChange(days)}
          className={cn(
            "rounded-sm px-3 py-1 text-xs font-medium transition-colors",
            value === days
              ? "bg-(--accent) text-(--text-invert)"
              : "text-(--text-secondary) hover:text-(--text-primary)",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
