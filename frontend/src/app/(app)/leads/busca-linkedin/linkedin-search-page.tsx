"use client"

import { useState, useRef, useCallback, useEffect, useMemo } from "react"
import Link from "next/link"
import Image from "next/image"
import { useSession } from "next-auth/react"
import {
  ChevronLeft,
  Info,
  Search,
  X,
  Plus,
  Building2,
  MapPin,
  Briefcase,
  Link2,
  ChevronDown,
  Loader2,
  UserCheck,
  ExternalLink,
  UserCircle2,
  Globe,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  useSearchLinkedIn,
  useImportLinkedInProfiles,
  useLinkedInSearchParams,
  type LinkedInProfile,
  type LinkedInSearchParams,
  type LinkedInSearchParamItem,
} from "@/lib/api/hooks/use-leads"
import { useLeadLists } from "@/lib/api/hooks/use-lead-lists"
import { cn } from "@/lib/utils"

// ── Constantes ────────────────────────────────────────────────────────

const NETWORK_OPTIONS = [
  { value: 1, label: "1º grau", description: "Conexões diretas" },
  { value: 2, label: "2º grau", description: "Conexões de conexões" },
  { value: 3, label: "3º+", description: "Demais pessoas" },
]

function networkLabel(nd: number | null): string {
  if (nd === 1) return "1º"
  if (nd === 2) return "2º"
  if (nd === 3) return "3º+"
  return ""
}

function networkBadgeClass(nd: number | null): string {
  if (nd === 1)
    return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30"
  if (nd === 2) return "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30"
  return "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30"
}

// ── Componente: Tag (chip removível) ─────────────────────────────────

function Tag({
  label,
  onRemove,
  color = "default",
}: {
  label: string
  onRemove: () => void
  color?: "default" | "blue" | "emerald" | "amber"
}) {
  const colorClasses = {
    default: "border-(--border-default) bg-(--bg-overlay) text-(--text-primary)",
    blue: "border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-400",
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        colorClasses[color],
      )}
    >
      {label}
      <button
        type="button"
        onClick={onRemove}
        className="ml-0.5 rounded-full opacity-60 transition-opacity hover:opacity-100"
        aria-label={`Remover ${label}`}
      >
        <X size={10} />
      </button>
    </span>
  )
}

// ── Componente: Input de tags livres ─────────────────────────────────

