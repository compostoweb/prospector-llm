"use client"

import { AnalyticsPeriodFilter } from "@/components/shared/analytics-period-filter"
import { buildDateFilterValue, type AnalyticsDateFilterOption } from "@/lib/analytics-period"

interface PeriodFilterProps {
  value: number
  onChange: (days: number) => void
  className?: string
}

const OPTIONS: AnalyticsDateFilterOption[] = [
  { id: "last_7_days", label: "7 dias", days: 7 },
  { id: "last_30_days", label: "30 dias", days: 30 },
  { id: "last_90_days", label: "90 dias", days: 90 },
]

export function PeriodFilter({ value, onChange, className }: PeriodFilterProps) {
  const selectedOption = OPTIONS.find((option) => option.days === value) ?? OPTIONS[1]

  return (
    <AnalyticsPeriodFilter
      value={buildDateFilterValue(selectedOption)}
      onChange={(next) => {
        const matched = OPTIONS.find((option) => option.id === next.id)
        onChange(matched?.days ?? 30)
      }}
      options={OPTIONS}
      enableCustom={false}
      className={className}
    />
  )
}
