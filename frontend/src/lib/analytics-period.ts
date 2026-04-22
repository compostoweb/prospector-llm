import { addDays, differenceInCalendarDays, format, parseISO } from "date-fns"
import { ptBR } from "date-fns/locale"

export interface AnalyticsRangeQuery {
  days?: number
  startDate?: string
  endDate?: string
}

export type AnalyticsDatePresetId =
  | "today"
  | "yesterday"
  | "last_7_days"
  | "last_15_days"
  | "last_30_days"
  | "last_60_days"
  | "last_90_days"
  | "custom"

export interface AnalyticsDateFilterOption {
  id: AnalyticsDatePresetId
  label: string
  days?: number
}

export interface AnalyticsDateFilterValue {
  id: AnalyticsDatePresetId
  label: string
  startDate: string
  endDate: string
}

export const ANALYTICS_DATE_FILTER_OPTIONS: AnalyticsDateFilterOption[] = [
  { id: "today", label: "Hoje" },
  { id: "yesterday", label: "Ontem" },
  { id: "last_7_days", label: "7 dias", days: 7 },
  { id: "last_15_days", label: "15 dias", days: 15 },
  { id: "last_30_days", label: "30 dias", days: 30 },
  { id: "last_60_days", label: "60 dias", days: 60 },
  { id: "last_90_days", label: "90 dias", days: 90 },
]

export function formatDateForInput(date: Date): string {
  return format(date, "yyyy-MM-dd")
}

export function parseInputDate(value: string): Date {
  return parseISO(value)
}

export function shiftInputDate(value: string, days: number): string {
  return formatDateForInput(addDays(parseInputDate(value), days))
}

export function getTodayInputDate(anchorDate = new Date()): string {
  return formatDateForInput(anchorDate)
}

export function formatSelectedRangeLabel(startDate: string, endDate: string): string {
  const start = format(parseInputDate(startDate), "dd/MM/yyyy", { locale: ptBR })
  const end = format(parseInputDate(endDate), "dd/MM/yyyy", { locale: ptBR })

  if (startDate === endDate) {
    return start
  }

  return `${start} - ${end}`
}

export function buildDateFilterValue(
  option: AnalyticsDateFilterOption | { id: "custom"; label: string },
  customRange?: { startDate: string; endDate: string },
  anchorDate = new Date(),
): AnalyticsDateFilterValue {
  const today = getTodayInputDate(anchorDate)

  if (option.id === "today") {
    return { id: option.id, label: option.label, startDate: today, endDate: today }
  }

  if (option.id === "yesterday") {
    const yesterday = shiftInputDate(today, -1)
    return { id: option.id, label: option.label, startDate: yesterday, endDate: yesterday }
  }

  if (option.id === "custom") {
    return {
      id: option.id,
      label: option.label,
      startDate: customRange?.startDate ?? today,
      endDate: customRange?.endDate ?? today,
    }
  }

  const span = Math.max((option.days ?? 1) - 1, 0)
  return {
    id: option.id,
    label: option.label,
    startDate: shiftInputDate(today, -span),
    endDate: today,
  }
}

export function resolveDateFilterValue(
  range: { startDate: string; endDate: string },
  anchorDate = new Date(),
): AnalyticsDateFilterValue {
  const matchedOption = ANALYTICS_DATE_FILTER_OPTIONS.find((option) => {
    const presetValue = buildDateFilterValue(option, undefined, anchorDate)
    return presetValue.startDate === range.startDate && presetValue.endDate === range.endDate
  })

  if (matchedOption) {
    return buildDateFilterValue(matchedOption, undefined, anchorDate)
  }

  return buildDateFilterValue({ id: "custom", label: "Personalizado" }, range, anchorDate)
}

export function getDateFilterDayCount(startDate: string, endDate: string): number {
  return differenceInCalendarDays(parseInputDate(endDate), parseInputDate(startDate)) + 1
}

export function getRangeQueryFromFilter(value: AnalyticsDateFilterValue): AnalyticsRangeQuery {
  return {
    startDate: value.startDate,
    endDate: value.endDate,
  }
}

export function buildAnalyticsQueryString(range: AnalyticsRangeQuery = {}): string {
  const params = new URLSearchParams()

  if (range.startDate && range.endDate) {
    params.set("start_date", range.startDate)
    params.set("end_date", range.endDate)
  } else {
    params.set("days", String(range.days ?? 30))
  }

  const query = params.toString()
  return query ? `?${query}` : ""
}
