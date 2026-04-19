"use client"

import { useState } from "react"
import Link from "next/link"
import { useLeads } from "@/lib/api/hooks/use-leads"
import { useLeadLists } from "@/lib/api/hooks/use-lead-lists"
import { useUIStore } from "@/store/ui-store"
import { LeadTable } from "@/components/leads/lead-table"
import { LeadCreateDialog } from "@/components/leads/lead-create-dialog"
import { LeadImportDialog } from "@/components/leads/lead-import-dialog"
import { LeadMergeDialog } from "@/components/leads/lead-merge-dialog"
import { Search, X, Linkedin, GitMerge, AlertTriangle } from "lucide-react"
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

const SOURCE_OPTIONS = [
  { value: "", label: "Todas as origens" },
  { value: "manual", label: "Manual" },
  { value: "apify_maps", label: "Apify Maps" },
  { value: "apify_linkedin", label: "Apify LinkedIn" },
  { value: "linkedin_search", label: "Busca LinkedIn" },
  { value: "import", label: "Importação" },
  { value: "api", label: "Ferramenta interna/API" },
]

export default function LeadsPage() {
  const { activeFilters, setFilter, clearFilters } = useUIStore()
  const { data: lists } = useLeadLists()
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([])
  const [showMergeDialog, setShowMergeDialog] = useState(false)

  const { data, isLoading } = useLeads({
    page,
    page_size: 20,
    ...(activeFilters.status?.[0] ? { status: activeFilters.status[0] } : {}),
    ...(activeFilters.source ? { source: activeFilters.source } : {}),
    ...(activeFilters.list_id ? { list_id: activeFilters.list_id } : {}),
    ...(activeFilters.segment ? { segment: activeFilters.segment } : {}),
    ...(activeFilters.score_min != null ? { score_min: activeFilters.score_min } : {}),
    ...(activeFilters.score_max != null ? { score_max: activeFilters.score_max } : {}),
    ...(search ? { search } : {}),
  })

  const hasFilters =
    !!activeFilters.status?.[0] ||
    !!activeFilters.source ||
    !!activeFilters.list_id ||
    !!activeFilters.segment ||
    activeFilters.score_min != null ||
    activeFilters.score_max != null ||
    !!search
  const selectedLeads = (data?.items ?? []).filter((lead) => selectedLeadIds.includes(lead.id))
  const overlappingCadenceLeads = (data?.items ?? []).filter(
    (lead) => lead.has_multiple_active_cadences,
  )

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
      <div className="space-y-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
        {/* Busca */}
        <div className="flex flex-wrap items-end gap-3">
          <form onSubmit={handleSearch} className="relative min-w-50 flex-1">
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

          <FilterSelect
            label="Origem"
            value={activeFilters.source ?? ""}
            onChange={(value) => {
              setFilter("source", value || undefined)
              setPage(1)
            }}
            options={SOURCE_OPTIONS}
          />

          <FilterSelect
            label="Listas"
            value={activeFilters.list_id ?? ""}
            onChange={(value) => {
              setFilter("list_id", value || undefined)
              setPage(1)
            }}
            options={[
              { value: "", label: "Todas as listas" },
              ...((lists ?? []).map((list) => ({ value: list.id, label: list.name })) as Array<{
                value: string
                label: string
              }>),
            ]}
          />

          <FilterInput
            label="Segmento"
            value={activeFilters.segment ?? ""}
            placeholder="Ex: SaaS"
            onChange={(value) => {
              setFilter("segment", value || undefined)
              setPage(1)
            }}
          />

          <FilterInput
            label="Score mín."
            type="number"
            min={0}
            max={100}
            value={activeFilters.score_min != null ? String(activeFilters.score_min) : ""}
            placeholder="0"
            onChange={(value) => {
              setFilter("score_min", value === "" ? undefined : Number(value))
              setPage(1)
            }}
          />

          <FilterInput
            label="Score máx."
            type="number"
            min={0}
            max={100}
            value={activeFilters.score_max != null ? String(activeFilters.score_max) : ""}
            placeholder="100"
            onChange={(value) => {
              setFilter("score_max", value === "" ? undefined : Number(value))
              setPage(1)
            }}
          />

          {hasFilters && (
            <button
              type="button"
              onClick={() => {
                clearFilters()
                setSearch("")
                setPage(1)
              }}
              className="mb-0.5 flex items-center gap-1 text-xs text-(--text-tertiary) hover:text-(--danger)"
            >
              <X size={12} aria-hidden="true" />
              Limpar
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1">
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
      </div>

      {/* Tabela */}
      {overlappingCadenceLeads.length > 0 && (
        <div className="flex items-start gap-3 rounded-lg border border-(--warning) bg-(--warning-subtle) px-4 py-3 text-sm text-(--warning-subtle-fg)">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Há leads em múltiplas cadências ativas nesta página.</p>
            <p className="mt-1 text-xs text-(--warning-subtle-fg)">
              Esses casos ficam sinalizados na tabela para evitar interpretar reply em uma cadência
              errada.
            </p>
          </div>
        </div>
      )}

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

interface FilterSelectProps {
  label: string
  value: string
  onChange: (value: string) => void
  options: Array<{
    value: string
    label: string
  }>
}

function FilterSelect({ label, value, onChange, options }: FilterSelectProps) {
  return (
    <label className="flex min-w-40 flex-col gap-1 text-xs font-medium text-(--text-secondary)">
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 text-sm text-(--text-primary) focus:border-(--accent) focus:outline-none"
      >
        {options.map((option) => (
          <option key={option.value || "all"} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

interface FilterInputProps {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: "text" | "number"
  min?: number
  max?: number
}

function FilterInput({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  min,
  max,
}: FilterInputProps) {
  return (
    <label className="flex min-w-32 flex-col gap-1 text-xs font-medium text-(--text-secondary)">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 text-sm text-(--text-primary) placeholder:text-(--text-tertiary) focus:border-(--accent) focus:outline-none"
      />
    </label>
  )
}
