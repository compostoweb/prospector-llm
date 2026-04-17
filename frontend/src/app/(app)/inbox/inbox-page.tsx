"use client"

import { useCallback, useMemo, useRef, useState } from "react"
import {
  type InboxFilter,
  useConversations,
  useSyncInbox,
  useMarkChatAsRead,
} from "@/lib/api/hooks/use-inbox"
import { ConversationList } from "@/components/inbox/conversation-list"
import { ChatPanel } from "@/components/inbox/chat-panel"
import { ContactSidebar } from "@/components/inbox/contact-sidebar"
import { EmptyState } from "@/components/shared/empty-state"
import { MessageSquare, AlertTriangle } from "lucide-react"

export default function InboxPage() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)
  const [showContact, setShowContact] = useState(true)
  const [filter, setFilter] = useState<InboxFilter>("all")
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(value)
    }, 350)
  }, [])

  const { data, isLoading, isError } = useConversations({ filter, search: debouncedSearch })
  const syncMutation = useSyncInbox()
  const markAsRead = useMarkChatAsRead()

  const conversations = useMemo(() => data?.items ?? [], [data?.items])

  const handleSelectChat = useCallback(
    (chatId: string) => {
      setSelectedChatId(chatId)
      const conv = conversations.find((c) => c.chat_id === chatId)
      if (conv && conv.unread_count > 0) {
        markAsRead.mutate({ chatId })
      }
    },
    [conversations, markAsRead],
  )

  return (
    <div className="-m-6 flex h-screen overflow-hidden">
      {/* Col 1: Lista de conversas */}
      <ConversationList
        conversations={conversations}
        isLoading={isLoading}
        selectedChatId={selectedChatId}
        onSelect={handleSelectChat}
        filter={filter}
        onFilterChange={setFilter}
        search={search}
        onSearchChange={handleSearchChange}
        onSync={() => syncMutation.mutate()}
        isSyncing={syncMutation.isPending}
      />

      {/* Col 2: Chat */}
      {isError ? (
        <div className="flex flex-1 items-center justify-center border-r border-(--border-default) bg-(--bg-page)">
          <EmptyState
            icon={AlertTriangle}
            title="Inbox indisponível"
            description="Não foi possível carregar as conversas. Verifique se a API do backend está acessível."
          />
        </div>
      ) : selectedChatId ? (
        <ChatPanel
          chatId={selectedChatId}
          onToggleContact={() => setShowContact((v) => !v)}
          showContact={showContact}
        />
      ) : (
        <div className="flex flex-1 items-center justify-center border-r border-(--border-default) bg-(--bg-page)">
          <EmptyState
            icon={MessageSquare}
            title="Selecione uma conversa"
            description="Escolha uma conversa na lista à esquerda para ver as mensagens."
          />
        </div>
      )}

      {/* Col 3: Contact sidebar */}
      {selectedChatId && showContact && <ContactSidebar chatId={selectedChatId} />}
    </div>
  )
}
