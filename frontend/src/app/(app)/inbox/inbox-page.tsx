"use client"

import { useState } from "react"
import { useConversations } from "@/lib/api/hooks/use-inbox"
import { ConversationList } from "@/components/inbox/conversation-list"
import { ChatPanel } from "@/components/inbox/chat-panel"
import { ContactSidebar } from "@/components/inbox/contact-sidebar"
import { EmptyState } from "@/components/shared/empty-state"
import { MessageSquare } from "lucide-react"

export default function InboxPage() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)
  const [showContact, setShowContact] = useState(true)
  const { data, isLoading } = useConversations()

  const conversations = data?.items ?? []

  return (
    <div className="-m-6 flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Col 1: Lista de conversas */}
      <ConversationList
        conversations={conversations}
        isLoading={isLoading}
        selectedChatId={selectedChatId}
        onSelect={setSelectedChatId}
      />

      {/* Col 2: Chat */}
      {selectedChatId ? (
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
      {selectedChatId && showContact && (
        <ContactSidebar chatId={selectedChatId} />
      )}
    </div>
  )
}
