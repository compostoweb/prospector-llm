import Link from "next/link"
import { truncate } from "@/lib/utils"
import { LeadScore } from "@/components/leads/lead-score"
import { BadgeIntent } from "@/components/shared/badge-intent"
import { Building2, MapPin, Mail, Linkedin } from "lucide-react"
import type { Lead } from "@/lib/api/hooks/use-leads"

interface LeadCardProps {
  lead: Lead
}

export function LeadCard({ lead }: LeadCardProps) {
  return (
    <Link
      href={`/leads/${lead.id}`}
      className="block rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm) transition-shadow hover:shadow-(--shadow-md)"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-(--text-primary)">{lead.full_name}</p>
          {lead.job_title && (
            <p className="mt-0.5 truncate text-sm text-(--text-secondary)">
              {truncate(lead.job_title, 50)}
            </p>
          )}
        </div>
        <LeadScore score={lead.score} size="sm" />
      </div>

      <div className="mt-3 space-y-1.5">
        {lead.company_name && (
          <p className="flex items-center gap-1.5 text-xs text-(--text-secondary)">
            <Building2 size={12} aria-hidden="true" />
            {lead.company_name}
          </p>
        )}
        {lead.location && (
          <p className="flex items-center gap-1.5 text-xs text-(--text-secondary)">
            <MapPin size={12} aria-hidden="true" />
            {lead.location}
          </p>
        )}
        {lead.email && (
          <p className="flex items-center gap-1.5 text-xs text-(--text-secondary)">
            <Mail size={12} aria-hidden="true" />
            <span className="truncate">{lead.email}</span>
          </p>
        )}
        {lead.linkedin_url && (
          <p className="flex items-center gap-1.5 text-xs text-(--text-secondary)">
            <Linkedin size={12} aria-hidden="true" />
            <span className="truncate">{lead.linkedin_url}</span>
          </p>
        )}
      </div>

      {lead.last_intent && (
        <div className="mt-3">
          <BadgeIntent intent={lead.last_intent} />
        </div>
      )}
    </Link>
  )
}
