"use client"

import { useState } from "react"
import Link from "next/link"
import { useLeads } from "@/lib/api/hooks/use-leads"
import { useUIStore } from "@/store/ui-store"
import { LeadTable } from "@/components/leads/lead-table"
import { LeadCreateDialog } from "@/components/leads/lead-create-dialog"
import { LeadImportDialog } from "@/components/leads/lead-import-dialog"
import { LeadMergeDialog } from "@/components/leads/lead-merge-dialog"
import { Search, X, Linkedin, GitMerge } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "raw", label: "Novo" },
  { value: "enriched", label: "Enriquecido" },
  { value: "in_cadence", label: "Em cadência" },
  { value: "converted", label: "Convertido" },
  { value: "archived", label: "Arquivado" },
]

export default function LeadsPage() {
  const { activeFilters, setFilter, clearFilters } = useUIStore()
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([])
  const [showMergeDialog, setShowMergeDialog] = useState(false)

  const { data, isLoading } = useLeads({
    page,
    page_size: 20,
    ...(activeFilters.status?.[0] ? { status: activeFilters.status[0] } : {}),
    ...(search ? { search } : {}),
  })

  const hasFilters = !!activeFilters.status?.[0] || !!search
  const selectedLeads = (data?.items ?? []).filter((lead) => selectedLeadIds.includes(lead.id))

  function handleSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setPage(1)
  }

  function toggleLead(leadId: string, checked: boolean) {
    setSelectedLeadIds((current) => {
      if (checked) return [...new Set([...current, leadId])]
      return current.filter((id) => id !== leadId)
    })
  }

  function toggleAll(checked: boolean) {
    if (!data) return
    setSelectedLeadIds(checked ? data.items.map((lead) => lead.id) : [])
  }

  return (
    <div className="space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Leads</h1>
          <p className="text-sm text-(--text-secondary)">
            {data ? `${data.total} lead${data.total !== 1 ? "s" : ""}` : "Carregando…"}
          </p>
        </div>
        <div className="flex gap-2">
          {selectedLeadIds.length >= 2 && (
            <Button variant="outline" onClick={() => setShowMergeDialog(true)}>
              <GitMerge size={14} aria-hidden="true" />
              Mesclar {selectedLeadIds.length}
            </Button>
          )}
          <LeadImportDialog />
          <Link
            href="/leads/busca-linkedin"
            className="inline-flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 text-sm font-medium text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
          >
            <Linkedin size={14} />
            Busca LinkedIn
          </Link>
          <LeadCreateDialog />
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Busca */}
        <form onSubmit={handleSearch} className="relative flex-1 min-w-50 max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            aria-hidden="true"
          />
          <input
            type="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Buscar por nome, empresa ou cargo…"
            className="w-full rounded-md border border-(--border-default) bg-(--bg-surface) py-2 pl-8 pr-3 text-sm text-(--text-primary) placeholder:text-(--text-tertiary) focus:border-(--accent) focus:outline-none"
          />
        </form>

        {/* Filtro por status */}
        <div className="flex items-center gap-1">
          {STATUS_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setFilter("status", value ? [value] : [])
                setPage(1)
              }}
              className={cn(
                "rounded-(--radius-full) px-3 py-1.5 text-xs font-medium transition-colors",
                (activeFilters.status?.[0] ?? "") === value
                  ? "bg-(--accent) text-white"
                  : "bg-(--bg-overlay) text-(--text-secondary) hover:bg-(--bg-sunken)",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Limpar filtros */}
        {hasFilters && (
          <button
            type="button"
            onClick={() => {
              clearFilters()
              setSearch("")
              setPage(1)
            }}
            className="flex items-center gap-1 text-xs text-(--text-tertiary) hover:text-(--danger)"
          >
            <X size={12} aria-hidden="true" />
            Limpar
          </button>
        )}
      </div>

      {/* Tabela */}
      <LeadTable
        leads={data?.items ?? []}
        isLoading={isLoading}
        selectedLeadIds={selectedLeadIds}
        onToggleLead={toggleLead}
        onToggleAll={toggleAll}
        onLeadDeleted={() => setSelectedLeadIds([])}
      />

      <LeadMergeDialog
        open={showMergeDialog}
        onOpenChange={setShowMergeDialog}
        leads={selectedLeads}
        onMerged={() => setSelectedLeadIds([])}
      />

      {/* Paginação */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-(--text-secondary)">
            Página {data.page} de {data.pages}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={data.page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-md border border-(--border-default) px-3 py-1.5 text-xs text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) disabled:cursor-not-allowed disabled:opacity-40"
            >
              Anterior
            </button>
            <button
              type="button"
              disabled={data.page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-md border border-(--border-default) px-3 py-1.5 text-xs text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) disabled:cursor-not-allowed disabled:opacity-40"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
