import { AlertTriangle, ShieldAlert } from "lucide-react"
import { BadgeChannel } from "@/components/shared/badge-channel"
import { EmptyState } from "@/components/shared/empty-state"
import type { LeadInteraction } from "@/lib/api/hooks/use-leads"
import { formatRelativeTime } from "@/lib/utils"

interface LeadReplyAuditProps {
  interactions: LeadInteraction[]
  isLoading?: boolean
}

const statusLabel: Record<"ambiguous" | "unmatched", string> = {
  ambiguous: "Ambíguo",
  unmatched: "Sem vínculo automático",
}

const statusClass: Record<"ambiguous" | "unmatched", string> = {
  ambiguous: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  unmatched: "border-(--border-default) bg-(--bg-overlay) text-(--text-secondary)",
}

export function LeadReplyAudit({ interactions, isLoading = false }: LeadReplyAuditProps) {
  const auditItems = interactions.filter(
    (interaction) =>
      interaction.direction === "inbound" &&
      (interaction.reply_match_status === "ambiguous" ||
        interaction.reply_match_status === "unmatched"),
  )

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, index) => (
          <div key={index} className="h-20 animate-pulse rounded-lg bg-(--bg-overlay)" />
        ))}
      </div>
    )
  }

  if (auditItems.length === 0) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="Nenhum reply pendente de auditoria"
        description="Replies ambíguos ou sem vínculo automático aparecem aqui para revisão manual."
        className="px-4 py-10"
      />
    )
  }

  return (
    <div className="space-y-3">
      {auditItems.map((interaction) => {
        const status = interaction.reply_match_status as "ambiguous" | "unmatched"
        return (
          <article
            key={interaction.id}
            className="rounded-lg border border-(--border-subtle) bg-(--bg-surface) p-4"
          >
            <div className="flex flex-wrap items-center gap-2">
              <BadgeChannel channel={interaction.channel} />
              <span
                className={`inline-flex items-center gap-1 rounded-(--radius-full) border px-2 py-0.5 text-xs font-medium ${statusClass[status]}`}
              >
                <AlertTriangle size={12} aria-hidden="true" />
                {statusLabel[status]}
              </span>
              <time dateTime={interaction.created_at} className="text-xs text-(--text-tertiary)">
                {formatRelativeTime(interaction.created_at)}
              </time>
            </div>

            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-(--text-secondary)">
              {interaction.content_text || "Sem conteúdo textual disponível."}
            </p>

            <div className="mt-3 flex flex-wrap gap-3 text-xs text-(--text-tertiary)">
              {interaction.reply_match_source && (
                <span>Fonte do vínculo: {interaction.reply_match_source}</span>
              )}
              {interaction.reply_match_status === "ambiguous" &&
                interaction.reply_match_sent_cadence_count != null && (
                  <span>Cadências candidatas: {interaction.reply_match_sent_cadence_count}</span>
                )}
            </div>
          </article>
        )
      })}
    </div>
  )
}
