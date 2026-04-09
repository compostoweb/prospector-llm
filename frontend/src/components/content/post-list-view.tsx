"use client"

import { useState } from "react"
import { formatDateBR } from "@/lib/date"
import {
  ExternalLink,
  Eye,
  Heart,
  MessageCircle,
  TrendingUp,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Bookmark,
  Pencil,
  Check,
  Clock,
  Send,
  XCircle,
  Trash2,
  ChevronDown,
  ImageIcon,
  VideoIcon,
  Filter,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { StatusBadge, PillarBadge } from "@/components/content/post-badges"
import { NotionLogo } from "@/components/ui/notion-logo"
import { EditPostDialog } from "@/components/content/edit-post-dialog"
import {
  useApprovePost,
  useSchedulePost,
  useCancelSchedule,
  usePublishNow,
  useDeletePost,
  type ContentPost,
} from "@/lib/api/hooks/use-content"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
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

export type SortKey = "recent" | "impressions" | "likes" | "comments" | "saves" | "engagement"
export type SortDir = "desc" | "asc"

interface PostListViewProps {
  posts: ContentPost[]
  sortBy: SortKey
  onSortChange: (key: SortKey) => void
}

function sortPosts(posts: ContentPost[], sortBy: SortKey, sortDir: SortDir): ContentPost[] {
  const sorted = [...posts]
  const dir = sortDir === "asc" ? 1 : -1
  switch (sortBy) {
    case "recent":
      return sorted.sort((a, b) => {
        const da = a.published_at ?? a.publish_date ?? a.created_at
        const db = b.published_at ?? b.publish_date ?? b.created_at
        return dir * (new Date(da).getTime() - new Date(db).getTime())
      })
    case "impressions":
      return sorted.sort((a, b) => dir * (a.impressions - b.impressions))
    case "likes":
      return sorted.sort((a, b) => dir * (a.likes - b.likes))
    case "comments":
      return sorted.sort((a, b) => dir * (a.comments - b.comments))
    case "saves":
      return sorted.sort((a, b) => dir * (a.saves - b.saves))
    case "engagement":
      return sorted.sort((a, b) => dir * ((a.engagement_rate ?? 0) - (b.engagement_rate ?? 0)))
    default:
      return sorted
  }
}

function getLinkedInUrl(urn: string | null): string | null {
  if (!urn) return null
  return `https://www.linkedin.com/feed/update/${urn}`
}

export function PostListView({ posts, sortBy, onSortChange }: PostListViewProps) {
  const [editPost, setEditPost] = useState<ContentPost | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [pillarFilter, setPillarFilter] = useState<string>("all")
  const [sortDir, setSortDir] = useState<SortDir>("desc")

  function handleSortChange(key: SortKey) {
    if (key === sortBy) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"))
    } else {
      onSortChange(key)
      setSortDir("desc")
    }
  }

  const sortedPosts = sortPosts(posts, sortBy, sortDir).filter(
    (p) =>
      (statusFilter === "all" || p.status === statusFilter) &&
      (pillarFilter === "all" || p.pillar === pillarFilter),
  )
  const allSelected = sortedPosts.length > 0 && sortedPosts.every((p) => selectedIds.has(p.id))
  const someSelected = !allSelected && sortedPosts.some((p) => selectedIds.has(p.id))

  const approveMut = useApprovePost()
  const scheduleMut = useSchedulePost()
  const cancelMut = useCancelSchedule()
  const deleteMut = useDeletePost()

  function toggleAll() {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(sortedPosts.map((p) => p.id)))
    }
  }

  function toggleOne(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function bulkApprove() {
    const ids = sortedPosts
      .filter((p) => selectedIds.has(p.id) && p.status === "draft")
      .map((p) => p.id)
    await Promise.all(ids.map((id) => approveMut.mutateAsync(id)))
    setSelectedIds(new Set())
  }

  async function bulkSchedule() {
    const ids = sortedPosts
      .filter((p) => selectedIds.has(p.id) && p.status === "approved" && !!p.publish_date)
      .map((p) => p.id)
    await Promise.all(ids.map((id) => scheduleMut.mutateAsync(id)))
    setSelectedIds(new Set())
  }

  async function bulkCancel() {
    const ids = sortedPosts
      .filter((p) => selectedIds.has(p.id) && p.status === "scheduled")
      .map((p) => p.id)
    await Promise.all(ids.map((id) => cancelMut.mutateAsync(id)))
    setSelectedIds(new Set())
  }

  async function bulkDelete() {
    const ids = Array.from(selectedIds)
    await Promise.all(ids.map((id) => deleteMut.mutateAsync(id)))
    setSelectedIds(new Set())
    setShowDeleteConfirm(false)
  }

  const canApprove = sortedPosts.some((p) => selectedIds.has(p.id) && p.status === "draft")
  const canSchedule = sortedPosts.some(
    (p) => selectedIds.has(p.id) && p.status === "approved" && !!p.publish_date,
  )
  const canCancel = sortedPosts.some((p) => selectedIds.has(p.id) && p.status === "scheduled")

  const gridCols = "grid-cols-[32px_1fr_100px_90px_70px_70px_70px_70px_70px_36px_130px]"

  return (
    <>
      {/* Bulk toolbar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-sm mb-2 text-xs">
          <span className="text-(--text-secondary) font-medium mr-1">
            {selectedIds.size} selecionado{selectedIds.size !== 1 ? "s" : ""}
          </span>
          <div className="flex items-center gap-1.5 flex-1">
            {canApprove && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5"
                onClick={bulkApprove}
                disabled={approveMut.isPending}
              >
                <Check className="h-3 w-3" />
                Aprovar
              </Button>
            )}
            {canSchedule && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5"
                onClick={bulkSchedule}
                disabled={scheduleMut.isPending}
              >
                <Clock className="h-3 w-3" />
                Agendar
              </Button>
            )}
            {canCancel && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5"
                onClick={bulkCancel}
                disabled={cancelMut.isPending}
              >
                <XCircle className="h-3 w-3" />
                Cancelar agendamento
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs gap-1.5 text-(--danger) hover:text-(--danger) border-(--danger) hover:border-(--danger)"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleteMut.isPending}
            >
              <Trash2 className="h-3 w-3" />
              Excluir
            </Button>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs text-(--text-tertiary)"
            onClick={() => setSelectedIds(new Set())}
          >
            Limpar seleção
          </Button>
        </div>
      )}

      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) overflow-hidden shadow-sm">
        {/* Header */}
        <TooltipProvider delayDuration={300}>
        <div
          className={cn(
            "grid gap-2 px-4 py-2.5 border-b border-(--border-default) bg-(--bg-overlay) text-xs font-medium text-(--text-tertiary) uppercase tracking-wide items-center",
            gridCols,
          )}
        >
          <Checkbox
            checked={allSelected ? true : someSelected ? "indeterminate" : false}
            onCheckedChange={toggleAll}
            aria-label="Selecionar todos"
            className="ml-0.5"
          />
          <span>Post</span>
          {/* Filtro de Status */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className={`flex items-center gap-1 text-xs font-medium uppercase tracking-wide hover:text-(--text-primary) transition-colors ${
                  statusFilter !== "all" ? "text-(--accent)" : "text-(--text-tertiary)"
                }`}
              >
                Status
                <Filter className="h-3 w-3" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-36">
              {[
                { value: "all", label: "Todos" },
                { value: "draft", label: "Rascunho" },
                { value: "approved", label: "Aprovado" },
                { value: "scheduled", label: "Agendado" },
                { value: "published", label: "Publicado" },
                { value: "failed", label: "Falhou" },
              ].map((opt) => (
                <DropdownMenuItem
                  key={opt.value}
                  onSelect={() => setStatusFilter(opt.value)}
                  className={statusFilter === opt.value ? "font-medium text-(--accent)" : ""}
                >
                  {opt.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          {/* Filtro de Pilar */}
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
              {[
                { value: "all", label: "Todos" },
                { value: "authority", label: "Autoridade" },
                { value: "case", label: "Caso" },
                { value: "vision", label: "Visão" },
              ].map((opt) => (
                <DropdownMenuItem
                  key={opt.value}
                  onSelect={() => setPillarFilter(opt.value)}
                  className={pillarFilter === opt.value ? "font-medium text-(--accent)" : ""}
                >
                  {opt.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <SortHeader
            label="Impr."
            sortKey="impressions"
            currentSort={sortBy}
            sortDir={sortDir}
            onSort={handleSortChange}
            tooltip="Ordena por alcance total de impressões"
          />
          <SortHeader label="Likes" sortKey="likes" currentSort={sortBy} sortDir={sortDir} onSort={handleSortChange} tooltip="Ordena por número de curtidas" />
          <SortHeader label="Com." sortKey="comments" currentSort={sortBy} sortDir={sortDir} onSort={handleSortChange} tooltip="Ordena por número de comentários" />
          <SortHeader label="Salv." sortKey="saves" currentSort={sortBy} sortDir={sortDir} onSort={handleSortChange} tooltip="Ordena por número de salvamentos" />
          <SortHeader
            label="Eng."
            sortKey="engagement"
            currentSort={sortBy}
            sortDir={sortDir}
            onSort={handleSortChange}
            tooltip="Ordena por taxa de engajamento (likes+com.+salv.) / impressões"
          />
          <span />
          <span className="text-center">Ações</span>
        </div>
        </TooltipProvider>

        {/* Rows */}
        {sortedPosts.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-(--text-tertiary)">
            Nenhum post encontrado.
          </div>
        ) : (
          sortedPosts.map((post) => (
            <PostRow
              key={post.id}
              post={post}
              onEdit={() => setEditPost(post)}
              isSelected={selectedIds.has(post.id)}
              onToggleSelect={() => toggleOne(post.id)}
              gridCols={gridCols}
            />
          ))
        )}
      </div>

      {editPost && (
        <EditPostDialog
          post={editPost}
          open={!!editPost}
          onOpenChange={(open) => {
            if (!open) setEditPost(null)
          }}
        />
      )}

      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir posts selecionados?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta ação não pode ser desfeita. {selectedIds.size} post
              {selectedIds.size !== 1 ? "s" : ""} será{selectedIds.size !== 1 ? "ão" : ""}{" "}
              permanentemente excluído{selectedIds.size !== 1 ? "s" : ""}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-(--danger) hover:bg-(--danger) text-white"
              onClick={bulkDelete}
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

function SortHeader({
  label,
  sortKey,
  currentSort,
  sortDir,
  onSort,
  tooltip,
}: {
  label: string
  sortKey: SortKey
  currentSort: SortKey
  sortDir: SortDir
  onSort: (key: SortKey) => void
  tooltip: string
}) {
  const active = currentSort === sortKey
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex items-center gap-0.5">
          <button
            type="button"
            onClick={() => onSort(sortKey)}
            className={cn(
              "flex items-center gap-0.5 cursor-pointer transition-colors",
              active ? "text-(--accent)" : "hover:text-(--text-secondary)",
            )}
          >
            {label}
            {active ? (
              sortDir === "desc" ? (
                <ArrowDown className="h-3 w-3" />
              ) : (
                <ArrowUp className="h-3 w-3" />
              )
            ) : (
              <ArrowUpDown className="h-3 w-3 opacity-50" />
            )}
          </button>
          {active && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onSort("recent")
              }}
              className="ml-0.5 text-(--text-tertiary) hover:text-(--danger) transition-colors"
              aria-label="Remover ordenação"
            >
              <X className="h-2.5 w-2.5" />
            </button>
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="text-xs max-w-48 text-center">
        {tooltip}
        {active && (
          <span className="block text-(--text-tertiary) mt-0.5">
            {sortDir === "desc" ? "↓ maior para menor" : "↑ menor para maior"}
          </span>
        )}
      </TooltipContent>
    </Tooltip>
  )
}

const STATUS_TRANSITIONS: Record<
  string,
  { label: string; icon: React.ReactNode; action: string }[]
> = {
  draft: [{ label: "Aprovar", icon: <Check className="h-3.5 w-3.5 mr-2" />, action: "approve" }],
  approved: [
    { label: "Agendar", icon: <Clock className="h-3.5 w-3.5 mr-2" />, action: "schedule" },
    { label: "Publicar agora", icon: <Send className="h-3.5 w-3.5 mr-2" />, action: "publish" },
  ],
  scheduled: [
    {
      label: "Cancelar agendamento",
      icon: <XCircle className="h-3.5 w-3.5 mr-2" />,
      action: "cancel",
    },
    { label: "Publicar agora", icon: <Send className="h-3.5 w-3.5 mr-2" />, action: "publish" },
  ],
  published: [],
  failed: [],
}

function PostRow({
  post,
  onEdit,
  isSelected,
  onToggleSelect,
  gridCols,
}: {
  post: ContentPost
  onEdit: () => void
  isSelected: boolean
  onToggleSelect: () => void
  gridCols: string
}) {
  const linkedInUrl = getLinkedInUrl(post.linkedin_post_urn)
  const dateStr = post.published_at ?? post.publish_date

  const approvePost = useApprovePost()
  const schedulePost = useSchedulePost()
  const cancelSchedulePost = useCancelSchedule()
  const publishNowPost = usePublishNow()
  const deletePostMut = useDeletePost()

  function runAction(action: string) {
    switch (action) {
      case "approve":
        approvePost.mutate(post.id)
        break
      case "schedule":
        schedulePost.mutate(post.id)
        break
      case "cancel":
        cancelSchedulePost.mutate(post.id)
        break
      case "publish":
        publishNowPost.mutate(post.id)
        break
    }
  }

  const transitions = STATUS_TRANSITIONS[post.status] ?? []

  return (
    <div
      className={cn(
        "grid gap-2 px-4 py-3 border-b border-(--border-default) last:border-b-0 hover:bg-(--bg-overlay) transition-colors items-center text-xs",
        gridCols,
        isSelected && "bg-(--accent-subtle)",
      )}
    >
      {/* Checkbox */}
      <Checkbox
        checked={isSelected}
        onCheckedChange={onToggleSelect}
        aria-label="Selecionar post"
        className="ml-0.5"
      />

      {/* Title + date + time */}
      <div className="flex flex-col gap-0.5 min-w-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <button
            type="button"
            onClick={onEdit}
            className="text-sm font-medium text-(--text-primary) truncate text-left cursor-pointer hover:text-(--accent) transition-colors"
          >
            {post.notion_page_id && (
              <NotionLogo className="h-3.5 w-3.5 shrink-0 inline-block mr-1.5 align-middle" aria-label="Importado do Notion" />
            )}
            {post.title}
          </button>
          {post.image_url && (
            <ImageIcon className="h-4.5 w-4.5 shrink-0 text-sky-500" aria-label="Tem imagem" />
          )}
          {post.video_url && (
            <VideoIcon className="h-4.5 w-4.5 shrink-0 text-violet-500" aria-label="Tem vídeo" />
          )}
        </div>
        {dateStr && (
          <span className="text-xs text-(--text-tertiary)">
            {formatDateBR(dateStr, "dd MMM yyyy 'às' HH:mm")}
          </span>
        )}
      </div>

      {/* Status — clickable dropdown */}
      <div>
        {transitions.length > 0 ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                title="Alterar status"
                className="inline-flex items-center gap-1 cursor-pointer group"
              >
                <StatusBadge status={post.status} />
                <ChevronDown className="h-3 w-3 text-(--text-tertiary) opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-52">
              {transitions.map((t) => (
                <DropdownMenuItem
                  key={t.action}
                  onClick={() => runAction(t.action)}
                  disabled={t.action === "schedule" && !post.publish_date}
                >
                  {t.icon}
                  {t.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <StatusBadge status={post.status} />
        )}
      </div>

      {/* Pilar */}
      <div>
        <PillarBadge pillar={post.pillar} />
      </div>

      {/* Impressions */}
      <span className="text-(--text-secondary) flex items-center gap-1">
        <Eye className="h-3 w-3 text-(--text-tertiary)" />
        {post.impressions > 0 ? post.impressions.toLocaleString("pt-BR") : "—"}
      </span>

      {/* Likes */}
      <span className="text-(--text-secondary) flex items-center gap-1">
        <Heart className="h-3 w-3 text-(--text-tertiary)" />
        {post.likes > 0 ? post.likes.toLocaleString("pt-BR") : "—"}
      </span>

      {/* Comments */}
      <span className="text-(--text-secondary) flex items-center gap-1">
        <MessageCircle className="h-3 w-3 text-(--text-tertiary)" />
        {post.comments > 0 ? post.comments.toLocaleString("pt-BR") : "—"}
      </span>

      {/* Saves */}
      <span className="text-(--text-secondary) flex items-center gap-1">
        <Bookmark className="h-3 w-3 text-(--text-tertiary)" />
        {post.saves > 0 ? post.saves.toLocaleString("pt-BR") : "—"}
      </span>

      {/* Engagement rate */}
      <span className="text-(--text-secondary) flex items-center gap-1">
        <TrendingUp className="h-3 w-3 text-(--text-tertiary)" />
        {post.engagement_rate != null ? `${post.engagement_rate.toFixed(1)}%` : "—"}
      </span>

      {/* LinkedIn link */}
      <div className="flex justify-center">
        {linkedInUrl ? (
          <a
            href={linkedInUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-(--text-tertiary) hover:text-(--accent) transition-colors"
            title="Abrir no LinkedIn"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : (
          <span className="text-(--text-tertiary) opacity-30">
            <ExternalLink className="h-3.5 w-3.5" />
          </span>
        )}
      </div>

      {/* Actions — visible icon buttons */}
      <TooltipProvider delayDuration={200}>
        <div className="flex items-center gap-0.5">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onEdit}>
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">Editar</TooltipContent>
          </Tooltip>

          {post.status === "draft" && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-(--success-subtle-fg)"
                  onClick={() => approvePost.mutate(post.id)}
                >
                  <Check className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">Aprovar</TooltipContent>
            </Tooltip>
          )}

          {post.status === "approved" && (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => schedulePost.mutate(post.id)}
                    disabled={!post.publish_date}
                  >
                    <Clock className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">Agendar</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => publishNowPost.mutate(post.id)}
                  >
                    <Send className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">Publicar agora</TooltipContent>
              </Tooltip>
            </>
          )}

          {post.status === "scheduled" && (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => cancelSchedulePost.mutate(post.id)}
                  >
                    <XCircle className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">Cancelar agendamento</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => publishNowPost.mutate(post.id)}
                  >
                    <Send className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">Publicar agora</TooltipContent>
              </Tooltip>
            </>
          )}

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-red-500 hover:text-red-600"
                onClick={() => deletePostMut.mutate(post.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">Excluir</TooltipContent>
          </Tooltip>
        </div>
      </TooltipProvider>
    </div>
  )
}
