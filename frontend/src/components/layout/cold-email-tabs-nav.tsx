"use client"

import type { Route } from "next"
import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { FileText, Flame, Mail } from "lucide-react"
import { ColdEmailOverviewActions } from "@/components/cold-email/cold-email-overview-actions"
import { AnalyticsPeriodFilter } from "@/components/shared/analytics-period-filter"
import { buildDateFilterValue, resolveDateFilterValue } from "@/lib/analytics-period"
import { cn } from "@/lib/utils"

const tabs = [
  { href: "/cold-email", label: "Visão geral", icon: Mail },
  { href: "/cold-email/warmup", label: "Warm-up", icon: Flame },
  { href: "/cold-email/templates", label: "Templates", icon: FileText },
] as const

export function ColdEmailTabsNav() {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const showDateFilter = pathname === "/cold-email"
  const showOverviewHeader = pathname === "/cold-email"
  const showOverviewActions = pathname === "/cold-email"
  const startDate = searchParams.get("start_date")
  const endDate = searchParams.get("end_date")
  const dateFilter =
    startDate && endDate
      ? resolveDateFilterValue({ startDate, endDate })
      : buildDateFilterValue({ id: "last_30_days", label: "30 dias", days: 30 })

  function handleDateFilterChange(next: typeof dateFilter) {
    const params = new URLSearchParams(searchParams.toString())
    params.set("start_date", next.startDate)
    params.set("end_date", next.endDate)
    const query = params.toString()
    const nextUrl = query ? `${pathname}?${query}` : pathname
    router.replace(nextUrl as Route, { scroll: false })
  }

  return (
    <div className="border-b border-(--border-default) bg-(--bg-page)">
      {showOverviewHeader ? (
        <div className="flex flex-col gap-3 pb-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold text-(--text-primary)">Cold Email</h1>
            <p className="text-sm text-(--text-secondary)">Cadências de prospecção por e-mail</p>
          </div>

          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center sm:justify-end">
            {showOverviewActions ? <ColdEmailOverviewActions /> : null}
            {showDateFilter ? (
              <AnalyticsPeriodFilter
                value={dateFilter}
                onChange={handleDateFilterChange}
                className="w-full sm:min-w-72 sm:w-auto"
              />
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <nav
          aria-label="Cold Email"
          className="-mb-px flex min-w-0 flex-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {tabs.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/cold-email"
                ? pathname === href
                : pathname === href || pathname.startsWith(href + "/")
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm transition-colors md:px-4",
                  active
                    ? "border-(--accent) font-medium text-(--accent-subtle-fg)"
                    : "border-transparent text-(--text-secondary) hover:border-(--border-default) hover:text-(--text-primary)",
                )}
              >
                <Icon size={15} aria-hidden="true" className="shrink-0" />
                <span className="whitespace-nowrap">{label}</span>
              </Link>
            )
          })}
        </nav>
      </div>
    </div>
  )
}
