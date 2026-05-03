"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import {
  useChatMessages,
  useConversations,
  useSendMessage,
  useSuggestReply,
  useAddReaction,
  useRemoveReaction,
  type SuggestTone,
  type ChatMessage,
} from "@/lib/api/hooks/use-inbox"
import { ChatInput } from "@/components/inbox/chat-input"
import { cn } from "@/lib/utils"
import {
  User,
  PanelRightOpen,
  PanelRightClose,
  Loader2,
  FileText,
  Download,
  Play,
  SmilePlus,
  AlertTriangle,
} from "lucide-react"
import { EmptyState } from "@/components/shared/empty-state"
import { InboxAvatar } from "@/components/inbox/inbox-avatar"

interface ChatPanelProps {
  chatId: string
  onToggleContact: () => void
  showContact: boolean
}

export function ChatPanel({ chatId, onToggleContact, showContact }: ChatPanelProps) {
  const { data, isLoading, isError } = useChatMessages(chatId)
  const { data: convData } = useConversations()
  const sendMessage = useSendMessage()
  const suggestReply = useSuggestReply()
  const addReaction = useAddReaction()
  const removeReaction = useRemoveReaction()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [inputText, setInputText] = useState("")
  const [reactionMsgId, setReactionMsgId] = useState<string | null>(null)

  const messages = [...(data?.items ?? [])].sort(
    (left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime(),
  )

  // Get attendee info for avatar
  const conversation = convData?.items?.find((c) => c.chat_id === chatId)
  const otherAttendee = conversation?.attendees[0]
  const attendeeName = conversation?.lead_name || otherAttendee?.name || "Contato"
  const attendeeAvatar = otherAttendee?.profile_picture_url

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

  const handleReaction = useCallback(
    (messageId: string, emoji: string) => {
      setReactionMsgId(null)
      addReaction.mutate({ chatId, messageId, emoji })
    },
    [chatId, addReaction],
  )

  const handleRemoveReaction = useCallback(
    (messageId: string, emoji: string) => {
      removeReaction.mutate({ chatId, messageId, emoji })
    },
    [chatId, removeReaction],
  )

  return (
    <div className="flex flex-1 flex-col bg-(--bg-page)">
      {/* Header */}
      <div className="flex h-12 items-center justify-between border-b border-(--border-default) bg-(--bg-surface) px-4">
        <div className="flex items-center gap-2">
          <InboxAvatar
            src={attendeeAvatar}
            alt={attendeeName}
            fallbackLabel={attendeeName}
            className="h-6 w-6"
          />
          <h3 className="text-sm font-semibold text-(--text-primary)">{attendeeName}</h3>
        </div>
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
      <div
        className="flex-1 overflow-y-auto p-4"
        onClick={() => reactionMsgId && setReactionMsgId(null)}
      >
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 size={24} className="animate-spin text-(--text-tertiary)" />
          </div>
        ) : isError ? (
          <div className="flex h-full items-center justify-center">
            <EmptyState
              icon={AlertTriangle}
              title="Mensagens indisponíveis"
              description="Não foi possível carregar esta conversa. Verifique se a API do backend está acessível."
              className="max-w-md"
            />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2">
            <User size={32} className="text-(--text-tertiary)" />
            <p className="text-sm text-(--text-tertiary)">Nenhuma mensagem nesta conversa ainda.</p>
            <p className="text-xs text-(--text-tertiary)">Envie a primeira mensagem abaixo!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg, idx) => {
              const showDateSep = shouldShowDateSeparator(messages, idx)
              return (
                <div key={msg.id}>
                  {showDateSep && (
                    <div className="my-4 flex items-center gap-3">
                      <div className="h-px flex-1 bg-(--border-default)" />
                      <span className="text-[11px] font-medium text-(--text-tertiary)">
                        {formatDateSeparator(msg.timestamp)}
                      </span>
                      <div className="h-px flex-1 bg-(--border-default)" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "group/msg flex gap-2",
                      msg.is_own ? "flex-row-reverse" : "flex-row",
                    )}
                  >
                    {/* Avatar */}
                    {!msg.is_own && (
                      <InboxAvatar
                        src={attendeeAvatar}
                        alt={msg.sender_name}
                        fallbackLabel={msg.sender_name}
                        className="h-7 w-7"
                      />
                    )}

                    {/* Bubble + reaction trigger */}
                    <div className="relative max-w-[70%]">
                      <div
                        className={cn(
                          "rounded-lg px-3 py-2 text-sm",
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
                        {msg.text && (
                          <p className="whitespace-pre-wrap">
                            <Linkify text={msg.text} isOwn={msg.is_own} />
                          </p>
                        )}
                        <MessageAttachments attachments={msg.attachments} isOwn={msg.is_own} />
                        <p
                          className={cn(
                            "mt-1 text-right text-[10px]",
                            msg.is_own ? "text-white/70" : "text-(--text-tertiary)",
                          )}
                        >
                          {formatTime(msg.timestamp)}
                        </p>
                      </div>

                      {/* Reaction trigger (visible on hover) */}
                      <button
                        type="button"
                        onClick={() => setReactionMsgId(reactionMsgId === msg.id ? null : msg.id)}
                        aria-label="Reagir à mensagem"
                        className={cn(
                          "absolute -bottom-2 rounded-full border border-(--border-default) bg-(--bg-surface) p-1 shadow-sm transition-opacity",
                          msg.is_own ? "-left-3" : "-right-3",
                          reactionMsgId === msg.id
                            ? "opacity-100"
                            : "opacity-0 group-hover/msg:opacity-100",
                        )}
                      >
                        <SmilePlus size={12} className="text-(--text-tertiary)" />
                      </button>

                      {/* Reaction picker popup */}
                      {reactionMsgId === msg.id && (
                        <div
                          className={cn(
                            "absolute z-20 mt-1 flex gap-0.5 rounded-full border border-(--border-default) bg-(--bg-surface) px-1.5 py-1 shadow-lg",
                            msg.is_own ? "right-0" : "left-0",
                          )}
                        >
                          {REACTION_EMOJIS.map((emoji) => (
                            <button
                              key={emoji}
                              type="button"
                              onClick={() => handleReaction(msg.id, emoji)}
                              className="flex h-7 w-7 items-center justify-center rounded-full text-base transition-transform hover:scale-125 hover:bg-(--bg-overlay)"
                            >
                              {emoji}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Existing reactions display */}
                      {msg.reactions && msg.reactions.length > 0 && (
                        <div
                          className={cn(
                            "mt-0.5 flex gap-1",
                            msg.is_own ? "justify-end" : "justify-start",
                          )}
                        >
                          {groupReactions(msg.reactions).map(({ emoji, count, isOwn }) => (
                            <button
                              key={emoji}
                              type="button"
                              onClick={() =>
                                isOwn
                                  ? handleRemoveReaction(msg.id, emoji)
                                  : handleReaction(msg.id, emoji)
                              }
                              className={cn(
                                "flex items-center gap-0.5 rounded-full border px-1.5 py-0.5 text-[11px] transition-colors",
                                isOwn
                                  ? "border-(--accent) bg-(--accent-subtle) text-(--accent)"
                                  : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:bg-(--bg-overlay)",
                              )}
                            >
                              <span>{emoji}</span>
                              {count > 1 && <span>{count}</span>}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
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

function formatDateSeparator(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const diffDays = Math.round((today.getTime() - msgDay.getTime()) / 86400000)

    if (diffDays === 0) return "Hoje"
    if (diffDays === 1) return "Ontem"
    if (diffDays < 7) {
      return date.toLocaleDateString("pt-BR", { weekday: "long" })
    }
    return date.toLocaleDateString("pt-BR", { day: "numeric", month: "short", year: "numeric" })
  } catch {
    return ""
  }
}

function shouldShowDateSeparator(messages: ChatMessage[], index: number): boolean {
  if (index === 0) return true
  try {
    const currMsg = messages[index]
    const prevMsg = messages[index - 1]
    if (!currMsg || !prevMsg) return false
    const curr = new Date(currMsg.timestamp)
    const prev = new Date(prevMsg.timestamp)
    return (
      curr.getFullYear() !== prev.getFullYear() ||
      curr.getMonth() !== prev.getMonth() ||
      curr.getDate() !== prev.getDate()
    )
  } catch {
    return false
  }
}

// ── Attachment rendering ────────────────────────────────────────────

interface AttachmentItem {
  url?: string
  type?: string
  name?: string
  mime_type?: string
  size?: number
  [key: string]: unknown
}

function MessageAttachments({
  attachments,
  isOwn,
}: {
  attachments: AttachmentItem[]
  isOwn: boolean
}) {
  if (!attachments || attachments.length === 0) return null

  return (
    <div className="mt-1.5 space-y-1.5">
      {attachments.map((att, i) => {
        const url = att.url || ""
        const mimeType = att.mime_type || att.type || ""
        const name = att.name || "Anexo"

        if (mimeType.startsWith("image/") || /\.(jpg|jpeg|png|gif|webp)$/i.test(url)) {
          return (
            <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="block">
              {/* eslint-disable-next-line @next/next/no-img-element -- attachment URLs are arbitrary external assets */}
              <img src={url} alt={name} className="max-h-48 max-w-full rounded-md object-contain" />
            </a>
          )
        }

        if (mimeType.startsWith("video/") || /\.(mp4|webm|mov)$/i.test(url)) {
          return (
            <div key={i} className="max-w-75">
              <video controls className="w-full rounded-md" preload="metadata">
                <source src={url} type={mimeType || undefined} />
              </video>
            </div>
          )
        }

        if (mimeType.startsWith("audio/") || /\.(mp3|ogg|wav|m4a)$/i.test(url)) {
          return (
            <div key={i} className="flex items-center gap-2">
              <Play size={14} className={isOwn ? "text-white/80" : "text-(--text-secondary)"} />
              <audio controls preload="metadata" className="h-8 flex-1">
                <source src={url} type={mimeType || undefined} />
              </audio>
            </div>
          )
        }

        // Generic file
        return (
          <a
            key={i}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs transition-colors",
              isOwn
                ? "border-white/20 text-white/90 hover:bg-white/10"
                : "border-(--border-default) text-(--text-secondary) hover:bg-(--bg-overlay)",
            )}
          >
            <FileText size={14} />
            <span className="min-w-0 flex-1 truncate">{name}</span>
            <Download size={12} />
          </a>
        )
      })}
    </div>
  )
}

// ── Reaction helpers ────────────────────────────────────────────────

const REACTION_EMOJIS = ["👍", "❤️", "😂", "😮", "😢", "🔥", "👏"]

interface GroupedReaction {
  emoji: string
  count: number
  isOwn: boolean
}

function groupReactions(reactions: { emoji: string; is_own: boolean }[]): GroupedReaction[] {
  const map = new Map<string, GroupedReaction>()
  for (const r of reactions) {
    const existing = map.get(r.emoji)
    if (existing) {
      existing.count++
      if (r.is_own) existing.isOwn = true
    } else {
      map.set(r.emoji, { emoji: r.emoji, count: 1, isOwn: r.is_own })
    }
  }
  return Array.from(map.values())
}

// ── Linkify ─────────────────────────────────────────────────────────

const URL_RE = /https?:\/\/[^\s<>"')\]]+/g

function Linkify({ text, isOwn }: { text: string; isOwn: boolean }) {
  const parts: React.ReactNode[] = []
  let lastIndex = 0

  for (const match of text.matchAll(URL_RE)) {
    const url = match[0]
    const start = match.index
    if (start > lastIndex) {
      parts.push(text.slice(lastIndex, start))
    }
    parts.push(
      <a
        key={start}
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "underline break-all",
          isOwn ? "text-white/90 hover:text-white" : "text-(--accent) hover:text-(--accent)",
        )}
      >
        {url}
      </a>,
    )
    lastIndex = start + url.length
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return <>{parts}</>
}
