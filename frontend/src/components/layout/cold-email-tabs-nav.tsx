"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { FileText, Flame, Mail } from "lucide-react"
import { cn } from "@/lib/utils"

const tabs = [
  { href: "/cold-email", label: "Visão geral", icon: Mail },
  { href: "/cold-email/warmup", label: "Warm-up", icon: Flame },
  { href: "/cold-email/templates", label: "Templates", icon: FileText },
] as const

export function ColdEmailTabsNav() {
  const pathname = usePathname()

  return (
    <div className="border-b border-(--border-default) bg-(--bg-page)">
      <nav
        aria-label="Cold Email"
        className="-mb-px flex w-full overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
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
  )
}
