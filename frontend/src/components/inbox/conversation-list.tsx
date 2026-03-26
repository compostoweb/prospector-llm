"use client"

import { cn } from "@/lib/utils"
import type { Conversation, InboxFilter } from "@/lib/api/hooks/use-inbox"
import { MessageSquare, User, Search, X, RefreshCw } from "lucide-react"
import Image from "next/image"
import { useRef } from "react"

interface ConversationListProps {
  conversations: Conversation[]
  isLoading: boolean
  selectedChatId: string | null
  onSelect: (chatId: string) => void
  filter: InboxFilter
  onFilterChange: (filter: InboxFilter) => void
  search: string
  onSearchChange: (search: string) => void
  onSync?: () => void
  isSyncing?: boolean
}

const FILTERS: { value: InboxFilter; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "unread", label: "Não lidas" },
]

export function ConversationList({
  conversations,
  isLoading,
  selectedChatId,
  onSelect,
  filter,
  onFilterChange,
  search,
  onSearchChange,
  onSync,
  isSyncing,
}: ConversationListProps) {
  const searchRef = useRef<HTMLInputElement>(null)

  return (
    <div className="flex h-full w-80 shrink-0 flex-col border-r border-(--border-default) bg-(--bg-surface)">
      {/* Header */}
      <div className="flex h-12 items-center justify-between border-b border-(--border-default) px-4">
        <div className="flex items-center">
          <MessageSquare size={16} className="mr-2 text-(--text-tertiary)" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-(--text-primary)">Inbox LinkedIn</h2>
        </div>
        {onSync && (
          <button
            type="button"
            onClick={onSync}
            disabled={isSyncing}
            title="Sincronizar conversas"
            className="rounded-md p-1.5 text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary) disabled:opacity-50"
          >
            <RefreshCw size={14} className={isSyncing ? "animate-spin" : ""} />
          </button>
        )}
      </div>

      {/* Search */}
      <div className="border-b border-(--border-default) px-3 py-2">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            aria-hidden="true"
          />
          <input
            ref={searchRef}
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Pesquisar mensagens"
            className="h-8 w-full rounded-md border border-(--border-default) bg-(--bg-page) pl-8 pr-8 text-xs text-(--text-primary) placeholder:text-(--text-tertiary) focus:border-(--accent) focus:outline-none"
          />
          {search && (
            <button
              type="button"
              onClick={() => {
                onSearchChange("")
                searchRef.current?.focus()
              }}
              aria-label="Limpar busca"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-(--text-tertiary) hover:text-(--text-primary)"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-(--border-default) px-3 py-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => onFilterChange(f.value)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              filter === f.value
                ? "bg-(--accent) text-white"
                : "bg-(--bg-overlay) text-(--text-secondary) hover:bg-(--bg-page) hover:text-(--text-primary)",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-0.5 p-1.5">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="flex items-start gap-2.5 px-3 py-3">
                <div className="h-10 w-10 shrink-0 animate-pulse rounded-full bg-(--bg-overlay)" />
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="h-3 w-24 animate-pulse rounded bg-(--bg-overlay)" />
                  <div className="h-2.5 w-40 animate-pulse rounded bg-(--bg-overlay)" />
                </div>
              </div>
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex h-full items-center justify-center p-4">
            <p className="text-center text-xs text-(--text-tertiary)">
              {search
                ? `Nenhum resultado para "${search}"`
                : filter === "unread"
                  ? "Nenhuma conversa não lida."
                  : "Nenhuma conversa encontrada."}
            </p>
          </div>
        ) : (
          <div className="space-y-0">
            {conversations.map((conv) => {
              const otherAttendee = conv.attendees[0]
              const attendeeName = otherAttendee?.name || null
              const displayName = conv.lead_name || attendeeName || "Membro LinkedIn"
              const avatarUrl = otherAttendee?.profile_picture_url
              const isSelected = conv.chat_id === selectedChatId
              const isUnread = conv.unread_count > 0
              const dateLabel = conv.last_message_at
                ? formatConvDate(conv.last_message_at)
                : null

              // Format preview like LinkedIn: "Name: message preview..."
              const preview = conv.last_message_text
                ? truncatePreview(conv.last_message_text, 80)
                : null

              return (
                <button
                  key={conv.chat_id}
                  type="button"
                  onClick={() => onSelect(conv.chat_id)}
                  className={cn(
                    "flex w-full items-start gap-2.5 border-b border-(--border-default) px-3 py-3 text-left transition-colors",
                    isSelected
                      ? "bg-(--accent-subtle)"
                      : isUnread
                        ? "bg-(--bg-surface) hover:bg-(--bg-overlay)"
                        : "hover:bg-(--bg-overlay)",
                  )}
                >
                  {/* Avatar */}
                  {avatarUrl ? (
                    <Image
                      src={avatarUrl}
                      alt={displayName}
                      width={40}
                      height={40}
                      unoptimized
                      className="h-10 w-10 shrink-0 rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-(--bg-overlay)">
                      <User size={16} className="text-(--text-tertiary)" aria-hidden="true" />
                    </div>
                  )}

                  <div className="min-w-0 flex-1">
                    {/* Row 1: Name + Date */}
                    <div className="flex items-center justify-between gap-1">
                      <p
                        className={cn(
                          "truncate text-sm",
                          isUnread ? "font-semibold text-(--text-primary)" : "font-medium text-(--text-primary)",
                        )}
                      >
                        {displayName}
                      </p>
                      {dateLabel && (
                        <span
                          className={cn(
                            "shrink-0 text-[11px]",
                            isUnread ? "font-semibold text-(--text-primary)" : "text-(--text-tertiary)",
                          )}
                        >
                          {dateLabel}
                        </span>
                      )}
                    </div>

                    {/* Row 2: Message preview + unread badge */}
                    <div className="mt-0.5 flex items-center gap-1.5">
                      {preview ? (
                        <p
                          className={cn(
                            "min-w-0 flex-1 truncate text-xs",
                            isUnread
                              ? "font-medium text-(--text-secondary)"
                              : "text-(--text-tertiary)",
                          )}
                        >
                          {preview}
                        </p>
                      ) : (
                        <span className="flex-1" />
                      )}
                      {isUnread && (
                        <span className="flex h-4.5 min-w-4.5 shrink-0 items-center justify-center rounded-full bg-(--accent) px-1 text-[10px] font-bold text-white">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function formatConvDate(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const diffDays = Math.round((today.getTime() - msgDay.getTime()) / 86400000)

    if (diffDays === 0) {
      return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    }
    if (diffDays === 1) return "Ontem"
    if (diffDays < 7) {
      return date.toLocaleDateString("pt-BR", { weekday: "short" })
    }
    return date.toLocaleDateString("pt-BR", { day: "numeric", month: "short" })
  } catch {
    return ""
  }
}

function truncatePreview(text: string, maxLen: number): string {
  // Remove line breaks for preview
  const clean = text.replace(/\n+/g, " ").trim()
  if (clean.length <= maxLen) return clean
  return clean.slice(0, maxLen).trimEnd() + "…"
}
