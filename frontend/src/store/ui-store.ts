import { create } from "zustand"
import { persist } from "zustand/middleware"
import { SIDEBAR_COLLAPSED_COOKIE } from "@/lib/sidebar-preferences"

function persistSidebarCollapsedPreference(collapsed: boolean) {
  if (typeof document === "undefined") {
    return
  }

  document.cookie = `${SIDEBAR_COLLAPSED_COOKIE}=${collapsed}; path=/; max-age=31536000; samesite=lax`
}

// ── Tipos ─────────────────────────────────────────────────────────────

interface ActiveFilters {
  status?: string[]
  source?: string
  cadence_id?: string
  list_id?: string
  segment?: string
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
      toggleSidebar: () =>
        set((state) => {
          const nextCollapsed = !state.sidebarCollapsed
          persistSidebarCollapsedPreference(nextCollapsed)
          return { sidebarCollapsed: nextCollapsed }
        }),
      setSidebarCollapsed: (collapsed) => {
        persistSidebarCollapsedPreference(collapsed)
        set({ sidebarCollapsed: collapsed })
      },

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
      onRehydrateStorage: () => (state) => {
        if (state) {
          persistSidebarCollapsedPreference(state.sidebarCollapsed)
        }
      },
    },
  ),
)
