"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { FileText, Sparkles, Settings2 } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Route } from "next"

const TABS = [
  { href: "/content", label: "Calendário", Icon: FileText },
  { href: "/content/gerar", label: "Gerar com IA", Icon: Sparkles },
  { href: "/content/configuracoes", label: "Configurações", Icon: Settings2 },
]

export function ContentTabs() {
  const pathname = usePathname()

  return (
    <nav className="flex gap-1 border-b border-(--border-default)">
      {TABS.map(({ href, label, Icon }) => {
        const isActive = pathname === href
        return (
          <Link
            key={href}
            href={href as Route}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm border-b-2 -mb-px transition-colors",
              isActive
                ? "border-(--accent) text-(--accent) font-medium"
                : "border-transparent text-(--text-secondary) hover:text-(--text-primary)",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        )
      })}
    </nav>
  )
}
