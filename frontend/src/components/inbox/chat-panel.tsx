"use client"

import { useState, useRef, useEffect } from "react"
import {
  useChatMessages,
  useSendMessage,
  useSuggestReply,
  type SuggestTone,
} from "@/lib/api/hooks/use-inbox"
import { ChatInput } from "@/components/inbox/chat-input"
import { cn } from "@/lib/utils"
import { User, PanelRightOpen, PanelRightClose, Loader2 } from "lucide-react"

interface ChatPanelProps {
  chatId: string
  onToggleContact: () => void
  showContact: boolean
}

export function ChatPanel({ chatId, onToggleContact, showContact }: ChatPanelProps) {
  const { data, isLoading } = useChatMessages(chatId)
  const sendMessage = useSendMessage()
  const suggestReply = useSuggestReply()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [inputText, setInputText] = useState("")

  const messages = data?.items ?? []

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])

  async function handleSend() {
    const text = inputText.trim()
    if (!text) return
    setInputText("")
    await sendMessage.mutateAsync({ chatId, text })
  }

  async function handleSuggest(tone: SuggestTone) {
    const result = await suggestReply.mutateAsync({ chatId, tone })
    setInputText(result.suggested_text)
  }

  return (
    <div className="flex flex-1 flex-col bg-(--bg-page)">
      {/* Header */}
      <div className="flex h-12 items-center justify-between border-b border-(--border-default) bg-(--bg-surface) px-4">
        <h3 className="text-sm font-semibold text-(--text-primary)">Conversa</h3>
        <button
          type="button"
          onClick={onToggleContact}
          aria-label={showContact ? "Ocultar painel de contato" : "Mostrar painel de contato"}
          className="rounded-md p-1.5 text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
        >
          {showContact ? (
            <PanelRightClose size={16} aria-hidden="true" />
          ) : (
            <PanelRightOpen size={16} aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 size={24} className="animate-spin text-(--text-tertiary)" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-(--text-tertiary)">Nenhuma mensagem encontrada.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn("flex gap-2", msg.is_own ? "flex-row-reverse" : "flex-row")}
              >
                {/* Avatar */}
                {!msg.is_own && (
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-(--bg-overlay)">
                    <User size={12} className="text-(--text-tertiary)" aria-hidden="true" />
                  </div>
                )}

                {/* Bubble */}
                <div
                  className={cn(
                    "max-w-[70%] rounded-lg px-3 py-2 text-sm",
                    msg.is_own
                      ? "bg-(--accent) text-white"
                      : "bg-(--bg-surface) text-(--text-primary) border border-(--border-default)",
                  )}
                >
                  {!msg.is_own && (
                    <p className="mb-0.5 text-[10px] font-medium text-(--text-secondary)">
                      {msg.sender_name}
                    </p>
                  )}
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                  <p
                    className={cn(
                      "mt-1 text-right text-[10px]",
                      msg.is_own ? "text-white/70" : "text-(--text-tertiary)",
                    )}
                  >
                    {formatTime(msg.timestamp)}
                  </p>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <ChatInput
        value={inputText}
        onChange={setInputText}
        onSend={handleSend}
        onSuggest={handleSuggest}
        isSending={sendMessage.isPending}
        isSuggesting={suggestReply.isPending}
        chatId={chatId}
      />
    </div>
  )
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
  } catch {
    return ""
  }
}
