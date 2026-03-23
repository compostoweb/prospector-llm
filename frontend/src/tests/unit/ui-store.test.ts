import { describe, it, expect, beforeEach } from "vitest"
import { useUIStore } from "@/store/ui-store"

// ── Estado inicial padrão ─────────────────────────────────────────────

const DEFAULT_STATE = {
  sidebarCollapsed: false,
  activeFilters: {},
  selectedLeadId: null,
}

// ── Testes ────────────────────────────────────────────────────────────

describe("useUIStore", () => {
  beforeEach(() => {
    // Limpa o mock de localStorage entre testes (evita contaminação do persist)
    localStorage.clear()
    useUIStore.setState(DEFAULT_STATE)
  })

  // ── Sidebar ─────────────────────────────────────────────────────────

  describe("sidebar", () => {
    it("estado inicial: sidebarCollapsed = false", () => {
      expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    })

    it("toggleSidebar inverte o valor (false → true)", () => {
      useUIStore.getState().toggleSidebar()
      expect(useUIStore.getState().sidebarCollapsed).toBe(true)
    })

    it("toggleSidebar inverte o valor (true → false)", () => {
      useUIStore.setState({ sidebarCollapsed: true })
      useUIStore.getState().toggleSidebar()
      expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    })

    it("setSidebarCollapsed define valor explícito true", () => {
      useUIStore.getState().setSidebarCollapsed(true)
      expect(useUIStore.getState().sidebarCollapsed).toBe(true)
    })

    it("setSidebarCollapsed define valor explícito false", () => {
      useUIStore.setState({ sidebarCollapsed: true })
      useUIStore.getState().setSidebarCollapsed(false)
      expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    })
  })

  // ── activeFilters ────────────────────────────────────────────────────

  describe("activeFilters", () => {
    it("estado inicial: filtros vazios", () => {
      expect(useUIStore.getState().activeFilters).toEqual({})
    })

    it("setFilter define chave 'search'", () => {
      useUIStore.getState().setFilter("search", "Acme")
      expect(useUIStore.getState().activeFilters.search).toBe("Acme")
    })

    it("setFilter define chave 'status'", () => {
      useUIStore.getState().setFilter("status", ["enriched", "raw"])
      expect(useUIStore.getState().activeFilters.status).toEqual(["enriched", "raw"])
    })

    it("setFilter define chave 'cadence_id'", () => {
      useUIStore.getState().setFilter("cadence_id", "cad-123")
      expect(useUIStore.getState().activeFilters.cadence_id).toBe("cad-123")
    })

    it("setFilter define score_min e score_max", () => {
      useUIStore.getState().setFilter("score_min", 40)
      useUIStore.getState().setFilter("score_max", 90)
      const filters = useUIStore.getState().activeFilters
      expect(filters.score_min).toBe(40)
      expect(filters.score_max).toBe(90)
    })

    it("setFilter preserva outras chaves ao adicionar uma nova", () => {
      useUIStore.getState().setFilter("search", "Acme")
      useUIStore.getState().setFilter("status", ["converted"])
      const filters = useUIStore.getState().activeFilters
      expect(filters.search).toBe("Acme")
      expect(filters.status).toEqual(["converted"])
    })

    it("setFilter sobrescreve chave existente", () => {
      useUIStore.getState().setFilter("search", "Acme")
      useUIStore.getState().setFilter("search", "Novo valor")
      expect(useUIStore.getState().activeFilters.search).toBe("Novo valor")
    })

    it("clearFilters reseta para objeto vazio", () => {
      useUIStore.getState().setFilter("search", "Acme")
      useUIStore.getState().setFilter("status", ["raw"])
      useUIStore.getState().clearFilters()
      expect(useUIStore.getState().activeFilters).toEqual({})
    })
  })

  // ── selectedLeadId ───────────────────────────────────────────────────

  describe("selectedLeadId", () => {
    it("estado inicial: null", () => {
      expect(useUIStore.getState().selectedLeadId).toBeNull()
    })

    it("setSelectedLeadId define um ID", () => {
      useUIStore.getState().setSelectedLeadId("lead-abc-123")
      expect(useUIStore.getState().selectedLeadId).toBe("lead-abc-123")
    })

    it("setSelectedLeadId pode ser resetado para null", () => {
      useUIStore.getState().setSelectedLeadId("lead-abc-123")
      useUIStore.getState().setSelectedLeadId(null)
      expect(useUIStore.getState().selectedLeadId).toBeNull()
    })

    it("setSelectedLeadId sobrescreve valor anterior", () => {
      useUIStore.getState().setSelectedLeadId("lead-1")
      useUIStore.getState().setSelectedLeadId("lead-2")
      expect(useUIStore.getState().selectedLeadId).toBe("lead-2")
    })
  })
})
