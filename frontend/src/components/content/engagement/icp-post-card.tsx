"use client"

import { useState } from "react"
import { ExternalLink, ChevronDown, ChevronUp, User, Lightbulb, ThumbsUp, MessageCircle, Repeat2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { CommentCard } from "./comment-card"
import type { EngagementPost } from "@/lib/content-engagement/types"

interface IcpPostCardProps {
  post: EngagementPost
  className?: string
}

export function IcpPostCard({ post, className }: IcpPostCardProps) {
  const [expanded, setExpanded] = useState(false)
  const comments = post.suggested_comments ?? []
  const hasComments = comments.length > 0
  const wasCommented = comments.some((c) => c.status === "posted")

  return (
    <div
      className={cn(
        "rounded-xl border bg-(--bg-surface) overflow-hidden transition-shadow hover:shadow-md",
        wasCommented
          ? "border-emerald-300/60 dark:border-emerald-700/40"
          : "border-(--border-default)",
        className
      )}
    >
      {/* Author header */}
      <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-sky-100 to-indigo-100 dark:from-sky-900/30 dark:to-indigo-900/30">
            <User className="h-4.5 w-4.5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-(--text-primary) truncate">
                {post.author_name ?? "Autor desconhecido"}
              </p>
              {wasCommented && (
                <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                  Comentado
                </span>
              )}
            </div>
            {post.author_title && (
              <p className="text-xs text-(--text-secondary) line-clamp-2 mt-0.5 leading-relaxed">
                {post.author_title}
              </p>
            )}
          </div>
        </div>

        {post.post_url && (
          <a
            href={post.post_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir post no LinkedIn"
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-(--border-default) hover:bg-(--bg-overlay) transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5 text-(--text-secondary)" />
          </a>
        )}
      </div>

      {/* Post text */}
      <div className="px-5 pb-3">
        <p
          className={cn(
            "text-sm text-(--text-primary) whitespace-pre-wrap leading-relaxed",
            !expanded && "line-clamp-4"
          )}
        >
          {post.post_text}
        </p>
        {post.post_text.length > 250 && (
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

      {/* Engagement metrics */}
      <div className="flex items-center gap-4 px-5 pb-3 text-xs text-(--text-tertiary)">
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
          <span className="ml-auto text-xs font-medium text-(--text-secondary)">
            Score {post.engagement_score}
          </span>
        )}
      </div>

      {/* Ângulo sugerido */}
      {post.what_to_replicate && (
        <div className="mx-5 mb-3 rounded-lg border border-amber-200/60 bg-amber-50/60 dark:border-amber-800/30 dark:bg-amber-900/10 px-4 py-3">
          <div className="flex items-start gap-2">
            <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-700/70 dark:text-amber-400/70 mb-0.5">
                Ângulo sugerido
              </p>
              <p className="text-sm text-amber-900 dark:text-amber-200 leading-relaxed">
                {post.what_to_replicate}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Comentários sugeridos */}
      {hasComments && (
        <div className="border-t border-(--border-default) bg-(--bg-sunken) px-5 py-4 space-y-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-(--text-tertiary)">
            Comentários sugeridos
          </p>
          {comments.map((c) => (
            <CommentCard key={c.id} comment={c} />
          ))}
        </div>
      )}

      {!hasComments && (
        <div className="border-t border-(--border-default) px-5 py-3">
          <p className="text-xs text-(--text-tertiary) italic">
            Nenhum comentário gerado para este post.
          </p>
        </div>
      )}
    </div>
  )
}
