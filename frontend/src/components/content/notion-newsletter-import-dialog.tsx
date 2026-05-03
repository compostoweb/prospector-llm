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
import {
  useNotionNewsletterPreview,
  useImportNewslettersFromNotion,
  type NotionNewsletterPreview,
} from "@/lib/api/hooks/use-content-newsletters"

type Phase = "preview" | "importing" | "result"

interface NotionNewsletterImportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function NotionNewsletterImportDialog({
  open,
  onOpenChange,
}: NotionNewsletterImportDialogProps) {
  const [phase, setPhase] = useState<Phase>("preview")
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [result, setResult] = useState<{
    imported: number
    skipped: number
    failed: number
  } | null>(null)

  const qc = useQueryClient()

  const {
    data: newsletters,
    isLoading,
    error: fetchError,
  } = useNotionNewsletterPreview(open && phase === "preview")
  const importMutation = useImportNewslettersFromNotion()

  function handleClose() {
    onOpenChange(false)
    setTimeout(() => {
      setPhase("preview")
      setSelected(new Set())
      setResult(null)
    }, 300)
  }

  function toggleSelect(pageId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(pageId)) next.delete(pageId)
      else next.add(pageId)
      return next
    })
  }

  function handleSelectAll() {
    if (!sorted) return
    const ids = sorted.filter((n) => !n.already_imported).map((n) => n.page_id)
    setSelected(new Set(ids))
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
      void qc.refetchQueries({ queryKey: ["content-newsletters"] })
    } catch {
      setPhase("preview")
    }
  }

  const sorted = newsletters
    ? [...newsletters].sort((a, b) => (a.edition_number ?? 0) - (b.edition_number ?? 0))
    : undefined
  const IMPORTABLE_STATUSES = ["approved", "published"]
  const importable = sorted?.filter(
    (n) => !n.already_imported && IMPORTABLE_STATUSES.includes(n.status_notion ?? ""),
  ) ?? []
  const allImportableSelected =
    importable.length > 0 && importable.every((n) => selected.has(n.page_id))

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose() }}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col gap-0 p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-(--border-default)">
          <DialogTitle className="flex items-center gap-2 text-base font-semibold">
            <NotionLogo className="h-4 w-4" />
            Importar newsletters do Notion
          </DialogTitle>
        </DialogHeader>

        {/* ── Fase: preview ─────────────────────────────────────── */}
        {phase === "preview" && (
          <>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {isLoading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3 text-(--text-secondary)">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span className="text-sm">Buscando newsletters do Notion…</span>
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

              {!isLoading && !fetchError && sorted && sorted.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 gap-2 text-(--text-secondary)">
                  <FileText className="h-8 w-8 opacity-30" />
                  <p className="text-sm">Nenhuma newsletter encontrada no banco de dados Notion.</p>
                </div>
              )}

              {!isLoading && !fetchError && sorted && sorted.length > 0 && (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm text-(--text-secondary)">
                      {importable.length} disponíve{importable.length === 1 ? "l" : "is"} para
                      importar
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={allImportableSelected ? handleDeselectAll : handleSelectAll}
                      disabled={importable.length === 0}
                    >
                      {allImportableSelected ? "Desmarcar todas" : "Selecionar todas"}
                    </Button>
                  </div>

                  <div className="space-y-2">
                    {sorted.map((nl) => (
                      <NotionNewsletterRow
                        key={nl.page_id}
                        newsletter={nl}
                        checked={selected.has(nl.page_id)}
                        onToggle={() => toggleSelect(nl.page_id)}
                      />
                    ))}
                  </div>

                  {sorted.some((n) => n.already_imported) && (
                    <p className="mt-3 text-xs text-(--text-tertiary) flex items-center gap-1.5">
                      <Ban className="h-3 w-3 shrink-0" />
                      Edições marcadas como &quot;Já importada&quot; não serão importadas novamente.
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

        {/* ── Fase: importing ───────────────────────────────────── */}
        {phase === "importing" && (
          <div className="flex flex-col items-center justify-center py-16 gap-4 text-(--text-secondary)">
            <Loader2 className="h-8 w-8 animate-spin text-(--accent-default)" />
            <div className="text-center">
              <p className="text-sm font-medium text-(--text-primary)">Importando newsletters…</p>
              <p className="text-xs mt-1">
                Aguarde enquanto as edições são criadas e o Notion é atualizado.
              </p>
            </div>
          </div>
        )}

        {/* ── Fase: result ──────────────────────────────────────── */}
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
                    As newsletters foram adicionadas ao Content Hub com status Rascunho.
                  </p>
                </div>

                <div className="w-full max-w-xs grid grid-cols-3 gap-4 mt-2">
                  <ResultStat label="Importadas" value={result.imported} variant="success" />
                  <ResultStat label="Ignoradas" value={result.skipped} variant="neutral" />
                  <ResultStat label="Falhas" value={result.failed} variant="danger" />
                </div>

                {result.failed > 0 && (
                  <p className="text-xs text-(--warning-default) mt-1">
                    {result.failed} edição{result.failed > 1 ? "ões" : ""} não pôde ser importada.
                    Verifique os dados no Notion e tente novamente.
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

function statusBadgeClass(status: string): string {
  switch (status) {
    case "draft":
      return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
    case "approved":
      return "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
    case "scheduled":
      return "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
    case "published":
      return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
    default:
      return "bg-(--bg-overlay) text-(--text-secondary)"
  }
}

function NotionNewsletterRow({
  newsletter,
  checked,
  onToggle,
}: {
  newsletter: NotionNewsletterPreview
  checked: boolean
  onToggle: () => void
}) {
  const IMPORTABLE_STATUSES = ["approved", "published"]
  const isAlreadyImported = newsletter.already_imported
  const isStatusBlocked =
    !isAlreadyImported && !IMPORTABLE_STATUSES.includes(newsletter.status_notion ?? "")
  const isDisabled = isAlreadyImported || isStatusBlocked

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
      <label
        className={`flex items-start gap-3 p-3 ${isDisabled ? "cursor-default" : "cursor-pointer"}`}
      >
        <Checkbox
          checked={isDisabled ? false : checked}
          onCheckedChange={() => { if (!isDisabled) onToggle() }}
          disabled={isDisabled}
          className="mt-0.5 shrink-0"
        />
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            {newsletter.edition_number != null && (
              <span className="shrink-0 rounded bg-(--bg-overlay) px-1.5 py-0.5 text-xs font-medium text-(--text-secondary)">
                #{newsletter.edition_number}
              </span>
            )}
            <span className="text-sm font-medium text-(--text-primary) truncate">
              {newsletter.title || "(Sem título)"}
            </span>
            {isAlreadyImported && (
              <span className="shrink-0 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-1.5 py-0.5 text-xs font-medium">
                Já importada
              </span>
            )}
            {isStatusBlocked && (
              <span className="shrink-0 rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 px-1.5 py-0.5 text-xs font-medium">
                Só aprovadas/publicadas
              </span>
            )}
            {newsletter.status_notion && !isAlreadyImported && (
              <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-xs font-medium ${statusBadgeClass(newsletter.status_notion)}`}>
                {newsletter.status_notion}
              </span>
            )}
          </div>

          {newsletter.subtitle && (
            <p className="text-xs text-(--text-secondary) line-clamp-1">{newsletter.subtitle}</p>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            {newsletter.scheduled_for && (
              <span className="inline-flex items-center gap-1 rounded bg-(--bg-overlay) px-1.5 py-0.5 text-xs text-(--text-secondary) font-medium">
                📅 {formatDate(newsletter.scheduled_for)}
              </span>
            )}
            {newsletter.body_preview && (
              <span className="text-xs text-(--text-tertiary) truncate max-w-80">
                {newsletter.body_preview}
              </span>
            )}
          </div>
        </div>
      </label>
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
    const normalized = dateStr.length === 10 ? `${dateStr}T12:00:00` : dateStr
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(normalized))
  } catch {
    return dateStr
  }
}
