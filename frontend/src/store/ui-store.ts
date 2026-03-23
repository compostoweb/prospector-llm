import { create } from "zustand"
import { persist } from "zustand/middleware"

// ── Tipos ─────────────────────────────────────────────────────────────

interface ActiveFilters {
  status?: string[]
  cadence_id?: string
  search?: string
  score_min?: number
  score_max?: number
}

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void

  // Filtros da listagem de leads
  activeFilters: ActiveFilters
  setFilter: <K extends keyof ActiveFilters>(key: K, value: ActiveFilters[K]) => void
  clearFilters: () => void

  // Lead selecionado na lista (para scroll-sync / preview)
  selectedLeadId: string | null
  setSelectedLeadId: (id: string | null) => void
}

// ── Store ─────────────────────────────────────────────────────────────

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Sidebar — persiste no localStorage
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // Filtros — NÃO persistem (resetam ao recarregar)
      activeFilters: {},
      setFilter: (key, value) =>
        set((state) => ({
          activeFilters: { ...state.activeFilters, [key]: value },
        })),
      clearFilters: () => set({ activeFilters: {} }),

      // Lead selecionado — NÃO persiste
      selectedLeadId: null,
      setSelectedLeadId: (id) => set({ selectedLeadId: id }),
    }),
    {
      name: "prospector-ui",
      // Persiste apenas a sidebar
      partialize: (state) => ({ sidebarCollapsed: state.sidebarCollapsed }),
    },
  ),
)
