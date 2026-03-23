"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Users,
  GitBranch,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  User,
  Plug,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useUIStore } from "@/store/ui-store"

// ── Navegação ─────────────────────────────────────────────────────────

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/cadencias", label: "Cadências", icon: GitBranch },
] as const

const settingsItems = [
  { href: "/configuracoes/conta", label: "Conta", icon: User },
  { href: "/configuracoes/llm", label: "Modelos LLM", icon: Zap },
  { href: "/configuracoes/unipile", label: "Unipile", icon: Plug },
  { href: "/configuracoes/integracoes", label: "Integrações", icon: Settings },
] as const

// ── Sidebar ───────────────────────────────────────────────────────────

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  return (
    <aside
      className={cn(
        "group relative flex h-full flex-col border-r border-(--border-default) bg-(--bg-surface) transition-[width] duration-200",
        sidebarCollapsed ? "w-14" : "w-56",
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-14 items-center border-b border-(--border-default) px-3",
          sidebarCollapsed ? "justify-center" : "gap-2",
        )}
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-(--accent)">
          <span className="text-[10px] font-bold text-white">P</span>
        </div>
        {!sidebarCollapsed && (
          <span className="text-sm font-semibold text-(--text-primary)">Prospector</span>
        )}
      </div>

      {/* Navegação principal */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/")
          return (
            <Link
              key={href}
              href={href}
              title={sidebarCollapsed ? label : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                active
                  ? "bg-(--accent-subtle) text-(--accent-subtle-fg) font-medium"
                  : "text-(--text-secondary) hover:bg-(--bg-overlay) hover:text-(--text-primary)",
                sidebarCollapsed && "justify-center",
              )}
            >
              <Icon size={16} aria-hidden="true" className="shrink-0" />
              {!sidebarCollapsed && <span>{label}</span>}
            </Link>
          )
        })}

        {/* Separador */}
        <div className="my-2 border-t border-(--border-subtle)" />

        {/* Configurações */}
        {!sidebarCollapsed && (
          <p className="mb-1 px-2.5 text-[11px] font-medium uppercase tracking-wider text-(--text-tertiary)">
            Configurações
          </p>
        )}
        {settingsItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              title={sidebarCollapsed ? label : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                active
                  ? "bg-(--accent-subtle) text-(--accent-subtle-fg) font-medium"
                  : "text-(--text-secondary) hover:bg-(--bg-overlay) hover:text-(--text-primary)",
                sidebarCollapsed && "justify-center",
              )}
            >
              <Icon size={16} aria-hidden="true" className="shrink-0" />
              {!sidebarCollapsed && <span>{label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Botão colapsar */}
      <button
        type="button"
        onClick={toggleSidebar}
        aria-label={sidebarCollapsed ? "Expandir menu" : "Recolher menu"}
        className="m-2 flex items-center justify-center rounded-md border border-(--border-default) py-1.5 text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-secondary)"
      >
        {sidebarCollapsed ? (
          <ChevronRight size={14} aria-hidden="true" />
        ) : (
          <ChevronLeft size={14} aria-hidden="true" />
        )}
      </button>
    </aside>
  )
}
