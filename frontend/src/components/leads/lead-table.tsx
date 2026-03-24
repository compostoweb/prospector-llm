import Link from "next/link"
import { truncate } from "@/lib/utils"
import { LeadScore } from "@/components/leads/lead-score"
import { EmptyState } from "@/components/shared/empty-state"
import { Users } from "lucide-react"
import type { Lead } from "@/lib/api/hooks/use-leads"

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
}

export function LeadTable({ leads, isLoading }: LeadTableProps) {
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
    <div className="overflow-hidden rounded-lg border border-(--border-default)">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-(--border-default) bg-(--bg-overlay)">
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
              Lead
            </th>
            <th className="hidden px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-tertiary) md:table-cell">
              Empresa
            </th>
            <th className="hidden px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-tertiary) lg:table-cell">
              Status
            </th>
            <th className="hidden px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-(--text-tertiary) lg:table-cell">
              Segmento
            </th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
              Score
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-(--border-subtle) bg-(--bg-surface)">
          {leads.map((lead) => (
            <tr key={lead.id} className="transition-colors hover:bg-(--bg-overlay)">
              <td className="px-4 py-3">
                <Link href={`/leads/${lead.id}`} className="block hover:underline">
                  <p className="font-medium text-(--text-primary)">{lead.name}</p>
                  {lead.job_title && (
                    <p className="text-xs text-(--text-tertiary)">{truncate(lead.job_title, 40)}</p>
                  )}
                </Link>
              </td>
              <td className="hidden px-4 py-3 text-(--text-secondary) md:table-cell">
                {lead.company ?? "—"}
              </td>
              <td className="hidden px-4 py-3 lg:table-cell">
                <span
                  className={`inline-flex rounded-(--radius-full) px-2 py-0.5 text-xs font-medium ${statusClass[lead.status]}`}
                >
                  {statusLabel[lead.status]}
                </span>
              </td>
              <td className="hidden px-4 py-3 lg:table-cell">
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
