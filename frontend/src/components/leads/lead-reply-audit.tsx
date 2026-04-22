import { ReplyAuditTable, type ReplyAuditTableItem } from "@/components/replies/reply-audit-table"
import type { Lead, LeadInteraction } from "@/lib/api/hooks/use-leads"

interface LeadReplyAuditProps {
  lead: Lead
  interactions: LeadInteraction[]
  isLoading?: boolean
}

export function LeadReplyAudit({ lead, interactions, isLoading = false }: LeadReplyAuditProps) {
  const auditItems = interactions
    .filter((interaction) => {
      const isLowConfidence = interaction.reply_match_source === "fallback_single_cadence"
      const isPendingStatus =
        interaction.reply_match_status === "ambiguous" ||
        interaction.reply_match_status === "unmatched"
      return (
        interaction.direction === "inbound" &&
        interaction.reply_reviewed_at == null &&
        (isPendingStatus || isLowConfidence)
      )
    })
    .map<ReplyAuditTableItem>((interaction) => ({
      interactionId: interaction.id,
      leadId: lead.id,
      leadName: lead.name,
      leadCompany: lead.company,
      leadJobTitle: lead.job_title,
      leadHasMultipleActiveCadences: lead.has_multiple_active_cadences,
      leadActiveCadenceCount: lead.active_cadence_count,
      channel: interaction.channel,
      createdAt: interaction.created_at,
      replyMatchStatus:
        interaction.reply_match_source === "fallback_single_cadence"
          ? "low_confidence"
          : ((interaction.reply_match_status ?? "unmatched") as
              | "ambiguous"
              | "unmatched"
              | "low_confidence"),
      replyMatchSource: interaction.reply_match_source,
      replyMatchSentCadenceCount: interaction.reply_match_sent_cadence_count,
      contentText: interaction.content_text,
    }))

  return (
    <ReplyAuditTable
      items={auditItems}
      isLoading={isLoading}
      showLeadColumn={false}
      emptyTitle="Nenhum reply pendente de auditoria"
      emptyDescription="Replies ambíguos ou sem vínculo automático aparecem aqui para revisão manual."
    />
  )
}
