"use client"

import { useEffect, useRef, useCallback, type MutableRefObject } from "react"
import { useSession } from "next-auth/react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { useNotificationsStore } from "@/store/notifications-store"
import { env } from "@/env"

// ── Tipos ─────────────────────────────────────────────────────────────

export type WSEventType =
  | "lead.replied"
  | "lead.enriched"
  | "lead.score_updated"
  | "step.sent"
  | "step.failed"
  | "cadence.finished"
  | "connection.accepted"
  | "inbox.new_message"
  | "inbox.chat_read"
  | "inbound.reply_ambiguous"
  | "ping"

export interface WSEvent {
  type: WSEventType
  data: Record<string, unknown>
  tenant_id: string
  timestamp: string
}

// ── Constantes ────────────────────────────────────────────────────────

const RECONNECT_DELAYS = [1_000, 2_000, 4_000, 8_000, 30_000] // backoff escalonado

// Chaves do TanStack Query que cada evento deve invalidar
const INVALIDATION_MAP: Partial<Record<WSEventType, string[][]>> = {
  "lead.replied": [
    ["leads"],
    ["cadences"],
    ["dashboard", "stats"],
    ["analytics", "cadences", "overview"],
    ["analytics", "cadences"],
    ["analytics", "email"],
    ["analytics", "recent-replies"],
    ["analytics", "intents"],
    ["analytics", "channels"],
    ["analytics", "funnel"],
  ],
  "lead.enriched": [["leads"]],
  "lead.score_updated": [["leads"]],
  "step.sent": [
    ["leads"],
    ["cadences"],
    ["dashboard", "stats"],
    ["analytics", "cadences", "overview"],
    ["analytics", "channels"],
    ["analytics", "email"],
  ],
  "step.failed": [["leads"], ["cadences"], ["analytics", "cadences", "overview"]],
  "cadence.finished": [
    ["cadences"],
    ["analytics", "cadences", "overview"],
    ["analytics", "funnel"],
    ["analytics", "performance"],
  ],
  "connection.accepted": [["leads"], ["manual-tasks"], ["dashboard", "stats"]],
  "inbox.new_message": [
    ["inbox", "conversations"],
    ["inbox", "messages"],
  ],
  "inbound.reply_ambiguous": [["cadences"], ["analytics", "cadences"], ["analytics", "email"]],
  "inbox.chat_read": [["inbox", "conversations"]],
}

// ── Hook principal ────────────────────────────────────────────────────

function scheduleReconnectAttempt({
  retryCountRef,
  retryTimerRef,
  unmountedRef,
  connect,
}: {
  retryCountRef: MutableRefObject<number>
  retryTimerRef: MutableRefObject<ReturnType<typeof setTimeout> | null>
  unmountedRef: MutableRefObject<boolean>
  connect: () => void
}) {
  if (unmountedRef.current) return
  const delay =
    RECONNECT_DELAYS[Math.min(retryCountRef.current, RECONNECT_DELAYS.length - 1)] ?? 30_000
  retryCountRef.current += 1
  retryTimerRef.current = setTimeout(connect, delay)
}

