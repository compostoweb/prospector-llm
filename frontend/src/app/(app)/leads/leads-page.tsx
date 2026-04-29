"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import {
  useLeads,
  useEnrichLead,
  useArchiveLead,
  usePermanentDeleteLead,
} from "@/lib/api/hooks/use-leads"
import { useLeadLists } from "@/lib/api/hooks/use-lead-lists"
import { useUIStore } from "@/store/ui-store"
import { LeadTable } from "@/components/leads/lead-table"
import { LeadCreateDialog } from "@/components/leads/lead-create-dialog"
import { LeadImportDialog } from "@/components/leads/lead-import-dialog"
import { LeadMergeDialog } from "@/components/leads/lead-merge-dialog"
import {
  Search,
  X,
  Linkedin,
  GitMerge,
  AlertTriangle,
  Sparkles,
  Archive,
  Trash2,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

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

const EMAIL_QUALITY_OPTIONS = [
  { value: "", label: "Qualquer qualidade" },
  { value: "green", label: "Email verde" },
  { value: "orange", label: "Email laranja" },
  { value: "red", label: "Email vermelho" },
]

const BOOLEAN_FILTER_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "true", label: "Sim" },
  { value: "false", label: "Não" },
]

export default function LeadsPage() {
  const { activeFilters, setFilter, clearFilters } = useUIStore()
  const { data: lists } = useLeadLists()
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([])
  const [showMergeDialog, setShowMergeDialog] = useState(false)
  const [enrichingIds, setEnrichingIds] = useState<Set<string>>(new Set())
  const [includeMobileOnEnrich, setIncludeMobileOnEnrich] = useState(true)
  const [forceRefreshOnEnrich, setForceRefreshOnEnrich] = useState(false)
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [bulkPending, setBulkPending] = useState(false)
  const prevStatusRef = useRef<Map<string, string>>(new Map())
  const enrichLead = useEnrichLead()
  const archiveLead = useArchiveLead()
  const permanentDelete = usePermanentDeleteLead()

  const { data, isLoading } = useLeads(
    {
      page,
      page_size: 20,
      ...(activeFilters.status?.[0] ? { status: activeFilters.status[0] } : {}),
      ...(activeFilters.source ? { source: activeFilters.source } : {}),
      ...(activeFilters.list_id ? { list_id: activeFilters.list_id } : {}),
      ...(activeFilters.segment ? { segment: activeFilters.segment } : {}),
      ...(activeFilters.score_min != null ? { score_min: activeFilters.score_min } : {}),
      ...(activeFilters.score_max != null ? { score_max: activeFilters.score_max } : {}),
      ...(activeFilters.email_quality ? { email_quality: activeFilters.email_quality } : {}),
      ...(activeFilters.has_verified_email != null
        ? { has_verified_email: activeFilters.has_verified_email }
        : {}),
      ...(activeFilters.has_mobile != null ? { has_mobile: activeFilters.has_mobile } : {}),
      ...(activeFilters.linkedin_mismatch != null
        ? { linkedin_mismatch: activeFilters.linkedin_mismatch }
        : {}),
      ...(search ? { search } : {}),
    },
    { refetchInterval: enrichingIds.size > 0 ? 5000 : false },
  )

  const hasFilters =
    !!activeFilters.status?.[0] ||
    !!activeFilters.source ||
    !!activeFilters.list_id ||
    !!activeFilters.segment ||
    activeFilters.score_min != null ||
    activeFilters.score_max != null ||
    !!activeFilters.email_quality ||
    activeFilters.has_verified_email != null ||
    activeFilters.has_mobile != null ||
    activeFilters.linkedin_mismatch != null ||
    !!search
  const selectedLeads = (data?.items ?? []).filter((lead) => selectedLeadIds.includes(lead.id))
  const overlappingCadenceLeads = (data?.items ?? []).filter(
    (lead) => lead.has_multiple_active_cadences,
  )

  useEffect(() => {
    if (!data || enrichingIds.size === 0) return
    const prevStatuses = prevStatusRef.current
    data.items.forEach((lead) => {
      const prevStatus = prevStatuses.get(lead.id)
      if (prevStatus !== undefined && prevStatus !== lead.status && enrichingIds.has(lead.id)) {
        toast.success(`${lead.name} foi enriquecido`)
        setEnrichingIds((curr) => {
          const next = new Set(curr)
          next.delete(lead.id)
          return next
        })
      }
      prevStatuses.set(lead.id, lead.status)
    })
  }, [data, enrichingIds])

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

  function handleEnrichStart(leadId: string) {
    setEnrichingIds((curr) => new Set([...curr, leadId]))
  }

  async function handleBulkEnrich() {
    const ids = [...selectedLeadIds]
    setBulkPending(true)
    toast.loading(`Iniciando enriquecimento…`, { id: "bulk-enrich" })
    setEnrichingIds((curr) => new Set([...curr, ...ids]))
    const results = await Promise.allSettled(
      ids.map((id) =>
        enrichLead.mutateAsync({
          leadId: id,
          include_mobile: includeMobileOnEnrich,
          force_refresh: forceRefreshOnEnrich,
        }),
      ),
    )
    const succeeded = results.filter((r) => r.status === "fulfilled").length
    toast.success(`${succeeded} de ${ids.length} leads enviados para enriquecimento`, {
      id: "bulk-enrich",
    })
    setSelectedLeadIds([])
    setBulkPending(false)
  }

  async function handleBulkArchive() {
    const ids = [...selectedLeadIds]
    setBulkPending(true)
    toast.loading(`Arquivando ${ids.length} leads…`, { id: "bulk-archive" })
    const results = await Promise.allSettled(ids.map((id) => archiveLead.mutateAsync(id)))
    const succeeded = results.filter((r) => r.status === "fulfilled").length
    toast.success(`${succeeded} de ${ids.length} leads arquivados`, { id: "bulk-archive" })
    setSelectedLeadIds([])
    setBulkPending(false)
  }

  async function handleBulkDelete() {
    const ids = [...selectedLeadIds]
    setBulkPending(true)
    toast.loading(`Excluindo ${ids.length} leads…`, { id: "bulk-delete" })
    const results = await Promise.allSettled(ids.map((id) => permanentDelete.mutateAsync(id)))
    const succeeded = results.filter((r) => r.status === "fulfilled").length
    toast.success(`${succeeded} de ${ids.length} leads excuídos`, { id: "bulk-delete" })
    setSelectedLeadIds([])
    setBulkDeleteOpen(false)
    setBulkPending(false)
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
        <div className="flex items-center gap-2">
          <LeadImportDialog />
          <Link
            href="/leads/busca-linkedin"
            className="inline-flex h-7 items-center gap-1.5 rounded-sm bg-[#0A66C2] px-3 text-xs font-medium text-white transition-opacity hover:opacity-90"
          >
            <Linkedin size={13} />
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

          <FilterSelect
            label="Qualidade do email"
            value={activeFilters.email_quality ?? ""}
            onChange={(value) => {
              setFilter(
                "email_quality",
                value === "" ? undefined : (value as "red" | "orange" | "green"),
              )
              setPage(1)
            }}
            options={EMAIL_QUALITY_OPTIONS}
          />

          <FilterSelect
            label="Email verificado"
            value={serializeBooleanFilter(activeFilters.has_verified_email)}
            onChange={(value) => {
              setFilter("has_verified_email", parseBooleanFilter(value))
              setPage(1)
            }}
            options={BOOLEAN_FILTER_OPTIONS}
          />

          <FilterSelect
            label="Tem mobile"
            value={serializeBooleanFilter(activeFilters.has_mobile)}
            onChange={(value) => {
              setFilter("has_mobile", parseBooleanFilter(value))
              setPage(1)
            }}
            options={BOOLEAN_FILTER_OPTIONS}
          />

          <FilterSelect
            label="Mismatch LinkedIn"
            value={serializeBooleanFilter(activeFilters.linkedin_mismatch)}
            onChange={(value) => {
              setFilter("linkedin_mismatch", parseBooleanFilter(value))
              setPage(1)
            }}
            options={BOOLEAN_FILTER_OPTIONS}
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

      {/* Ações em massa */}
      {selectedLeadIds.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-(--accent) bg-(--accent) px-4 py-2.5 shadow-(--shadow-sm)">
          <span className="text-sm font-semibold text-white">
            {selectedLeadIds.length} lead{selectedLeadIds.length !== 1 ? "s" : ""} selecionado
            {selectedLeadIds.length !== 1 ? "s" : ""}
          </span>
          <div className="h-4 w-px bg-white/30" />
          <div className="flex flex-wrap items-center gap-3 text-xs text-white/90">
            <label className="inline-flex items-center gap-2">
              <Checkbox
                checked={includeMobileOnEnrich}
                onCheckedChange={(checked) => setIncludeMobileOnEnrich(checked === true)}
                className="border-white/50 data-[state=checked]:bg-white data-[state=checked]:text-(--accent)"
              />
              Buscar mobile
            </label>
            <label className="inline-flex items-center gap-2">
              <Checkbox
                checked={forceRefreshOnEnrich}
                onCheckedChange={(checked) => setForceRefreshOnEnrich(checked === true)}
                className="border-white/50 data-[state=checked]:bg-white data-[state=checked]:text-(--accent)"
              />
              Forçar refresh
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {selectedLeadIds.length >= 2 && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white"
                onClick={() => setShowMergeDialog(true)}
                disabled={bulkPending}
              >
                <GitMerge size={12} aria-hidden="true" />
                Mesclar
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-7 border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white"
              onClick={handleBulkEnrich}
              disabled={bulkPending}
            >
              {bulkPending ? (
                <Loader2 size={12} className="animate-spin" aria-hidden="true" />
              ) : (
                <Sparkles size={12} aria-hidden="true" />
              )}
              Enriquecer
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white"
              onClick={handleBulkArchive}
              disabled={bulkPending}
            >
              <Archive size={12} aria-hidden="true" />
              Arquivar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 border-red-300/60 bg-red-500/30 text-white hover:bg-red-500/50 hover:text-white"
              onClick={() => setBulkDeleteOpen(true)}
              disabled={bulkPending}
            >
              <Trash2 size={12} aria-hidden="true" />
              Excluir
            </Button>
          </div>
          <div className="flex-1" />
          <button
            type="button"
            onClick={() => setSelectedLeadIds([])}
            className="rounded-md p-1 text-white/70 transition-colors hover:bg-white/20 hover:text-white"
            aria-label="Desmarcar todos"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      )}

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
        enrichingLeadIds={enrichingIds}
        onEnrich={handleEnrichStart}
        enrichOptions={{
          include_mobile: includeMobileOnEnrich,
          force_refresh: forceRefreshOnEnrich,
        }}
      />

      <LeadMergeDialog
        open={showMergeDialog}
        onOpenChange={setShowMergeDialog}
        leads={selectedLeads}
        onMerged={() => setSelectedLeadIds([])}
      />

      <AlertDialog open={bulkDeleteOpen} onOpenChange={setBulkDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Excluir {selectedLeadIds.length} lead{selectedLeadIds.length !== 1 ? "s" : ""}{" "}
              definitivamente?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Esta ação não pode ser desfeita. Os leads serão permanentemente removidos do sistema,
              incluindo histórico de interações e etapas de cadência.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={bulkPending}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-(--danger) text-white hover:opacity-90"
              disabled={bulkPending}
              onClick={handleBulkDelete}
            >
              {bulkPending && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
              Excluir definitivamente
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Paginação */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-3">
          <p className="text-sm text-(--text-secondary)">
            Página <span className="font-semibold text-(--text-primary)">{data.page}</span> de{" "}
            <span className="font-semibold text-(--text-primary)">{data.pages}</span>
            <span className="mx-2 text-(--text-tertiary)">·</span>
            <span className="text-xs text-(--text-tertiary)">
              Exibindo{" "}
              <span className="font-medium text-(--text-secondary)">
                {(data.page - 1) * data.page_size + 1}–
                {Math.min(data.page * data.page_size, data.total)}
              </span>{" "}
              de <span className="font-medium text-(--text-secondary)">{data.total}</span> leads
            </span>
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={data.page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="inline-flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 text-sm font-medium text-(--text-secondary) transition-colors hover:border-(--accent) hover:bg-(--accent-subtle) hover:text-(--accent) disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← Anterior
            </button>
            <button
              type="button"
              disabled={data.page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
              className="inline-flex items-center gap-1.5 rounded-md border border-(--accent) bg-(--accent) px-3 py-1.5 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function parseBooleanFilter(value: string): boolean | undefined {
  if (value === "true") return true
  if (value === "false") return false
  return undefined
}

function serializeBooleanFilter(value: boolean | undefined): string {
  if (value === true) return "true"
  if (value === false) return "false"
  return ""
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
