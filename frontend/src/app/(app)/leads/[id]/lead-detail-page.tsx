"use client"

import { useLead, useLeadSteps } from "@/lib/api/hooks/use-leads"
import { LeadScore } from "@/components/leads/lead-score"
import { LeadTimeline } from "@/components/leads/lead-timeline"
import { BadgeIntent } from "@/components/shared/badge-intent"
import { ArrowLeft, Building2, Mail, MapPin, Linkedin, ExternalLink } from "lucide-react"
import Link from "next/link"
import { notFound } from "next/navigation"

interface Props {
  params: Promise<{ id: string }>
}

export default function LeadDetailPage({ params }: Props) {
  const { id } = params as unknown as { id: string }
  return <LeadDetailContent id={id} />
}

function LeadDetailContent({ id }: { id: string }) {
  const { data: lead, isLoading: loadingLead, error } = useLead(id)
  const { data: steps, isLoading: loadingSteps } = useLeadSteps(id)

  if (error) return notFound()

  if (loadingLead) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-[var(--radius-md)] bg-[var(--bg-overlay)]" />
        <div className="h-40 animate-pulse rounded-[var(--radius-lg)] bg-[var(--bg-overlay)]" />
      </div>
    )
  }

  if (!lead) return null

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Voltar */}
      <Link
        href="/leads"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
      >
        <ArrowLeft size={14} aria-hidden="true" />
        Voltar para leads
      </Link>

      {/* Card principal */}
      <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-6 shadow-[var(--shadow-sm)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">{lead.full_name}</h1>
            {lead.job_title && (
              <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{lead.job_title}</p>
            )}
            {lead.last_intent && (
              <div className="mt-2">
                <BadgeIntent intent={lead.last_intent} />
              </div>
            )}
          </div>
          <LeadScore score={lead.score} showLabel />
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {lead.company_name && (
            <InfoRow icon={Building2} label="Empresa" value={lead.company_name} />
          )}
          {lead.location && <InfoRow icon={MapPin} label="Localização" value={lead.location} />}
          {lead.email && (
            <InfoRow icon={Mail} label="E-mail">
              <a href={`mailto:${lead.email}`} className="text-[var(--accent)] hover:underline">
                {lead.email}
              </a>
            </InfoRow>
          )}
          {lead.linkedin_url && (
            <InfoRow icon={Linkedin} label="LinkedIn">
              <a
                href={lead.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[var(--accent)] hover:underline"
              >
                Ver perfil
                <ExternalLink size={11} aria-hidden="true" />
              </a>
            </InfoRow>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-6 shadow-[var(--shadow-sm)]">
        <h2 className="mb-5 text-sm font-semibold text-[var(--text-primary)]">
          Histórico de atividade
        </h2>
        <LeadTimeline steps={steps ?? []} isLoading={loadingSteps} />
      </div>
    </div>
  )
}

// ── Componente auxiliar ───────────────────────────────────────────────

interface InfoRowProps {
  icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: "true" }>
  label: string
  value?: string
  children?: React.ReactNode
}

function InfoRow({ icon: Icon, label, value, children }: InfoRowProps) {
  return (
    <div className="flex items-start gap-2">
      <Icon size={14} className="mt-0.5 shrink-0 text-[var(--text-tertiary)]" aria-hidden="true" />
      <div>
        <p className="text-[11px] uppercase tracking-wider text-[var(--text-tertiary)]">{label}</p>
        {children ?? <p className="text-sm text-[var(--text-primary)]">{value}</p>}
      </div>
    </div>
  )
}
