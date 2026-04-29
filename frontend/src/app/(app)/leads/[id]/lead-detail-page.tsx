"use client"

import { useParams, useRouter } from "next/navigation"
import { useState } from "react"
import {
  ArrowLeft,
  Building2,
  Globe,
  Linkedin,
  Mail,
  MapPin,
  Phone,
  Briefcase,
  Tag,
  Loader2,
  GitBranch,
  Archive,
  Workflow,
  List,
  Sparkles,
} from "lucide-react"
import Link from "next/link"
import { toast } from "sonner"
import {
  useLead,
  useLeadInteractions,
  useLeadSteps,
  useArchiveLead,
  useEnrollLead,
  useEnrichLead,
} from "@/lib/api/hooks/use-leads"
import type { LeadContactPoint, LeadEmail } from "@/lib/api/hooks/use-leads"
import { useCadences } from "@/lib/api/hooks/use-cadences"
import { ContactQualityBadge } from "@/components/leads/contact-quality-badge"
import { LeadDeleteDialog } from "@/components/leads/lead-delete-dialog"
import { LeadEditDialog } from "@/components/leads/lead-edit-dialog"
import { LeadReplyAudit } from "@/components/leads/lead-reply-audit"
import { LeadTimeline } from "@/components/leads/lead-timeline"
import { LeadScore } from "@/components/leads/lead-score"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"

const statusLabel: Record<string, string> = {
  raw: "Novo",
  enriched: "Enriquecido",
  in_cadence: "Em cadência",
  converted: "Convertido",
  archived: "Arquivado",
}

const statusClass: Record<string, string> = {
  raw: "bg-(--neutral-subtle) text-(--neutral-subtle-fg)",
  enriched: "bg-(--info-subtle) text-(--info-subtle-fg)",
  in_cadence: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
  converted: "bg-(--success-subtle) text-(--success-subtle-fg)",
  archived: "bg-(--neutral-subtle) text-(--text-disabled)",
}

