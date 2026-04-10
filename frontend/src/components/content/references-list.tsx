"use client"

import { useState } from "react"
import {
  BookOpen,
  Filter,
  Plus,
  Trash2,
  ExternalLink,
  Loader2,
  Sparkles,
  CheckCircle2,
  LayoutGrid,
  List,
} from "lucide-react"
import {
  useContentReferences,
  useCreateContentReference,
  useDeleteContentReference,
  useAnalyzeReferenceUrl,
  type ContentReference,
  type ContentReferenceCreate,
  type PostPillar,
  type HookType,
} from "@/lib/api/hooks/use-content"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import { PillarBadge, HookBadge } from "@/components/content/post-badges"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const PILLAR_OPTIONS: { value: PostPillar; label: string }[] = [
  { value: "authority", label: "Autoridade" },
  { value: "case", label: "Caso" },
  { value: "vision", label: "Visão" },
]

const HOOK_OPTIONS: { value: HookType; label: string }[] = [
  { value: "loop_open", label: "Loop aberto" },
  { value: "contrarian", label: "Contrário" },
  { value: "identification", label: "Identificação" },
  { value: "shortcut", label: "Atalho" },
  { value: "benefit", label: "Benefício" },
  { value: "data", label: "Dado" },
]

function emptyForm(): ContentReferenceCreate {
  return {
    body: "",
    author_name: null,
    author_title: null,
    author_company: null,
    hook_type: null,
    pillar: null,
    engagement_score: null,
    source_url: null,
    notes: null,
  }
}