function TagInput({
  tags,
  onAdd,
  onRemove,
  placeholder,
  tagColor = "default",
}: {
  tags: string[]
  onAdd: (v: string) => void
  onRemove: (v: string) => void
  placeholder?: string
  tagColor?: "default" | "blue" | "emerald" | "amber"
}) {
  const [draft, setDraft] = useState("")

  const commit = (raw: string = draft) => {
    const val = raw.trim()
    if (val && !tags.includes(val)) onAdd(val)
    setDraft("")
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    // Adicionar imediatamente ao digitar vírgula
    if (val.endsWith(",")) {
      commit(val.slice(0, -1))
    } else {
      setDraft(val)
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex gap-1">
        <input
          value={draft}
          onChange={handleChange}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              commit()
            }
            if (e.key === "Backspace" && draft === "" && tags.length > 0) {
              const last = tags[tags.length - 1]
              if (last) onRemove(last)
            }
          }}
          onBlur={() => {
            if (draft.trim()) commit()
          }}
          placeholder={placeholder}
          className="h-8 flex-1 rounded-lg border border-(--border-default) bg-(--bg-surface) px-2.5 text-xs text-(--text-primary) placeholder:text-(--text-tertiary) focus:outline-none focus:ring-2 focus:ring-(--accent)/40 focus:border-(--accent)"
        />
        <button
          type="button"
          onClick={() => commit()}
          disabled={!draft.trim()}
          aria-label="Adicionar"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-(--border-default) text-(--text-tertiary) transition-colors hover:border-(--accent) hover:text-(--accent) disabled:opacity-30"
        >
          <Plus size={12} />
        </button>
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.map((t) => (
            <Tag key={t} label={t} onRemove={() => onRemove(t)} color={tagColor} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Componente: Typeahead com lookup de IDs (Location / Industry) ─────

function TypeaheadTagInput({
  type,
  selected,
  onAdd,
  onRemove,
  placeholder,
  tagColor = "default",
}: {
  type: "LOCATION" | "INDUSTRY"
  selected: LinkedInSearchParamItem[]
  onAdd: (item: LinkedInSearchParamItem) => void
  onRemove: (id: string) => void
  placeholder?: string
  tagColor?: "default" | "blue" | "emerald" | "amber"
}) {
  const [query, setQuery] = useState("")
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  // Busca todos os itens uma vez (Unipile ignora o query param, filtramos no cliente)
  const { data: allItems = [], isFetching } = useLinkedInSearchParams(type)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  // Filtra localmente: exclui já selecionados e aplica texto digitado
  const filteredSuggestions = allItems.filter(
    (s) =>
      !selected.some((sel) => sel.id === s.id) &&
      (query.trim() === "" || s.title.toLowerCase().includes(query.trim().toLowerCase())),
  )

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1.5">
      <div className="relative">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          placeholder={placeholder}
          className="h-8 w-full rounded-lg border border-(--border-default) bg-(--bg-surface) px-2.5 pr-7 text-xs text-(--text-primary) placeholder:text-(--text-tertiary) focus:outline-none focus:ring-2 focus:ring-(--accent)/40 focus:border-(--accent)"
        />
        {isFetching ? (
          <Loader2
            size={12}
            className="absolute right-2 top-1/2 -translate-y-1/2 animate-spin text-(--text-tertiary)"
          />
        ) : query.length > 0 ? (
          <button
            type="button"
            aria-label="Limpar busca"
            onClick={() => {
              setQuery("")
              setOpen(false)
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-(--text-tertiary) hover:text-(--text-primary)"
          >
            <X size={11} />
          </button>
        ) : null}
      </div>

      {open && filteredSuggestions.length > 0 && (
        <div className="absolute top-9 z-50 max-h-48 w-full overflow-y-auto rounded-lg border border-(--border-default) bg-(--bg-surface) py-1 shadow-xl">
          {filteredSuggestions.slice(0, 12).map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                onAdd(item)
                setQuery("")
                // Keep dropdown open for multi-select
                setTimeout(() => inputRef.current?.focus(), 0)
              }}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-(--text-primary) transition-colors hover:bg-(--accent-subtle)"
            >
              <Plus size={10} className="shrink-0 text-(--text-tertiary)" />
              {item.title}
            </button>
          ))}
        </div>
      )}

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {selected.map((item) => (
            <Tag
              key={item.id}
              label={item.title}
              onRemove={() => onRemove(item.id)}
              color={tagColor}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Componente: Checkbox group multi-select ───────────────────────────

function CheckboxGroup<T extends string | number>({
  options,
  selected,
  onToggle,
}: {
  options: { value: T; label: string; description?: string }[]
  selected: T[]
  onToggle: (v: T) => void
}) {
  return (
    <div className="flex flex-col gap-1">
      {options.map((opt) => {
        const active = selected.includes(opt.value)
        return (
          <button
            key={String(opt.value)}
            type="button"
            onClick={() => onToggle(opt.value)}
            className={cn(
              "flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-left text-xs transition-colors",
              active
                ? "border-(--accent) bg-(--accent-subtle) text-(--text-primary)"
                : "border-(--border-default) text-(--text-secondary) hover:border-(--border-strong) hover:text-(--text-primary)",
            )}
          >
            <span
              className={cn(
                "flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border transition-colors",
                active ? "border-(--accent) bg-(--accent)" : "border-(--border-default)",
              )}
            >
              {active && (
                <svg viewBox="0 0 10 10" className="h-2.5 w-2.5">
                  <path
                    d="M2 5l2.5 2.5L8 3"
                    stroke="white"
                    strokeWidth="1.5"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </span>
            <span className="font-medium">{opt.label}</span>
            {opt.description && (
              <span className="ml-auto text-[10px] text-(--text-tertiary)">{opt.description}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ── Helpers: extração de empresa do headline ─────────────────────────

function extractCompanyFromHeadline(headline: string | null): string | null {
  if (!headline) return null
  // Formatos comuns: "Cargo | Empresa", "Cargo – Empresa", "Cargo - Empresa", "Cargo @ Empresa"
  const separators = [" | ", " · ", " – ", " — ", " @ ", " at ", " na ", " em "]
  for (const sep of separators) {
    const idx = headline.indexOf(sep)
    if (idx > 0) return headline.slice(idx + sep.length).trim()
  }
  return null
}

// ── Componente: Sidebar de detalhes do lead ───────────────────────────

function LeadDetailSidebar({
  profile,
  onClose,
  onSelect,
  isSelected,
}: {
  profile: LinkedInProfile
  onClose: () => void
  onSelect: () => void
  isSelected: boolean
}) {
  const derivedCompany = profile.company ?? extractCompanyFromHeadline(profile.headline)

  return (
    <aside className="flex w-80 shrink-0 flex-col overflow-y-auto border-l border-(--border-default) bg-(--bg-surface)">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-(--border-default) px-4 py-3">
        <span className="text-xs font-semibold text-(--text-primary)">Detalhes do perfil</span>
        <button
          type="button"
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center rounded text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
          aria-label="Fechar detalhes"
        >
          <X size={14} />
        </button>
      </div>

      <div className="flex flex-col gap-5 p-5">
        {/* Avatar + nome */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-(--border-subtle) bg-(--bg-overlay) shadow-md">
            {profile.profile_picture_url ? (
              <Image
                src={profile.profile_picture_url}
                alt={profile.name}
                width={80}
                height={80}
                className="h-full w-full object-cover"
                unoptimized
              />
            ) : (
              <UserCircle2 size={36} className="text-(--text-tertiary)" />
            )}
          </div>
          <div>
            <h2 className="text-sm font-bold text-(--text-primary)">{profile.name}</h2>
            {profile.headline && (
              <p className="mt-0.5 text-xs leading-snug text-(--text-secondary)">
                {profile.headline}
              </p>
            )}
          </div>
          {profile.network_distance != null && (
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold",
                networkBadgeClass(profile.network_distance),
              )}
            >
              {networkLabel(profile.network_distance)} grau de conexão
            </span>
          )}
        </div>

        <Separator />

        {/* Detalhes */}
        <div className="flex flex-col gap-4 text-xs">
          {derivedCompany && (
            <div className="flex items-start gap-2.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-500/10">
                <Building2 size={13} className="text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wide text-(--text-tertiary)">
                  Empresa
                </p>
                <p className="mt-0.5 font-semibold text-(--text-primary)">{derivedCompany}</p>
              </div>
            </div>
          )}

          {profile.location && (
            <div className="flex items-start gap-2.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
                <MapPin size={13} className="text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wide text-(--text-tertiary)">
                  Localização
                </p>
                <p className="mt-0.5 font-semibold text-(--text-primary)">{profile.location}</p>
              </div>
            </div>
          )}

          {profile.profile_url && (
            <div className="flex items-start gap-2.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
                <Globe size={13} className="text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wide text-(--text-tertiary)">
                  LinkedIn
                </p>
                <a
                  href={profile.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-0.5 inline-flex items-center gap-1 font-medium text-(--accent) hover:underline"
                >
                  Ver perfil completo
                  <ExternalLink size={10} />
                </a>
              </div>
            </div>
          )}
        </div>

        <div className="mt-auto pt-2">
          <Button
            size="sm"
            variant={isSelected ? "outline" : "default"}
            onClick={onSelect}
            className="w-full"
          >
            <UserCheck size={13} />
            {isSelected ? "Remover seleção" : "Selecionar para importar"}
          </Button>
        </div>
      </div>
    </aside>
  )
}

// ── Componente principal ──────────────────────────────────────────────

export default function LinkedInSearchPage() {
  // ── Filtros
  const [keywords, setKeywords] = useState("")
  const [titles, setTitles] = useState<string[]>([])
  const [companies, setCompanies] = useState<string[]>([])
  const [locationItems, setLocationItems] = useState<LinkedInSearchParamItem[]>([])
  const [industryItems, setIndustryItems] = useState<LinkedInSearchParamItem[]>([])
  const [networkDistance, setNetworkDistance] = useState<number[]>([])
  const [limit, setLimit] = useState(25)

  // ── Resultados
  const [results, setResults] = useState<LinkedInProfile[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)

  // ── Seleção
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // ── Sidebar de detalhe
  const [detailProfile, setDetailProfile] = useState<LinkedInProfile | null>(null)

  // ── Import
  const [targetListId, setTargetListId] = useState<string>("__none")
  const [importResult, setImportResult] = useState<{ created: number; skipped: number } | null>(
    null,
  )

  // ── UI
  const [booleanHintOpen, setBooleanHintOpen] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const keywordsRef = useRef<HTMLTextAreaElement>(null)

  const { status: sessionStatus } = useSession()
  const { mutateAsync: searchLinkedIn, isPending: isSearching } = useSearchLinkedIn()
  const { mutateAsync: importProfiles, isPending: isImporting } = useImportLinkedInProfiles()
  const { data: lists = [] } = useLeadLists()

  // ── Filtragem client-side de network distance ─────────────────────
  // A Unipile pode retornar graus fora do filtro selecionado, então
  // filtramos no cliente para garantir consistência.
  const filteredResults = useMemo(() => {
    if (networkDistance.length === 0) return results
    return results.filter((p) => {
      if (p.network_distance == null) return true
      return networkDistance.includes(p.network_distance)
    })
  }, [results, networkDistance])

  // ── Helpers ───────────────────────────────────────────────────────

  const insertAtCursor = useCallback(
    (text: string) => {
      const el = keywordsRef.current
      if (!el) return
      const start = el.selectionStart ?? keywords.length
      const end = el.selectionEnd ?? keywords.length
      const before = keywords.slice(0, start)
      const after = keywords.slice(end)
      const sepBefore = before && !before.endsWith(" ") ? " " : ""
      const sepAfter = after && !after.startsWith(" ") ? " " : ""
      const newVal = before + sepBefore + text + sepAfter + after
      setKeywords(newVal)
      setTimeout(() => {
        el.focus()
        const pos = before.length + sepBefore.length + text.length + sepAfter.length
        el.setSelectionRange(pos, pos)
      }, 0)
    },
    [keywords],
  )

  const buildParams = useCallback(
    (nextCursor?: string | null): LinkedInSearchParams => {
      const params: LinkedInSearchParams = {
        keywords: keywords.trim() || " ",
        limit,
        ...(nextCursor ? { cursor: nextCursor } : {}),
      }
      if (titles.length > 0) params.titles = titles
      if (companies.length > 0) params.companies = companies
      if (locationItems.length > 0) params.location_ids = locationItems.map((l) => l.id)
      if (industryItems.length > 0) params.industry_ids = industryItems.map((i) => i.id)
      if (networkDistance.length > 0) params.network_distance = networkDistance
      return params
    },
    [keywords, titles, companies, locationItems, industryItems, networkDistance, limit],
  )

  const hasAnyFilter =
    keywords.trim().length > 0 ||
    titles.length > 0 ||
    companies.length > 0 ||
    locationItems.length > 0 ||
    industryItems.length > 0 ||
    networkDistance.length > 0

  const handleSearch = useCallback(async () => {
    if (!hasAnyFilter) return
    setResults([])
    setCursor(null)
    setSelectedIds(new Set())
    setImportResult(null)
    setSearchError(null)
    setHasSearched(true)
    setDetailProfile(null)
    try {
      const result = await searchLinkedIn(buildParams(null))
      setResults(result.items)
      setCursor(result.cursor)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Erro ao buscar perfis")
    }
  }, [hasAnyFilter, buildParams, searchLinkedIn])

  const handleLoadMore = useCallback(async () => {
    if (!cursor || isSearching) return
    try {
      const result = await searchLinkedIn(buildParams(cursor))
      setResults((prev) => [...prev, ...result.items])
      setCursor(result.cursor)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Erro ao carregar mais")
    }
  }, [cursor, isSearching, buildParams, searchLinkedIn])

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const toggleAll = () => {
    setSelectedIds(
      selectedIds.size === filteredResults.length
        ? new Set()
        : new Set(filteredResults.map((p) => p.provider_id)),
    )
  }

  const handleImport = async () => {
    const toImport = filteredResults.filter((p) => selectedIds.has(p.provider_id))
    const res = await importProfiles({
      profiles: toImport,
      ...(targetListId && targetListId !== "__none" ? { list_id: targetListId } : {}),
    })
    setImportResult({ created: res.created, skipped: res.skipped })
    setSelectedIds(new Set())
  }

  const toggleNetwork = (v: number) => {
    setNetworkDistance((prev) => (prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]))
  }

  const hasActiveFilters =
    titles.length > 0 ||
    companies.length > 0 ||
    locationItems.length > 0 ||
    industryItems.length > 0 ||
    networkDistance.length > 0

  const allSelected = filteredResults.length > 0 && selectedIds.size === filteredResults.length

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDetailProfile(null)
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [])

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className="flex h-full flex-col overflow-hidden bg-(--bg-canvas)">
      {/* ── Header ── */}
      <div className="flex items-center gap-3 border-b border-(--border-default) bg-(--bg-surface) px-6 py-3">
        <Link
          href="/leads"
          className="flex items-center gap-1.5 text-sm text-(--text-secondary) transition-colors hover:text-(--text-primary)"
        >
          <ChevronLeft size={15} />
          Leads
        </Link>
        <span className="text-(--border-default)">/</span>
        <h1 className="text-sm font-bold text-(--text-primary)">Busca LinkedIn</h1>
      </div>

      {/* ── Layout: filtros | resultados | detalhe ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Painel de filtros ── */}
        <aside className="flex w-70 shrink-0 flex-col overflow-y-auto border-r border-(--border-default) bg-(--bg-surface)">
          {/* Seção: Palavras-chave */}
          <div className="border-b border-(--border-subtle) p-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-5 w-5 items-center justify-center rounded bg-violet-500/10">
                <Search size={10} className="text-violet-600 dark:text-violet-400" />
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-secondary)">
                Palavras-chave
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-1">
                {["AND", "OR", "NOT"].map((op) => (
                  <button
                    key={op}
                    type="button"
                    onClick={() => insertAtCursor(op)}
                    className="rounded-md border border-(--border-default) bg-(--bg-canvas) px-1.5 py-0.5 font-mono text-[10px] font-bold text-(--text-secondary) transition-colors hover:border-violet-400 hover:text-violet-600 dark:hover:text-violet-400"
                  >
                    {op}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => insertAtCursor('"frase exata"')}
                  className="rounded-md border border-(--border-default) bg-(--bg-canvas) px-1.5 py-0.5 font-mono text-[10px] font-medium text-(--text-secondary) transition-colors hover:border-violet-400 hover:text-violet-600 dark:hover:text-violet-400"
                >
                  &quot;frase exata&quot;
                </button>
                <button
                  type="button"
                  onClick={() => insertAtCursor("()")}
                  className="rounded-md border border-(--border-default) bg-(--bg-canvas) px-1.5 py-0.5 font-mono text-[10px] font-medium text-(--text-secondary) transition-colors hover:border-violet-400 hover:text-violet-600 dark:hover:text-violet-400"
                >
                  ( )
                </button>
              </div>
              <textarea
                ref={keywordsRef}
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void handleSearch()
                }}
                placeholder={'"gerente de TI" AND (startup OR PME)'}
                rows={3}
                className="w-full resize-none rounded-lg border border-(--border-default) bg-(--bg-canvas) px-2.5 py-2 font-mono text-xs text-(--text-primary) placeholder:text-(--text-tertiary) focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400"
              />
              <button
                type="button"
                onClick={() => setBooleanHintOpen((o) => !o)}
                className="flex items-center gap-1 text-[11px] text-(--text-tertiary) transition-colors hover:text-(--text-secondary)"
              >
                <Info size={11} />
                Como usar busca booleana
                <ChevronDown
                  size={11}
                  className={cn("ml-auto transition-transform", booleanHintOpen && "rotate-180")}
                />
              </button>
              {booleanHintOpen && (
                <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-2.5 text-[11px] leading-relaxed text-(--text-secondary)">
                  <ul className="space-y-0.5">
                    <li>
                      <code className="font-mono font-bold text-violet-600 dark:text-violet-400">
                        AND
                      </code>{" "}
                      — todos os termos
                    </li>
                    <li>
                      <code className="font-mono font-bold text-violet-600 dark:text-violet-400">
                        OR
                      </code>{" "}
                      — qualquer dos termos
                    </li>
                    <li>
                      <code className="font-mono font-bold text-violet-600 dark:text-violet-400">
                        NOT
                      </code>{" "}
                      — excluir termo
                    </li>
                    <li>
                      <code className="font-mono font-bold text-violet-600 dark:text-violet-400">
                        &quot;texto&quot;
                      </code>{" "}
                      — frase exata
                    </li>
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Seção: Cargo */}
          <div className="border-b border-(--border-subtle) p-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-5 w-5 items-center justify-center rounded bg-blue-500/10">
                <Briefcase size={10} className="text-blue-600 dark:text-blue-400" />
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-secondary)">
                Cargo
              </p>
            </div>
            <TagInput
              tags={titles}
              onAdd={(v) => setTitles((p) => [...p, v])}
              onRemove={(v) => setTitles((p) => p.filter((x) => x !== v))}
              placeholder="Ex: CTO, Diretor de TI"
              tagColor="blue"
            />
          </div>

          {/* Seção: Empresa */}
          <div className="border-b border-(--border-subtle) p-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-5 w-5 items-center justify-center rounded bg-indigo-500/10">
                <Building2 size={10} className="text-indigo-600 dark:text-indigo-400" />
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-secondary)">
                Empresa
              </p>
            </div>
            <TagInput
              tags={companies}
              onAdd={(v) => setCompanies((p) => [...p, v])}
              onRemove={(v) => setCompanies((p) => p.filter((x) => x !== v))}
              placeholder="Ex: Nubank, iFood"
            />
          </div>

          {/* Seção: Localização */}
          <div className="border-b border-(--border-subtle) p-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-5 w-5 items-center justify-center rounded bg-emerald-500/10">
                <MapPin size={10} className="text-emerald-600 dark:text-emerald-400" />
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-secondary)">
                Localização
              </p>
            </div>
            <TypeaheadTagInput
              type="LOCATION"
              selected={locationItems}
              onAdd={(item) => setLocationItems((p) => [...p, item])}
              onRemove={(id) => setLocationItems((p) => p.filter((x) => x.id !== id))}
              placeholder="Clique para ver opções"
              tagColor="emerald"
            />
          </div>

          {/* Seção: Setor */}
          <div className="border-b border-(--border-subtle) p-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-5 w-5 items-center justify-center rounded bg-amber-500/10">
                <Globe size={10} className="text-amber-600 dark:text-amber-400" />
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-secondary)">
                Setor
              </p>
            </div>
            <TypeaheadTagInput
              type="INDUSTRY"
              selected={industryItems}
              onAdd={(item) => setIndustryItems((p) => [...p, item])}
              onRemove={(id) => setIndustryItems((p) => p.filter((x) => x.id !== id))}
              placeholder="Clique para ver opções"
              tagColor="amber"
            />
          </div>

          {/* Seção: Grau de conexão */}
          <div className="border-b border-(--border-subtle) p-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-5 w-5 items-center justify-center rounded bg-rose-500/10">
                <UserCheck size={10} className="text-rose-600 dark:text-rose-400" />
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-secondary)">
                Grau de conexão
              </p>
            </div>
            <CheckboxGroup
              options={NETWORK_OPTIONS}
              selected={networkDistance}
              onToggle={toggleNetwork}
            />
          </div>

          {/* Seção: Ações */}
          <div className="mt-auto border-t border-(--border-default) bg-(--bg-canvas) p-4">
            <div className="mb-3 flex items-center justify-between">
              <Label className="text-[10px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                Resultados
              </Label>
              <Select value={String(limit)} onValueChange={(v) => setLimit(Number(v))}>
                <SelectTrigger className="h-7 w-24 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[10, 25, 50, 100].map((n) => (
                    <SelectItem key={n} value={String(n)} className="text-xs">
                      {n} perfis
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={() => void handleSearch()}
              disabled={!hasAnyFilter || isSearching || sessionStatus !== "authenticated"}
              className="w-full"
              size="sm"
            >
              {isSearching ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Buscando…
                </>
              ) : (
                <>
                  <Search size={14} />
                  Buscar
                </>
              )}
            </Button>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={() => {
                  setTitles([])
                  setCompanies([])
                  setLocationItems([])
                  setIndustryItems([])
                  setNetworkDistance([])
                }}
                className="mt-2 flex w-full items-center justify-center gap-1 text-[11px] text-(--text-tertiary) hover:text-(--text-secondary)"
              >
                <X size={10} />
                Limpar filtros
              </button>
            )}
          </div>
        </aside>

        {/* ── Área de resultados ── */}
        <main className="flex flex-1 flex-col overflow-hidden">
          {/* Banner de erro */}
          {searchError && (
            <div className="flex items-center justify-between border-b border-(--border-subtle) bg-red-500/10 px-5 py-2 text-xs">
              <span className="text-red-700 dark:text-red-400">{searchError}</span>
              <button
                type="button"
                aria-label="Fechar erro"
                onClick={() => setSearchError(null)}
                className="text-(--text-tertiary) hover:text-(--text-primary)"
              >
                <X size={13} />
              </button>
            </div>
          )}

          {/* Barra de ações */}
          {hasSearched && (
            <div className="flex flex-wrap items-center gap-3 border-b border-(--border-default) bg-(--bg-canvas) px-5 py-2.5 text-xs">
              {filteredResults.length > 0 && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="select-all"
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="Selecionar todos"
                    className="h-4 w-4 cursor-pointer rounded border-gray-300 accent-(--accent)"
                  />
                  <label htmlFor="select-all" className="cursor-pointer text-(--text-secondary)">
                    {allSelected ? "Desmarcar todos" : "Selecionar todos"}
                  </label>
                </div>
              )}

              {selectedIds.size > 0 && (
                <>
                  <Separator orientation="vertical" className="h-4" />
                  <span className="text-(--text-secondary)">
                    <span className="font-medium text-(--text-primary)">{selectedIds.size}</span>{" "}
                    selecionado{selectedIds.size !== 1 ? "s" : ""}
                  </span>
                  <Separator orientation="vertical" className="h-4" />
                  <Select value={targetListId} onValueChange={setTargetListId}>
                    <SelectTrigger className="h-7 w-44 text-xs">
                      <SelectValue placeholder="Sem lista" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none" className="text-xs">
                        Sem lista
                      </SelectItem>
                      {lists.map((l) => (
                        <SelectItem key={l.id} value={l.id} className="text-xs">
                          {l.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    size="sm"
                    onClick={() => void handleImport()}
                    disabled={isImporting}
                    className="h-7 text-xs"
                  >
                    {isImporting ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <UserCheck size={12} />
                    )}
                    Importar {selectedIds.size}
                  </Button>
                </>
              )}

              <div className="ml-auto text-(--text-tertiary)">
                {filteredResults.length} resultado{filteredResults.length !== 1 ? "s" : ""}
                {networkDistance.length > 0 && filteredResults.length !== results.length && (
                  <span className="ml-1 text-(--text-tertiary)">
                    (filtrado de {results.length})
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Banner de import bem-sucedido */}
          {importResult && (
            <div className="flex items-center justify-between border-b border-(--border-subtle) bg-green-500/10 px-5 py-2 text-xs">
              <span className="text-green-700 dark:text-green-400">
                <span className="font-medium">{importResult.created}</span> lead
                {importResult.created !== 1 ? "s" : ""} importado
                {importResult.created !== 1 ? "s" : ""}
                {importResult.skipped > 0 && (
                  <>
                    , <span className="font-medium">{importResult.skipped}</span> já existia
                    {importResult.skipped !== 1 ? "m" : ""}
                  </>
                )}
              </span>
              <button
                type="button"
                aria-label="Fechar notificação"
                onClick={() => setImportResult(null)}
                className="text-(--text-tertiary) hover:text-(--text-primary)"
              >
                <X size={13} />
              </button>
            </div>
          )}

          {/* Lista de resultados */}
          <div className="flex-1 overflow-y-auto">
            {/* Estado inicial */}
            {!hasSearched && (
              <div className="flex flex-col items-center justify-center gap-4 py-28">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-500/10">
                  <Search size={28} strokeWidth={1.5} className="text-violet-500" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-(--text-primary)">
                    Busque profissionais no LinkedIn
                  </p>
                  <p className="mt-1 max-w-sm text-xs leading-relaxed text-(--text-tertiary)">
                    Use os filtros ao lado para encontrar leads. Combine palavras-chave, cargos,
                    localização e grau de conexão.
                  </p>
                </div>
                <kbd className="rounded-lg border border-(--border-default) bg-(--bg-surface) px-2.5 py-1 font-mono text-[11px] text-(--text-tertiary)">
                  Ctrl+Enter para buscar
                </kbd>
              </div>
            )}

            {/* Sem resultados */}
            {hasSearched && !isSearching && filteredResults.length === 0 && (
              <div className="flex flex-col items-center justify-center gap-3 py-28">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10">
                  <Search size={24} strokeWidth={1.5} className="text-amber-500" />
                </div>
                <p className="text-sm font-medium text-(--text-primary)">
                  Nenhum resultado encontrado
                </p>
                <p className="text-xs text-(--text-tertiary)">
                  Tente ampliar os filtros ou alterar as palavras-chave
                </p>
              </div>
            )}

            {/* Resultados */}
            {filteredResults.length > 0 && (
              <div className="divide-y divide-(--border-subtle)">
                {filteredResults.map((profile) => {
                  const isSelected = selectedIds.has(profile.provider_id)
                  const isActive = detailProfile?.provider_id === profile.provider_id
                  const rowCompany = profile.company ?? extractCompanyFromHeadline(profile.headline)
                  return (
                    <div
                      key={profile.provider_id}
                      onClick={() => setDetailProfile(isActive ? null : profile)}
                      className={cn(
                        "flex cursor-pointer items-center gap-3.5 px-5 py-3.5 transition-all",
                        isActive
                          ? "bg-(--accent-subtle) border-l-2 border-l-(--accent)"
                          : isSelected
                            ? "bg-(--bg-overlay) border-l-2 border-l-transparent"
                            : "border-l-2 border-l-transparent hover:bg-(--bg-overlay)",
                      )}
                    >
                      {/* Checkbox */}
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          e.stopPropagation()
                          toggleSelect(profile.provider_id)
                        }}
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`Selecionar ${profile.name}`}
                        className="h-4 w-4 cursor-pointer rounded border-gray-300 accent-(--accent)"
                      />

                      {/* Avatar */}
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-(--border-subtle) bg-(--bg-overlay)">
                        {profile.profile_picture_url ? (
                          <Image
                            src={profile.profile_picture_url}
                            alt={profile.name}
                            width={40}
                            height={40}
                            className="h-full w-full object-cover"
                            unoptimized
                          />
                        ) : (
                          <span className="text-sm font-semibold text-(--text-tertiary)">
                            {profile.name.charAt(0).toUpperCase()}
                          </span>
                        )}
                      </div>

                      {/* Informações */}
                      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-[13px] font-semibold text-(--text-primary)">
                            {profile.name}
                          </span>
                          {profile.network_distance != null && (
                            <Badge
                              variant="outline"
                              className={cn(
                                "shrink-0 rounded-full px-1.5 py-px text-[10px] font-semibold leading-none",
                                networkBadgeClass(profile.network_distance),
                              )}
                            >
                              {networkLabel(profile.network_distance)}
                            </Badge>
                          )}
                        </div>
                        {profile.headline && (
                          <span className="truncate text-xs text-(--text-secondary)">
                            {profile.headline}
                          </span>
                        )}
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                          {rowCompany && (
                            <span className="flex items-center gap-1 text-[11px] text-(--text-tertiary)">
                              <Building2 size={10} />
                              {rowCompany}
                            </span>
                          )}
                          {profile.location && (
                            <span className="flex items-center gap-1 text-[11px] text-(--text-tertiary)">
                              <MapPin size={10} />
                              {profile.location}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Link externo */}
                      {profile.profile_url && (
                        <span
                          role="link"
                          tabIndex={0}
                          onClick={(e) => {
                            e.stopPropagation()
                            window.open(profile.profile_url ?? "", "_blank", "noopener,noreferrer")
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.stopPropagation()
                              window.open(
                                profile.profile_url ?? "",
                                "_blank",
                                "noopener,noreferrer",
                              )
                            }
                          }}
                          className="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded-md text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                          aria-label={`Abrir perfil de ${profile.name} no LinkedIn`}
                        >
                          <Link2 size={13} />
                        </span>
                      )}
                    </div>
                  )
                })}

                {/* Carregar mais */}
                {cursor && (
                  <div className="flex justify-center py-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void handleLoadMore()}
                      disabled={isSearching}
                    >
                      {isSearching ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : (
                        <Plus size={13} />
                      )}
                      Carregar mais
                    </Button>
                  </div>
                )}

                {!cursor && filteredResults.length > 0 && (
                  <p className="py-4 text-center text-xs text-(--text-tertiary)">
                    Fim dos resultados — {filteredResults.length} perfil
                    {filteredResults.length !== 1 ? "is" : ""} carregado
                    {filteredResults.length !== 1 ? "s" : ""}
                  </p>
                )}
              </div>
            )}
          </div>
        </main>

        {/* ── Sidebar de detalhes do lead ── */}
        {detailProfile && (
          <LeadDetailSidebar
            profile={detailProfile}
            onClose={() => setDetailProfile(null)}
            onSelect={() => toggleSelect(detailProfile.provider_id)}
            isSelected={selectedIds.has(detailProfile.provider_id)}
          />
        )}
      </div>
    </div>
  )
}
