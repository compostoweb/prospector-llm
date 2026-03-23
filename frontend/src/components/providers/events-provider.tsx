"use client"

import { useEvents } from "@/lib/ws/use-events"

/** Provider client-side que inicializa o WebSocket de eventos */
export function EventsProvider({ children }: { children: React.ReactNode }) {
  useEvents()
  return <>{children}</>
}
