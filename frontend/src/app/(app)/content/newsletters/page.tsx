"use client"

import { useState } from "react"
import { format, parseISO } from "date-fns"
import { ptBR } from "date-fns/locale"
import {
  Plus,
  Sparkles,
  Trash2,
  Calendar,
  CheckCircle2,
  Pencil,
  ExternalLink,
  FileText,
  ArrowUpDown,
  Eye,
  ThumbsUp,
  MessageSquare,
  Repeat2,
} from "lucide-react"
import { Button, buttonVariants } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import {
  useContentNewsletters,
  useCreateNewsletter,
  useDeleteNewsletter,
  type ContentNewsletter,
  type NewsletterStatus,
} from "@/lib/api/hooks/use-content-newsletters"
import { CreateNewsletterDialog } from "@/components/content/create-newsletter-dialog"
import { EditNewsletterDialog } from "@/components/content/edit-newsletter-dialog"
import { NotionNewsletterImportDialog } from "@/components/content/notion-newsletter-import-dialog"
import { NotionLogo } from "@/components/ui/notion-logo"

const STATUS_LABEL: Record<NewsletterStatus, string> = {
  draft: "Rascunho",
  validated: "Validada",
  approved: "Aprovada",
  scheduled: "Agendada",
  published: "Publicada",
  failed: "Falhou",
  deleted: "Excluída",
}

const STATUS_VARIANT: Record<
  NewsletterStatus,
  "default" | "outline" | "success" | "warning" | "danger" | "neutral" | "info"
> = {
  draft: "outline",
  validated: "info",
  approved: "info",
  scheduled: "warning",
  published: "success",
  failed: "danger",
  deleted: "neutral",
}

type SortKey = "edition" | "title" | "updated_at" | "published_at" | "views" | "reactions"

function sortNewsletters(
  list: ContentNewsletter[],
  key: SortKey,
  dir: "asc" | "desc",
): ContentNewsletter[] {
  const sorted = [...list]
  const mul = dir === "asc" ? 1 : -1
  return sorted.sort((a, b) => {
    switch (key) {
      case "edition":
        return mul * (a.edition_number - b.edition_number)
      case "title":
        return mul * a.title.localeCompare(b.title, "pt-BR")
      case "views":
        return mul * ((a.pulse_views_count ?? -1) - (b.pulse_views_count ?? -1))
      case "reactions":
        return mul * ((a.pulse_reactions_count ?? -1) - (b.pulse_reactions_count ?? -1))
      case "published_at": {
        const da = a.published_at ? new Date(a.published_at).getTime() : 0
        const db = b.published_at ? new Date(b.published_at).getTime() : 0
        return mul * (da - db)
      }
      case "updated_at":
      default:
        return mul * (new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime())
    }
  })
}

const GRID = "grid-cols-[44px_120px_1fr_110px_70px_70px_70px_70px_120px_120px_36px_100px]"