export default function LeadDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const leadId = params.id

  const { data: lead, isLoading } = useLead(leadId)
  const { data: steps, isLoading: loadingSteps } = useLeadSteps(leadId)
  const { data: interactions, isLoading: loadingInteractions } = useLeadInteractions(leadId)
  const { data: cadences } = useCadences()
  const { mutate: archiveLead, isPending: archiving } = useArchiveLead()
  const { mutate: enrollLead, isPending: enrolling } = useEnrollLead()
  const { mutate: enrichLead, isPending: enriching } = useEnrichLead()
  const [showEnroll, setShowEnroll] = useState(false)
  const [includeMobileOnEnrich, setIncludeMobileOnEnrich] = useState(true)
  const [forceRefreshOnEnrich, setForceRefreshOnEnrich] = useState(false)

  if (isLoading) {
    return (
      <div className="flex h-60 items-center justify-center">
        <Loader2
          size={24}
          className="animate-spin text-(--text-tertiary)"
          aria-label="Carregando"
        />
      </div>
    )
  }

  if (!lead) {
    return (
      <div className="space-y-4">
        <Link
          href="/leads"
          className="inline-flex items-center gap-1.5 text-sm text-(--text-secondary) hover:text-(--text-primary)"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Voltar
        </Link>
        <p className="text-sm text-(--text-secondary)">Lead não encontrado.</p>
      </div>
    )
  }

  const activeCadences = cadences?.filter((c) => c.is_active) ?? []
  const sortedEmails = [...lead.emails].sort(
    (left, right) => Number(right.is_primary) - Number(left.is_primary),
  )
  const emailContactPoints = lead.contact_points.filter((point) => point.kind === "email")
  const phoneContactPoints = lead.contact_points.filter((point) => point.kind === "phone")

  function handleArchive() {
    archiveLead(leadId, {
      onSuccess: () => router.push("/leads"),
    })
  }

  function handleEnroll(cadenceId: string) {
    enrollLead({ leadId, cadenceId }, { onSuccess: () => setShowEnroll(false) })
  }

  function handleEnrich() {
    enrichLead(
      {
        leadId,
        include_mobile: includeMobileOnEnrich,
        force_refresh: forceRefreshOnEnrich,
      },
      {
        onSuccess: () => {
          toast.success("Enriquecimento iniciado")
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : "Falha ao iniciar enriquecimento")
        },
      },
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Link
            href="/leads"
            className="inline-flex items-center gap-1.5 text-xs text-(--text-tertiary) hover:text-(--text-secondary)"
          >
            <ArrowLeft size={12} aria-hidden="true" />
            Leads
          </Link>
          <h1 className="text-lg font-semibold text-(--text-primary)">{lead.name}</h1>
          {lead.job_title && <p className="text-sm text-(--text-secondary)">{lead.job_title}</p>}
          <div className="flex items-center gap-2 pt-1">
            <span
              className={`inline-flex rounded-(--radius-full) px-2.5 py-0.5 text-xs font-medium ${statusClass[lead.status] ?? ""}`}
            >
              {statusLabel[lead.status] ?? lead.status}
            </span>
            <LeadScore score={lead.score} size="sm" />
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <LeadEditDialog lead={lead} />
          {lead.status !== "archived" && (
            <Button variant="outline" size="sm" disabled={enriching} onClick={handleEnrich}>
              <Sparkles size={14} aria-hidden="true" />
              Enriquecer
            </Button>
          )}
          {lead.status !== "archived" && lead.status !== "in_cadence" && (
            <Button variant="outline" size="sm" onClick={() => setShowEnroll(!showEnroll)}>
              <GitBranch size={14} aria-hidden="true" />
              Inscrever
            </Button>
          )}
          {lead.status !== "archived" && (
            <Button variant="ghost" size="sm" disabled={archiving} onClick={handleArchive}>
              <Archive size={14} aria-hidden="true" />
              Arquivar
            </Button>
          )}
        </div>
      </div>

      {lead.status !== "archived" && (
        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-3 text-xs text-(--text-secondary)">
          <span className="font-medium text-(--text-primary)">Configuração do enriquecimento</span>
          <label className="inline-flex items-center gap-2">
            <Checkbox
              checked={includeMobileOnEnrich}
              onCheckedChange={(checked) => setIncludeMobileOnEnrich(checked === true)}
            />
            Buscar mobile
          </label>
          <label className="inline-flex items-center gap-2">
            <Checkbox
              checked={forceRefreshOnEnrich}
              onCheckedChange={(checked) => setForceRefreshOnEnrich(checked === true)}
            />
            Forçar refresh
          </label>
        </div>
      )}

      {/* Enroll dropdown */}
      {showEnroll && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Selecione uma cadência</CardTitle>
          </CardHeader>
          <CardContent>
            {activeCadences.length === 0 ? (
              <p className="text-xs text-(--text-tertiary)">Nenhuma cadência ativa encontrada.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {activeCadences.map((c) => (
                  <Button
                    key={c.id}
                    variant="outline"
                    size="sm"
                    disabled={enrolling}
                    onClick={() => handleEnroll(c.id)}
                  >
                    {enrolling ? (
                      <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                    ) : null}
                    {c.name}
                  </Button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Content grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: info */}
        <div className="space-y-4 lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Informações</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {lead.company && <InfoRow icon={Building2} label="Empresa" value={lead.company} />}
              {lead.linkedin_current_company && (
                <InfoRow
                  icon={Linkedin}
                  label="Empresa atual no LinkedIn"
                  value={lead.linkedin_current_company}
                />
              )}
              {lead.industry && <InfoRow icon={Tag} label="Setor" value={lead.industry} />}
              {lead.company_size && (
                <InfoRow icon={Briefcase} label="Tamanho" value={lead.company_size} />
              )}
              {lead.segment && <InfoRow icon={Tag} label="Segmento" value={lead.segment} />}
              <InfoRow icon={Workflow} label="Origem" value={lead.origin_label} />
              {lead.origin_detail && (
                <InfoRow icon={Workflow} label="Detalhe da origem" value={lead.origin_detail} />
              )}
              {(lead.location ?? lead.city) && (
                <InfoRow
                  icon={MapPin}
                  label="Localização"
                  value={lead.location ?? lead.city ?? ""}
                />
              )}
              {lead.website && <InfoRow icon={Globe} label="Website" value={lead.website} link />}
              {lead.company_domain && !lead.website && (
                <InfoRow icon={Globe} label="Domínio" value={lead.company_domain} link />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Contato</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {emailContactPoints.length > 0 ? (
                emailContactPoints.map((point) => (
                  <LeadContactPointRow key={point.id} point={point} label="Email" />
                ))
              ) : sortedEmails.length > 0 ? (
                sortedEmails.map((email) => <LeadEmailRow key={email.id} email={email} />)
              ) : (
                <p className="text-xs text-(--text-tertiary)">Nenhum email registrado.</p>
              )}
              {phoneContactPoints.length > 0 ? (
                phoneContactPoints.map((point) => (
                  <LeadContactPointRow key={point.id} point={point} label="Telefone" />
                ))
              ) : lead.phone ? (
                <InfoRow icon={Phone} label="Telefone" value={lead.phone} />
              ) : null}
              {lead.linkedin_url && (
                <InfoRow icon={Linkedin} label="LinkedIn" value={lead.linkedin_url} link />
              )}
              {lead.linkedin_mismatch && lead.linkedin_current_company && (
                <div className="rounded-(--radius) border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  O LinkedIn aponta empresa atual diferente da empresa salva neste lead.
                </div>
              )}
            </CardContent>
          </Card>

          {lead.notes && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Notas</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-(--text-secondary)">
                  {lead.notes}
                </p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Listas vinculadas</CardTitle>
            </CardHeader>
            <CardContent>
              {lead.lead_lists.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {lead.lead_lists.map((list) => (
                    <Link
                      key={list.id}
                      href={`/listas/${list.id}`}
                      className="inline-flex items-center gap-1 rounded-(--radius-full) border border-(--border-default) px-3 py-1 text-xs text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                    >
                      <List size={12} aria-hidden="true" />
                      {list.name}
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-(--text-tertiary)">
                  Este lead ainda não está em nenhuma lista.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Ações avançadas</CardTitle>
            </CardHeader>
            <CardContent>
              <LeadDeleteDialog
                lead={lead}
                onDeleted={() => router.push("/leads")}
                trigger={
                  <Button variant="destructive" size="sm">
                    Excluir definitivamente
                  </Button>
                }
              />
            </CardContent>
          </Card>
        </div>

        {/* Right: timeline */}
        <div className="lg:col-span-2">
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Timeline da cadência</CardTitle>
              </CardHeader>
              <CardContent>
                <LeadTimeline steps={steps ?? []} isLoading={loadingSteps} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Auditoria de replies</CardTitle>
              </CardHeader>
              <CardContent>
                <LeadReplyAudit
                  lead={lead}
                  interactions={interactions?.items ?? []}
                  isLoading={loadingInteractions}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

function labelForLeadEmail(type: "corporate" | "personal" | "unknown", isPrimary: boolean) {
  if (type === "corporate") return isPrimary ? "Email corporativo" : "Email corporativo extra"
  if (type === "personal") return isPrimary ? "Email pessoal" : "Email pessoal extra"
  return isPrimary ? "Email principal" : "Email adicional"
}

function LeadEmailRow({ email }: { email: LeadEmail }) {
  return (
    <div className="flex items-start gap-2.5">
      <Mail size={14} className="mt-0.5 shrink-0 text-(--text-tertiary)" aria-hidden="true" />
      <div className="min-w-0 overflow-hidden space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[11px] font-medium uppercase tracking-wider text-(--text-tertiary)">
            {labelForLeadEmail(email.email_type, email.is_primary)}
          </p>
          <ContactQualityBadge
            qualityBucket={email.quality_bucket}
            qualityScore={email.quality_score}
            verificationStatus={email.verification_status}
            source={email.source}
          />
        </div>
        <p className="text-xs text-(--text-secondary)">{email.email}</p>
        {email.source ? (
          <p className="text-[11px] text-(--text-tertiary)">Fonte: {email.source}</p>
        ) : null}
      </div>
    </div>
  )
}

function LeadContactPointRow({ point, label }: { point: LeadContactPoint; label: string }) {
  const Icon = point.kind === "phone" ? Phone : Mail

  return (
    <div className="flex items-start gap-2.5">
      <Icon size={14} className="mt-0.5 shrink-0 text-(--text-tertiary)" aria-hidden="true" />
      <div className="min-w-0 overflow-hidden space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-[11px] font-medium uppercase tracking-wider text-(--text-tertiary)">
            {point.is_primary ? `${label} principal` : `${label} adicional`}
          </p>
          <ContactQualityBadge
            qualityBucket={point.quality_bucket}
            qualityScore={point.quality_score}
            verificationStatus={null}
            source={point.source}
          />
        </div>
        <p className="text-xs text-(--text-secondary)">{point.value}</p>
        {point.source ? (
          <p className="text-[11px] text-(--text-tertiary)">Fonte: {point.source}</p>
        ) : null}
        {typeof point.evidence_json?.linkedin_company_match === "boolean" ? (
          <p className="text-[11px] text-(--text-tertiary)">
            Cruzamento LinkedIn:{" "}
            {point.evidence_json.linkedin_company_match ? "compatível" : "divergente"}
          </p>
        ) : null}
      </div>
    </div>
  )
}

// ── Componente auxiliar ───────────────────────────────────────────────

interface InfoRowProps {
  icon: React.ComponentType<{ size?: number; className?: string }>
  label: string
  value: string
  link?: boolean
}

function InfoRow({ icon: Icon, label, value, link }: InfoRowProps) {
  // For link display, strip query params and show only the clean path
  const displayValue = link ? value.split("?")[0] : value

  return (
    <div className="flex items-start gap-2.5">
      <Icon size={14} className="mt-0.5 shrink-0 text-(--text-tertiary)" aria-hidden="true" />
      <div className="min-w-0 overflow-hidden">
        <p className="text-[11px] font-medium uppercase tracking-wider text-(--text-tertiary)">
          {label}
        </p>
        {link ? (
          <a
            href={value.startsWith("http") ? value : `https://${value}`}
            target="_blank"
            rel="noopener noreferrer"
            className="block truncate text-xs text-(--accent) hover:underline"
            title={displayValue}
          >
            {displayValue}
          </a>
        ) : (
          <p className="text-xs text-(--text-secondary)">{value}</p>
        )}
      </div>
    </div>
  )
}
