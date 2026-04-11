"use client"

import { useEffect, useMemo, useState } from "react"
import {
  Loader2,
  Play,
  AlertCircle,
  Search,
  MessageSquareText,
  Users,
  BookOpen,
  Plus,
  X,
  History,
  SlidersHorizontal,
  FileText,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  MessageCircle,
  Repeat2,
  BookmarkCheck,
  ThumbsUp,
  Globe,
  Copy,
  Upload,
  Layers3,
  Trash2,
} from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { HookBadge, PillarBadge } from "@/components/content/post-badges"
import { useContentThemes, type ContentTheme } from "@/lib/api/hooks/use-content"
import { cn } from "@/lib/utils"
import { PostReferenceCard } from "./post-reference-card"
import { IcpPostCard } from "./icp-post-card"
import { LinkedPostSelector } from "./linked-post-selector"
import {
  engagementKeys,
  useComposeGoogleDiscoveryQueries,
  useDeleteEngagementPost,
  useImportExternalPosts,
  useEngagementPosts,
  useEngagementSession,
  useEngagementSessions,
  useGoogleDiscoveryHistory,
  useRunScan,
  useUnmarkCommentPosted,
} from "@/lib/api/hooks/use-content-engagement"
import type {
  EngagementPost,
  EngagementSession,
  EngagementSessionDetail,
  GoogleDiscoveryQuery,
  ImportExternalPostsResponse,
  SessionStatus,
} from "@/lib/content-engagement/types"
import type { EngagementComment } from "@/lib/content-engagement/types"
import { toast } from "sonner"

// ── Skeleton do scan em andamento ─────────────────────────────────────────────

const STEP_LABELS: Record<number, string> = {
  1: "Buscando posts de referência...",
  2: "Buscando posts de decisores ICP...",
  3: "Analisando posts com IA...",
  4: "Gerando sugestões de comentários...",
}

const STEP_PROGRESS_WIDTH: Record<number, string> = {
  1: "w-1/4",
  2: "w-1/2",
  3: "w-3/4",
  4: "w-full",
}

const HISTORY_PAGE_SIZE = 8

const STATUS_META: Record<SessionStatus, { label: string; className: string }> = {
  running: {
    label: "Em andamento",
    className: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
  },
  completed: {
    label: "Concluído",
    className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  },
  partial: {
    label: "Parcial",
    className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  },
  failed: {
    label: "Falhou",
    className: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  },
}

function formatHistoryDate(value: string) {
  return new Date(value).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function formatLinkedPostLabel(linkedPostId: string | null) {
  if (!linkedPostId) return "Sem vínculo"
  return `Post ${linkedPostId.slice(0, 8)}`
}

function formatScanSourceLabel(scanSource: EngagementSession["scan_source"]) {
  if (scanSource === "apify") return "Scanner LinkedIn"
  if (scanSource === "linkedin_api") return "LinkedIn API"
  return "Manual"
}

function formatPostSourceLabel(source: string) {
  if (source === "apify") return "Scanner"
  if (source === "linkedin_api") return "API"
  if (source === "google") return "Google"
  return "Manual"
}

function formatMergedSourcesLabel(sources: string[] | null | undefined) {
  const normalized = (sources ?? []).map((source) => formatPostSourceLabel(source))
  return normalized.join(" + ")
}

function getPostSourceBadgeClass(source: string) {
  if (source === "google") {
    return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200"
  }
  if (source === "manual") {
    return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
  }
  if (source === "linkedin_api") {
    return "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
  }
  return "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
}

function formatSessionEventLabel(eventType: string) {
  const labels: Record<string, string> = {
    scan_requested: "Scan solicitado",
    queue_pickup_started: "Worker iniciou",
    reference_search_completed: "Referências capturadas",
    icp_search_completed: "ICP capturados",
    comments_generated: "Comentários gerados",
    external_posts_imported: "Posts externos importados",
    scan_completed: "Scan concluído",
    scan_failed: "Scan falhou",
    comment_posted: "Comentário marcado como postado",
    comment_unposted: "Comentário desfeito",
  }

  return labels[eventType] ?? eventType
}

function splitCriteriaInput(value: string) {
  const items = value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean)

  const deduped: string[] = []
  const seen = new Set<string>()

  for (const item of items) {
    const normalized = item.toLowerCase()
    if (seen.has(normalized)) continue
    seen.add(normalized)
    deduped.push(item)
  }

  return deduped
}

function mergeUniqueItems(...groups: string[][]) {
  const merged: string[] = []
  const seen = new Set<string>()

  for (const group of groups) {
    for (const item of group) {
      const normalized = item.trim().toLowerCase()
      if (!normalized || seen.has(normalized)) continue
      seen.add(normalized)
      merged.push(item.trim())
    }
  }

  return merged
}

function readCriteriaList(criteria: Record<string, unknown> | null, key: string) {
  const value = criteria?.[key]
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : []
}

function readCriteriaString(criteria: Record<string, unknown> | null, key: string) {
  const value = criteria?.[key]
  return typeof value === "string" && value.trim() ? value.trim() : null
}

function formatGoogleCriteriaSummary(query: GoogleDiscoveryQuery) {
  const keywords = readCriteriaList(query.criteria, "keywords")
  const titles = readCriteriaList(query.criteria, "titles")
  const sectors = readCriteriaList(query.criteria, "sectors")
  const parts: string[] = []

  if (keywords.length > 0)
    parts.push(`${keywords.length} keyword${keywords.length !== 1 ? "s" : ""}`)
  if (titles.length > 0) parts.push(`${titles.length} cargo${titles.length !== 1 ? "s" : ""}`)
  if (sectors.length > 0) parts.push(`${sectors.length} setor${sectors.length !== 1 ? "es" : ""}`)

  return parts.join(" • ") || "Critérios livres"
}

function summarizeSessionCriteria(session: EngagementSession) {
  const parts: string[] = []
  const themeCount = session.selected_theme_titles?.length ?? 0
  const keywordCount = session.effective_keywords?.length ?? 0
  const titlesCount = session.icp_titles_used?.length ?? 0
  const sectorsCount = session.icp_sectors_used?.length ?? 0

  if (themeCount > 0) parts.push(`${themeCount} tema${themeCount !== 1 ? "s" : ""}`)
  if (keywordCount > 0) parts.push(`${keywordCount} keyword${keywordCount !== 1 ? "s" : ""}`)
  if (titlesCount > 0 || sectorsCount > 0) {
    parts.push(
      `${titlesCount} cargo${titlesCount !== 1 ? "s" : ""} / ${sectorsCount} setor${sectorsCount !== 1 ? "es" : ""}`,
    )
  }

  return parts.length > 0 ? parts.join(" • ") : "Configuração padrão"
}

function SessionStatusBadge({ status }: { status: SessionStatus }) {
  const meta = STATUS_META[status]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold",
        meta.className,
      )}
    >
      {status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
      {meta.label}
    </span>
  )
}

