"use client"

import { useState } from "react"
import { Copy, Check, RefreshCw, CheckCircle2, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  useMarkCommentPosted,
  useRegenerateComment,
  useUnmarkCommentPosted,
} from "@/lib/api/hooks/use-content-engagement"
import type { EngagementComment } from "@/lib/content-engagement/types"
import { toast } from "sonner"

interface CommentCardProps {
  comment: EngagementComment
  className?: string
}

export function CommentCard({ comment, className }: CommentCardProps) {
  const [copied, setCopied] = useState(false)
  const markPosted = useMarkCommentPosted()
  const unmarkPosted = useUnmarkCommentPosted()
  const regenerate = useRegenerateComment()

  const isPosted = comment.status === "posted"
  const isUndoing = unmarkPosted.isPending
  const isRegenerating = regenerate.isPending

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(comment.comment_text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback silencioso
    }
  }

  async function handleMarkPosted() {
    if (isPosted) return
    try {
      await markPosted.mutateAsync(comment.id)
      toast.success("Comentário marcado como postado")
    } catch {
      toast.error("Não foi possível marcar o comentário como postado")
    }
  }

  async function handleRegenerate() {
    try {
      await regenerate.mutateAsync(comment.id)
      toast.success("Comentário regenerado")
    } catch {
      toast.error("Não foi possível regenerar o comentário")
    }
  }

  async function handleUndoPosted() {
    if (!isPosted) return
    try {
      await unmarkPosted.mutateAsync(comment.id)
      toast.success("Marcação desfeita")
    } catch {
      toast.error("Não foi possível desfazer a marcação")
    }
  }

  return (
    <div
      className={cn(
        "rounded-lg border bg-(--bg-surface) p-4 space-y-2.5 transition-all",
        isPosted
          ? "border-emerald-200 dark:border-emerald-800/40 opacity-60"
          : "border-(--border-default)",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-bold uppercase tracking-wider text-(--text-tertiary)">
          Variação {comment.variation}
        </span>
        {isPosted && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            <CheckCircle2 className="h-2.5 w-2.5" />
            Postado
          </span>
        )}
      </div>

      <p className="text-sm text-(--text-primary) whitespace-pre-wrap leading-relaxed">
        {comment.comment_text}
      </p>

      <div className="flex items-center gap-1.5 pt-1">
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopy}
          className="h-7 gap-1.5 text-xs"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" />
              Copiado
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              Copiar
            </>
          )}
        </Button>

        {!isPosted ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleMarkPosted}
              disabled={markPosted.isPending}
              className="h-7 gap-1.5 text-xs text-(--text-secondary)"
            >
              <CheckCircle2 className={cn("h-3 w-3", markPosted.isPending && "animate-pulse")} />
              {markPosted.isPending ? "Salvando..." : "Já postei"}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleRegenerate}
              disabled={isRegenerating}
              className="h-7 gap-1.5 text-xs text-(--text-secondary) ml-auto"
            >
              <RefreshCw className={cn("h-3 w-3", isRegenerating && "animate-spin")} />
              Regenerar
            </Button>
          </>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleUndoPosted}
            disabled={isUndoing}
            className="ml-auto h-7 gap-1.5 text-xs text-(--text-secondary)"
          >
            <RotateCcw className={cn("h-3 w-3", isUndoing && "animate-spin")} />
            {isUndoing ? "Desfazendo..." : "Desfazer"}
          </Button>
        )}
      </div>
    </div>
  )
}