export function ReferencesList() {
  const { data: references, isLoading } = useContentReferences()
  const createRef = useCreateContentReference()
  const deleteRef = useDeleteContentReference()
  const analyzeUrl = useAnalyzeReferenceUrl()

  const [sheetOpen, setSheetOpen] = useState(false)
  const [form, setForm] = useState<ContentReferenceCreate>(emptyForm())
  const [pillarFilter, setPillarFilter] = useState<PostPillar | "all">("all")
  const [hookFilter, setHookFilter] = useState<HookType | "all">("all")
  const [urlInput, setUrlInput] = useState("")
  const [aiAnalyzed, setAiAnalyzed] = useState(false)
  const [viewMode, setViewMode] = useState<"table" | "grid">("table")
  const [viewRef, setViewRef] = useState<ContentReference | null>(null)
  const [engSort, setEngSort] = useState<"all" | "asc" | "desc">("all")

  const filteredRefs = (references ?? [])
    .filter((ref) => {
      if (pillarFilter !== "all" && ref.pillar !== pillarFilter) return false
      if (hookFilter !== "all" && ref.hook_type !== hookFilter) return false
      return true
    })
    .sort((a, b) => {
      if (engSort === "desc") return (b.engagement_score ?? 0) - (a.engagement_score ?? 0)
      if (engSort === "asc") return (a.engagement_score ?? 0) - (b.engagement_score ?? 0)
      return 0
    })

  function handleChange(field: keyof ContentReferenceCreate, value: string | number | null) {
    setForm((prev) => ({ ...prev, [field]: value === "" ? null : value }))
  }

  async function handleAnalyzeUrl() {
    if (!urlInput.trim()) return
    const result = await analyzeUrl.mutateAsync(urlInput.trim())
    setForm((prev) => ({
      ...prev,
      body: result.body ?? prev.body,
      author_name: result.author_name ?? prev.author_name ?? null,
      author_title: result.author_title ?? prev.author_title ?? null,
      author_company: result.author_company ?? prev.author_company ?? null,
      hook_type: result.hook_type ?? prev.hook_type ?? null,
      pillar: result.pillar ?? prev.pillar ?? null,
      engagement_score: result.engagement_score ?? prev.engagement_score ?? null,
      notes: result.notes ?? prev.notes ?? null,
      source_url: urlInput.trim(),
    }))
    setAiAnalyzed(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.body.trim()) return
    await createRef.mutateAsync(form)
    setForm(emptyForm())
    setUrlInput("")
    setAiAnalyzed(false)
    setSheetOpen(false)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-(--text-primary)">Referências</h2>
          <p className="text-xs text-(--text-tertiary) mt-0.5">
            Posts de inspiração que a IA pode usar como referência para geração de conteúdo.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-md border border-(--border-default) p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded transition-colors ${viewMode === "table" ? "bg-(--accent) text-white" : "text-(--text-tertiary) hover:text-(--text-secondary)"}`}
              title="Visualização em lista"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded transition-colors ${viewMode === "grid" ? "bg-(--accent) text-white" : "text-(--text-tertiary) hover:text-(--text-secondary)"}`}
              title="Visualização em cards"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>
          <Button size="sm" className="gap-1.5" onClick={() => setSheetOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
            Adicionar
          </Button>
        </div>
      </div>

      {/* Lista */}
      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-5 w-5 animate-spin text-(--text-tertiary)" />
        </div>
      ) : !references || references.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
          <BookOpen className="h-8 w-8 text-(--text-tertiary)" />
          <p className="text-sm text-(--text-secondary)">Nenhuma referência ainda.</p>
          <p className="text-xs text-(--text-tertiary)">
            Adicione posts que servem de inspiração para o estilo e formato.
          </p>
        </div>
      ) : filteredRefs.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
          <p className="text-sm text-(--text-tertiary)">Nenhuma referência com esses filtros.</p>
        </div>
      ) : viewMode === "table" ? (
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) overflow-hidden shadow-sm">
          {/* Header */}
          <div
            className={cn(
              "grid gap-2 px-4 py-2.5 border-b border-(--border-default) bg-(--bg-overlay) text-xs font-medium text-(--text-tertiary) uppercase tracking-wide items-center",
              REF_GRID_COLS,
            )}
          >
            <span>Post</span>
            {/* Pilar filter */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className={`flex items-center gap-1 text-xs font-medium uppercase tracking-wide hover:text-(--text-primary) transition-colors ${
                    pillarFilter !== "all" ? "text-(--accent)" : "text-(--text-tertiary)"
                  }`}
                >
                  Pilar
                  <Filter className="h-3 w-3" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-36">
                {[{ value: "all", label: "Todos" }, ...PILLAR_OPTIONS].map((opt) => (
                  <DropdownMenuItem
                    key={opt.value}
                    onSelect={() => setPillarFilter(opt.value as PostPillar | "all")}
                    className={pillarFilter === opt.value ? "font-medium text-(--accent)" : ""}
                  >
                    {opt.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            {/* Gancho filter */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className={`flex items-center gap-1 text-xs font-medium uppercase tracking-wide hover:text-(--text-primary) transition-colors ${
                    hookFilter !== "all" ? "text-(--accent)" : "text-(--text-tertiary)"
                  }`}
                >
                  Gancho
                  <Filter className="h-3 w-3" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-40">
                {[{ value: "all", label: "Todos" }, ...HOOK_OPTIONS].map((opt) => (
                  <DropdownMenuItem
                    key={opt.value}
                    onSelect={() => setHookFilter(opt.value as HookType | "all")}
                    className={hookFilter === opt.value ? "font-medium text-(--accent)" : ""}
                  >
                    {opt.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            {/* Engajamento sort */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className={`flex items-center gap-1 text-xs font-medium uppercase tracking-wide hover:text-(--text-primary) transition-colors text-right ${
                    engSort !== "all" ? "text-(--accent)" : "text-(--text-tertiary)"
                  }`}
                >
                  Engajamento
                  <Filter className="h-3 w-3" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                {[
                  { value: "all", label: "Sem ordenação" },
                  { value: "desc", label: "↓ Maior primeiro" },
                  { value: "asc", label: "↑ Menor primeiro" },
                ].map((opt) => (
                  <DropdownMenuItem
                    key={opt.value}
                    onSelect={() => setEngSort(opt.value as "all" | "asc" | "desc")}
                    className={engSort === opt.value ? "font-medium text-(--accent)" : ""}
                  >
                    {opt.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <span>Salvo em</span>
            <span className="text-center">Ações</span>
          </div>
          {/* Rows */}
          {filteredRefs.map((ref) => (
            <ReferenceRow
              key={ref.id}
              reference={ref}
              onDelete={() => deleteRef.mutate(ref.id)}
              isDeleting={deleteRef.isPending && deleteRef.variables === ref.id}
              onView={() => setViewRef(ref)}
            />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filteredRefs.map((ref) => (
            <ReferenceCard
              key={ref.id}
              reference={ref}
              onDelete={() => deleteRef.mutate(ref.id)}
              isDeleting={deleteRef.isPending && deleteRef.variables === ref.id}
              onView={() => setViewRef(ref)}
            />
          ))}
        </div>
      )}

      {/* Detail modal */}
      <ReferenceDetailDialog reference={viewRef} onClose={() => setViewRef(null)} />

      {/* Dialog de criação */}
      <Dialog
        open={sheetOpen}
        onOpenChange={(open) => {
          setSheetOpen(open)
          if (!open) {
            setForm(emptyForm())
            setUrlInput("")
            setAiAnalyzed(false)
          }
        }}
      >
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nova referência</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4 py-4">
            {/* URL + AI Analysis */}
            <div className="rounded-lg border border-(--border-default) bg-(--bg-subtle) p-3 flex flex-col gap-2">
              <Label
                htmlFor="ref-url-input"
                className="text-xs font-medium text-(--text-secondary)"
              >
                Cole a URL do post para análise com IA
              </Label>
              <div className="flex gap-2">
                <Input
                  id="ref-url-input"
                  type="url"
                  value={urlInput}
                  onChange={(e) => {
                    setUrlInput(e.target.value)
                    setAiAnalyzed(false)
                  }}
                  placeholder="https://linkedin.com/posts/..."
                  className="text-sm flex-1"
                  disabled={analyzeUrl.isPending}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="gap-1.5 shrink-0"
                  onClick={handleAnalyzeUrl}
                  disabled={!urlInput.trim() || analyzeUrl.isPending}
                >
                  {analyzeUrl.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  {analyzeUrl.isPending ? "Analisando…" : "Analisar com IA"}
                </Button>
              </div>
              {analyzeUrl.isError && (
                <p className="text-xs text-(--danger)">
                  Não foi possível extrair o conteúdo da URL. Preencha manualmente.
                </p>
              )}
              {aiAnalyzed && (
                <div className="flex items-center gap-1.5 text-xs text-(--success, green)">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Dados extraídos com IA — revise antes de salvar
                </div>
              )}
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="ref-body">Texto do post *</Label>
              <Textarea
                id="ref-body"
                value={form.body}
                onChange={(e) => setForm((p) => ({ ...p, body: e.target.value }))}
                placeholder="Cole aqui o texto completo do post de referência..."
                rows={8}
                required
                className="resize-none text-sm leading-relaxed font-sans whitespace-pre-wrap"
              />
              <p className="text-xs text-(--text-tertiary) text-right">{form.body.length} chars</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1.5">
                <Label htmlFor="ref-author_name">Autor</Label>
                <Input
                  id="ref-author_name"
                  value={form.author_name ?? ""}
                  onChange={(e) => handleChange("author_name", e.target.value)}
                  placeholder="Ex: João Silva"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="ref-author_title">Cargo / área</Label>
                <Input
                  id="ref-author_title"
                  value={form.author_title ?? ""}
                  onChange={(e) => handleChange("author_title", e.target.value)}
                  placeholder="Ex: CEO de SaaS"
                />
              </div>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="ref-author_company">Empresa</Label>
              <Input
                id="ref-author_company"
                value={form.author_company ?? ""}
                onChange={(e) => handleChange("author_company", e.target.value)}
                placeholder="Ex: Resultados Digitais"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1.5">
                <Label>Pilar</Label>
                <Select
                  value={form.pillar ?? "none"}
                  onValueChange={(v) =>
                    handleChange("pillar", v === "none" ? null : (v as PostPillar))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Nenhum" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nenhum</SelectItem>
                    {PILLAR_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-1.5">
                <Label>Tipo de gancho</Label>
                <Select
                  value={form.hook_type ?? "none"}
                  onValueChange={(v) =>
                    handleChange("hook_type", v === "none" ? null : (v as HookType))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Nenhum" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nenhum</SelectItem>
                    {HOOK_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="ref-engagement">Score de engajamento</Label>
              <Input
                id="ref-engagement"
                type="number"
                min={0}
                max={100}
                value={form.engagement_score ?? ""}
                onChange={(e) =>
                  handleChange(
                    "engagement_score",
                    e.target.value ? parseInt(e.target.value, 10) : null,
                  )
                }
                placeholder="0–100"
                className="w-28"
              />
              <p className="text-xs text-(--text-tertiary)">
                Avaliação subjetiva do desempenho (0 = baixo, 100 = viral).
              </p>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="ref-notes">Notas</Label>
              <Textarea
                id="ref-notes"
                value={form.notes ?? ""}
                onChange={(e) => handleChange("notes", e.target.value)}
                placeholder="O que torna esse post exemplo? Estrutura, gancho, dados..."
                rows={3}
                className="resize-none text-sm"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSheetOpen(false)
                  setForm(emptyForm())
                  setUrlInput("")
                  setAiAnalyzed(false)
                }}
                disabled={createRef.isPending}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={!form.body.trim() || createRef.isPending}>
                {createRef.isPending ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                    Salvando…
                  </>
                ) : (
                  "Salvar referência"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  })
}

function formatScore(score: number | null): string {
  if (score === null) return "—"
  return score.toLocaleString("pt-BR")
}

// ── Grid layout ──────────────────────────────────────────────────────

const REF_GRID_COLS = "grid-cols-[1fr_80px_110px_100px_100px_70px]"

// ── Row (table view) ─────────────────────────────────────────────────

interface ReferenceRowProps {
  reference: ContentReference
  onDelete: () => void
  isDeleting: boolean
  onView: () => void
}

function ReferenceRow({ reference, onDelete, isDeleting, onView }: ReferenceRowProps) {
  return (
    <div
      className={cn(
        "grid gap-2 px-4 py-3 border-b border-(--border-default) last:border-b-0 hover:bg-(--bg-overlay) transition-colors items-center text-xs cursor-pointer",
        REF_GRID_COLS,
      )}
      onClick={onView}
    >
      {/* Autor + preview */}
      <div className="flex flex-col gap-0.5 min-w-0">
        <p className="text-sm font-medium text-(--text-primary) truncate">
          {reference.author_name ?? "Sem autor"}
        </p>
        {reference.author_title && (
          <p className="text-xs text-(--text-tertiary) truncate">{reference.author_title}</p>
        )}
        <p className="text-xs text-(--text-secondary) truncate mt-0.5">{reference.body}</p>
      </div>

      {/* Pilar */}
      <div>
        {reference.pillar ? (
          <PillarBadge pillar={reference.pillar} />
        ) : (
          <span className="text-xs text-(--text-tertiary)">—</span>
        )}
      </div>

      {/* Gancho */}
      <div>
        {reference.hook_type ? (
          <HookBadge hook={reference.hook_type} />
        ) : (
          <span className="text-xs text-(--text-tertiary)">—</span>
        )}
      </div>

      {/* Engajamento */}
      <div className="text-right">
        <span className="text-sm tabular-nums text-(--text-secondary)">
          {formatScore(reference.engagement_score)}
          {reference.engagement_score !== null && (
            <span className="text-xs text-(--text-tertiary) ml-0.5">pts</span>
          )}
        </span>
      </div>

      {/* Data */}
      <div>
        <span className="text-xs text-(--text-tertiary) tabular-nums">
          {formatDate(reference.created_at)}
        </span>
      </div>

      {/* Ações */}
      <div className="flex items-center justify-center gap-1" onClick={(e) => e.stopPropagation()}>
        {reference.source_url && (
          <a
            href={reference.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded text-(--text-tertiary) hover:text-(--text-primary) transition-colors"
            title="Ver fonte"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        <button
          type="button"
          onClick={onDelete}
          disabled={isDeleting}
          className="p-1.5 rounded text-(--text-tertiary) hover:text-(--danger) transition-colors disabled:opacity-50"
          title="Excluir"
        >
          {isDeleting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Trash2 className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
    </div>
  )
}

// ── Card individual ───────────────────────────────────────────────────

interface ReferenceCardProps {
  reference: ContentReference
  onDelete: () => void
  isDeleting: boolean
  onView: () => void
}

function ReferenceCard({ reference, onDelete, isDeleting, onView }: ReferenceCardProps) {
  const initials = (reference.author_name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()

  return (
    <div
      className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 flex flex-col gap-3 shadow-sm cursor-pointer hover:bg-(--bg-overlay) transition-colors"
      onClick={onView}
    >
      {/* Autor */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-(--accent)/15 text-(--accent) flex items-center justify-center text-xs font-bold shrink-0">
          {initials}
        </div>
        <div className="min-w-0">
          {reference.author_name && (
            <p className="text-sm font-semibold text-(--text-primary) truncate leading-tight">
              {reference.author_name}
            </p>
          )}
          {reference.author_title && (
            <p className="text-xs text-(--text-tertiary) truncate leading-tight">
              {reference.author_title}
            </p>
          )}
        </div>
      </div>

      {/* Engajamento */}
      {reference.engagement_score !== null && (
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold tabular-nums text-(--text-primary)">
            {formatScore(reference.engagement_score)}
          </span>
          <span className="text-xs text-(--text-tertiary)">pts engajamento</span>
        </div>
      )}

      {/* Corpo do post (truncated) */}
      <p className="text-sm text-(--text-secondary) whitespace-pre-wrap leading-relaxed line-clamp-3">
        {reference.body}
      </p>

      {/* Notas */}
      {reference.notes && (
        <p className="text-xs text-(--text-tertiary) italic border-t border-(--border-default) pt-2">
          {reference.notes}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-(--border-default)">
        {reference.pillar && <PillarBadge pillar={reference.pillar} />}
        {reference.hook_type && <HookBadge hook={reference.hook_type} />}
        <span className="text-xs text-(--text-tertiary) tabular-nums">
          {formatDate(reference.created_at)}
        </span>
        <div className="flex items-center gap-1 ml-auto" onClick={(e) => e.stopPropagation()}>
          {reference.source_url && (
            <a
              href={reference.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded text-(--text-tertiary) hover:text-(--text-primary) transition-colors"
              title="Ver fonte"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          <button
            type="button"
            onClick={onDelete}
            disabled={isDeleting}
            className="p-1.5 rounded text-(--text-tertiary) hover:text-(--danger) transition-colors disabled:opacity-50"
            title="Excluir"
          >
            {isDeleting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Detail dialog ─────────────────────────────────────────────────────

function ReferenceDetailDialog({
  reference,
  onClose,
}: {
  reference: ContentReference | null
  onClose: () => void
}) {
  if (!reference) return null

  const initials = (reference.author_name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()

  return (
    <Dialog
      open={!!reference}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="sr-only">Referência</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          {/* Author */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-(--accent)/15 text-(--accent) flex items-center justify-center text-sm font-bold shrink-0">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              {reference.author_name && (
                <p className="text-sm font-semibold text-(--text-primary) truncate">
                  {reference.author_name}
                </p>
              )}
              <div className="flex items-center gap-2 text-xs text-(--text-tertiary)">
                {reference.author_title && (
                  <span className="truncate">{reference.author_title}</span>
                )}
                {reference.author_title && reference.author_company && <span>·</span>}
                {reference.author_company && (
                  <span className="truncate">{reference.author_company}</span>
                )}
              </div>
            </div>
          </div>

          {/* Meta badges */}
          <div className="flex items-center gap-2 flex-wrap">
            {reference.pillar && <PillarBadge pillar={reference.pillar} />}
            {reference.hook_type && <HookBadge hook={reference.hook_type} />}
            {reference.engagement_score !== null && (
              <span className="inline-flex items-center gap-1 text-xs text-(--text-secondary)">
                <span className="font-semibold tabular-nums">
                  {formatScore(reference.engagement_score)}
                </span>
                <span className="text-(--text-tertiary)">pts</span>
              </span>
            )}
            <span className="text-xs text-(--text-tertiary) tabular-nums ml-auto">
              Salvo em {formatDate(reference.created_at)}
            </span>
          </div>

          {/* Body */}
          <div className="rounded-lg border border-(--border-default) bg-(--bg-subtle) p-4">
            <p className="text-sm text-(--text-secondary) whitespace-pre-wrap leading-relaxed">
              {reference.body}
            </p>
          </div>

          {/* Notes */}
          {reference.notes && (
            <div className="rounded-lg border border-(--border-default) bg-(--bg-subtle) p-3">
              <p className="text-xs font-medium text-(--text-tertiary) mb-1">Notas</p>
              <p className="text-sm text-(--text-secondary)">{reference.notes}</p>
            </div>
          )}

          {/* Source link */}
          {reference.source_url && (
            <a
              href={reference.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-(--accent) hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Ver post original
            </a>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
