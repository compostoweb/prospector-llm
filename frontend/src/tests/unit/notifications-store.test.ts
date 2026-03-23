import { describe, it, expect, beforeEach } from "vitest"
import { useNotificationsStore } from "@/store/notifications-store"
import type { NotificationKind } from "@/store/notifications-store"

// ── Helper ────────────────────────────────────────────────────────────

function push(
  kind: NotificationKind = "system",
  title = "Teste",
  extra?: { body?: string; lead_id?: string; cadence_id?: string },
) {
  useNotificationsStore.getState().push({ kind, title, ...extra })
}

// ── Testes ────────────────────────────────────────────────────────────

describe("useNotificationsStore", () => {
  beforeEach(() => {
    // Reseta store a cada teste para garantir isolamento
    useNotificationsStore.setState({ notifications: [], unreadCount: 0 })
  })

  // ── Estado inicial ───────────────────────────────────────────────────

  describe("estado inicial", () => {
    it("notifications é array vazio", () => {
      expect(useNotificationsStore.getState().notifications).toHaveLength(0)
    })

    it("unreadCount é zero", () => {
      expect(useNotificationsStore.getState().unreadCount).toBe(0)
    })
  })

  // ── push ─────────────────────────────────────────────────────────────

  describe("push", () => {
    it("adiciona uma notificação", () => {
      push("lead.replied", "Lead respondeu")
      expect(useNotificationsStore.getState().notifications).toHaveLength(1)
    })

    it("auto-gera id único (string não vazia)", () => {
      push()
      const { id } = useNotificationsStore.getState().notifications[0]!
      expect(typeof id).toBe("string")
      expect(id.length).toBeGreaterThan(0)
    })

    it("dois pushes geram ids distintos", () => {
      push()
      push()
      const [n1, n2] = useNotificationsStore.getState().notifications
      expect(n1!.id).not.toBe(n2!.id)
    })

    it("define read: false por padrão", () => {
      push()
      expect(useNotificationsStore.getState().notifications[0]!.read).toBe(false)
    })

    it("define created_at como ISO string válida", () => {
      push()
      const { created_at } = useNotificationsStore.getState().notifications[0]!
      expect(() => new Date(created_at)).not.toThrow()
      expect(new Date(created_at).toISOString()).toBe(created_at)
    })

    it("armazena kind e title corretamente", () => {
      push("step.sent", "Passo enviado")
      const n = useNotificationsStore.getState().notifications[0]!
      expect(n.kind).toBe("step.sent")
      expect(n.title).toBe("Passo enviado")
    })

    it("armazena campos opcionais (body, lead_id, cadence_id)", () => {
      push("lead.replied", "Respondeu", {
        body: "Texto da mensagem",
        lead_id: "lead-uuid-123",
        cadence_id: "cad-uuid-456",
      })
      const n = useNotificationsStore.getState().notifications[0]!
      expect(n.body).toBe("Texto da mensagem")
      expect(n.lead_id).toBe("lead-uuid-123")
      expect(n.cadence_id).toBe("cad-uuid-456")
    })

    it("incrementa unreadCount a cada push", () => {
      push()
      push()
      push()
      expect(useNotificationsStore.getState().unreadCount).toBe(3)
    })

    it("prepend — a notificação mais recente fica no índice 0", () => {
      push("system", "Primeira")
      push("system", "Segunda")
      expect(useNotificationsStore.getState().notifications[0]!.title).toBe("Segunda")
    })

    it("respeita limite de 50 notificações (FIFO — descarta as mais antigas)", () => {
      for (let i = 0; i < 55; i++) {
        push("system", `Notif ${i}`)
      }
      const store = useNotificationsStore.getState()
      expect(store.notifications).toHaveLength(50)
      // A mais recente (54) deve estar no topo
      expect(store.notifications[0]!.title).toBe("Notif 54")
      // A mais antiga permitida deve ser Notif 5 (55 - 50 = 5)
      expect(store.notifications[49]!.title).toBe("Notif 5")
    })

    it("suporta todos os kinds válidos sem erro", () => {
      const kinds: NotificationKind[] = [
        "lead.replied",
        "lead.enriched",
        "step.sent",
        "step.failed",
        "cadence.finished",
        "system",
      ]
      expect(() => {
        kinds.forEach((kind) => push(kind, `Notif ${kind}`))
      }).not.toThrow()
      expect(useNotificationsStore.getState().notifications).toHaveLength(kinds.length)
    })
  })

  // ── markRead ──────────────────────────────────────────────────────────

  describe("markRead", () => {
    it("marca a notificação como read: true", () => {
      push()
      const { id } = useNotificationsStore.getState().notifications[0]!
      useNotificationsStore.getState().markRead(id)
      expect(useNotificationsStore.getState().notifications[0]!.read).toBe(true)
    })

    it("decrementa unreadCount em 1", () => {
      push()
      push()
      const { id } = useNotificationsStore.getState().notifications[0]!
      useNotificationsStore.getState().markRead(id)
      expect(useNotificationsStore.getState().unreadCount).toBe(1)
    })

    it("não afeta outras notificações", () => {
      push("system", "A")
      push("system", "B")
      const idB = useNotificationsStore.getState().notifications[0]!.id
      useNotificationsStore.getState().markRead(idB)
      // A (índice 1) ainda deve estar não lida
      expect(useNotificationsStore.getState().notifications[1]!.read).toBe(false)
    })

    it("não altera unreadCount ao marcar notificação já lida", () => {
      push()
      const { id } = useNotificationsStore.getState().notifications[0]!
      useNotificationsStore.getState().markRead(id)
      useNotificationsStore.getState().markRead(id) // segunda chamada
      expect(useNotificationsStore.getState().unreadCount).toBe(0)
    })

    it("não faz nada para id inexistente", () => {
      push()
      useNotificationsStore.getState().markRead("id-que-nao-existe")
      expect(useNotificationsStore.getState().unreadCount).toBe(1)
    })
  })

  // ── markAllRead ───────────────────────────────────────────────────────

  describe("markAllRead", () => {
    it("marca todas as notificações como lidas", () => {
      push()
      push()
      push()
      useNotificationsStore.getState().markAllRead()
      const allRead = useNotificationsStore.getState().notifications.every((n) => n.read)
      expect(allRead).toBe(true)
    })

    it("zera o unreadCount", () => {
      push()
      push()
      useNotificationsStore.getState().markAllRead()
      expect(useNotificationsStore.getState().unreadCount).toBe(0)
    })

    it("não falha com lista vazia", () => {
      expect(() => useNotificationsStore.getState().markAllRead()).not.toThrow()
      expect(useNotificationsStore.getState().unreadCount).toBe(0)
    })
  })

  // ── dismiss ───────────────────────────────────────────────────────────

  describe("dismiss", () => {
    it("remove a notificação da lista", () => {
      push("system", "Para remover")
      const { id } = useNotificationsStore.getState().notifications[0]!
      useNotificationsStore.getState().dismiss(id)
      expect(useNotificationsStore.getState().notifications).toHaveLength(0)
    })

    it("decrementa unreadCount ao remover notificação não lida", () => {
      push()
      const { id } = useNotificationsStore.getState().notifications[0]!
      useNotificationsStore.getState().dismiss(id)
      expect(useNotificationsStore.getState().unreadCount).toBe(0)
    })

    it("não altera unreadCount ao remover notificação já lida", () => {
      push()
      const { id } = useNotificationsStore.getState().notifications[0]!
      useNotificationsStore.getState().markRead(id)
      useNotificationsStore.getState().dismiss(id)
      expect(useNotificationsStore.getState().unreadCount).toBe(0)
    })

    it("preserva outras notificações", () => {
      push("system", "Manter A")
      push("system", "Remover B")
      const idB = useNotificationsStore.getState().notifications[0]!.id
      useNotificationsStore.getState().dismiss(idB)
      expect(useNotificationsStore.getState().notifications).toHaveLength(1)
      expect(useNotificationsStore.getState().notifications[0]!.title).toBe("Manter A")
    })

    it("não faz nada para id inexistente", () => {
      push()
      useNotificationsStore.getState().dismiss("id-invalido")
      expect(useNotificationsStore.getState().notifications).toHaveLength(1)
    })
  })

  // ── clear ─────────────────────────────────────────────────────────────

  describe("clear", () => {
    it("remove todas as notificações", () => {
      push()
      push()
      push()
      useNotificationsStore.getState().clear()
      expect(useNotificationsStore.getState().notifications).toHaveLength(0)
    })

    it("zera o unreadCount", () => {
      push()
      push()
      useNotificationsStore.getState().clear()
      expect(useNotificationsStore.getState().unreadCount).toBe(0)
    })

    it("não falha com lista vazia", () => {
      expect(() => useNotificationsStore.getState().clear()).not.toThrow()
    })
  })
})
