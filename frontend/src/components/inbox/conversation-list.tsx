"use client"

import { cn } from "@/lib/utils"
import type { Conversation } from "@/lib/api/hooks/use-inbox"
import { MessageSquare, User } from "lucide-react"
import Image from "next/image"

interface ConversationListProps {
  conversations: Conversation[]
  isLoading: boolean
  selectedChatId: string | null
  onSelect: (chatId: string) => void
}

export function ConversationList({
  conversations,
  isLoading,
  selectedChatId,
  onSelect,
}: ConversationListProps) {
  return (
    <div className="flex h-full w-75 shrink-0 flex-col border-r border-(--border-default) bg-(--bg-surface)">
      {/* Header */}
      <div className="flex h-12 items-center border-b border-(--border-default) px-4">
        <MessageSquare size={16} className="mr-2 text-(--text-tertiary)" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-(--text-primary)">Inbox LinkedIn</h2>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-1 p-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded-md bg-(--bg-overlay)" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex h-full items-center justify-center p-4">
            <p className="text-center text-xs text-(--text-tertiary)">
              Nenhuma conversa encontrada.
            </p>
          </div>
        ) : (
          <div className="space-y-0.5 p-1">
            {conversations.map((conv) => {
              const otherAttendee = conv.attendees[0]
              const attendeeName = otherAttendee?.name || null
              const displayName = conv.lead_name || attendeeName || "Desconhecido"
              const displayCompany = conv.lead_company
              const avatarUrl = otherAttendee?.profile_picture_url
              const isSelected = conv.chat_id === selectedChatId

              return (
                <button
                  key={conv.chat_id}
                  type="button"
                  onClick={() => onSelect(conv.chat_id)}
                  className={cn(
                    "flex w-full items-start gap-2.5 rounded-md px-3 py-2.5 text-left transition-colors",
                    isSelected
                      ? "bg-(--accent-subtle) text-(--accent-subtle-fg)"
                      : "text-(--text-primary) hover:bg-(--bg-overlay)",
                  )}
                >
                  {/* Avatar */}
                  {avatarUrl ? (
                    <Image
                      src={avatarUrl}
                      alt={displayName}
                      width={36}
                      height={36}
                      unoptimized
                      className="h-9 w-9 shrink-0 rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-(--bg-overlay)">
                      <User size={14} className="text-(--text-tertiary)" aria-hidden="true" />
                    </div>
                  )}

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1">
                      <p className="truncate text-sm font-medium">{displayName}</p>
                      {conv.unread_count > 0 && (
                        <span className="flex h-4 min-w-4 shrink-0 items-center justify-center rounded-full bg-(--accent) px-1 text-[10px] font-bold text-white">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                    {displayCompany && (
                      <p className="truncate text-[11px] text-(--text-secondary)">
                        {displayCompany}
                      </p>
                    )}
                    {conv.last_message_text && (
                      <p className="mt-0.5 truncate text-xs text-(--text-tertiary)">
                        {conv.last_message_text}
                      </p>
                    )}
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
