"use client"

import { useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Loader2, FileText, CheckCircle2, AlertCircle, Ban } from "lucide-react"
import { Button } from "@/components/ui/button"
import { NotionLogo } from "@/components/ui/notion-logo"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Checkbox } from "@/components/ui/checkbox"
import { PillarBadge } from "@/components/content/post-badges"
import {
  useNotionPreview,
  useImportFromNotion,
  type NotionPostPreview,
} from "@/lib/api/hooks/use-content"
import type { PostPillar } from "@/lib/api/hooks/use-content"

type Phase = "preview" | "importing" | "result"

interface NotionImportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function NotionImportDialog({ open, onOpenChange }: NotionImportDialogProps) {
  const [phase, setPhase] = useState<Phase>("preview")
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [result, setResult] = useState<{
    imported: number
    skipped: number
    failed: number
  } | null>(null)

  const qc = useQueryClient()

  // Busca posts do Notion apenas quando o dialog está aberto
  const {
    data: posts,
    isLoading,
    error: fetchError,
  } = useNotionPreview(open && phase === "preview")
  const importMutation = useImportFromNotion()

  function handleClose() {
    onOpenChange(false)
    // Reset state depois que a animação de fechar termina
    setTimeout(() => {
      setPhase("preview")
      setSelected(new Set())
      setResult(null)
    }, 300)
  }

