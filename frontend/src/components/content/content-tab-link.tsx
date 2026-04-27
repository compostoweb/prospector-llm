"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  FileText,
  Sparkles,
  Settings2,
  BookOpen,
  LayoutDashboard,
  Lightbulb,
  LayoutList,
  Inbox,
  MessageSquare,
  ImageIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { Route } from "next"

const TABS = [
  { href: "/content", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/content/posts", label: "Posts", Icon: LayoutList },
  { href: "/content/calendario", label: "Calendário", Icon: FileText },
  { href: "/content/inbound", label: "Inbound", Icon: Inbox },
  { href: "/content/engajamento", label: "Engajamento", Icon: MessageSquare },
  { href: "/content/gerar", label: "Gerar com IA", Icon: Sparkles },
  { href: "/content/galeria", label: "Galeria", Icon: ImageIcon },
  { href: "/content/temas", label: "Temas", Icon: Lightbulb },
  { href: "/content/referencias", label: "Referências", Icon: BookOpen },
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
