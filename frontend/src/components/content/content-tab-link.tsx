"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { type LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Route } from "next"

interface ContentTabLinkProps {
  href: string
  label: string
  Icon: LucideIcon
}

export function ContentTabLink({ href, label, Icon }: ContentTabLinkProps) {
  const pathname = usePathname()
  const isActive = pathname === href

  return (
    <Link
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
}
