"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import {
  LayoutDashboard,
  Users,
  GitBranch,
  Settings,
  ChevronLeft,
  ChevronRight,
  List,
  ClipboardList,
  MessageSquare,
  Bell,
  LogOut,
  Search,
  Mail,
  FileText,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useUIStore } from "@/store/ui-store"
import { useNotificationsStore } from "@/store/notifications-store"
import { ThemeToggle } from "@/components/layout/theme-toggle"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

// ── Navegação ─────────────────────────────────────────────────────────

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/leads/busca-linkedin", label: "Busca LinkedIn", icon: Search },
  { href: "/listas", label: "Listas", icon: List },
  { href: "/cadencias", label: "Cadências", icon: GitBranch },
  { href: "/cold-email", label: "Cold Email", icon: Mail },
  { href: "/content", label: "Conteúdo", icon: FileText },
  { href: "/tarefas", label: "Tarefas", icon: ClipboardList },
  { href: "/inbox", label: "Inbox", icon: MessageSquare },
] as const

const settingsItems = [{ href: "/configuracoes", label: "Configurações", icon: Settings }] as const

// ── Sidebar ───────────────────────────────────────────────────────────

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { data: session } = useSession()
  const unreadCount = useNotificationsStore((s) => s.unreadCount)
  const user = session?.user

  async function handleSignOut() {
    await signOut({ redirectTo: "/login" })
  }

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
        {(() => {
          // Usa o href mais específico (mais longo) que corresponde ao pathname atual
          const activeHref = [...navItems]
            .sort((a, b) => b.href.length - a.href.length)
            .find(({ href }) => pathname === href || pathname.startsWith(href + "/"))?.href

          return navItems.map(({ href, label, icon: Icon }) => {
            const active = href === activeHref
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
          })
        })()}

        {/* Separador */}
        <div className="my-2 border-t border-(--border-subtle)" />

        {/* Configurações */}
        {!sidebarCollapsed && (
          <p className="mb-1 px-2.5 text-[11px] font-medium uppercase tracking-wider text-(--text-tertiary)">
            Configurações
          </p>
        )}
        {settingsItems.map(({ href, label, icon: Icon }) => {
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
      </nav>

      {/* Rodapé — controles de usuário */}
      <div className="border-t border-(--border-default) p-2 flex flex-col gap-0.5">
        {sidebarCollapsed ? (
          /* ── Modo colapsado: ícones centralizados ── */
          <>
            <div className="flex justify-center">
              <ThemeToggle collapsed />
            </div>

            {/* Bell */}
            <div className="flex justify-center">
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Notificações${unreadCount > 0 ? ` — ${unreadCount} não lidas` : ""}`}
                className="relative h-8 w-8"
              >
                <Bell size={16} aria-hidden="true" />
                {unreadCount > 0 && (
                  <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-(--danger) text-[9px] font-bold text-white">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Button>
            </div>

            {/* User avatar */}
            <div className="flex justify-center">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    aria-label="Menu do usuário"
                  >
                    <Avatar className="size-6">
                      <AvatarImage src={user?.image ?? undefined} alt={user?.name ?? "Usuário"} />
                      <AvatarFallback className="text-[10px]">
                        {user?.name?.charAt(0).toUpperCase() ?? "U"}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent side="right" align="end" className="w-48">
                  <DropdownMenuLabel className="font-normal">
                    <p className="truncate text-xs font-medium text-(--text-primary)">
                      {user?.name}
                    </p>
                    <p className="truncate text-xs text-(--text-tertiary)">{user?.email}</p>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem destructive className="cursor-pointer" onClick={handleSignOut}>
                    <LogOut size={14} aria-hidden="true" />
                    Sair
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </>
        ) : (
          /* ── Modo expandido: controles com labels ── */
          <>
            <div className="flex justify-center py-0.5">
              <ThemeToggle />
            </div>

            {/* Bell */}
            <Button
              variant="ghost"
              aria-label={`Notificações${unreadCount > 0 ? ` — ${unreadCount} não lidas` : ""}`}
              className="relative flex h-8 w-full items-center justify-start gap-2.5 rounded-md px-2.5 text-sm text-(--text-secondary) hover:bg-(--bg-overlay) hover:text-(--text-primary)"
            >
              <Bell size={16} aria-hidden="true" className="shrink-0" />
              <span>Notificações</span>
              {unreadCount > 0 && (
                <span className="ml-auto flex h-4 min-w-4 items-center justify-center rounded-full bg-(--danger) px-1 text-[9px] font-bold text-white">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Button>

            {/* User dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex h-8 w-full items-center justify-start gap-2.5 rounded-md px-2.5 text-sm text-(--text-secondary) hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                  aria-label="Menu do usuário"
                >
                  <Avatar className="size-5 shrink-0">
                    <AvatarImage src={user?.image ?? undefined} alt={user?.name ?? "Usuário"} />
                    <AvatarFallback className="text-[10px]">
                      {user?.name?.charAt(0).toUpperCase() ?? "U"}
                    </AvatarFallback>
                  </Avatar>
                  <span className="truncate">{user?.name ?? user?.email}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="right" align="end" className="w-48">
                <DropdownMenuLabel className="font-normal">
                  <p className="truncate text-xs font-medium text-(--text-primary)">{user?.name}</p>
                  <p className="truncate text-xs text-(--text-tertiary)">{user?.email}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem destructive className="cursor-pointer" onClick={handleSignOut}>
                  <LogOut size={14} aria-hidden="true" />
                  Sair
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
      </div>

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