function ActiveConfigurationSummary({
  linkedPostId,
  selectedThemesCount,
  manualKeywordsCount,
  icpTitlesCount,
  icpSectorsCount,
  effectiveKeywords,
}: {
  linkedPostId: string | null
  selectedThemesCount: number
  manualKeywordsCount: number
  icpTitlesCount: number
  icpSectorsCount: number
  effectiveKeywords: string[]
}) {
  const hasConfiguration =
    !!linkedPostId || effectiveKeywords.length > 0 || icpTitlesCount > 0 || icpSectorsCount > 0

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) px-5 py-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">Configuração ativa</p>
          <p className="mt-0.5 text-xs text-(--text-secondary)">
            {hasConfiguration
              ? "O próximo scan vai usar os filtros e contexto abaixo."
              : "Nenhum filtro extra aplicado. O próximo scan usará a estratégia padrão."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] font-medium text-(--text-secondary)">
          <span className="inline-flex items-center gap-1 rounded-full bg-(--bg-overlay) px-2.5 py-1">
            <FileText className="h-3 w-3" />
            {linkedPostId ? "Post vinculado" : "Sem post vinculado"}
          </span>
          <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1">
            {selectedThemesCount} tema{selectedThemesCount !== 1 ? "s" : ""}
          </span>
          <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1">
            {manualKeywordsCount} keyword{manualKeywordsCount !== 1 ? "s" : ""} manual
            {manualKeywordsCount !== 1 ? "s" : ""}
          </span>
          <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1">
            {icpTitlesCount} cargo{icpTitlesCount !== 1 ? "s" : ""} ICP
          </span>
          <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1">
            {icpSectorsCount} setor{icpSectorsCount !== 1 ? "es" : ""} ICP
          </span>
        </div>
      </div>

      {effectiveKeywords.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {effectiveKeywords.slice(0, 6).map((keyword) => (
            <span
              key={keyword}
              className="inline-flex items-center rounded-full border border-(--border-default) bg-(--bg-sunken) px-2.5 py-1 text-xs text-(--text-secondary)"
            >
              {keyword}
            </span>
          ))}
          {effectiveKeywords.length > 6 && (
            <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-tertiary)">
              +{effectiveKeywords.length - 6}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function TokenListInput({
  label,
  placeholder,
  inputValue,
  onInputChange,
  onInputKeyDown,
  onAdd,
  items,
  onRemove,
  disabled,
}: {
  label: string
  placeholder: string
  inputValue: string
  onInputChange: (value: string) => void
  onInputKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void
  onAdd: () => void
  items: string[]
  onRemove: (item: string) => void
  disabled: boolean
}) {
  return (
    <div className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
        {label}
      </p>
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={onInputKeyDown}
          placeholder={placeholder}
          disabled={disabled}
        />
        <Button
          type="button"
          variant="outline"
          className="gap-1.5"
          onClick={onAdd}
          disabled={disabled || !inputValue.trim()}
        >
          <Plus className="h-3.5 w-3.5" />
          Adicionar
        </Button>
      </div>
      {items.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {items.map((item) => (
            <span
              key={`${label}-${item}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-(--border-default) bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-secondary)"
            >
              {item}
              <button
                type="button"
                className="rounded-full p-0.5 text-(--text-tertiary) transition hover:bg-(--bg-sunken) hover:text-(--text-primary)"
                onClick={() => onRemove(item)}
                aria-label={`Remover ${item}`}
                title={`Remover ${item}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function PostOriginBadges({ post }: { post: EngagementPost }) {
  const mergedSourcesLabel = formatMergedSourcesLabel(post.merged_sources)

  return (
    <>
      <span
        className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold",
          getPostSourceBadgeClass(post.source),
        )}
      >
        {formatPostSourceLabel(post.source)}
      </span>
      {post.merge_count > 1 && (
        <span
          className="inline-flex items-center gap-1 rounded-full bg-(--bg-overlay) px-2 py-0.5 text-[10px] font-semibold text-(--text-secondary)"
          title={mergedSourcesLabel || undefined}
        >
          <Layers3 className="h-3 w-3" />
          Mesclado x{post.merge_count}
        </span>
      )}
    </>
  )
}

interface ExternalImportSeed {
  source: "google" | "manual"
  postType: "icp" | "reference"
  payload: string
  contextLabel: string | null
  discoveryQueryId: string | null
}

function buildGoogleImportSeed({
  keywords,
  titles,
  sectors,
  exactPhrases,
  company,
  queryText,
  discoveryQueryId,
}: {
  keywords: string[]
  titles: string[]
  sectors: string[]
  exactPhrases?: string[]
  company?: string | null
  queryText?: string | null
  discoveryQueryId?: string | null
}): ExternalImportSeed {
  const normalizedKeywords = mergeUniqueItems(keywords)
  const normalizedTitles = mergeUniqueItems(titles)
  const normalizedSectors = mergeUniqueItems(sectors)
  const normalizedPhrases = mergeUniqueItems(exactPhrases ?? [])
  const normalizedCompany = company?.trim() || null
  const payload = JSON.stringify(
    [
      {
        post_url: null,
        author_name: null,
        author_title: normalizedTitles[0] ?? null,
        author_company: normalizedCompany,
        post_text: "",
        likes: 0,
        comments: 0,
        shares: 0,
      },
    ],
    null,
    2,
  )

  const contextParts: string[] = []
  if (queryText) contextParts.push(`query \"${queryText}\"`)
  if (normalizedKeywords.length > 0) {
    contextParts.push(
      `${normalizedKeywords.length} keyword${normalizedKeywords.length !== 1 ? "s" : ""}`,
    )
  }
  if (normalizedTitles.length > 0) {
    contextParts.push(`${normalizedTitles.length} cargo${normalizedTitles.length !== 1 ? "s" : ""}`)
  }
  if (normalizedSectors.length > 0) {
    contextParts.push(
      `${normalizedSectors.length} setor${normalizedSectors.length !== 1 ? "es" : ""}`,
    )
  }
  if (normalizedPhrases.length > 0) {
    contextParts.push(
      `${normalizedPhrases.length} frase${normalizedPhrases.length !== 1 ? "s" : ""}`,
    )
  }

  return {
    source: "google",
    postType: "icp",
    payload,
    contextLabel: contextParts.length > 0 ? contextParts.join(" • ") : null,
    discoveryQueryId: discoveryQueryId ?? null,
  }
}

function ScanConfigurationPanel({
  linkedPostId,
  onLinkedPostChange,
  themes,
  selectedThemeIds,
  onToggleTheme,
  keywordInput,
  onKeywordInputChange,
  onKeywordInputKeyDown,
  onAddKeyword,
  manualKeywords,
  onRemoveKeyword,
  icpTitleInput,
  onIcpTitleInputChange,
  onIcpTitleInputKeyDown,
  onAddIcpTitle,
  icpTitles,
  onRemoveIcpTitle,
  icpSectorInput,
  onIcpSectorInputChange,
  onIcpSectorInputKeyDown,
  onAddIcpSector,
  icpSectors,
  onRemoveIcpSector,
  effectiveKeywords,
  disabled,
}: {
  linkedPostId: string | null
  onLinkedPostChange: (postId: string | null) => void
  themes: ContentTheme[]
  selectedThemeIds: string[]
  onToggleTheme: (themeId: string) => void
  keywordInput: string
  onKeywordInputChange: (value: string) => void
  onKeywordInputKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void
  onAddKeyword: () => void
  manualKeywords: string[]
  onRemoveKeyword: (keyword: string) => void
  icpTitleInput: string
  onIcpTitleInputChange: (value: string) => void
  onIcpTitleInputKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void
  onAddIcpTitle: () => void
  icpTitles: string[]
  onRemoveIcpTitle: (value: string) => void
  icpSectorInput: string
  onIcpSectorInputChange: (value: string) => void
  onIcpSectorInputKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void
  onAddIcpSector: () => void
  icpSectors: string[]
  onRemoveIcpSector: (value: string) => void
  effectiveKeywords: string[]
  disabled: boolean
}) {
  return (
    <div className="space-y-4">
      <LinkedPostSelector value={linkedPostId} onChange={onLinkedPostChange} disabled={disabled} />

      <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-(--text-primary)">Configuração do scan</p>
            <p className="text-xs text-(--text-secondary) mt-0.5">
              Selecione temas do banco e adicione palavras-chave manuais para deixar a busca mais
              precisa.
            </p>
          </div>
          {effectiveKeywords.length > 0 && (
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-[11px] font-medium text-(--text-secondary)">
              {effectiveKeywords.length} keyword{effectiveKeywords.length !== 1 ? "s" : ""} ativa
              {effectiveKeywords.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
            Temas do banco
          </p>
          <div className="flex max-h-52 flex-wrap gap-2 overflow-y-auto pr-1">
            {themes.map((theme) => {
              const isSelected = selectedThemeIds.includes(theme.id)
              return (
                <button
                  key={theme.id}
                  type="button"
                  onClick={() => onToggleTheme(theme.id)}
                  disabled={disabled}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition-colors",
                    isSelected
                      ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                      : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--accent)",
                    theme.used && !isSelected && "opacity-70",
                  )}
                >
                  <PillarBadge pillar={theme.pillar} className="px-1.5 py-0 text-[10px]" />
                  <span>{theme.title}</span>
                </button>
              )
            })}
          </div>
        </div>

        <TokenListInput
          label="Palavras-chave manuais"
          placeholder="Ex.: automação comercial, ERP, IA aplicada"
          inputValue={keywordInput}
          onInputChange={onKeywordInputChange}
          onInputKeyDown={onKeywordInputKeyDown}
          onAdd={onAddKeyword}
          items={manualKeywords}
          onRemove={onRemoveKeyword}
          disabled={disabled}
        />

        <div className="grid gap-4 xl:grid-cols-2">
          <TokenListInput
            label="Cargos ICP"
            placeholder="Ex.: CEO, COO, Diretor de TI"
            inputValue={icpTitleInput}
            onInputChange={onIcpTitleInputChange}
            onInputKeyDown={onIcpTitleInputKeyDown}
            onAdd={onAddIcpTitle}
            items={icpTitles}
            onRemove={onRemoveIcpTitle}
            disabled={disabled}
          />
          <TokenListInput
            label="Setores ICP"
            placeholder="Ex.: Tecnologia, Saúde, Logística"
            inputValue={icpSectorInput}
            onInputChange={onIcpSectorInputChange}
            onInputKeyDown={onIcpSectorInputKeyDown}
            onAdd={onAddIcpSector}
            items={icpSectors}
            onRemove={onRemoveIcpSector}
            disabled={disabled}
          />
        </div>

        {effectiveKeywords.length > 0 && (
          <div className="rounded-lg border border-(--border-default) bg-(--bg-sunken) px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
              Busca efetiva desta execução
            </p>
            <p className="mt-1 text-sm text-(--text-secondary)">{effectiveKeywords.join(" • ")}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function GoogleDiscoveryDialog({
  open,
  onOpenChange,
  defaultKeywords,
  defaultTitles,
  defaultSectors,
  linkedPostId,
  onApplyCriteria,
  onSeedImportPayload,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultKeywords: string[]
  defaultTitles: string[]
  defaultSectors: string[]
  linkedPostId: string | null
  onApplyCriteria: (criteria: { keywords: string[]; titles: string[]; sectors: string[] }) => void
  onSeedImportPayload: (seed: ExternalImportSeed) => void
}) {
  const composeGoogleQueries = useComposeGoogleDiscoveryQueries()
  const { data: history = [], isLoading: isHistoryLoading } = useGoogleDiscoveryHistory(12)
  const [keywordsText, setKeywordsText] = useState("")
  const [exactPhrasesText, setExactPhrasesText] = useState("comentários")
  const [titlesText, setTitlesText] = useState("")
  const [sectorsText, setSectorsText] = useState("")
  const [company, setCompany] = useState("")

  useEffect(() => {
    if (!open) return
    setKeywordsText(defaultKeywords.join("\n"))
    setTitlesText(defaultTitles.join("\n"))
    setSectorsText(defaultSectors.join("\n"))
    setExactPhrasesText("comentários")
    setCompany("")
  }, [defaultKeywords, defaultSectors, defaultTitles, open])

  async function handleCompose() {
    const keywords = splitCriteriaInput(keywordsText)
    if (keywords.length === 0) {
      toast.error("Informe pelo menos uma keyword para compor as buscas")
      return
    }

    try {
      await composeGoogleQueries.mutateAsync({
        keywords,
        exact_phrases: splitCriteriaInput(exactPhrasesText),
        titles: splitCriteriaInput(titlesText),
        sectors: splitCriteriaInput(sectorsText),
        company: company.trim() || null,
        linked_post_id: linkedPostId,
      })
    } catch {
      toast.error("Não foi possível compor as buscas do Google")
    }
  }

  async function handleCopy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      toast.success("Consulta copiada")
    } catch {
      toast.error("Não foi possível copiar a consulta")
    }
  }

  async function handleCopyBatch(queries: GoogleDiscoveryQuery[]) {
    try {
      await navigator.clipboard.writeText(queries.map((query) => query.query_text).join("\n"))
      toast.success("Bloco de consultas copiado")
    } catch {
      toast.error("Não foi possível copiar as consultas")
    }
  }

  function applyCurrentCriteria() {
    onApplyCriteria({
      keywords: splitCriteriaInput(keywordsText),
      titles: splitCriteriaInput(titlesText),
      sectors: splitCriteriaInput(sectorsText),
    })
    onOpenChange(false)
    toast.success("Critérios aplicados ao próximo scan")
  }

  function applyHistoryCriteria(query: GoogleDiscoveryQuery) {
    onApplyCriteria({
      keywords: readCriteriaList(query.criteria, "keywords"),
      titles: readCriteriaList(query.criteria, "titles"),
      sectors: readCriteriaList(query.criteria, "sectors"),
    })
    onOpenChange(false)
    toast.success("Critérios do histórico aplicados ao scan")
  }

  function seedImporterFromCurrentCriteria() {
    onSeedImportPayload(
      buildGoogleImportSeed({
        keywords: splitCriteriaInput(keywordsText),
        titles: splitCriteriaInput(titlesText),
        sectors: splitCriteriaInput(sectorsText),
        exactPhrases: splitCriteriaInput(exactPhrasesText),
        company,
      }),
    )
    onOpenChange(false)
    toast.success("Payload-base enviado ao importador")
  }

  function seedImporterFromHistory(query: GoogleDiscoveryQuery) {
    onSeedImportPayload(
      buildGoogleImportSeed({
        queryText: query.query_text,
        discoveryQueryId: query.id,
        keywords: readCriteriaList(query.criteria, "keywords"),
        titles: readCriteriaList(query.criteria, "titles"),
        sectors: readCriteriaList(query.criteria, "sectors"),
        exactPhrases: readCriteriaList(query.criteria, "exact_phrases"),
        company: readCriteriaString(query.criteria, "company"),
      }),
    )
    onOpenChange(false)
    toast.success("Payload-base do histórico enviado ao importador")
  }

  const generatedQueries = composeGoogleQueries.data ?? []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Composer Google</DialogTitle>
          <DialogDescription>
            Monte operadores de busca para localizar posts no Google e reutilize os critérios no
            scanner principal.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-4 rounded-xl border border-(--border-default) bg-(--bg-surface) p-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                Keywords base
              </p>
              <p className="mt-1 text-xs text-(--text-secondary)">
                Use uma keyword por linha ou separe por vírgulas para gerar variações de busca.
              </p>
            </div>
            <textarea
              value={keywordsText}
              onChange={(event) => setKeywordsText(event.target.value)}
              className="min-h-28 w-full rounded-lg border border-(--border-default) bg-(--bg-sunken) px-3 py-2 text-sm text-(--text-primary) outline-none transition focus:border-(--accent)"
              placeholder="Uma keyword por linha ou separada por vírgula"
            />

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                  Frases exatas
                </p>
                <textarea
                  value={exactPhrasesText}
                  onChange={(event) => setExactPhrasesText(event.target.value)}
                  className="min-h-24 w-full rounded-lg border border-(--border-default) bg-(--bg-sunken) px-3 py-2 text-sm text-(--text-primary) outline-none transition focus:border-(--accent)"
                  placeholder="Ex.: comentários, dores operacionais"
                />
              </div>
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                  Empresa opcional
                </p>
                <Input
                  value={company}
                  onChange={(event) => setCompany(event.target.value)}
                  placeholder="Ex.: Composto Web"
                />
                <p className="text-xs text-(--text-secondary)">
                  Boa para afunilar buscas por conta, marca ou concorrente.
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                  Cargos ICP
                </p>
                <textarea
                  value={titlesText}
                  onChange={(event) => setTitlesText(event.target.value)}
                  className="min-h-24 w-full rounded-lg border border-(--border-default) bg-(--bg-sunken) px-3 py-2 text-sm text-(--text-primary) outline-none transition focus:border-(--accent)"
                  placeholder="CEO\nCOO\nDiretor de TI"
                />
              </div>
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                  Setores ICP
                </p>
                <textarea
                  value={sectorsText}
                  onChange={(event) => setSectorsText(event.target.value)}
                  className="min-h-24 w-full rounded-lg border border-(--border-default) bg-(--bg-sunken) px-3 py-2 text-sm text-(--text-primary) outline-none transition focus:border-(--accent)"
                  placeholder="Tecnologia\nIndústria\nSaúde"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                className="gap-2"
                onClick={handleCompose}
                disabled={composeGoogleQueries.isPending}
              >
                {composeGoogleQueries.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Compondo...
                  </>
                ) : (
                  <>
                    <Globe className="h-4 w-4" />
                    Gerar consultas
                  </>
                )}
              </Button>
              <Button type="button" variant="outline" onClick={applyCurrentCriteria}>
                Aplicar critérios ao scan
              </Button>
              <Button type="button" variant="outline" onClick={seedImporterFromCurrentCriteria}>
                <Upload className="mr-1.5 h-3.5 w-3.5" />
                Gerar payload-base
              </Button>
            </div>

            {generatedQueries.length > 0 && (
              <div className="rounded-xl border border-(--border-default) bg-(--bg-sunken) p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-(--text-primary)">Consultas geradas</p>
                    <p className="mt-0.5 text-xs text-(--text-secondary)">
                      Copie uma busca individual ou leve o bloco completo para o navegador.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopyBatch(generatedQueries)}
                  >
                    <Copy className="mr-1.5 h-3.5 w-3.5" />
                    Copiar bloco
                  </Button>
                </div>
                <div className="mt-3 space-y-2">
                  {generatedQueries.map((query) => (
                    <div
                      key={query.id}
                      className="flex items-start justify-between gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) px-3 py-2"
                    >
                      <p className="flex-1 text-sm text-(--text-primary)">{query.query_text}</p>
                      <div className="flex shrink-0 gap-2">
                        <a
                          href={`https://www.google.com/search?q=${encodeURIComponent(query.query_text)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex h-8 items-center justify-center rounded-lg border border-(--border-default) px-3 text-xs text-(--text-secondary) transition hover:bg-(--bg-overlay)"
                        >
                          Abrir
                        </a>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            seedImporterFromHistory({
                              ...query,
                              criteria: {
                                ...(query.criteria ?? {}),
                                query_text: query.query_text,
                              },
                            })
                          }
                        >
                          Importar
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopy(query.query_text)}
                        >
                          Copiar
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="space-y-4 rounded-xl border border-(--border-default) bg-(--bg-surface) p-5">
            <div>
              <p className="text-sm font-semibold text-(--text-primary)">Histórico recente</p>
              <p className="mt-0.5 text-xs text-(--text-secondary)">
                Reaproveite composições anteriores sem remontar os critérios do zero.
              </p>
            </div>
            <div className="space-y-2">
              {isHistoryLoading ? (
                Array.from({ length: 4 }).map((_, index) => (
                  <div key={index} className="h-20 rounded-lg bg-(--bg-overlay) animate-pulse" />
                ))
              ) : history.length === 0 ? (
                <div className="rounded-lg border border-dashed border-(--border-default) px-4 py-8 text-center text-sm text-(--text-secondary)">
                  Nenhuma composição registrada ainda.
                </div>
              ) : (
                history.map((query) => (
                  <div
                    key={query.id}
                    className="rounded-lg border border-(--border-default) bg-(--bg-sunken) px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-(--text-primary)">
                          {query.query_text}
                        </p>
                        <p className="mt-1 text-xs text-(--text-secondary)">
                          {formatGoogleCriteriaSummary(query)} •{" "}
                          {formatHistoryDate(query.created_at)}
                        </p>
                        {query.imported_session_id ? (
                          <p className="mt-1 text-[11px] text-emerald-700 dark:text-emerald-300">
                            Importado na sessão {query.imported_session_id.slice(0, 8)}
                          </p>
                        ) : null}
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => applyHistoryCriteria(query)}
                        >
                          Usar critérios
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => seedImporterFromHistory(query)}
                        >
                          Gerar payload
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(query.query_text)}
                        >
                          Copiar
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function parseExternalImportPayload(payload: string) {
  const trimmed = payload.trim()
  if (!trimmed) {
    throw new Error("Cole um JSON com os posts que deseja importar")
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(trimmed)
  } catch {
    throw new Error("Formato inválido. Use um JSON array de objetos")
  }

  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("O JSON deve ser um array com pelo menos um post")
  }

  return parsed.map((item) => {
    if (!item || typeof item !== "object") {
      throw new Error("Cada item do array deve ser um objeto")
    }

    const record = item as Record<string, unknown>
    const postText = typeof record.post_text === "string" ? record.post_text.trim() : ""
    if (!postText) {
      throw new Error("Cada post precisa ter post_text preenchido")
    }

    return {
      post_text: postText,
      post_url: typeof record.post_url === "string" ? record.post_url : null,
      author_name: typeof record.author_name === "string" ? record.author_name : null,
      author_title: typeof record.author_title === "string" ? record.author_title : null,
      author_company: typeof record.author_company === "string" ? record.author_company : null,
      author_profile_url:
        typeof record.author_profile_url === "string" ? record.author_profile_url : null,
      likes: typeof record.likes === "number" ? record.likes : 0,
      comments: typeof record.comments === "number" ? record.comments : 0,
      shares: typeof record.shares === "number" ? record.shares : 0,
    }
  })
}

function ImportExternalPostsDialog({
  open,
  onOpenChange,
  sessionId,
  onImported,
  initialSeed,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId: string | null
  onImported: (result: ImportExternalPostsResponse) => void
  initialSeed: ExternalImportSeed | null
}) {
  const importExternalPosts = useImportExternalPosts()
  const [source, setSource] = useState<"google" | "manual">("google")
  const [postType, setPostType] = useState<"icp" | "reference">("icp")
  const [payload, setPayload] = useState("[")

  useEffect(() => {
    if (!open) return
    if (initialSeed) {
      setSource(initialSeed.source)
      setPostType(initialSeed.postType)
      setPayload(initialSeed.payload)
      return
    }

    setSource("google")
    setPostType("icp")
    setPayload(
      [
        "[",
        "  {",
        '    "post_url": "https://www.linkedin.com/posts/...",',
        '    "author_name": "Nome do decisor",',
        '    "author_title": "CEO",',
        '    "author_company": "Empresa",',
        '    "post_text": "Texto do post capturado externamente",',
        '    "likes": 12,',
        '    "comments": 4,',
        '    "shares": 1',
        "  }",
        "]",
      ].join("\n"),
    )
  }, [initialSeed, open])

  async function handleImport() {
    if (!sessionId) {
      toast.error("Abra ou execute uma sessão antes de importar posts externos")
      return
    }

    try {
      const posts = parseExternalImportPayload(payload).map((post) => ({
        ...post,
        source,
        post_type: postType,
      }))
      const result = await importExternalPosts.mutateAsync({
        sessionId,
        body: {
          posts,
          discovery_query_id: initialSeed?.discoveryQueryId ?? null,
        },
      })
      onImported(result)
      onOpenChange(false)
      toast.success(
        `${result.created_count} criado(s), ${result.merged_count} mesclado(s) na sessão atual`,
      )
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao importar posts externos")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Importar posts externos</DialogTitle>
          <DialogDescription>
            Traga capturas do Google ou de outras fontes para a sessão ativa. O backend funde
            duplicatas pela identidade do post.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                Fonte externa
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(["google", "manual"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setSource(option)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                      source === option
                        ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                        : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary)",
                    )}
                  >
                    {formatPostSourceLabel(option)}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">
                Tipo de destino
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(
                  [
                    ["icp", "Post de ICP"],
                    ["reference", "Referência"],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setPostType(value)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                      postType === value
                        ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                        : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary)",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-(--text-primary)">Payload JSON</p>
                <p className="mt-0.5 text-xs text-(--text-secondary)">
                  Um array de objetos com post_text obrigatório. Campos extras de autor e métricas
                  são opcionais.
                </p>
                {initialSeed?.contextLabel ? (
                  <p className="mt-2 text-xs text-(--text-secondary)">
                    Base pronta a partir de {initialSeed.contextLabel}. Preencha post_text e link
                    antes de importar.
                  </p>
                ) : null}
              </div>
              <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-[11px] text-(--text-secondary)">
                Sessão: {sessionId ? sessionId.slice(0, 8) : "nenhuma"}
              </span>
            </div>
            <Textarea
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              className="mt-3 min-h-72 font-mono text-xs"
              spellCheck={false}
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Fechar
            </Button>
            <Button
              type="button"
              className="gap-2"
              onClick={handleImport}
              disabled={!sessionId || importExternalPosts.isPending}
            >
              {importExternalPosts.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Importando...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Importar para a sessão
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function SessionHistoryTable({
  sessions,
  activeSessionId,
  onSelectSession,
  statusFilter,
  onStatusFilterChange,
  page,
  onPrevPage,
  onNextPage,
  canGoNext,
  isLoading,
}: {
  sessions: EngagementSession[]
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
  statusFilter: SessionStatus | "all"
  onStatusFilterChange: (status: SessionStatus | "all") => void
  page: number
  onPrevPage: () => void
  onNextPage: () => void
  canGoNext: boolean
  isLoading: boolean
}) {
  const filteredSessions =
    statusFilter === "all"
      ? sessions
      : sessions.filter((session) => session.status === statusFilter)

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-5 space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">Histórico de buscas</p>
          <p className="text-xs text-(--text-secondary) mt-0.5">
            Sessões paginadas com filtro de status e acesso direto ao resultado.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["all", "running", "completed", "partial", "failed"] as const).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => onStatusFilterChange(status)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                statusFilter === status
                  ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                  : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--accent) hover:text-(--text-primary)",
              )}
            >
              {status === "all" ? "Todos" : STATUS_META[status].label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-(--border-default)">
        <table className="min-w-full divide-y divide-(--border-default)">
          <thead className="bg-(--bg-overlay)">
            <tr className="text-left text-[11px] uppercase tracking-wider text-(--text-tertiary)">
              <th className="px-4 py-3 font-semibold">Data</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Origem</th>
              <th className="px-4 py-3 font-semibold">Post vinculado</th>
              <th className="px-4 py-3 font-semibold">Critérios</th>
              <th className="px-4 py-3 font-semibold text-right">Referências</th>
              <th className="px-4 py-3 font-semibold text-right">ICP</th>
              <th className="px-4 py-3 font-semibold text-right">Comentários</th>
              <th className="px-4 py-3 font-semibold text-right">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-(--border-default) bg-(--bg-surface)">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <tr key={index} className="animate-pulse">
                  <td className="px-4 py-3">
                    <div className="h-4 w-28 rounded bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="h-5 w-24 rounded-full bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="h-4 w-24 rounded bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="h-4 w-28 rounded bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="h-4 w-32 rounded bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="ml-auto h-4 w-8 rounded bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="ml-auto h-4 w-8 rounded bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="ml-auto h-4 w-8 rounded bg-(--bg-overlay)" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="ml-auto h-8 w-16 rounded bg-(--bg-overlay)" />
                  </td>
                </tr>
              ))
            ) : filteredSessions.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-sm text-(--text-secondary)">
                  Nenhuma sessão encontrada para este filtro nesta página.
                </td>
              </tr>
            ) : (
              filteredSessions.map((session) => {
                const isActive = session.id === activeSessionId
                return (
                  <tr
                    key={session.id}
                    className={cn(
                      "transition-colors hover:bg-(--bg-overlay)",
                      isActive && "bg-(--accent-subtle)/60",
                    )}
                  >
                    <td className="px-4 py-3 text-sm text-(--text-primary)">
                      {formatHistoryDate(session.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <SessionStatusBadge status={session.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-(--text-secondary)">
                      {formatScanSourceLabel(session.scan_source)}
                    </td>
                    <td className="px-4 py-3 text-sm text-(--text-secondary)">
                      {formatLinkedPostLabel(session.linked_post_id)}
                    </td>
                    <td className="px-4 py-3 text-xs text-(--text-secondary)">
                      {summarizeSessionCriteria(session)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-(--text-primary)">
                      {session.references_found}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-(--text-primary)">
                      {session.icp_posts_found}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-(--text-primary)">
                      {session.comments_generated}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        type="button"
                        variant={isActive ? "default" : "outline"}
                        size="sm"
                        onClick={() => onSelectSession(session.id)}
                      >
                        Ver
                      </Button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-(--text-tertiary)">Página {page}</p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onPrevPage}
            disabled={page === 1 || isLoading}
          >
            Anterior
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onNextPage}
            disabled={!canGoNext || isLoading}
          >
            Próxima
          </Button>
        </div>
      </div>
    </div>
  )
}

function ScanningState({
  currentStep,
  createdAt,
}: {
  currentStep?: number | null
  createdAt?: string | null
}) {
  const stepLabel = currentStep ? STEP_LABELS[currentStep] : undefined
  const progressWidthClass = currentStep ? STEP_PROGRESS_WIDTH[currentStep] : "w-0"
  const waitingForWorker =
    !currentStep && createdAt != null && Date.now() - new Date(createdAt).getTime() > 15 * 1000

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 rounded-xl border border-(--border-default) bg-(--bg-surface) px-6 py-5 shadow-sm">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-50 dark:bg-indigo-900/20">
          <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-(--text-primary)">Escaneando LinkedIn...</p>
            {currentStep && (
              <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                Etapa {currentStep}/4
              </span>
            )}
          </div>
          <p className="text-xs text-(--text-secondary) mt-0.5">
            {stepLabel ??
              (waitingForWorker
                ? "Aguardando o worker de conteúdo iniciar o scan na fila"
                : "Preparando scan e enviando job para processamento")}
          </p>
          {waitingForWorker && (
            <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
              Se isso persistir por mais alguns segundos, o scan será marcado como falho para evitar
              tela travada.
            </p>
          )}
          {currentStep && (
            <div className="mt-3 h-1.5 w-full rounded-full bg-(--bg-overlay) overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full bg-indigo-500 transition-all duration-500 ease-out",
                  progressWidthClass,
                )}
              />
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-6 space-y-4 animate-pulse"
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-(--bg-overlay)" />
              <div className="space-y-1.5 flex-1">
                <div className="h-4 w-32 rounded bg-(--bg-overlay)" />
                <div className="h-3 w-48 rounded bg-(--bg-overlay)" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-3.5 w-full rounded bg-(--bg-overlay)" />
              <div className="h-3.5 w-4/5 rounded bg-(--bg-overlay)" />
              <div className="h-3.5 w-2/3 rounded bg-(--bg-overlay)" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Summary bar ───────────────────────────────────────────────────────────────

function SummaryBar({ session }: { session: EngagementSessionDetail }) {
  const visibleKeywords = session.effective_keywords?.slice(0, 4) ?? []
  const visibleThemes = session.selected_theme_titles?.slice(0, 3) ?? []
  const stats = [
    {
      icon: BookOpen,
      label: "Referências",
      value: session.references_found,
      color: "text-indigo-600 dark:text-indigo-400",
      bg: "bg-indigo-50 dark:bg-indigo-900/20",
      border: "border-indigo-200 dark:border-indigo-800",
    },
    {
      icon: Users,
      label: "Posts de ICP",
      value: session.icp_posts_found,
      color: "text-sky-600 dark:text-sky-400",
      bg: "bg-sky-50 dark:bg-sky-900/20",
      border: "border-sky-200 dark:border-sky-800",
    },
    {
      icon: MessageSquareText,
      label: "Comentários",
      value: session.comments_generated,
      color: "text-emerald-600 dark:text-emerald-400",
      bg: "bg-emerald-50 dark:bg-emerald-900/20",
      border: "border-emerald-200 dark:border-emerald-800",
    },
  ]

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <SessionStatusBadge status={session.status} />
          <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2 py-0.5 text-[11px] font-medium text-(--text-secondary)">
            {formatScanSourceLabel(session.scan_source)}
          </span>
          <span className="text-xs text-(--text-secondary)">
            {formatHistoryDate(session.created_at)}
          </span>
          <span className="hidden text-(--text-tertiary) sm:inline">•</span>
          <span className="text-xs text-(--text-secondary)">
            {formatLinkedPostLabel(session.linked_post_id)}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          {stats.map(({ icon: Icon, label, value, color, bg, border }) => (
            <div
              key={label}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-1.5",
                bg,
                border,
              )}
            >
              <Icon className={cn("h-3.5 w-3.5", color)} />
              <span className={cn("text-sm font-bold leading-none", color)}>{value}</span>
              <span className="text-xs text-(--text-secondary)">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {(visibleThemes.length > 0 ||
        visibleKeywords.length > 0 ||
        session.linked_post_context_keywords?.length) && (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-(--border-default) pt-3">
          {visibleThemes.map((theme) => (
            <span
              key={`theme-${theme}`}
              className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-secondary)"
            >
              Tema: {theme}
            </span>
          ))}
          {visibleKeywords.map((keyword) => (
            <span
              key={`keyword-${keyword}`}
              className="inline-flex items-center rounded-full border border-(--border-default) bg-(--bg-sunken) px-2.5 py-1 text-xs text-(--text-secondary)"
            >
              {keyword}
            </span>
          ))}
          {session.linked_post_context_keywords?.length ? (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-1 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
              +{session.linked_post_context_keywords.length} keyword
              {session.linked_post_context_keywords.length !== 1 ? "s" : ""} do post vinculado
            </span>
          ) : null}
        </div>
      )}
    </div>
  )
}

function SessionEventsTimeline({ session }: { session: EngagementSessionDetail }) {
  if (!session.events?.length) return null

  return (
    <details className="group rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">Timeline operacional</p>
          <p className="mt-0.5 text-xs text-(--text-secondary)">
            Últimos eventos registrados desta sessão.
          </p>
        </div>
        <div className="flex items-center gap-2 text-(--text-tertiary)">
          <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-[11px] font-medium text-(--text-secondary)">
            {session.events.length} evento{session.events.length !== 1 ? "s" : ""}
          </span>
          <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
        </div>
      </summary>
      <div className="mt-3 space-y-2">
        {session.events.slice(0, 6).map((event) => (
          <div
            key={event.id}
            className="flex items-start justify-between gap-3 rounded-lg border border-(--border-default) bg-(--bg-sunken) px-3 py-2"
          >
            <div>
              <p className="text-xs font-medium text-(--text-primary)">
                {formatSessionEventLabel(event.event_type)}
              </p>
              {event.payload && Object.keys(event.payload).length > 0 ? (
                <p className="mt-0.5 text-[11px] text-(--text-secondary)">
                  {JSON.stringify(event.payload)}
                </p>
              ) : null}
            </div>
            <span className="shrink-0 text-[11px] text-(--text-tertiary)">
              {formatHistoryDate(event.created_at)}
            </span>
          </div>
        ))}
      </div>
    </details>
  )
}

function CompactMetric({ icon: Icon, value }: { icon: typeof ThumbsUp; value: number }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-(--text-tertiary)">
      <Icon className="h-3 w-3" />
      {value.toLocaleString("pt-BR")}
    </span>
  )
}

function ReferenceListRow({
  post,
  onOpen,
  canDelete,
  isDeleting,
  onDelete,
}: {
  post: EngagementPost
  onOpen: () => void
  canDelete: boolean
  isDeleting: boolean
  onDelete: (post: EngagementPost) => void
}) {
  return (
    <div
      onClick={onOpen}
      className="flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-(--bg-overlay)"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-(--text-primary)">
            {post.author_name ?? "Autor desconhecido"}
          </p>
          <PostOriginBadges post={post} />
          {post.hook_type && <HookBadge hook={post.hook_type} />}
          {post.pillar && <PillarBadge pillar={post.pillar} />}
          {post.is_saved && (
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
              <BookmarkCheck className="h-3 w-3" />
              Salvo
            </span>
          )}
        </div>
        {post.author_title && (
          <p className="mt-0.5 text-xs text-(--text-secondary)">{post.author_title}</p>
        )}
        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-(--text-secondary)">
          {post.post_text}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <CompactMetric icon={ThumbsUp} value={post.likes} />
          <CompactMetric icon={MessageCircle} value={post.comments} />
          <CompactMetric icon={Repeat2} value={post.shares} />
          {post.engagement_score != null && post.engagement_score > 0 && (
            <span className="text-xs font-medium text-(--text-secondary)">
              Score {post.engagement_score}
            </span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {canDelete && (
          <button
            type="button"
            title="Remover post da sessão manual"
            aria-label="Remover post da sessão manual"
            onClick={(event) => {
              event.stopPropagation()
              onDelete(post)
            }}
            disabled={isDeleting}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-(--border-default) text-(--danger) transition-colors hover:bg-(--danger-subtle) disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
        {post.post_url && (
          <a
            href={post.post_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir post no LinkedIn"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-(--border-default) text-(--text-secondary) transition-colors hover:bg-(--bg-overlay)"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={(event) => {
            event.stopPropagation()
            onOpen()
          }}
        >
          Ver
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}

function IcpListRow({
  post,
  onOpen,
  canDelete,
  isDeleting,
  onDelete,
}: {
  post: EngagementPost
  onOpen: () => void
  canDelete: boolean
  isDeleting: boolean
  onDelete: (post: EngagementPost) => void
}) {
  const comments = post.suggested_comments ?? []
  const wasCommented = comments.some((comment) => comment.status === "posted")

  return (
    <div
      onClick={onOpen}
      className={cn(
        "flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-(--bg-overlay)",
        wasCommented && "bg-emerald-50/40 dark:bg-emerald-900/10",
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {wasCommented && (
            <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
              Comentário postado
            </span>
          )}
          <p className="text-sm font-semibold text-(--text-primary)">
            {post.author_name ?? "Autor desconhecido"}
          </p>
          <PostOriginBadges post={post} />
          {comments.length > 0 && (
            <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2 py-0.5 text-[10px] font-semibold text-(--text-secondary)">
              {comments.length} comentário{comments.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        {post.author_title && (
          <p className="mt-0.5 text-xs text-(--text-secondary)">{post.author_title}</p>
        )}
        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-(--text-secondary)">
          {post.post_text}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <CompactMetric icon={ThumbsUp} value={post.likes} />
          <CompactMetric icon={MessageCircle} value={post.comments} />
          <CompactMetric icon={Repeat2} value={post.shares} />
          {post.what_to_replicate && (
            <span className="line-clamp-1 text-xs text-amber-700 dark:text-amber-300">
              Ângulo: {post.what_to_replicate}
            </span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {canDelete && (
          <button
            type="button"
            title="Remover post da sessão manual"
            aria-label="Remover post da sessão manual"
            onClick={(event) => {
              event.stopPropagation()
              onDelete(post)
            }}
            disabled={isDeleting}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-(--border-default) text-(--danger) transition-colors hover:bg-(--danger-subtle) disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
        {post.post_url && (
          <a
            href={post.post_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir post no LinkedIn"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-(--border-default) text-(--text-secondary) transition-colors hover:bg-(--bg-overlay)"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={(event) => {
            event.stopPropagation()
            onOpen()
          }}
        >
          Abrir
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}

interface PostedCommentEntry {
  comment: EngagementComment
  post: EngagementPost
}

function PostedCommentsModal({
  open,
  onOpenChange,
  entries,
  onOpenPost,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  entries: PostedCommentEntry[]
  onOpenPost: (post: EngagementPost) => void
}) {
  const unmarkPosted = useUnmarkCommentPosted()

  async function handleUndo(commentId: string) {
    try {
      await unmarkPosted.mutateAsync(commentId)
      toast.success("Marcação desfeita")
    } catch {
      toast.error("Não foi possível desfazer a marcação")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Comentários marcados como postados</DialogTitle>
          <DialogDescription>
            Gerencie os comentários já marcados como enviados nesta sessão.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-x-auto rounded-lg border border-(--border-default)">
          <table className="min-w-full divide-y divide-(--border-default)">
            <thead className="bg-(--bg-overlay)">
              <tr className="text-left text-[11px] uppercase tracking-wider text-(--text-tertiary)">
                <th className="px-4 py-3 font-semibold">Sessão</th>
                <th className="px-4 py-3 font-semibold">Post</th>
                <th className="px-4 py-3 font-semibold">Comentário feito</th>
                <th className="px-4 py-3 font-semibold">Link</th>
                <th className="px-4 py-3 font-semibold text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-(--border-default) bg-(--bg-surface)">
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-(--text-secondary)">
                    Nenhum comentário marcado como postado em nenhuma sessão.
                  </td>
                </tr>
              ) : (
                entries.map(({ comment, post }) => (
                  <tr key={comment.id} className="align-top">
                    <td className="px-4 py-3">
                      <span className="text-sm text-(--text-secondary)">
                        {formatHistoryDate(comment.posted_at ?? comment.created_at)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-(--text-primary)">
                          {post.author_name ?? "Autor desconhecido"}
                        </p>
                        {post.author_title && (
                          <p className="text-xs text-(--text-secondary)">{post.author_title}</p>
                        )}
                        <p className="line-clamp-2 text-xs text-(--text-tertiary)">
                          {post.post_text}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <p className="line-clamp-4 text-sm leading-relaxed text-(--text-primary)">
                        {comment.comment_text}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      {post.post_url ? (
                        <a
                          href={post.post_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm text-(--accent) hover:underline"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          Abrir post
                        </a>
                      ) : (
                        <span className="text-sm text-(--text-tertiary)">Sem link</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            onOpenPost(post)
                            onOpenChange(false)
                          }}
                        >
                          Ver detalhe
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUndo(comment.id)}
                          disabled={unmarkPosted.isPending}
                        >
                          Desfazer
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function PostDetailDrawer({
  post,
  onClose,
  canDelete,
  isDeleting,
  onDelete,
}: {
  post: EngagementPost | null
  onClose: () => void
  canDelete: boolean
  isDeleting: boolean
  onDelete: (post: EngagementPost) => void
}) {
  const mergedSourcesLabel = formatMergedSourcesLabel(post?.merged_sources)

  return (
    <Dialog open={!!post} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="left-auto right-0 top-0 h-dvh w-full max-w-3xl translate-x-0 translate-y-0 overflow-y-auto rounded-none border-l border-(--border-default) p-0">
        {post ? (
          <div className="space-y-0">
            <DialogHeader className="border-b border-(--border-default) px-6 py-5">
              <DialogTitle>{post.post_type === "icp" ? "Post de ICP" : "Referência"}</DialogTitle>
              <DialogDescription>
                {post.author_name ?? "Autor desconhecido"}
                {post.author_title ? ` · ${post.author_title}` : ""}
              </DialogDescription>
              <div className="mt-3 rounded-xl border border-(--border-default) bg-(--bg-sunken) px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <PostOriginBadges post={post} />
                  {canDelete ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-(--danger) hover:bg-(--danger-subtle) hover:text-(--danger)"
                      onClick={() => onDelete(post)}
                      disabled={isDeleting}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Remover da sessão
                    </Button>
                  ) : null}
                  {post.canonical_post_url ? (
                    <a
                      href={post.canonical_post_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 rounded-full border border-(--border-default) px-2 py-0.5 text-[10px] font-semibold text-(--text-secondary) transition-colors hover:bg-(--bg-overlay)"
                    >
                      <ExternalLink className="h-3 w-3" />
                      URL canônica
                    </a>
                  ) : null}
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-(--text-secondary)">
                  <span>Origem principal: {formatPostSourceLabel(post.source)}</span>
                  {post.merge_count > 1 && mergedSourcesLabel ? (
                    <span>Fontes agregadas: {mergedSourcesLabel}</span>
                  ) : null}
                </div>
              </div>
            </DialogHeader>
            <div className="p-6">
              {post.post_type === "icp" ? (
                <IcpPostCard post={post} />
              ) : (
                <PostReferenceCard post={post} />
              )}
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

// ── Resultados do scan ─────────────────────────────────────────────────────────

function SessionResults({
  session,
  onOpenPost,
  onDeletePost,
  deletingPostId,
}: {
  session: EngagementSessionDetail
  onOpenPost: (postId: string) => void
  onDeletePost: (post: EngagementPost) => void
  deletingPostId: string | null
}) {
  const referencePosts = session.posts.filter((p) => p.post_type === "reference")
  const icpPosts = session.posts.filter((p) => p.post_type === "icp")
  const canDeletePosts = session.scan_source === "manual"
  const [activeTab, setActiveTab] = useState<"icp" | "references">(
    icpPosts.length > 0 ? "icp" : "references",
  )

  return (
    <div className="space-y-4">
      <SummaryBar session={session} />
      <SessionEventsTimeline session={session} />

      {session.status === "partial" && session.error_message && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-300/60 bg-amber-50 dark:bg-amber-900/10 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <p className="text-sm text-amber-700 dark:text-amber-300">{session.error_message}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-(--border-default)">
        {(
          [
            { key: "icp" as const, label: "Posts de ICP", count: icpPosts.length, icon: Users },
            {
              key: "references" as const,
              label: "Referências",
              count: referencePosts.length,
              icon: BookOpen,
            },
          ] as const
        ).map(({ key, label, count, icon: TabIcon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === key
                ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-(--text-secondary) hover:text-(--text-primary)",
            )}
          >
            <TabIcon className="h-3.5 w-3.5" />
            {label}
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-semibold",
                activeTab === key
                  ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
                  : "bg-(--bg-overlay) text-(--text-secondary)",
              )}
            >
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div>
        {activeTab === "icp" &&
          (icpPosts.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-center">
              <Users className="mb-3 h-8 w-8 text-(--text-tertiary)" />
              <p className="text-sm text-(--text-secondary)">
                Nenhum post de ICP encontrado neste scan.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-surface) divide-y divide-(--border-default)">
              {icpPosts.map((post) => (
                <IcpListRow
                  key={post.id}
                  post={post}
                  onOpen={() => onOpenPost(post.id)}
                  canDelete={canDeletePosts}
                  isDeleting={deletingPostId === post.id}
                  onDelete={onDeletePost}
                />
              ))}
            </div>
          ))}
        {activeTab === "references" &&
          (referencePosts.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-center">
              <BookOpen className="mb-3 h-8 w-8 text-(--text-tertiary)" />
              <p className="text-sm text-(--text-secondary)">
                Nenhuma referência encontrada neste scan.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-surface) divide-y divide-(--border-default)">
              {referencePosts.map((post) => (
                <ReferenceListRow
                  key={post.id}
                  post={post}
                  onOpen={() => onOpenPost(post.id)}
                  canDelete={canDeletePosts}
                  isDeleting={deletingPostId === post.id}
                  onDelete={onDeletePost}
                />
              ))}
            </div>
          ))}
      </div>
    </div>
  )
}

// ── Componente principal ───────────────────────────────────────────────────────

export default function EngagementHubPage() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [linkedPostId, setLinkedPostId] = useState<string | null>(null)
  const [selectedThemeIds, setSelectedThemeIds] = useState<string[]>([])
  const [keywordInput, setKeywordInput] = useState("")
  const [manualKeywords, setManualKeywords] = useState<string[]>([])
  const [icpTitleInput, setIcpTitleInput] = useState("")
  const [icpTitles, setIcpTitles] = useState<string[]>([])
  const [icpSectorInput, setIcpSectorInput] = useState("")
  const [icpSectors, setIcpSectors] = useState<string[]>([])
  const [historyPage, setHistoryPage] = useState(1)
  const [historyStatusFilter, setHistoryStatusFilter] = useState<SessionStatus | "all">("all")
  const [configOpen, setConfigOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [googleDiscoveryOpen, setGoogleDiscoveryOpen] = useState(false)
  const [externalImportOpen, setExternalImportOpen] = useState(false)
  const [externalImportSeed, setExternalImportSeed] = useState<ExternalImportSeed | null>(null)
  const [postedCommentsOpen, setPostedCommentsOpen] = useState(false)
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: sessions } = useEngagementSessions({ page: 1, limit: HISTORY_PAGE_SIZE })
  const { data: historySessions = [], isLoading: isHistoryLoading } = useEngagementSessions({
    page: historyPage,
    limit: HISTORY_PAGE_SIZE,
  })
  const { data: allIcpPosts = [] } = useEngagementPosts(undefined, "icp")
  const { data: themes } = useContentThemes()
  const runScan = useRunScan()
  const deleteEngagementPost = useDeleteEngagementPost()

  // Mantem um unico observer de sessao para evitar polling/states antigos competindo entre si.
  const effectiveSessionId = activeSessionId ?? sessions?.[0]?.id ?? null
  const { data: displaySession, isLoading } = useEngagementSession(effectiveSessionId)
  const selectedPost = useMemo(
    () => displaySession?.posts.find((post) => post.id === selectedPostId) ?? null,
    [displaySession?.posts, selectedPostId],
  )
  const deletingPostId = deleteEngagementPost.isPending
    ? (deleteEngagementPost.variables ?? null)
    : null
  const postedCommentEntries = useMemo(
    () =>
      allIcpPosts
        .flatMap((post) =>
          (post.suggested_comments ?? [])
            .filter((comment) => comment.status === "posted")
            .map((comment) => ({ comment, post })),
        )
        .sort((left, right) => {
          const leftTime = new Date(left.comment.posted_at ?? left.comment.created_at).getTime()
          const rightTime = new Date(right.comment.posted_at ?? right.comment.created_at).getTime()
          return rightTime - leftTime
        }),
    [allIcpPosts],
  )
  const isRunning = displaySession?.status === "running"
  const isWaitingForWorker =
    isRunning &&
    !displaySession?.current_step &&
    displaySession?.created_at != null &&
    Date.now() - new Date(displaySession.created_at).getTime() > 15 * 1000
  const isQueuePickupFailed =
    displaySession?.status === "failed" &&
    displaySession.error_message?.includes("Fila de engajamento nao iniciou o scan")
  const isTimedOut =
    isRunning &&
    displaySession?.created_at != null &&
    Date.now() - new Date(displaySession.created_at).getTime() > 5 * 60 * 1000
  const isScanPending = runScan.isPending
  const selectedThemes = useMemo(
    () => (themes ?? []).filter((theme) => selectedThemeIds.includes(theme.id)),
    [selectedThemeIds, themes],
  )
  const effectiveKeywords = useMemo(() => {
    const seen = new Set<string>()
    return [...selectedThemes.map((theme) => theme.title), ...manualKeywords].filter((keyword) => {
      const normalized = keyword.trim().toLowerCase()
      if (!normalized || seen.has(normalized)) return false
      seen.add(normalized)
      return true
    })
  }, [manualKeywords, selectedThemes])

  // Quando o scan completa, atualiza a lista de sessões para remover o spinner
  useEffect(() => {
    if (displaySession && displaySession.status !== "running") {
      queryClient.invalidateQueries({ queryKey: engagementKeys.sessions() })
    }
  }, [displaySession, queryClient])

  function toggleTheme(themeId: string) {
    setSelectedThemeIds((current) =>
      current.includes(themeId) ? current.filter((id) => id !== themeId) : [...current, themeId],
    )
  }

  function addKeyword() {
    const keyword = keywordInput.trim()
    if (!keyword) return
    setManualKeywords((current) => {
      if (current.some((item) => item.toLowerCase() === keyword.toLowerCase())) return current
      return [...current, keyword]
    })
    setKeywordInput("")
  }

  function removeKeyword(keyword: string) {
    setManualKeywords((current) => current.filter((item) => item !== keyword))
  }

  function addIcpTitle() {
    const value = icpTitleInput.trim()
    if (!value) return
    setIcpTitles((current) => mergeUniqueItems(current, [value]))
    setIcpTitleInput("")
  }

  function removeIcpTitle(value: string) {
    setIcpTitles((current) => current.filter((item) => item !== value))
  }

  function addIcpSector() {
    const value = icpSectorInput.trim()
    if (!value) return
    setIcpSectors((current) => mergeUniqueItems(current, [value]))
    setIcpSectorInput("")
  }

  function removeIcpSector(value: string) {
    setIcpSectors((current) => current.filter((item) => item !== value))
  }

  function handleKeywordInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault()
      addKeyword()
    }
  }

  function handleIcpTitleInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault()
      addIcpTitle()
    }
  }

  function handleIcpSectorInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault()
      addIcpSector()
    }
  }

  function applyGoogleCriteria(criteria: {
    keywords: string[]
    titles: string[]
    sectors: string[]
  }) {
    setManualKeywords((current) => mergeUniqueItems(current, criteria.keywords))
    setIcpTitles((current) => mergeUniqueItems(current, criteria.titles))
    setIcpSectors((current) => mergeUniqueItems(current, criteria.sectors))
    setConfigOpen(true)
  }

  async function handleRunScan() {
    const payload = {
      linked_post_id: linkedPostId,
      ...(selectedThemeIds.length > 0 ? { selected_theme_ids: selectedThemeIds } : {}),
      ...(manualKeywords.length > 0 ? { manual_keywords: manualKeywords } : {}),
      ...(effectiveKeywords.length > 0 ? { keywords: effectiveKeywords } : {}),
      ...(icpTitles.length > 0 || icpSectors.length > 0
        ? {
            icp_filters: {
              ...(icpTitles.length > 0 ? { titles: icpTitles } : {}),
              ...(icpSectors.length > 0 ? { sectors: icpSectors } : {}),
            },
          }
        : {}),
    }
    const result = await runScan.mutateAsync(payload)
    setActiveSessionId(result.session_id)
    setHistoryPage(1)
    queryClient.invalidateQueries({ queryKey: engagementKeys.all })
  }

  function handleOpenPostInSession(post: EngagementPost) {
    setActiveSessionId(post.session_id)
    setSelectedPostId(post.id)
  }

  async function handleDeletePost(post: EngagementPost) {
    if (displaySession?.scan_source !== "manual") {
      return
    }

    const confirmed = window.confirm(
      `Remover este post da sessão manual?\n\n${post.author_name ?? "Autor desconhecido"}`,
    )
    if (!confirmed) {
      return
    }

    try {
      await deleteEngagementPost.mutateAsync(post.id)
      if (selectedPostId === post.id) {
        setSelectedPostId(null)
      }
      toast.success("Post removido da sessão manual")
    } catch {
      toast.error("Não foi possível remover o post da sessão")
    }
  }

  function handleExternalImportCompleted(result: ImportExternalPostsResponse) {
    setActiveSessionId(result.session_id)
  }

  function handleOpenExternalImport(seed: ExternalImportSeed | null = null) {
    setExternalImportSeed(seed)
    setExternalImportOpen(true)
  }

  const canGoNextHistoryPage = historySessions.length === HISTORY_PAGE_SIZE

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 dark:bg-indigo-900/20">
            <Search className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-(--text-primary)">Engajamento LinkedIn</h1>
            <p className="text-xs text-(--text-secondary)">
              Garimpagem de posts + sugestões de comentários para decisores do ICP
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          <Button
            type="button"
            className="gap-2 border border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200"
            onClick={() => setPostedCommentsOpen(true)}
          >
            <MessageCircle className="h-4 w-4" />
            Gerenciar postados
            <span className="rounded-full bg-white/70 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
              {postedCommentEntries.length}
            </span>
          </Button>
          <Button
            type="button"
            variant="outline"
            className="gap-2"
            onClick={() => handleOpenExternalImport()}
          >
            <Upload className="h-4 w-4" />
            Importar externo
          </Button>
          <Button
            type="button"
            variant="outline"
            className="gap-2"
            onClick={() => setGoogleDiscoveryOpen(true)}
          >
            <Globe className="h-4 w-4" />
            Composer Google
          </Button>
          <Button
            type="button"
            variant="outline"
            className="gap-2"
            onClick={() => setConfigOpen(true)}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Configurar scan
          </Button>
          <Button
            onClick={handleRunScan}
            disabled={isScanPending || isRunning}
            className="shrink-0 gap-2"
          >
            {isScanPending || isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {isRunning ? "Escaneando..." : "Iniciando..."}
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Novo Scan
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="gap-2"
            onClick={() => setHistoryOpen(true)}
          >
            <History className="h-4 w-4" />
            Histórico de buscas
          </Button>
        </div>
      </div>

      {isWaitingForWorker ? (
        <div className="flex items-start gap-3 rounded-xl border border-amber-300/50 bg-amber-50 px-5 py-4 dark:border-amber-800/50 dark:bg-amber-900/10">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div>
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
              Scan aguardando pickup na fila de engajamento
            </p>
            <p className="mt-0.5 text-xs text-amber-700/90 dark:text-amber-300/90">
              A task foi enviada, mas o worker-content-engagement ainda não começou o processamento.
            </p>
          </div>
        </div>
      ) : isQueuePickupFailed ? (
        <div className="flex items-start gap-3 rounded-xl border border-red-300/50 bg-red-50 px-5 py-4 dark:border-red-800/50 dark:bg-red-900/10">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-medium text-red-700 dark:text-red-300">
              Worker-content-engagement indisponível para este scan
            </p>
            <p className="mt-0.5 text-xs text-red-600/80 dark:text-red-400/80">
              {displaySession.error_message}
            </p>
          </div>
        </div>
      ) : null}

      <ActiveConfigurationSummary
        linkedPostId={linkedPostId}
        selectedThemesCount={selectedThemeIds.length}
        manualKeywordsCount={manualKeywords.length}
        icpTitlesCount={icpTitles.length}
        icpSectorsCount={icpSectors.length}
        effectiveKeywords={effectiveKeywords}
      />

      {/* Estado principal */}
      {isRunning && !isTimedOut ? (
        <ScanningState
          currentStep={displaySession?.current_step}
          createdAt={displaySession?.created_at}
        />
      ) : isTimedOut ? (
        <div className="flex items-start gap-3 rounded-xl border border-red-300/50 bg-red-50 dark:bg-red-900/10 px-5 py-4">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-medium text-red-700 dark:text-red-300">Scan expirou</p>
            <p className="text-xs text-red-600/80 dark:text-red-400/80 mt-0.5">
              O scan demorou demais. Verifique se o worker Celery está rodando e tente novamente.
            </p>
          </div>
        </div>
      ) : displaySession?.status === "failed" &&
        displaySession.error_message &&
        displaySession.posts.length === 0 ? (
        <div className="flex items-start gap-3 rounded-xl border border-red-300/50 bg-red-50 dark:bg-red-900/10 px-5 py-4">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-medium text-red-700 dark:text-red-300">
              Scan falhou antes de iniciar
            </p>
            <p className="text-xs text-red-600/80 dark:text-red-400/80 mt-0.5">
              {displaySession.error_message}
            </p>
          </div>
        </div>
      ) : isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-40 w-full rounded-xl bg-(--bg-overlay) animate-pulse" />
          ))}
        </div>
      ) : displaySession ? (
        <SessionResults
          session={displaySession}
          onOpenPost={setSelectedPostId}
          onDeletePost={handleDeletePost}
          deletingPostId={deletingPostId}
        />
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-(--border-default) py-20 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-(--bg-overlay)">
            <Search className="h-6 w-6 text-(--text-tertiary)" />
          </div>
          <p className="text-base font-medium text-(--text-primary)">Nenhum scan realizado</p>
          <p className="mt-1 text-sm text-(--text-secondary) max-w-sm">
            Clique em &quot;Novo Scan&quot; para garimpar posts relevantes e gerar sugestões de
            comentários.
          </p>
        </div>
      )}

      {/* Erro de scan */}
      {runScan.isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-300/50 bg-red-50 dark:bg-red-900/10 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
          <p className="text-sm text-red-700 dark:text-red-300">
            {runScan.error?.message ?? "Erro ao iniciar o scan."}
          </p>
        </div>
      )}

      <PostDetailDrawer
        post={selectedPost}
        onClose={() => setSelectedPostId(null)}
        canDelete={displaySession?.scan_source === "manual"}
        isDeleting={deletingPostId === selectedPost?.id}
        onDelete={handleDeletePost}
      />
      <PostedCommentsModal
        open={postedCommentsOpen}
        onOpenChange={setPostedCommentsOpen}
        entries={postedCommentEntries}
        onOpenPost={handleOpenPostInSession}
      />
      <GoogleDiscoveryDialog
        open={googleDiscoveryOpen}
        onOpenChange={setGoogleDiscoveryOpen}
        defaultKeywords={effectiveKeywords}
        defaultTitles={icpTitles}
        defaultSectors={icpSectors}
        linkedPostId={linkedPostId}
        onApplyCriteria={applyGoogleCriteria}
        onSeedImportPayload={handleOpenExternalImport}
      />
      <ImportExternalPostsDialog
        open={externalImportOpen}
        onOpenChange={setExternalImportOpen}
        sessionId={effectiveSessionId}
        onImported={handleExternalImportCompleted}
        initialSeed={externalImportSeed}
      />

      <Dialog open={configOpen} onOpenChange={setConfigOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Configurar scan</DialogTitle>
            <DialogDescription>
              Ajuste post vinculado, temas e palavras-chave sem ocupar espaço da página principal.
            </DialogDescription>
          </DialogHeader>

          <ScanConfigurationPanel
            linkedPostId={linkedPostId}
            onLinkedPostChange={setLinkedPostId}
            themes={themes ?? []}
            selectedThemeIds={selectedThemeIds}
            onToggleTheme={toggleTheme}
            keywordInput={keywordInput}
            onKeywordInputChange={setKeywordInput}
            onKeywordInputKeyDown={handleKeywordInputKeyDown}
            onAddKeyword={addKeyword}
            manualKeywords={manualKeywords}
            onRemoveKeyword={removeKeyword}
            icpTitleInput={icpTitleInput}
            onIcpTitleInputChange={setIcpTitleInput}
            onIcpTitleInputKeyDown={handleIcpTitleInputKeyDown}
            onAddIcpTitle={addIcpTitle}
            icpTitles={icpTitles}
            onRemoveIcpTitle={removeIcpTitle}
            icpSectorInput={icpSectorInput}
            onIcpSectorInputChange={setIcpSectorInput}
            onIcpSectorInputKeyDown={handleIcpSectorInputKeyDown}
            onAddIcpSector={addIcpSector}
            icpSectors={icpSectors}
            onRemoveIcpSector={removeIcpSector}
            effectiveKeywords={effectiveKeywords}
            disabled={isScanPending || isRunning}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Histórico de buscas</DialogTitle>
            <DialogDescription>
              Consulte sessões anteriores e troque rapidamente o resultado exibido na tela.
            </DialogDescription>
          </DialogHeader>

          <SessionHistoryTable
            sessions={historySessions}
            activeSessionId={effectiveSessionId}
            onSelectSession={(sessionId) => {
              setActiveSessionId(sessionId)
              setHistoryOpen(false)
            }}
            statusFilter={historyStatusFilter}
            onStatusFilterChange={(status) => {
              setHistoryStatusFilter(status)
              setHistoryPage(1)
            }}
            page={historyPage}
            onPrevPage={() => setHistoryPage((current) => Math.max(1, current - 1))}
            onNextPage={() => setHistoryPage((current) => current + 1)}
            canGoNext={canGoNextHistoryPage}
            isLoading={isHistoryLoading}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
