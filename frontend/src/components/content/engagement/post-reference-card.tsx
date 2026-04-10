"use client"

import { useState } from "react"
import { ExternalLink, Bookmark, BookmarkCheck, ChevronDown, ChevronUp, ThumbsUp, MessageCircle, Repeat2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { HookBadge } from "./hook-badge"
import { PillarBadge } from "./pillar-badge"
import { useSaveEngagementPost } from "@/lib/api/hooks/use-content-engagement"
import type { EngagementPost } from "@/lib/content-engagement/types"
import { toast } from "sonner"

interface PostReferenceCardProps {
  post: EngagementPost
  className?: string
}

export function PostReferenceCard({ post, className }: PostReferenceCardProps) {
  const [expanded, setExpanded] = useState(false)
  const savePost = useSaveEngagementPost()

  async function handleToggleSave() {
    try {
      await savePost.mutateAsync({ postId: post.id, is_saved: !post.is_saved })
      toast.success(
        post.is_saved ? "Referência removida" : "Salvo como referência",
        { description: post.is_saved ? undefined : "Disponível na aba Referências" },
      )
    } catch {
      toast.error("Erro ao salvar referência")
    }
  }

  return (
    <div
      className={cn(
        "rounded-xl border bg-(--bg-surface) overflow-hidden transition-shadow hover:shadow-md",
        post.is_saved
          ? "border-indigo-300/60 ring-1 ring-indigo-200/40 dark:border-indigo-700/40 dark:ring-indigo-800/30"
          : "border-(--border-default)",
        className
      )}
    >
      <div className="p-5 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex items-center gap-1.5 flex-wrap">
              <HookBadge hookType={post.hook_type} />
              <PillarBadge pillar={post.pillar} />
            </div>
            <p className="text-sm font-semibold text-(--text-primary) truncate">
              {post.author_name ?? "Autor desconhecido"}
            </p>
            {post.author_title && (
              <p className="text-xs text-(--text-secondary) line-clamp-1">
                {post.author_title}
              </p>
            )}
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleToggleSave}
              disabled={savePost.isPending}
              title={post.is_saved ? "Remover dos salvos" : "Salvar referência"}
            >
              {post.is_saved ? (
                <BookmarkCheck className="h-4 w-4 text-indigo-500" />
              ) : (
                <Bookmark className="h-4 w-4 text-(--text-tertiary)" />
              )}
            </Button>
            {post.post_url && (
              <a
                href={post.post_url}
                target="_blank"
                rel="noopener noreferrer"
                title="Abrir post no LinkedIn"
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg hover:bg-(--bg-overlay) transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5 text-(--text-tertiary)" />
              </a>
            )}
          </div>
        </div>

        {/* Métricas */}
        <div className="flex items-center gap-4 text-xs text-(--text-tertiary)">
          <span className="flex items-center gap-1">
            <ThumbsUp className="h-3 w-3" />
            {post.likes.toLocaleString("pt-BR")}
          </span>
          <span className="flex items-center gap-1">
            <MessageCircle className="h-3 w-3" />
            {post.comments.toLocaleString("pt-BR")}
          </span>
          <span className="flex items-center gap-1">
            <Repeat2 className="h-3 w-3" />
            {post.shares.toLocaleString("pt-BR")}
          </span>
          {post.engagement_score != null && post.engagement_score > 0 && (
            <span className="ml-auto font-medium text-(--text-secondary)">
              Score {post.engagement_score}
            </span>
          )}
        </div>

        {/* Texto (colapsável) */}
        <div>
          <p
            className={cn(
              "text-sm text-(--text-primary) whitespace-pre-wrap leading-relaxed",
              !expanded && "line-clamp-4"
            )}
          >
            {post.post_text}
          </p>
          {post.post_text.length > 300 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-1.5 flex items-center gap-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3.5 w-3.5" />
                  Ver menos
                </>
              ) : (
                <>
                  <ChevronDown className="h-3.5 w-3.5" />
                  Ver mais
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Insights LLM — collapsible */}
      {(post.why_it_performed || post.what_to_replicate) && (
        <div className="border-t border-(--border-default) bg-(--bg-sunken) px-5 py-3.5 space-y-2">
          {post.why_it_performed && (
            <details className="group">
              <summary className="flex cursor-pointer items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-(--text-tertiary) select-none">
                <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-180" />
                Por que performou
              </summary>
              <p className="mt-1 text-xs text-(--text-primary) leading-relaxed pl-4.5">
                {post.why_it_performed}
              </p>
            </details>
          )}
          {post.what_to_replicate && (
            <details className="group">
              <summary className="flex cursor-pointer items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-(--text-tertiary) select-none">
                <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-180" />
                O que replicar
              </summary>
              <p className="mt-1 text-xs text-(--text-primary) leading-relaxed pl-4.5">
                {post.what_to_replicate}
              </p>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
