"use client"

import { useSession, signOut } from "next-auth/react"
import { Bell, LogOut } from "lucide-react"
import { ThemeToggle } from "@/components/layout/theme-toggle"
import { useNotificationsStore } from "@/store/notifications-store"
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

interface TopbarProps {
  title?: string
}

export function Topbar({ title }: TopbarProps) {
  const { data: session } = useSession()
  const unreadCount = useNotificationsStore((s) => s.unreadCount)
  const user = session?.user

  async function handleSignOut() {
    await signOut({ redirectTo: "/login" })
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-(--border-default) bg-(--bg-surface) px-4">
      <div>{title && <h1 className="text-sm font-semibold text-(--text-primary)">{title}</h1>}</div>

      <div className="flex items-center gap-1">
        <ThemeToggle />

        {/* Notificações */}
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Notificações${unreadCount > 0 ? ` — ${unreadCount} não lidas` : ""}`}
          className="relative"
        >
          <Bell size={16} aria-hidden="true" />
          {unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-(--danger) text-[9px] font-bold text-white">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>

        {/* Menu do usuário */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="flex h-8 items-center gap-2 px-2"
              aria-label="Menu do usuário"
            >
              <Avatar className="size-6">
                <AvatarImage src={user?.image ?? undefined} alt={user?.name ?? "Usuário"} />
                <AvatarFallback className="text-[10px]">
                  {user?.name?.charAt(0).toUpperCase() ?? "U"}
                </AvatarFallback>
              </Avatar>
              <span className="hidden max-w-28 truncate text-sm text-(--text-primary) sm:block">
                {user?.name ?? user?.email}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
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
      </div>
    </header>
  )
}
