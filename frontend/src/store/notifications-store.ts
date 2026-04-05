import { create } from "zustand"

// ── Tipos ─────────────────────────────────────────────────────────────

export type NotificationKind =
  | "lead.replied"
  | "lead.enriched"
  | "step.sent"
  | "step.failed"
  | "cadence.finished"
  | "connection.accepted"
  | "inbox.new_message"
  | "system"

export interface Notification {
  id: string
  kind: NotificationKind
  title: string
  body?: string
  lead_id?: string
  cadence_id?: string
  read: boolean
  created_at: string // ISO
}

interface NotificationsState {
  notifications: Notification[]
  unreadCount: number

  push: (notification: Omit<Notification, "id" | "read" | "created_at">) => void
  markRead: (id: string) => void
  markAllRead: () => void
  dismiss: (id: string) => void
  clear: () => void
}

const MAX_NOTIFICATIONS = 50

// ── Store ─────────────────────────────────────────────────────────────

export const useNotificationsStore = create<NotificationsState>()((set) => ({
  notifications: [],
  unreadCount: 0,

  push: (notification) => {
    const newItem: Notification = {
      ...notification,
      id: crypto.randomUUID(),
      read: false,
      created_at: new Date().toISOString(),
    }

    set((state) => {
      const updated = [newItem, ...state.notifications].slice(0, MAX_NOTIFICATIONS)
      return {
        notifications: updated,
        unreadCount: updated.filter((n) => !n.read).length,
      }
    })
  },

  markRead: (id) => {
    set((state) => {
      const updated = state.notifications.map((n) => (n.id === id ? { ...n, read: true } : n))
      return { notifications: updated, unreadCount: updated.filter((n) => !n.read).length }
    })
  },

  markAllRead: () => {
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    }))
  },

  dismiss: (id) => {
    set((state) => {
      const updated = state.notifications.filter((n) => n.id !== id)
      return { notifications: updated, unreadCount: updated.filter((n) => !n.read).length }
    })
  },

  clear: () => set({ notifications: [], unreadCount: 0 }),
}))
