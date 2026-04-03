"use client"

import { useState } from "react"
import { format, parseISO } from "date-fns"
import { ptBR } from "date-fns/locale"
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
} from "lucide-react"
import { cn } from "@/lib/utils"
import { StatusBadge, PillarBadge } from "@/components/content/post-badges"
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface PostCardProps {
  post: ContentPost
}

export function PostCard({ post }: PostCardProps) {
  const [expanded, setExpanded] = useState(false)

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
    <div
      className={cn(
        "rounded-(--radius-lg) border border-(--border-default) bg-(--bg-surface) p-4 flex flex-col gap-3 shadow-(--shadow-sm)",
        post.status === "failed" && "border-(--danger)",
      )}
    >
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
          <p className="text-sm font-medium text-(--text-primary) truncate">{post.title}</p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <ActionMenu
            post={post}
            isLoading={isLoading}
            onApprove={() => approve.mutate(post.id)}
            onSchedule={() => schedule.mutate(post.id)}
            onCancelSchedule={() => cancelSchedule.mutate(post.id)}
            onPublishNow={() => publishNow.mutate(post.id)}
            onDelete={() => deletePost.mutate(post.id)}
          />
        </div>
      </div>

      {/* Preview do body */}
      <div
        className="cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setExpanded((v) => !v)}
      >
        <p
          className={cn(
            "text-sm text-(--text-secondary) whitespace-pre-wrap",
            !expanded && "line-clamp-3",
          )}
        >
          {post.body}
        </p>
        <button className="flex items-center gap-1 text-xs text-(--accent) mt-1">
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" /> Recolher
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" /> Ver tudo
            </>
          )}
        </button>
      </div>

      {/* Metadados */}
      <div className="flex items-center gap-4 text-xs text-(--text-tertiary) flex-wrap">
        {post.publish_date && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {format(parseISO(post.publish_date), "dd MMM yyyy 'às' HH:mm", { locale: ptBR })}
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
            Publicado em {format(parseISO(post.published_at), "dd MMM yyyy", { locale: ptBR })}
          </span>
        )}
        {post.status === "published" && post.impressions > 0 && (
          <span className="flex items-center gap-1">
            👁 {post.impressions.toLocaleString("pt-BR")} impressões
          </span>
        )}
      </div>

      {/* Erro */}
      {post.error_message && (
        <div className="flex items-start gap-2 rounded-(--radius-md) bg-(--danger-subtle) text-(--danger-subtle-fg) p-2 text-xs">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
          {post.error_message}
        </div>
      )}
    </div>
  )
}

// ── Menu de ações ──────────────────────────────────────────────────────

interface ActionMenuProps {
  post: ContentPost
  isLoading: boolean
  onApprove: () => void
  onSchedule: () => void
  onCancelSchedule: () => void
  onPublishNow: () => void
  onDelete: () => void
}

function ActionMenu({
  post,
  isLoading,
  onApprove,
  onSchedule,
  onCancelSchedule,
  onPublishNow,
  onDelete,
}: ActionMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" disabled={isLoading} className="h-7 px-2 text-xs">
          Ações
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {post.status === "draft" && (
          <DropdownMenuItem onClick={onApprove}>
            <Check className="h-3.5 w-3.5 mr-2" />
            Aprovar
          </DropdownMenuItem>
        )}
        {post.status === "approved" && (
          <>
            <DropdownMenuItem onClick={onSchedule} disabled={!post.publish_date}>
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
        {post.status === "draft" && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onDelete}
              className="text-(--danger) focus:text-(--danger)"
            >
              <Trash2 className="h-3.5 w-3.5 mr-2" />
              Excluir
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
