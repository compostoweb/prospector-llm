"use client"

import { useMemo } from "react"
import { FileText } from "lucide-react"
import { useContentPosts, type ContentPost } from "@/lib/api/hooks/use-content"
import { cn } from "@/lib/utils"

interface LinkedPostSelectorProps {
  value: string | null
  onChange: (postId: string | null) => void
  disabled?: boolean
}

export function LinkedPostSelector({ value, onChange, disabled }: LinkedPostSelectorProps) {
  const { data: postsData } = useContentPosts()

  const posts: ContentPost[] = useMemo(() => {
    const now = Date.now()
    const allPosts = postsData ?? []
    const eligible = allPosts.filter((post) => {
      if (post.status === "published" || post.status === "failed") return false
      if (!post.publish_date) return true
      return new Date(post.publish_date).getTime() >= now - 24 * 60 * 60 * 1000
    })

    return eligible.sort((left, right) => {
      const leftDate = left.publish_date ? new Date(left.publish_date).getTime() : Number.MAX_SAFE_INTEGER
      const rightDate = right.publish_date ? new Date(right.publish_date).getTime() : Number.MAX_SAFE_INTEGER

      if (leftDate !== rightDate) return leftDate - rightDate
      return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()
    })
  }, [postsData])

  if (posts.length === 0) return null

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) px-5 py-4">
      <label htmlFor="linked-post-select" className="mb-2 block text-xs font-semibold text-(--text-secondary) uppercase tracking-wider">
        Qual post você vai publicar depois?
      </label>
      <select
        id="linked-post-select"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={disabled}
        className={cn(
          "w-full rounded-lg border border-(--border-default) bg-(--bg-sunken) px-3 py-2 text-sm text-(--text-primary)",
          "focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400",
          "disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      >
        <option value="">Nenhum (opcional)</option>
        {posts.map((p) => (
          <option key={p.id} value={p.id}>
            {p.title}
            {p.publish_date
              ? ` — ${new Date(p.publish_date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}`
              : ""}
          </option>
        ))}
      </select>
      <div className="mt-2 text-[11px] text-(--text-tertiary)">
        {posts.length} post{posts.length !== 1 ? "s" : ""} elegível{posts.length !== 1 ? "is" : ""} para vincular ao scan.
      </div>
      {value && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-(--text-tertiary)">
          <FileText className="h-3 w-3" />
          <span>O scan priorizará temas alinhados a este post</span>
        </div>
      )}
    </div>
  )
}
