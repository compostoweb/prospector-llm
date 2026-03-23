"use client"

import { useSession, signOut } from "next-auth/react"
import { Bell, LogOut, ChevronDown } from "lucide-react"
import { ThemeToggle } from "@/components/layout/theme-toggle"
import { useNotificationsStore } from "@/store/notifications-store"
import { cn } from "@/lib/utils"
import { useState } from "react"

interface TopbarProps {
  title?: string
}

export function Topbar({ title }: TopbarProps) {
  const { data: session } = useSession()
  const unreadCount = useNotificationsStore((s) => s.unreadCount)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const user = session?.user

  async function handleSignOut() {
    await signOut({ redirectTo: "/login" })
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border-default)] bg-[var(--bg-surface)] px-4">
      {/* Título da página */}
      <div>
        {title && <h1 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h1>}
      </div>

      {/* Ações à direita */}
      <div className="flex items-center gap-2">
        <ThemeToggle />

        {/* Notificações */}
        <button
          type="button"
          aria-label={`Notificações${unreadCount > 0 ? ` — ${unreadCount} não lidas` : ""}`}
          className="relative flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-overlay)] hover:text-[var(--text-primary)]"
        >
          <Bell size={16} aria-hidden="true" />
          {unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-[var(--danger)] text-[9px] font-bold text-white">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>

        {/* Menu do usuário */}
        <div className="relative">
          <button
            type="button"
            aria-label="Menu do usuário"
            aria-expanded={userMenuOpen}
            onClick={() => setUserMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-[var(--radius-md)] px-2 py-1 text-sm transition-colors hover:bg-[var(--bg-overlay)]"
          >
            {user?.image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.image}
                alt={user.name ?? "Usuário"}
                width={24}
                height={24}
                className="h-6 w-6 rounded-full object-cover"
              />
            ) : (
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--accent)] text-[10px] font-bold text-white">
                {user?.name?.charAt(0).toUpperCase() ?? "U"}
              </div>
            )}
            <span className="hidden max-w-[120px] truncate text-[var(--text-primary)] sm:block">
              {user?.name ?? user?.email}
            </span>
            <ChevronDown
              size={12}
              aria-hidden="true"
              className={cn(
                "text-[var(--text-tertiary)] transition-transform",
                userMenuOpen && "rotate-180",
              )}
            />
          </button>

          {/* Dropdown */}
          {userMenuOpen && (
            <>
              {/* Overlay para fechar */}
              <div
                className="fixed inset-0 z-10"
                aria-hidden="true"
                onClick={() => setUserMenuOpen(false)}
              />
              <div className="absolute right-0 top-full z-20 mt-1 w-48 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] py-1 shadow-[var(--shadow-md)]">
                <div className="border-b border-[var(--border-subtle)] px-3 py-2">
                  <p className="truncate text-xs font-medium text-[var(--text-primary)]">
                    {user?.name}
                  </p>
                  <p className="truncate text-xs text-[var(--text-tertiary)]">{user?.email}</p>
                </div>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-overlay)] hover:text-[var(--danger)]"
                >
                  <LogOut size={14} aria-hidden="true" />
                  Sair
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
