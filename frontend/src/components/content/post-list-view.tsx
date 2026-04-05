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
  Bookmark,
  Pencil,
  Check,
  Clock,
  Send,
  XCircle,
  Trash2,
  ChevronDown,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { StatusBadge, PillarBadge } from "@/components/content/post-badges"
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export type SortKey = "recent" | "impressions" | "likes" | "comments" | "saves" | "engagement"

interface PostListViewProps {
  posts: ContentPost[]
  sortBy: SortKey
  onSortChange: (key: SortKey) => void
}

function sortPosts(posts: ContentPost[], sortBy: SortKey): ContentPost[] {
  const sorted = [...posts]
  switch (sortBy) {
    case "recent":
      return sorted.sort((a, b) => {
        const da = a.published_at ?? a.publish_date ?? a.created_at
        const db = b.published_at ?? b.publish_date ?? b.created_at
        return new Date(db).getTime() - new Date(da).getTime()
      })
    case "impressions":
      return sorted.sort((a, b) => b.impressions - a.impressions)
    case "likes":
      return sorted.sort((a, b) => b.likes - a.likes)
    case "comments":
      return sorted.sort((a, b) => b.comments - a.comments)
    case "saves":
      return sorted.sort((a, b) => b.saves - a.saves)
    case "engagement":
      return sorted.sort((a, b) => (b.engagement_rate ?? 0) - (a.engagement_rate ?? 0))
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
  const sortedPosts = sortPosts(posts, sortBy)

  return (
    <>
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) overflow-hidden shadow-sm">
        {/* Header */}
        <div className="grid grid-cols-[1fr_100px_90px_70px_70px_70px_70px_70px_36px_130px] gap-2 px-4 py-2.5 border-b border-(--border-default) bg-(--bg-overlay) text-xs font-medium text-(--text-tertiary) uppercase tracking-wide">
          <span>Post</span>
          <span>Status</span>
          <span>Pilar</span>
          <SortHeader
            label="Impr."
            sortKey="impressions"
            currentSort={sortBy}
            onSort={onSortChange}
          />
          <SortHeader label="Likes" sortKey="likes" currentSort={sortBy} onSort={onSortChange} />
          <SortHeader label="Com." sortKey="comments" currentSort={sortBy} onSort={onSortChange} />
          <SortHeader label="Salv." sortKey="saves" currentSort={sortBy} onSort={onSortChange} />
          <SortHeader
            label="Eng."
            sortKey="engagement"
            currentSort={sortBy}
            onSort={onSortChange}
          />
          <span />
          <span className="text-center">Ações</span>
        </div>

        {/* Rows */}
        {sortedPosts.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-(--text-tertiary)">
            Nenhum post encontrado.
          </div>
        ) : (
          sortedPosts.map((post) => (
            <PostRow key={post.id} post={post} onEdit={() => setEditPost(post)} />
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
    </>
  )
}

function SortHeader({
  label,
  sortKey,
  currentSort,
  onSort,
}: {
  label: string
  sortKey: SortKey
  currentSort: SortKey
  onSort: (key: SortKey) => void
}) {
  const active = currentSort === sortKey
  return (
    <button
      type="button"
      onClick={() => onSort(sortKey)}
      className={cn(
        "flex items-center gap-0.5 cursor-pointer transition-colors",
        active ? "text-(--accent)" : "hover:text-(--text-secondary)",
      )}
    >
      {label}
      <ArrowUpDown className="h-3 w-3" />
    </button>
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

function PostRow({ post, onEdit }: { post: ContentPost; onEdit: () => void }) {
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
    <div className="grid grid-cols-[1fr_100px_90px_70px_70px_70px_70px_70px_36px_130px] gap-2 px-4 py-3 border-b border-(--border-default) last:border-b-0 hover:bg-(--bg-overlay) transition-colors items-center text-xs">
      {/* Title + date + time */}
      <div className="flex flex-col gap-0.5 min-w-0">
        <button
          type="button"
          onClick={onEdit}
          className="text-sm font-medium text-(--text-primary) truncate text-left cursor-pointer hover:text-(--accent) transition-colors"
        >
          {post.title}
        </button>
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
