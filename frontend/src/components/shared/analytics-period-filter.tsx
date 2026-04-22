"use client"

import { useEffect, useMemo, useState } from "react"
import {
  addDays,
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isWithinInterval,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns"
import { ptBR } from "date-fns/locale"
import { CalendarRange, Check, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  ANALYTICS_DATE_FILTER_OPTIONS,
  buildDateFilterValue,
  formatSelectedRangeLabel,
  parseInputDate,
  type AnalyticsDateFilterOption,
  type AnalyticsDateFilterValue,
} from "@/lib/analytics-period"
import { cn } from "@/lib/utils"

interface AnalyticsPeriodFilterProps {
  value: AnalyticsDateFilterValue
  onChange: (next: AnalyticsDateFilterValue) => void
  options?: readonly AnalyticsDateFilterOption[]
  enableCustom?: boolean
  className?: string
}

const WEEKDAY_LABELS = Array.from({ length: 7 }, (_, index) =>
  format(addDays(startOfWeek(new Date(), { weekStartsOn: 1 }), index), "EEEEE", { locale: ptBR }),
)

function MonthCalendar({
  month,
  startDate,
  endDate,
  onSelect,
}: {
  month: Date
  startDate: string
  endDate: string
  onSelect: (value: string) => void
}) {
  const intervalStart = startOfWeek(startOfMonth(month), { weekStartsOn: 1 })
  const intervalEnd = endOfWeek(endOfMonth(month), { weekStartsOn: 1 })
  const days = eachDayOfInterval({ start: intervalStart, end: intervalEnd })
  const rangeStart = parseInputDate(startDate)
  const rangeEnd = parseInputDate(endDate)

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-2.5">
      <div className="mb-2 text-center text-[13px] font-semibold capitalize text-(--text-primary)">
        {format(month, "MMMM yyyy", { locale: ptBR })}
      </div>
      <div className="mb-1.5 grid grid-cols-7 gap-1">
        {WEEKDAY_LABELS.map((weekday, index) => (
          <div
            key={`${weekday}-${index}`}
            className="flex h-6 items-center justify-center text-[10px] font-medium uppercase text-(--text-tertiary)"
          >
            {weekday}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => {
          const value = format(day, "yyyy-MM-dd")
          const isStart = isSameDay(day, rangeStart)
          const isEnd = isSameDay(day, rangeEnd)
          const isSingleDay = startDate === endDate && isStart && isEnd
          const isBetween =
            startDate !== endDate && isWithinInterval(day, { start: rangeStart, end: rangeEnd })
          const isCurrentMonth = isSameMonth(day, month)

          return (
            <button
              key={value}
              type="button"
              onClick={() => onSelect(value)}
              className={cn(
                "flex h-8 items-center justify-center rounded-md text-[13px] transition-colors",
                isSingleDay || isStart || isEnd
                  ? "bg-(--accent) font-semibold text-white"
                  : isBetween
                    ? "bg-(--accent-subtle) text-(--accent-subtle-fg)"
                    : isCurrentMonth
                      ? "text-(--text-primary) hover:bg-(--bg-overlay)"
                      : "text-(--text-disabled) hover:bg-(--bg-overlay)",
              )}
            >
              {format(day, "d")}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function AnalyticsPeriodFilter({
  value,
  onChange,
  options = ANALYTICS_DATE_FILTER_OPTIONS,
  enableCustom = true,
  className,
}: AnalyticsPeriodFilterProps) {
  const [open, setOpen] = useState(false)
  const [draftStartDate, setDraftStartDate] = useState(value.startDate)
  const [draftEndDate, setDraftEndDate] = useState(value.endDate)
  const [visibleMonth, setVisibleMonth] = useState(() =>
    startOfMonth(parseInputDate(value.startDate)),
  )

  useEffect(() => {
    setDraftStartDate(value.startDate)
    setDraftEndDate(value.endDate)
    setVisibleMonth(startOfMonth(parseInputDate(value.startDate)))
  }, [value.endDate, value.startDate])

  const selectedLabel = value.id === "custom" ? "Personalizado" : value.label
  const resolvedDraftEndDate = draftEndDate || draftStartDate
  const canApplyCustom = draftStartDate.trim().length > 0
  const calendarMonths = useMemo(() => [visibleMonth, addMonths(visibleMonth, 1)], [visibleMonth])

  function handlePresetSelect(option: AnalyticsDateFilterOption) {
    onChange(buildDateFilterValue(option))
    setOpen(false)
  }

  function handleCalendarSelect(nextValue: string) {
    if (!draftStartDate || (draftStartDate && draftEndDate)) {
      setDraftStartDate(nextValue)
      setDraftEndDate("")
      return
    }

    if (nextValue < draftStartDate) {
      setDraftEndDate(draftStartDate)
      setDraftStartDate(nextValue)
      return
    }

    setDraftEndDate(nextValue)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex min-h-12 min-w-64 items-center justify-between gap-3 rounded-xl border border-(--border-default) bg-(--bg-surface) px-3.5 py-2.5 text-left shadow-(--shadow-sm) transition-colors hover:bg-amber-100",
            open && "border-(--accent)",
            className,
          )}
        >
          <div className="flex min-w-0 items-center gap-2.5 self-center">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-(--bg-overlay) text-(--accent)">
              <CalendarRange size={15} aria-hidden="true" />
            </div>
            <div className="min-w-0 self-center">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 leading-none">
                <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-(--text-tertiary)">
                  Período
                </span>
                <span className="text-sm font-semibold text-(--text-primary)">{selectedLabel}</span>
                <span className="text-[12px] text-(--text-secondary)">
                  {formatSelectedRangeLabel(value.startDate, value.endDate)}
                </span>
              </div>
            </div>
          </div>
          <ChevronDown
            size={15}
            className="shrink-0 self-center text-(--text-tertiary)"
            aria-hidden="true"
          />
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-[min(95vw,46rem)] rounded-xl border border-(--border-default) bg-(--bg-surface) p-3 shadow-(--shadow-md)"
      >
        <div className="space-y-3">
          <div className="flex flex-col gap-0.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-(--text-tertiary)">
              Filtros rápidos
            </p>
            <p className="text-xs text-(--text-secondary)">
              Selecione um período pronto ou monte um intervalo exato.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            {options.map((option) => {
              const isActive = value.id === option.id

              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => handlePresetSelect(option)}
                  className={cn(
                    "flex items-center justify-between rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "border-(--accent) bg-(--accent) text-white"
                      : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:bg-(--bg-overlay) hover:text-(--text-primary)",
                  )}
                >
                  <span>{option.label}</span>
                  <Check size={14} className={cn(isActive ? "opacity-100" : "opacity-0")} />
                </button>
              )
            })}
          </div>

          {enableCustom ? (
            <div className="rounded-xl border border-(--border-default) bg-(--bg-overlay) p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-(--text-primary)">Personalizado</p>
                  <p className="text-xs text-(--text-secondary)">
                    Clique no calendário para definir início e fim do intervalo.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setVisibleMonth((current) => subMonths(current, 1))}
                    className="rounded-md border border-(--border-default) bg-(--bg-surface) p-1.5 text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                    aria-label="Mês anterior"
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setVisibleMonth((current) => addMonths(current, 1))}
                    className="rounded-md border border-(--border-default) bg-(--bg-surface) p-1.5 text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                    aria-label="Próximo mês"
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>

              <div className="mt-3 grid gap-2.5 xl:grid-cols-2">
                {calendarMonths.map((month) => (
                  <MonthCalendar
                    key={month.toISOString()}
                    month={month}
                    startDate={draftStartDate}
                    endDate={resolvedDraftEndDate}
                    onSelect={handleCalendarSelect}
                  />
                ))}
              </div>

              <div className="mt-3 grid gap-2.5 md:grid-cols-2">
                <div className="space-y-1.5">
                  <label
                    className="text-xs font-medium text-(--text-secondary)"
                    htmlFor="analytics-range-start-date"
                  >
                    De
                  </label>
                  <Input
                    id="analytics-range-start-date"
                    type="date"
                    value={draftStartDate}
                    max={resolvedDraftEndDate || undefined}
                    onChange={(e) => setDraftStartDate(e.target.value)}
                    className="h-9 bg-(--bg-surface)"
                  />
                </div>
                <div className="space-y-1.5">
                  <label
                    className="text-xs font-medium text-(--text-secondary)"
                    htmlFor="analytics-range-end-date"
                  >
                    Até
                  </label>
                  <Input
                    id="analytics-range-end-date"
                    type="date"
                    value={resolvedDraftEndDate}
                    min={draftStartDate || undefined}
                    onChange={(e) => setDraftEndDate(e.target.value)}
                    className="h-9 bg-(--bg-surface)"
                  />
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2.5">
                <p className="text-xs text-(--text-secondary)">
                  Intervalo selecionado:{" "}
                  {formatSelectedRangeLabel(draftStartDate, resolvedDraftEndDate)}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDraftStartDate(value.startDate)
                      setDraftEndDate(value.endDate)
                    }}
                    className="rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 text-sm font-medium text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                  >
                    Reverter
                  </button>
                  <button
                    type="button"
                    disabled={!canApplyCustom}
                    onClick={() => {
                      onChange(
                        buildDateFilterValue(
                          { id: "custom", label: "Personalizado" },
                          {
                            startDate: draftStartDate,
                            endDate: resolvedDraftEndDate,
                          },
                        ),
                      )
                      setOpen(false)
                    }}
                    className="rounded-md bg-(--accent) px-3 py-1.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Aplicar período
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </PopoverContent>
    </Popover>
  )
}
