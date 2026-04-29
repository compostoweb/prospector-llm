"use client"

import Link from "next/link"
import { AlertTriangle, Archive, Loader2, Mail, Phone, Sparkles, Users } from "lucide-react"
import { toast } from "sonner"
import { useArchiveLead, useEnrichLead, type Lead } from "@/lib/api/hooks/use-leads"
import { Button } from "@/components/ui/button"
import { LeadEditDialog } from "@/components/leads/lead-edit-dialog"
import { LeadDeleteDialog } from "@/components/leads/lead-delete-dialog"
import { Checkbox } from "@/components/ui/checkbox"
import { leadSourceLabel, truncate } from "@/lib/utils"
import { LeadScore } from "@/components/leads/lead-score"
import { ContactQualityBadge } from "@/components/leads/contact-quality-badge"
import { EmptyState } from "@/components/shared/empty-state"

const statusLabel: Record<Lead["status"], string> = {
  raw: "Novo",
  enriched: "Enriquecido",
  in_cadence: "Em cadência",
  converted: "Convertido",
  archived: "Arquivado",
}

const statusClass: Record<Lead["status"], string> = {
  raw: "bg-(--neutral-subtle) text-(--neutral-subtle-fg)",
  enriched: "bg-(--info-subtle) text-(--info-subtle-fg)",
  in_cadence: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
  converted: "bg-(--success-subtle) text-(--success-subtle-fg)",
  archived: "bg-(--neutral-subtle) text-(--text-disabled)",
}

interface LeadTableProps {
  leads: Lead[]
  isLoading?: boolean
  selectedLeadIds?: string[]
  onToggleLead?: (leadId: string, checked: boolean) => void
  onToggleAll?: (checked: boolean) => void
  onLeadDeleted?: () => void
  enrichingLeadIds?: Set<string>
  onEnrich?: (leadId: string) => void
  enrichOptions?: {
    include_mobile: boolean
    force_refresh: boolean
  }
}

