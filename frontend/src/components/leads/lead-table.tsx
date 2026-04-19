"use client"

import Link from "next/link"
import { AlertTriangle, Archive, Mail, Phone, Sparkles, Users } from "lucide-react"
import { toast } from "sonner"
import { useArchiveLead, useEnrichLead, type Lead } from "@/lib/api/hooks/use-leads"
import { Button } from "@/components/ui/button"
import { LeadEditDialog } from "@/components/leads/lead-edit-dialog"
import { LeadDeleteDialog } from "@/components/leads/lead-delete-dialog"
import { Checkbox } from "@/components/ui/checkbox"
import { leadSourceLabel, truncate } from "@/lib/utils"
import { LeadScore } from "@/components/leads/lead-score"
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
}

export function LeadTable({
  leads,
  isLoading,
  selectedLeadIds = [],
  onToggleLead,
  onToggleAll,
  onLeadDeleted,
}: LeadTableProps) {
  const archiveLead = useArchiveLead()
  const enrichLead = useEnrichLead()
  const allSelected = leads.length > 0 && selectedLeadIds.length === leads.length

  function handleEnrich(leadId: string) {
    enrichLead.mutate(leadId, {
      onSuccess: () => {
        toast.success("Enriquecimento iniciado")
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : "Falha ao iniciar enriquecimento")
      },
    })
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
                className="border-white/70 hover:border-amber-300"
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
                    <p className="text-xs text-(--text-tertiary)">{truncate(lead.job_title, 40)}</p>
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
                  {lead.job_title && (
                    <p className="mt-1 text-xs text-(--text-tertiary)">
                      {truncate(lead.job_title, 42)}
                    </p>
                  )}
                </div>
              </td>
              <td className="px-4 py-3">
                <div className="space-y-1 text-xs text-(--text-secondary)">
                  <div className="flex items-center gap-2">
                    <Mail size={12} aria-hidden="true" className="text-(--text-tertiary)" />
                    <span>{lead.email_corporate ?? lead.email_personal ?? "Sem email"}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone size={12} aria-hidden="true" className="text-(--text-tertiary)" />
                    <span>{lead.phone ?? "Sem telefone"}</span>
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
                      disabled={enrichLead.isPending}
                      aria-label="Enriquecer lead"
                      title="Enriquecer lead"
                    >
                      <Sparkles size={14} aria-hidden="true" />
                      <span>Enriquecer</span>
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
