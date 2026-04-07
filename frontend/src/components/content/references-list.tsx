"use client"

import { useState } from "react"
import { BookOpen, Filter, Plus, Trash2, ExternalLink, Loader2 } from "lucide-react"
import {
  useContentReferences,
  useCreateContentReference,
  useDeleteContentReference,
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
import { PillarBadge } from "@/components/content/post-badges"

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

const HOOK_LABEL: Record<HookType, string> = Object.fromEntries(
  HOOK_OPTIONS.map((o) => [o.value, o.label]),
) as Record<HookType, string>

function emptyForm(): ContentReferenceCreate {
  return {
    body: "",
    author_name: null,
    author_title: null,
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

  const [sheetOpen, setSheetOpen] = useState(false)
  const [form, setForm] = useState<ContentReferenceCreate>(emptyForm())
  const [pillarFilter, setPillarFilter] = useState<PostPillar | "all">("all")
  const [hookFilter, setHookFilter] = useState<HookType | "all">("all")

  const filteredRefs = (references ?? []).filter((ref) => {
    if (pillarFilter !== "all" && ref.pillar !== pillarFilter) return false
    if (hookFilter !== "all" && ref.hook_type !== hookFilter) return false
    return true
  })

  function handleChange(field: keyof ContentReferenceCreate, value: string | number | null) {
    setForm((prev) => ({ ...prev, [field]: value === "" ? null : value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.body.trim()) return
    await createRef.mutateAsync(form)
    setForm(emptyForm())
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
        <Button size="sm" className="gap-1.5" onClick={() => setSheetOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          Adicionar
        </Button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="h-4 w-4 text-(--text-tertiary)" />
        <Select
          value={pillarFilter}
          onValueChange={(v) => setPillarFilter(v as PostPillar | "all")}
        >
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Todos os pilares" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" className="text-xs">
              Todos os pilares
            </SelectItem>
            {PILLAR_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value} className="text-xs">
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={hookFilter} onValueChange={(v) => setHookFilter(v as HookType | "all")}>
          <SelectTrigger className="h-8 w-44 text-xs">
            <SelectValue placeholder="Todos os ganchos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" className="text-xs">
              Todos os ganchos
            </SelectItem>
            {HOOK_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value} className="text-xs">
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filteredRefs.map((ref) => (
            <ReferenceCard
              key={ref.id}
              reference={ref}
              onDelete={() => deleteRef.mutate(ref.id)}
              isDeleting={deleteRef.isPending && deleteRef.variables === ref.id}
            />
          ))}
        </div>
      )}

      {/* Dialog de criação */}
      <Dialog open={sheetOpen} onOpenChange={setSheetOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nova referência</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4 py-4">
            <div className="grid gap-1.5">
              <Label htmlFor="ref-body">Texto do post *</Label>
              <Textarea
                id="ref-body"
                value={form.body}
                onChange={(e) => setForm((p) => ({ ...p, body: e.target.value }))}
                placeholder="Cole aqui o texto completo do post de referência..."
                rows={8}
                required
                className="resize-none text-sm font-mono"
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
              <Label htmlFor="ref-source_url">URL da fonte</Label>
              <Input
                id="ref-source_url"
                type="url"
                value={form.source_url ?? ""}
                onChange={(e) => handleChange("source_url", e.target.value)}
                placeholder="https://linkedin.com/posts/..."
              />
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
                onClick={() => setSheetOpen(false)}
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

// ── Card individual ───────────────────────────────────────────────────

interface ReferenceCardProps {
  reference: ContentReference
  onDelete: () => void
  isDeleting: boolean
}

function ReferenceCard({ reference, onDelete, isDeleting }: ReferenceCardProps) {
  const [expanded, setExpanded] = useState(false)

  const initials = (reference.author_name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 flex flex-col gap-3 shadow-sm">
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

      {/* Barra de engajamento */}
      {reference.engagement_score !== null && (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-(--bg-overlay) rounded-full overflow-hidden">
            <div
              className={`h-full bg-(--accent) rounded-full transition-all [--bar-w:${reference.engagement_score}%] w-(--bar-w)`}
            />
          </div>
          <span className="text-xs text-(--text-tertiary) tabular-nums shrink-0">
            {reference.engagement_score}/100
          </span>
        </div>
      )}

      {/* Corpo do post */}
      <button type="button" className="text-left" onClick={() => setExpanded((v) => !v)}>
        <p
          className={`text-sm text-(--text-secondary) whitespace-pre-wrap leading-relaxed ${!expanded ? "line-clamp-3" : ""}`}
        >
          {reference.body}
        </p>
        <span className="text-xs text-(--accent) mt-1 inline-block">
          {expanded ? "Recolher" : `${reference.body.length} chars · Ver tudo`}
        </span>
      </button>

      {/* Notas */}
      {reference.notes && (
        <p className="text-xs text-(--text-tertiary) italic border-t border-(--border-default) pt-2">
          {reference.notes}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-(--border-default)">
        {reference.pillar && <PillarBadge pillar={reference.pillar} />}
        {reference.hook_type && (
          <span className="inline-flex items-center rounded-full border border-(--border-default) px-2 py-0.5 text-xs text-(--text-tertiary)">
            {HOOK_LABEL[reference.hook_type]}
          </span>
        )}
        <div className="flex items-center gap-1 ml-auto">
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
