"use client"

import { useEffect, useState } from "react"
import type { Route } from "next"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import {
  LayoutDashboard,
  Users,
  GitBranch,
  Settings,
  Building2,
  ChevronLeft,
  ChevronRight,
  List,
  ClipboardList,
  MessageSquare,
  Bell,
  LogOut,
  Search,
  Sparkles,
  Mail,
  FileText,
  type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useUIStore } from "@/store/ui-store"
import { useNotificationsStore } from "@/store/notifications-store"
import { ThemeToggle } from "@/components/layout/theme-toggle"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

// ── Navegação ─────────────────────────────────────────────────────────

const navItems: Array<{ href: Route; label: string; icon: LucideIcon }> = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/equipe" as Route, label: "Equipe", icon: Users },
  { href: "/leads/busca-linkedin", label: "Busca LinkedIn", icon: Search },
  { href: "/gerar-leads", label: "Gerar Leads", icon: Sparkles },
  { href: "/listas", label: "Listas", icon: List },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/inbox", label: "Inbox", icon: MessageSquare },
  { href: "/cadencias", label: "Cadências", icon: GitBranch },
  { href: "/cold-email", label: "Cold Email", icon: Mail },
  { href: "/tarefas", label: "Tarefas", icon: ClipboardList },
  { href: "/content", label: "Conteúdo", icon: FileText },
]

const settingsItems: Array<{ href: Route; label: string; icon: LucideIcon }> = [
  { href: "/configuracoes", label: "Configurações", icon: Settings },
]
const adminItems: Array<{ href: string; label: string; icon: LucideIcon }> = [
  { href: "/clientes", label: "Tenants", icon: Building2 },
]

interface SidebarProps {
  initialSidebarCollapsed?: boolean
}

interface SidebarItemBaseProps {
  active: boolean
  collapsed: boolean
  href: string
  icon: LucideIcon
  label: string
}

interface SidebarLinkItemProps extends SidebarItemBaseProps {
  kind: "link"
  href: Route
}

interface SidebarAnchorItemProps extends SidebarItemBaseProps {
  kind: "anchor"
}

type SidebarNavItemProps = SidebarLinkItemProps | SidebarAnchorItemProps

function SidebarItemInner({
  active,
  collapsed,
  icon: Icon,
  label,
}: Omit<SidebarItemBaseProps, "href">) {
  return (
    <>
      <span
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border transition-all duration-200",
          active
            ? "border-(--accent)/20 bg-(--accent)/10 text-(--accent) shadow-[0_10px_25px_-18px_var(--accent)]"
            : "border-transparent text-current",
          collapsed &&
            !active &&
            "group-hover/item:border-(--border-default) group-hover/item:bg-(--bg-overlay)",
        )}
      >
        <Icon size={16} aria-hidden="true" className="shrink-0" />
      </span>
      {!collapsed && <span className="truncate">{label}</span>}
    </>
  )
}

function SidebarNavItem({ active, collapsed, href, icon, kind, label }: SidebarNavItemProps) {
  const TooltipIcon = icon
  const className = cn(
    "group/item flex items-center gap-2 rounded-2xl px-2 py-1.5 text-sm transition-all duration-200",
    active
      ? "bg-[linear-gradient(135deg,var(--accent-subtle),color-mix(in_srgb,var(--accent-subtle)_74%,transparent))] text-(--accent-subtle-fg) shadow-[0_18px_40px_-28px_var(--accent)]"
      : "text-(--text-secondary) hover:bg-(--bg-overlay) hover:text-(--text-primary)",
    collapsed ? "justify-center px-1.5" : "pr-3",
  )

  const content =
    kind === "link" ? (
      <Link
        href={href}
        className={className}
        aria-current={active ? "page" : undefined}
        aria-label={collapsed ? label : undefined}
      >
        <SidebarItemInner active={active} collapsed={collapsed} icon={icon} label={label} />
      </Link>
    ) : (
      <a
        href={href}
        className={className}
        aria-current={active ? "page" : undefined}
        aria-label={collapsed ? label : undefined}
      >
        <SidebarItemInner active={active} collapsed={collapsed} icon={icon} label={label} />
      </a>
    )

  if (!collapsed) {
    return content
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{content}</TooltipTrigger>
      <TooltipContent
        side="right"
        sideOffset={14}
        className="bg-[linear-gradient(135deg,color-mix(in_srgb,var(--bg-surface)_96%,white_4%),color-mix(in_srgb,var(--bg-surface)_88%,var(--accent-subtle)_12%))] text-(--text-primary)"
      >
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-(--accent)/10 text-(--accent)">
            <TooltipIcon size={14} aria-hidden="true" />
          </span>
          <span>{label}</span>
        </div>
      </TooltipContent>
    </Tooltip>
  )
}

