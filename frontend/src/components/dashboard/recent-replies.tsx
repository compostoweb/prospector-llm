import Link from "next/link"
import { formatRelativeTime } from "@/lib/utils"
import { BadgeIntent } from "@/components/shared/badge-intent"
import { BadgeChannel } from "@/components/shared/badge-channel"
import { EmptyState } from "@/components/shared/empty-state"
import { MessageSquare } from "lucide-react"
import type { RecentReply } from "@/lib/api/hooks/use-analytics"

interface RecentRepliesProps {
  replies: RecentReply[]
  isLoading?: boolean
}

export function RecentReplies({ replies, isLoading }: RecentRepliesProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-14 animate-pulse rounded-[var(--radius-md)] bg-[var(--bg-overlay)]"
          />
        ))}
      </div>
    )
  }

  if (replies.length === 0) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="Nenhuma resposta ainda"
        description="As respostas dos leads aparecerão aqui"
      />
    )
  }

  return (
    <ul className="space-y-2">
      {replies.map((reply) => (
        <li key={`${reply.lead_id}-${reply.replied_at}`}>
          <Link
            href={`/leads/${reply.lead_id}`}
            className="flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2.5 transition-colors hover:border-[var(--border-default)] hover:bg-[var(--bg-overlay)]"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                {reply.lead_name}
              </p>
              {reply.company_name && (
                <p className="truncate text-xs text-[var(--text-tertiary)]">{reply.company_name}</p>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <BadgeChannel channel={reply.channel} />
              <BadgeIntent intent={reply.intent} />
              <time
                dateTime={reply.replied_at}
                className="whitespace-nowrap text-xs text-[var(--text-tertiary)]"
              >
                {formatRelativeTime(reply.replied_at)}
              </time>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}