export function useEvents() {
  const { data: session, status } = useSession()
  const queryClient = useQueryClient()
  const push = useNotificationsStore((s) => s.push)

  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  const issueWsTicket = useCallback(async () => {
    if (!session?.accessToken) return null

    const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/auth/ws-ticket`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
      },
      cache: "no-store",
    })

    if (!response.ok) {
      return null
    }

    const payload = (await response.json()) as { ticket?: string }
    return payload.ticket ?? null
  }, [session?.accessToken])

  const disconnect = useCallback(() => {
    unmountedRef.current = true
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current)
      retryTimerRef.current = null
    }
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  const handleEvent = useCallback(
    (event: WSEvent) => {
      // Invalida queries relevantes
      const keys = INVALIDATION_MAP[event.type]
      if (keys) {
        for (const queryKey of keys) {
          void queryClient.invalidateQueries({ queryKey })
        }
      }

      // Empurra notificação para eventos de interesse do usuário
      if (event.type === "lead.replied") {
        const lead = event.data as { name?: string; lead_id?: string }
        if (lead.lead_id) {
          void queryClient.invalidateQueries({ queryKey: ["leads", lead.lead_id, "steps"] })
          void queryClient.invalidateQueries({ queryKey: ["leads", lead.lead_id, "interactions"] })
        }
        push({
          kind: "lead.replied",
          title: "Nova resposta de lead",
          ...(lead.name ? { body: `${lead.name} respondeu` } : {}),
          ...(lead.lead_id ? { lead_id: lead.lead_id } : {}),
        })
      }

      if (event.type === "step.failed") {
        const step = event.data as { lead_name?: string; step_id?: string }
        push({
          kind: "step.failed",
          title: "Falha ao enviar mensagem",
          ...(step.lead_name ? { body: step.lead_name } : {}),
        })
      }

      if (event.type === "connection.accepted") {
        const conn = event.data as { lead_name?: string }
        push({
          kind: "connection.accepted",
          title: "Conexão aceita",
          ...(conn.lead_name ? { body: `${conn.lead_name} aceitou sua conexão` } : {}),
        })
      }

      if (event.type === "inbox.new_message") {
        const msg = event.data as { sender_name?: string }
        push({
          kind: "inbox.new_message",
          title: "Nova mensagem",
          ...(msg.sender_name ? { body: `${msg.sender_name} enviou uma mensagem` } : {}),
        })
      }

      if (event.type === "inbound.reply_ambiguous") {
        const data = event.data as {
          lead_id?: string
          lead_name?: string
          channel?: string
          sent_cadence_count?: number
        }
        const channelLabel = data.channel === "email" ? "email" : "LinkedIn"
        const leadLabel = data.lead_name || "Um lead"
        const cadenceLabel = data.sent_cadence_count
          ? `${data.sent_cadence_count} cadências ativas possíveis`
          : "mais de uma cadência possível"
        const body = `${leadLabel} respondeu por ${channelLabel}, mas o sistema não vinculou automaticamente porque há ${cadenceLabel}.`

        if (data.lead_id) {
          void queryClient.invalidateQueries({ queryKey: ["leads", data.lead_id, "steps"] })
          void queryClient.invalidateQueries({ queryKey: ["leads", data.lead_id, "interactions"] })
        }

        push({
          kind: "system",
          title: "Reply ambíguo detectado",
          body,
          ...(data.lead_id ? { lead_id: data.lead_id } : {}),
        })
        toast.warning("Reply ambíguo detectado", { description: body })
      }

      if (event.type === "inbox.chat_read") {
        const { chat_id } = event.data as { chat_id?: string }
        if (chat_id) {
          queryClient.setQueriesData<{ items: Array<{ chat_id: string; unread_count: number }> }>(
            { queryKey: ["inbox", "conversations"] },
            (old) => {
              if (!old?.items) return old
              return {
                ...old,
                items: old.items.map((c) =>
                  c.chat_id === chat_id ? { ...c, unread_count: 0 } : c,
                ),
              }
            },
          )
        }
      }
    },
    [queryClient, push],
  )

  const connect = useCallback(async () => {
    if (!session?.accessToken || unmountedRef.current) return

    const ticket = await issueWsTicket()
    if (!ticket || unmountedRef.current) {
      scheduleReconnectAttempt({
        retryCountRef,
        retryTimerRef,
        unmountedRef,
        connect: () => {
          void connect()
        },
      })
      return
    }

    const wsUrl = `${env.NEXT_PUBLIC_WS_URL}?ticket=${encodeURIComponent(ticket)}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      retryCountRef.current = 0 // reset backoff ao conectar
    }

    ws.onmessage = (msg: MessageEvent<string>) => {
      try {
        const event = JSON.parse(msg.data) as WSEvent
        if (event.type === "ping") return // keepalive
        handleEvent(event)
      } catch {
        // mensagem mal formada — ignorar silenciosamente
      }
    }

    ws.onclose = () => {
      scheduleReconnectAttempt({
        retryCountRef,
        retryTimerRef,
        unmountedRef,
        connect: () => {
          void connect()
        },
      })
    }

    ws.onerror = () => {
      ws.close() // dispara onclose → reconnect
    }
  }, [session?.accessToken, handleEvent, issueWsTicket])

  useEffect(() => {
    if (status !== "authenticated") return

    unmountedRef.current = false
    void connect()

    return disconnect
  }, [status, connect, disconnect])
}
