"use client"

import Image from "next/image"
import { useState } from "react"
import { formatDateBR, isFutureUTCDate } from "@/lib/date"
import {
  Calendar,
  Check,
  Clock,
  Send,
  Trash2,
  XCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Pencil,
  Sparkles,
  ExternalLink,
  Eye,
  Heart,
  MessageCircle,
  TrendingUp,
  Bookmark,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { StatusBadge, PillarBadge } from "@/components/content/post-badges"
import { NotionLogo } from "@/components/ui/notion-logo"
import {
  useApprovePost,
  useSchedulePost,
  useCancelSchedule,
  usePublishNow,
  useDeletePost,
  type ContentPost,
} from "@/lib/api/hooks/use-content"
import { EditPostDialog } from "@/components/content/edit-post-dialog"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface PostCardProps {
  post: ContentPost
}

export function PostCard({ post }: PostCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [improveOpen, setImproveOpen] = useState(false)

  const approve = useApprovePost()
  const schedule = useSchedulePost()
  const cancelSchedule = useCancelSchedule()
  const publishNow = usePublishNow()
  const deletePost = useDeletePost()

  const isLoading =
    approve.isPending ||
    schedule.isPending ||
    cancelSchedule.isPending ||
    publishNow.isPending ||
    deletePost.isPending

  return (
    <>
      <div
        className={cn(
          "rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 flex flex-col gap-3 shadow-(--shadow-sm) overflow-hidden",
          post.status === "failed" && "border-(--danger)",
        )}
      >
        {/* Thumbnail da imagem, se existir */}
        {post.image_url && (
          <Image
            src={post.image_url}
            alt={post.title || "Imagem do post"}
            width={1200}
            height={256}
            unoptimized
            className="-mx-4 -mt-4 w-[calc(100%+2rem)] h-32 object-cover"
          />
        )}

        {/* Cabeçalho */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={post.status} />
              <PillarBadge pillar={post.pillar} />
              {post.week_number && (
                <span className="text-xs text-(--text-tertiary)">Sem. {post.week_number}</span>
              )}
            </div>
            <div className="flex items-center gap-1.5 min-w-0">
              {post.notion_page_id && (
                <NotionLogo className="h-3.5 w-3.5 shrink-0" aria-label="Importado do Notion" />
              )}
              <p className="text-sm font-medium text-(--text-primary) truncate">{post.title}</p>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <ActionMenu
              post={post}
              isLoading={isLoading}
              onEdit={() => setEditOpen(true)}
              onImprove={() => {
                setImproveOpen(true)
                setEditOpen(true)
              }}
              onApprove={() => approve.mutate(post.id)}
              onSchedule={() => schedule.mutate(post.id)}
              onCancelSchedule={() => cancelSchedule.mutate(post.id)}
              onPublishNow={() => publishNow.mutate(post.id)}
              onDelete={() => deletePost.mutate(post.id)}
            />
          </div>
        </div>

        {/* Preview do body */}
        <button
          type="button"
          className="cursor-pointer text-left"
          onClick={() => setExpanded((v) => !v)}
        >
          <p
            className={cn(
              "text-sm text-(--text-secondary) whitespace-pre-wrap",
              !expanded && "line-clamp-3",
            )}
          >
            {post.body}
          </p>
          <span className="flex items-center gap-1 text-xs text-(--accent) mt-1">
            {expanded ? (
              <>
                <ChevronUp className="h-3 w-3" /> Recolher
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" /> Ver tudo
              </>
            )}
          </span>
        </button>

        {/* Metadados */}
        <div className="flex items-center gap-4 text-xs text-(--text-tertiary) flex-wrap">
          {post.publish_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatDateBR(post.publish_date, "dd MMM yyyy 'às' HH:mm")}
            </span>
          )}
          {post.character_count && (
            <span className="flex items-center gap-1">
              <span>{post.character_count} chars</span>
            </span>
          )}
          {post.published_at && (
            <span className="flex items-center gap-1 text-(--success)">
              <Check className="h-3 w-3" />
              Publicado em {formatDateBR(post.published_at, "dd MMM yyyy 'às' HH:mm")}
            </span>
          )}
          {post.status === "published" && post.impressions > 0 && (
            <span className="flex items-center gap-1">
              <Eye className="h-3 w-3" /> {post.impressions.toLocaleString("pt-BR")}
            </span>
          )}
          {post.status === "published" && post.likes > 0 && (
            <span className="flex items-center gap-1">
              <Heart className="h-3 w-3" /> {post.likes.toLocaleString("pt-BR")}
            </span>
          )}
          {post.status === "published" && post.comments > 0 && (
            <span className="flex items-center gap-1">
              <MessageCircle className="h-3 w-3" /> {post.comments.toLocaleString("pt-BR")}
            </span>
          )}
          {post.status === "published" && post.saves > 0 && (
            <span className="flex items-center gap-1">
              <Bookmark className="h-3 w-3" /> {post.saves.toLocaleString("pt-BR")}
            </span>
          )}
          {post.status === "published" &&
            post.engagement_rate != null &&
            post.engagement_rate > 0 && (
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" /> {post.engagement_rate.toFixed(1)}%
              </span>
            )}
          {post.linkedin_post_urn && (
            <a
              href={`https://www.linkedin.com/feed/update/${post.linkedin_post_urn}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-(--accent) transition-colors"
              title="Abrir no LinkedIn"
            >
              <ExternalLink className="h-3 w-3" /> LinkedIn
            </a>
          )}
        </div>

        {/* Erro */}
        {post.error_message && (
          <div className="flex items-start gap-2 rounded-md bg-(--danger-subtle) text-(--danger-subtle-fg) p-2 text-xs">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            {post.error_message}
          </div>
        )}
      </div>

      <EditPostDialog
        post={post}
        open={editOpen}
        onOpenChange={(value) => {
          setEditOpen(value)
          if (!value) {
            setImproveOpen(false)
          }
        }}
        defaultImproveOpen={improveOpen}
      />
    </>
  )
}

// ── Menu de ações ──────────────────────────────────────────────────────

interface ActionMenuProps {
  post: ContentPost
  isLoading: boolean
  onEdit: () => void
  onImprove: () => void
  onApprove: () => void
  onSchedule: () => void
  onCancelSchedule: () => void
  onPublishNow: () => void
  onDelete: () => void
}

function ActionMenu({
  post,
  isLoading,
  onEdit,
  onImprove,
  onApprove,
  onSchedule,
  onCancelSchedule,
  onPublishNow,
  onDelete,
}: ActionMenuProps) {
  const canSchedulePost = isFutureUTCDate(post.publish_date)
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" disabled={isLoading} className="h-7 px-2 text-xs">
          Ações
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {/* Editar — sempre disponível */}
        <DropdownMenuItem onClick={onEdit}>
          <Pencil className="h-3.5 w-3.5 mr-2" />
          Editar
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onImprove}>
          <Sparkles className="h-3.5 w-3.5 mr-2" />
          Melhorar com IA
        </DropdownMenuItem>

        {(post.status === "draft" ||
          post.status === "approved" ||
          post.status === "scheduled" ||
          post.status === "failed") && <DropdownMenuSeparator />}

        {post.status === "draft" && (
          <DropdownMenuItem onClick={onApprove}>
            <Check className="h-3.5 w-3.5 mr-2" />
            Aprovar
          </DropdownMenuItem>
        )}
        {post.status === "approved" && (
          <>
            <DropdownMenuItem onClick={onSchedule} disabled={!canSchedulePost}>
              <Clock className="h-3.5 w-3.5 mr-2" />
              Agendar
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onPublishNow}>
              <Send className="h-3.5 w-3.5 mr-2" />
              Publicar agora
            </DropdownMenuItem>
          </>
        )}
        {post.status === "scheduled" && (
          <>
            <DropdownMenuItem onClick={onPublishNow}>
              <Send className="h-3.5 w-3.5 mr-2" />
              Publicar agora
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onCancelSchedule}>
              <XCircle className="h-3.5 w-3.5 mr-2" />
              Cancelar agendamento
            </DropdownMenuItem>
          </>
        )}

        {/* Excluir — sempre disponível */}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onDelete} className="text-(--danger) focus:text-(--danger)">
          <Trash2 className="h-3.5 w-3.5 mr-2" />
          Excluir
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