export function LeadTable({
  leads,
  isLoading,
  selectedLeadIds = [],
  onToggleLead,
  onToggleAll,
  onLeadDeleted,
  enrichingLeadIds,
  onEnrich,
  enrichOptions,
}: LeadTableProps) {
  const archiveLead = useArchiveLead()
  const enrichLead = useEnrichLead()
  const allSelected = leads.length > 0 && selectedLeadIds.length === leads.length

  function handleEnrich(leadId: string) {
    onEnrich?.(leadId)
    enrichLead.mutate(
      { leadId, ...enrichOptions },
      {
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : "Falha ao iniciar enriquecimento")
        },
      },
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded-md bg-(--bg-overlay)" />
        ))}
      </div>
    )
  }

  if (leads.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title="Nenhum lead encontrado"
        description="Ajuste os filtros ou importe novos leads"
      />
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
      <table className="w-full min-w-7xl text-sm">
        <thead>
          <tr className="border-b border-(--accent) bg-(--accent)">
            <th className="px-4 py-3 text-left">
              <Checkbox
                checked={allSelected}
                onCheckedChange={(checked) => onToggleAll?.(checked === true)}
                className="border-white bg-white/20 data-[state=checked]:bg-white data-[state=checked]:text-(--accent) hover:border-amber-300"
              />
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Lead
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Empresa
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Contato
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Origem
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Listas
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Segmento
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Score
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-(--text-invert)">
              Ações
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-(--border-subtle) bg-(--bg-surface)">
          {leads.map((lead) => (
            <tr key={lead.id} className="transition-colors hover:bg-(--bg-overlay)">
              {(() => {
                const primaryEmail = getPreferredEmailPoint(lead)
                const primaryPhone = getPrimaryPhonePoint(lead)

                return (
                  <>
                    <td className="px-4 py-3 align-top">
                      <Checkbox
                        checked={selectedLeadIds.includes(lead.id)}
                        onCheckedChange={(checked) => onToggleLead?.(lead.id, checked === true)}
                        className="border-black/50 hover:border-amber-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/leads/${lead.id}`} className="block hover:underline">
                        <p className="font-medium text-(--text-primary)">{lead.name}</p>
                        {lead.job_title && (
                          <p className="text-xs text-(--text-tertiary)">
                            {truncate(lead.job_title, 40)}
                          </p>
                        )}
                        {enrichingLeadIds?.has(lead.id) && (
                          <div className="mt-1 inline-flex items-center gap-1 text-[11px] text-(--info-subtle-fg)">
                            <Loader2 size={10} className="animate-spin" aria-hidden="true" />
                            <span>Enriquecendo…</span>
                          </div>
                        )}
                        {lead.has_multiple_active_cadences && (
                          <div
                            className="mt-2 inline-flex max-w-56 items-center gap-1.5 rounded-(--radius-full) bg-(--warning-subtle) px-2.5 py-1 text-[11px] font-medium text-(--warning-subtle-fg)"
                            title={lead.active_cadences.map((cadence) => cadence.name).join(" • ")}
                          >
                            <AlertTriangle size={12} aria-hidden="true" />
                            <span>{lead.active_cadence_count} cadências ativas</span>
                          </div>
                        )}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-(--text-secondary)">
                      <div>
                        <p>{lead.company ?? "—"}</p>
                        {lead.linkedin_mismatch && lead.linkedin_current_company && (
                          <p className="mt-1 text-[11px] text-(--warning-subtle-fg)">
                            LinkedIn atual: {truncate(lead.linkedin_current_company, 42)}
                          </p>
                        )}
                        {lead.job_title && (
                          <p className="mt-1 text-xs text-(--text-tertiary)">
                            {truncate(lead.job_title, 42)}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1 text-xs text-(--text-secondary)">
                        <div className="flex flex-wrap items-center gap-2">
                          <Mail size={12} aria-hidden="true" className="text-(--text-tertiary)" />
                          <span>
                            {primaryEmail?.value ??
                              lead.email_corporate ??
                              lead.email_personal ??
                              "Sem email"}
                          </span>
                          {primaryEmail ? (
                            <ContactQualityBadge
                              compact
                              qualityBucket={primaryEmail.quality_bucket}
                              qualityScore={primaryEmail.quality_score}
                              verificationStatus={null}
                              source={primaryEmail.source}
                            />
                          ) : null}
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Phone size={12} aria-hidden="true" className="text-(--text-tertiary)" />
                          <span>{primaryPhone?.value ?? lead.phone ?? "Sem telefone"}</span>
                          {primaryPhone ? (
                            <ContactQualityBadge
                              compact
                              qualityBucket={primaryPhone.quality_bucket}
                              qualityScore={primaryPhone.quality_score}
                              verificationStatus={null}
                              source={primaryPhone.source}
                            />
                          ) : null}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <span className="inline-flex rounded-(--radius-full) bg-(--bg-overlay) px-2 py-0.5 text-xs font-medium text-(--text-secondary)">
                          {lead.origin_label || leadSourceLabel(lead.source)}
                        </span>
                        {lead.origin_detail && (
                          <p className="max-w-44 text-[11px] text-(--text-tertiary)">
                            {truncate(lead.origin_detail, 56)}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {lead.lead_lists.length > 0 ? (
                        <div className="flex max-w-44 flex-wrap gap-1">
                          {lead.lead_lists.slice(0, 3).map((list) => (
                            <span
                              key={list.id}
                              className="inline-flex rounded-(--radius-full) border border-(--border-default) px-2 py-0.5 text-[11px] text-(--text-secondary)"
                            >
                              {list.name}
                            </span>
                          ))}
                          {lead.lead_lists.length > 3 && (
                            <span className="text-[11px] text-(--text-tertiary)">
                              +{lead.lead_lists.length - 3}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-(--text-disabled)">Sem listas</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-(--radius-full) px-2 py-0.5 text-xs font-medium ${statusClass[lead.status]}`}
                      >
                        {statusLabel[lead.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {lead.segment ? (
                        <span className="text-xs text-(--text-secondary)">{lead.segment}</span>
                      ) : (
                        <span className="text-(--text-disabled)">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex justify-center">
                        <LeadScore score={lead.score} size="sm" />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <LeadEditDialog lead={lead} iconOnly variant="ghost" />
                        {lead.status !== "archived" && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-8 gap-1.5 text-(--text-secondary) hover:text-(--accent)"
                            onClick={() => handleEnrich(lead.id)}
                            disabled={enrichingLeadIds?.has(lead.id) ?? enrichLead.isPending}
                            aria-label="Enriquecer lead"
                            title="Enriquecer lead"
                          >
                            {enrichingLeadIds?.has(lead.id) ? (
                              <>
                                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                                <span>Enriquecendo…</span>
                              </>
                            ) : (
                              <>
                                <Sparkles size={14} aria-hidden="true" />
                                <span>Enriquecer</span>
                              </>
                            )}
                          </Button>
                        )}
                        {lead.status !== "archived" && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-(--text-tertiary) hover:text-(--danger)"
                            onClick={() => archiveLead.mutate(lead.id)}
                            aria-label="Arquivar lead"
                          >
                            <Archive size={14} aria-hidden="true" />
                          </Button>
                        )}
                        <LeadDeleteDialog
                          lead={lead}
                          {...(onLeadDeleted ? { onDeleted: onLeadDeleted } : {})}
                        />
                      </div>
                    </td>
                  </>
                )
              })()}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function getPreferredEmailPoint(lead: Lead) {
  const emailPoints = lead.contact_points.filter((point) => point.kind === "email")
  const preferredValue = lead.email_corporate ?? lead.email_personal

  if (preferredValue) {
    const matchedPoint = emailPoints.find((point) => point.value === preferredValue)
    if (matchedPoint) {
      return matchedPoint
    }
  }

  const primaryPoint = emailPoints.find((point) => point.is_primary)
  if (primaryPoint) {
    return primaryPoint
  }

  if (preferredValue) {
    const matched = lead.emails.find((email) => email.email === preferredValue)
    if (matched) {
      return {
        value: matched.email,
        source: matched.source,
        quality_bucket: matched.quality_bucket,
        quality_score: matched.quality_score,
      }
    }
  }

  const fallback = lead.emails.find((email) => email.is_primary) ?? lead.emails[0]
  return fallback
    ? {
        value: fallback.email,
        source: fallback.source,
        quality_bucket: fallback.quality_bucket,
        quality_score: fallback.quality_score,
      }
    : null
}

function getPrimaryPhonePoint(lead: Lead) {
  return lead.contact_points.find((point) => point.kind === "phone" && point.is_primary) ?? null
}