  function toggleSelect(pageId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(pageId)) {
        next.delete(pageId)
      } else {
        next.add(pageId)
      }
      return next
    })
  }

  function handleSelectAll() {
    if (!posts) return
    const importable = posts.filter((p) => !p.already_imported).map((p) => p.page_id)
    setSelected(new Set(importable))
  }

  function handleDeselectAll() {
    setSelected(new Set())
  }

  async function handleImport() {
    if (selected.size === 0) return
    setPhase("importing")
    try {
      const res = await importMutation.mutateAsync(Array.from(selected))
      setResult({ imported: res.imported, skipped: res.skipped, failed: res.failed })
      setPhase("result")
      // Força refetch imediato da listagem — não depende do intervalo de 5 min
      void qc.refetchQueries({ queryKey: ["content", "posts"] })
    } catch {
      // Volta para preview com erro exibido via importMutation.error
      setPhase("preview")
    }
  }

  const importablePosts = posts?.filter((p) => !p.already_imported) ?? []
  const allImportableSelected =
    importablePosts.length > 0 && importablePosts.every((p) => selected.has(p.page_id))

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) handleClose()
      }}
    >
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col gap-0 p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-(--border-default)">
          <DialogTitle className="flex items-center gap-2 text-base font-semibold">
            <NotionLogo className="h-4 w-4" />
            Importar posts do Notion
          </DialogTitle>
        </DialogHeader>

        {/* ── Fase: preview ────────────────────────────────────────── */}
        {phase === "preview" && (
          <>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {isLoading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3 text-(--text-secondary)">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span className="text-sm">Buscando posts do Notion…</span>
                </div>
              )}

              {(fetchError || importMutation.error) && !isLoading && (
                <div className="flex items-start gap-3 rounded-lg bg-(--danger-subtle) p-4 text-(--danger-subtle-fg)">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  <p className="text-sm leading-relaxed">
                    {(fetchError as Error)?.message ??
                      (importMutation.error as Error)?.message ??
                      "Erro desconhecido"}
                  </p>
                </div>
              )}

              {!isLoading && !fetchError && posts && posts.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 gap-2 text-(--text-secondary)">
                  <FileText className="h-8 w-8 opacity-30" />
                  <p className="text-sm">Nenhum post encontrado no banco de dados Notion.</p>
                </div>
              )}

              {!isLoading && !fetchError && posts && posts.length > 0 && (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm text-(--text-secondary)">
                      {importablePosts.length} disponíve{importablePosts.length === 1 ? "l" : "is"}{" "}
                      para importar
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={allImportableSelected ? handleDeselectAll : handleSelectAll}
                        disabled={importablePosts.length === 0}
                      >
                        {allImportableSelected ? "Desmarcar todos" : "Selecionar todos"}
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {posts.map((post) => (
                      <NotionPostRow
                        key={post.page_id}
                        post={post}
                        checked={selected.has(post.page_id)}
                        onToggle={() => toggleSelect(post.page_id)}
                      />
                    ))}
                  </div>

                  {posts.some((p) => p.already_imported) && (
                    <p className="mt-3 text-xs text-(--text-tertiary) flex items-center gap-1.5">
                      <Ban className="h-3 w-3 shrink-0" />
                      Posts marcados como &quot;Já importado&quot; não serão importados novamente.
                    </p>
                  )}
                </>
              )}
            </div>

            <DialogFooter className="px-6 py-4 border-t border-(--border-default) flex items-center justify-between w-full">
              <Button variant="ghost" size="sm" onClick={handleClose}>
                Cancelar
              </Button>
              <Button size="sm" onClick={handleImport} disabled={selected.size === 0 || isLoading}>
                Importar ({selected.size})
              </Button>
            </DialogFooter>
          </>
        )}

        {/* ── Fase: importing ──────────────────────────────────────── */}
        {phase === "importing" && (
          <div className="flex flex-col items-center justify-center py-16 gap-4 text-(--text-secondary)">
            <Loader2 className="h-8 w-8 animate-spin text-(--accent-default)" />
            <div className="text-center">
              <p className="text-sm font-medium text-(--text-primary)">Importando posts…</p>
              <p className="text-xs mt-1">
                Aguarde enquanto os posts são criados e o Notion é atualizado.
              </p>
            </div>
          </div>
        )}

        {/* ── Fase: result ─────────────────────────────────────────── */}
        {phase === "result" && result && (
          <>
            <div className="flex-1 px-6 py-8">
              <div className="flex flex-col items-center gap-4 text-center">
                <div className="rounded-full bg-(--success-subtle) p-3">
                  <CheckCircle2 className="h-6 w-6 text-(--success-default)" />
                </div>
                <div>
                  <p className="text-base font-semibold text-(--text-primary)">
                    Importação concluída
                  </p>
                  <p className="text-sm text-(--text-secondary) mt-1">
                    Os posts foram adicionados ao Content Hub com status Rascunho.
                  </p>
                </div>

                <div className="w-full max-w-xs grid grid-cols-3 gap-4 mt-2">
                  <ResultStat label="Importados" value={result.imported} variant="success" />
                  <ResultStat label="Ignorados" value={result.skipped} variant="neutral" />
                  <ResultStat label="Falhos" value={result.failed} variant="danger" />
                </div>

                {result.failed > 0 && (
                  <p className="text-xs text-(--warning-default) mt-1">
                    {result.failed} post{result.failed > 1 ? "s" : ""} não puderam ser importados.
                    Tente novamente individualmente ou verifique os dados no Notion.
                  </p>
                )}
              </div>
            </div>

            <DialogFooter className="px-6 py-4 border-t border-(--border-default)">
              <Button size="sm" onClick={handleClose}>
                Fechar
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ── Sub-componentes ───────────────────────────────────────────────────

function NotionPostRow({
  post,
  checked,
  onToggle,
}: {
  post: NotionPostPreview
  checked: boolean
  onToggle: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const isDisabled = post.already_imported

  return (
    <div
      className={`rounded-lg border transition-colors ${
        isDisabled
          ? "opacity-60 border-(--border-default) bg-(--bg-canvas)"
          : checked
            ? "border-(--accent-default) bg-(--accent-subtle)"
            : "border-(--border-default) hover:bg-(--bg-overlay)"
      }`}
    >
      {/* Linha principal — checkbox + info */}
      <label
        className={`flex items-start gap-3 p-3 ${isDisabled ? "cursor-default" : "cursor-pointer"}`}
      >
        <Checkbox
          checked={isDisabled ? false : checked}
          onCheckedChange={() => {
            if (!isDisabled) onToggle()
          }}
          disabled={isDisabled}
          className="mt-0.5 shrink-0"
        />
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-(--text-primary) truncate">
              {post.title || "(Sem título)"}
            </span>
            {post.pillar && <PillarBadge pillar={post.pillar as PostPillar} />}
            {isDisabled && (
              <span className="shrink-0 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-1.5 py-0.5 text-xs font-medium">
                Já importado
              </span>
            )}
          </div>

          {post.body_preview && !expanded && (
            <p className="text-xs text-(--text-secondary) line-clamp-1">{post.body_preview}</p>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            {post.publish_date && (
              <span className="inline-flex items-center gap-1 rounded bg-(--bg-overlay) px-1.5 py-0.5 text-xs text-(--text-secondary) font-medium">
                📅 {formatDate(post.publish_date)}
              </span>
            )}
            {post.week_number != null && (
              <span className="inline-flex items-center gap-1 rounded bg-(--bg-overlay) px-1.5 py-0.5 text-xs text-(--text-secondary) font-medium">
                Semana {post.week_number}
              </span>
            )}
            {post.hashtags && (
              <span className="text-xs text-(--text-tertiary) truncate max-w-60">{post.hashtags}</span>
            )}
          </div>
        </div>
        {/* Botão expandir */}
        {post.body_preview && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault()
              setExpanded((v) => !v)
            }}
            className="shrink-0 text-xs text-(--text-tertiary) hover:text-(--text-primary) underline underline-offset-2 mt-0.5 whitespace-nowrap"
            aria-label={expanded ? "Ocultar texto" : "Ver texto completo"}
          >
            {expanded ? "Ocultar" : "Ver texto"}
          </button>
        )}{" "}
      </label>

      {/* Texto expandido */}
      {expanded && post.body && (
        <div className="px-3 pb-3 pt-0 border-t border-(--border-default) mt-0">
          <p className="text-xs text-(--text-secondary) whitespace-pre-wrap leading-relaxed pt-2">
            {post.body}
          </p>
        </div>
      )}
    </div>
  )
}

function ResultStat({
  label,
  value,
  variant,
}: {
  label: string
  value: number
  variant: "success" | "neutral" | "danger"
}) {
  const styles = {
    success: "text-(--success-default)",
    neutral: "text-(--text-secondary)",
    danger: "text-(--danger-default)",
  }
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg bg-(--bg-overlay) p-3">
      <span className={`text-2xl font-bold ${styles[variant]}`}>{value}</span>
      <span className="text-xs text-(--text-secondary)">{label}</span>
    </div>
  )
}

function formatDate(dateStr: string): string {
  try {
    // Adiciona T12:00:00 para evitar off-by-one por timezone ao parsear datas no formato YYYY-MM-DD
    const normalized = dateStr.length === 10 ? `${dateStr}T12:00:00` : dateStr
    return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" }).format(
      new Date(normalized),
    )
  } catch {
    return dateStr
  }
}
