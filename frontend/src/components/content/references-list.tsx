"use client"

import { useState } from "react"
import { BookOpen, Plus, Trash2, ExternalLink, Loader2 } from "lucide-react"
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
      ) : (
        <div className="grid gap-3">
          {references.map((ref) => (
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

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 flex flex-col gap-2 shadow-sm">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {reference.pillar && <PillarBadge pillar={reference.pillar} />}
            {reference.hook_type && (
              <span className="inline-flex items-center rounded-full border border-(--border-default) px-2 py-0.5 text-xs text-(--text-tertiary)">
                {reference.hook_type.replace("_", " ")}
              </span>
            )}
            {reference.engagement_score !== null && (
              <span className="text-xs text-(--text-tertiary)">
                ⚡ {reference.engagement_score}/100
              </span>
            )}
          </div>
          {(reference.author_name || reference.author_title) && (
            <p className="text-xs text-(--text-secondary)">
              {[reference.author_name, reference.author_title].filter(Boolean).join(" · ")}
            </p>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
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

      {/* Preview do texto */}
      <button
        type="button"
        className="text-left cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <p
          className={`text-sm text-(--text-secondary) whitespace-pre-wrap ${!expanded ? "line-clamp-3" : ""}`}
        >
          {reference.body}
        </p>
        <span className="text-xs text-(--accent) mt-1">
          {expanded ? "Recolher" : `${reference.body.length} chars · Ver tudo`}
        </span>
      </button>

      {/* Notas */}
      {reference.notes && (
        <p className="text-xs text-(--text-tertiary) italic border-t border-(--border-default) pt-2 mt-1">
          {reference.notes}
        </p>
      )}
    </div>
  )
}