// ── Sidebar ───────────────────────────────────────────────────────────

export function Sidebar({ initialSidebarCollapsed = false }: SidebarProps) {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { data: session } = useSession()
  const unreadCount = useNotificationsStore((s) => s.unreadCount)
  const user = session?.user
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    // persist pode não estar disponível durante SSR
    const api = useUIStore.persist
    if (!api) return

    if (api.hasHydrated()) {
      setHydrated(true)
      return
    }

    const unsubscribe = api.onFinishHydration(() => {
      setHydrated(true)
    })

    return unsubscribe
  }, [])

  const collapsed = hydrated ? sidebarCollapsed : initialSidebarCollapsed

  async function handleSignOut() {
    await signOut({ redirectTo: "/login" })
  }

  return (
    <TooltipProvider delayDuration={110} skipDelayDuration={0} disableHoverableContent>
      <aside
        className={cn(
          "group relative flex h-full flex-col border-r border-(--border-default) bg-(--bg-surface)",
          hydrated && "transition-[width] duration-200",
          collapsed ? "w-16" : "w-56",
        )}
      >
        {/* Logo */}
        <div
          className={cn(
            "flex h-14 items-center border-b border-(--border-default) px-3",
            collapsed ? "justify-center" : "gap-2",
          )}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[linear-gradient(135deg,var(--accent),color-mix(in_srgb,var(--accent)_72%,black_28%))] shadow-[0_16px_30px_-20px_var(--accent)]">
            <span className="text-[10px] font-bold text-white">P</span>
          </div>
          {!collapsed && (
            <span className="text-sm font-semibold text-(--text-primary)">Prospector</span>
          )}
        </div>

        {/* Navegação principal */}
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
          {(() => {
            const activeHref = [...navItems]
              .sort((a, b) => b.href.length - a.href.length)
              .find(({ href }) => pathname === href || pathname.startsWith(href + "/"))?.href

            return navItems.map(({ href, label, icon }) => {
              const active = href === activeHref
              return (
                <SidebarNavItem
                  key={href}
                  kind="link"
                  href={href}
                  label={label}
                  icon={icon}
                  active={active}
                  collapsed={collapsed}
                />
              )
            })
          })()}

          <div className="my-2 border-t border-(--border-subtle)" />

          {!collapsed && (
            <p className="mb-1 px-2.5 text-[11px] font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
              Configurações
            </p>
          )}
          {settingsItems.map(({ href, label, icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/")
            return (
              <SidebarNavItem
                key={href}
                kind="link"
                href={href}
                label={label}
                icon={icon}
                active={active}
                collapsed={collapsed}
              />
            )
          })}

          {user?.is_superuser ? (
            <>
              <div className="my-2 border-t border-(--border-subtle)" />
              {!collapsed && (
                <p className="mb-1 px-2.5 text-[11px] font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                  Administração
                </p>
              )}
              {adminItems.map(({ href, label, icon }) => {
                const active = pathname === href || pathname.startsWith(href + "/")
                return (
                  <SidebarNavItem
                    key={href}
                    kind="anchor"
                    href={href}
                    label={label}
                    icon={icon}
                    active={active}
                    collapsed={collapsed}
                  />
                )
              })}
            </>
          ) : null}
        </nav>

        {/* Rodapé — controles de usuário */}
        <div className="flex flex-col gap-0.5 border-t border-(--border-default) p-2">
          {collapsed ? (
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
                    <DropdownMenuItem
                      destructive
                      className="cursor-pointer"
                      onClick={handleSignOut}
                    >
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
            </>
          )}
        </div>

        {/* Botão colapsar */}
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
          className="m-2 flex items-center justify-center rounded-xl border border-(--border-default) py-1.5 text-(--text-tertiary) transition-all duration-200 hover:bg-(--bg-overlay) hover:text-(--text-secondary)"
        >
          {collapsed ? (
            <ChevronRight size={14} aria-hidden="true" />
          ) : (
            <ChevronLeft size={14} aria-hidden="true" />
          )}
        </button>
      </aside>
    </TooltipProvider>
  )
}