export default function NewslettersPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [notionOpen, setNotionOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ContentNewsletter | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>("edition")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")

  const { data: rawList = [], isLoading } = useContentNewsletters()
  const createMutation = useCreateNewsletter()
  const deleteMutation = useDeleteNewsletter()

  const list = sortNewsletters(rawList, sortKey, sortDir)

  function handleSort(key: SortKey) {
    if (key === sortKey) setSortDir((d) => (d === "desc" ? "asc" : "desc"))
    else {
      setSortKey(key)
      setSortDir("desc")
    }
  }

  function SortBtn({
    label,
    col,
    className,
  }: {
    label: string
    col: SortKey
    className?: string
  }) {
    const active = sortKey === col
    return (
      <button
        type="button"
        onClick={() => handleSort(col)}
        className={cn(
          "inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wide transition-colors",
          active
            ? "bg-white/14 text-(--text-invert) ring-1 ring-white/20"
            : "text-(--text-invert) hover:text-amber-300",
          className,
        )}
      >
        {label}
        <ArrowUpDown
          className={cn("h-3 w-3", active ? "opacity-100" : "opacity-50")}
        />
      </button>
    )
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-(--text-primary)">Newsletters quinzenais</h2>
          <p className="text-sm text-(--text-secondary)">
            Operação Inteligente — 1.000–1.400 palavras, 5 seções fixas
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setNotionOpen(true)} className="gap-1.5">
            <NotionLogo className="h-3.5 w-3.5" />
            Importar do Notion
          </Button>
          <Button onClick={() => setCreateOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Nova edição
          </Button>
        </div>
      </div>

      {isLoading && (
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) h-40 animate-pulse" />
      )}

      {!isLoading && rawList.length === 0 && (
        <div className="rounded-lg border border-dashed border-(--border-default) p-8 text-center">
          <Sparkles className="mx-auto h-10 w-10 text-(--text-tertiary)" />
          <p className="mt-3 text-sm text-(--text-secondary)">
            Nenhuma newsletter criada ainda. Comece criando a primeira edição.
          </p>
        </div>
      )}

      {!isLoading && list.length > 0 && (
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) overflow-hidden shadow-sm">
          {/* Header */}
          <div
            className={cn(
              "grid gap-2 px-4 py-2.5 border-b border-(--border-default) bg-(--accent) text-xs font-medium text-(--text-invert) uppercase tracking-wide items-center",
              GRID,
            )}
          >
            {/* Capa */}
            <span />
            {/* Edição */}
            <SortBtn label="Edição" col="edition" />
            {/* Título */}
            <SortBtn label="Título" col="title" />
            {/* Status */}
            <span className="px-2 py-1 text-xs font-semibold uppercase tracking-wide">Status</span>
            {/* Views */}
            <SortBtn label="Views" col="views" className="justify-center" />
            {/* Reações */}
            <SortBtn label="Reaç" col="reactions" className="justify-center" />
            {/* Coments */}
            <span className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-center">Com.</span>
            {/* Reshares */}
            <span className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-center">Re.</span>
            {/* Publicado */}
            <SortBtn label="Publicado" col="published_at" />
            {/* Atualizado */}
            <SortBtn label="Atualizado" col="updated_at" />
            {/* Link */}
            <span />
            {/* Ações */}
            <span className="text-center px-2 py-1">Ações</span>
          </div>

          {/* Rows */}
          {list.map((nl) => (
            <NewsletterRow
              key={nl.id}
              nl={nl}
              onEdit={() => setEditingId(nl.id)}
              onDelete={() => setDeleteTarget(nl)}
              gridCols={GRID}
            />
          ))}
        </div>
      )}

      <CreateNewsletterDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={async (data) => {
          await createMutation.mutateAsync(data)
          setCreateOpen(false)
        }}
        isPending={createMutation.isPending}
      />

      {editingId && (
        <EditNewsletterDialog
          newsletterId={editingId}
          open={!!editingId}
          onOpenChange={(open) => !open && setEditingId(null)}
        />
      )}

      <NotionNewsletterImportDialog open={notionOpen} onOpenChange={setNotionOpen} />

      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Mover para a lixeira?</AlertDialogTitle>
            <AlertDialogDescription>
              A edição{deleteTarget ? ` #${deleteTarget.edition_number} — ${deleteTarget.title || "Sem título"}` : ""} será movida para a lixeira e poderá ser recuperada depois.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className={buttonVariants({ variant: "destructive" })}
              onClick={() => {
                if (deleteTarget) deleteMutation.mutate(deleteTarget.id)
                setDeleteTarget(null)
              }}
            >
              Mover para lixeira
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function NewsletterRow({
  nl,
  onEdit,
  onDelete,
  gridCols,
}: {
  nl: ContentNewsletter
  onEdit: () => void
  onDelete: () => void
  gridCols: string
}) {
  const metricCell = (value: number | null, icon: React.ReactNode, label: string) => (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="flex items-center justify-center gap-1 text-(--text-secondary)">
            {icon}
            {value != null ? value.toLocaleString("pt-BR") : <span className="text-(--text-tertiary)">—</span>}
          </span>
        </TooltipTrigger>
        <TooltipContent>{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )

  return (
    <div
      className={cn(
        "grid gap-2 px-4 py-3 border-b border-(--border-default) last:border-b-0 hover:bg-(--bg-overlay) transition-colors items-center text-xs",
        gridCols,
      )}
    >
      {/* Cover thumbnail */}
      <div className="h-8 w-8 shrink-0 overflow-hidden rounded border border-(--border-default) bg-(--bg-tertiary) flex items-center justify-center">
        {nl.cover_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={nl.cover_image_url} alt="capa" className="h-full w-full object-cover" />
        ) : (
          <FileText className="h-4 w-4 text-(--text-tertiary)" />
        )}
      </div>

      {/* Edition number */}
      <span className="font-mono font-semibold text-(--text-secondary)"># {nl.edition_number}</span>

      {/* Title */}
      <button
        type="button"
        onClick={onEdit}
        className="text-left font-medium text-(--text-primary) truncate hover:text-(--accent) transition-colors"
      >
        {nl.title || <em className="text-(--text-tertiary) font-normal">Sem título</em>}
      </button>

      {/* Status */}
      <div>
        <Badge variant={STATUS_VARIANT[nl.status]}>{STATUS_LABEL[nl.status]}</Badge>
      </div>

      {/* Views */}
      {metricCell(nl.pulse_views_count, <Eye className="h-3 w-3" />, "Visualizações (Pulse)")}
      {/* Reactions */}
      {metricCell(nl.pulse_reactions_count, <ThumbsUp className="h-3 w-3" />, "Reações")}
      {/* Comments */}
      {metricCell(nl.pulse_comments_count, <MessageSquare className="h-3 w-3" />, "Comentários")}
      {/* Reposts */}
      {metricCell(nl.pulse_reposts_count, <Repeat2 className="h-3 w-3" />, "Reshares")}

      {/* Published at */}
      <span className="text-(--text-tertiary)">
        {nl.published_at ? (
          <span className="inline-flex items-center gap-1 text-(--success)">
            <CheckCircle2 className="h-3 w-3" />
            {format(parseISO(nl.published_at), "dd/MM/yyyy", { locale: ptBR })}
          </span>
        ) : nl.scheduled_for ? (
          <span className="inline-flex items-center gap-1 text-(--warning)">
            <Calendar className="h-3 w-3" />
            {format(parseISO(nl.scheduled_for), "dd/MM HH:mm", { locale: ptBR })}
          </span>
        ) : (
          <span className="text-(--text-tertiary)">—</span>
        )}
      </span>

      {/* Updated at */}
      <span className="text-(--text-tertiary)">
        {format(parseISO(nl.updated_at), "dd/MM/yy HH:mm", { locale: ptBR })}
      </span>

      {/* External link */}
      <div className="flex justify-center">
        {nl.linkedin_pulse_url ? (
          <a
            href={nl.linkedin_pulse_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir no LinkedIn Pulse"
            className="text-(--text-tertiary) hover:text-(--accent) transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : null}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-center gap-1">
        <Button variant="ghost" size="icon" onClick={onEdit} title="Editar">
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" onClick={onDelete} title="Excluir">
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
