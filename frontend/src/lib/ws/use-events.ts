"use client"

import { useEffect, useRef, useCallback } from "react"
import { useSession } from "next-auth/react"
import { useQueryClient } from "@tanstack/react-query"
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
  "lead.replied": [["leads"], ["dashboard", "stats"]],
  "lead.enriched": [["leads"]],
  "lead.score_updated": [["leads"]],
  "step.sent": [["leads"], ["cadences"]],
  "step.failed": [["leads"], ["cadences"]],
  "cadence.finished": [["cadences"]],
}

// ── Hook principal ────────────────────────────────────────────────────

export function useEvents() {
  const { data: session, status } = useSession()
  const queryClient = useQueryClient()
  const push = useNotificationsStore((s) => s.push)

  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

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
    },
    [queryClient, push],
  )

  const connect = useCallback(() => {
    if (!session?.accessToken || unmountedRef.current) return

    const wsUrl = `${env.NEXT_PUBLIC_WS_URL}/ws/events?token=${session.accessToken}`
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
      if (unmountedRef.current) return
      const delay =
        RECONNECT_DELAYS[Math.min(retryCountRef.current, RECONNECT_DELAYS.length - 1)] ?? 30_000
      retryCountRef.current += 1
      retryTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close() // dispara onclose → reconnect
    }
  }, [session?.accessToken, handleEvent])

  useEffect(() => {
    if (status !== "authenticated") return

    unmountedRef.current = false
    connect()

    return () => {
      unmountedRef.current = true
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
      wsRef.current?.close()
    }
  }, [status, connect])
}
