"use client"

import { useState } from "react"
import {
  useConversationLead,
  useQuickCreateLead,
  useSendToCRM,
} from "@/lib/api/hooks/use-inbox"
import {
  User,
  Building2,
  Linkedin,
  Mail,
  Phone,
  MapPin,
  Target,
  Factory,
  Star,
  ClipboardList,
  Loader2,
  UserPlus,
  Send,
  Check,
  ExternalLink,
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"

interface ContactSidebarProps {
  chatId: string
}

export function ContactSidebar({ chatId }: ContactSidebarProps) {
  const { data: lead, isLoading } = useConversationLead(chatId)
  const quickCreate = useQuickCreateLead()
  const sendCRM = useSendToCRM()
  const [crmSent, setCrmSent] = useState(false)

  function handleCreateLead() {
    if (!lead) return
    quickCreate.mutate({
      chatId,
      body: {
        name: lead.attendee_name || "Contato LinkedIn",
        linkedin_url: lead.attendee_profile_url ?? undefined,
        linkedin_profile_id: lead.attendee_id ?? undefined,
      },
    })
  }

  function handleSendCRM() {
    sendCRM.mutate(
      { chatId },
      { onSuccess: () => setCrmSent(true) },
    )
  }

  return (
    <div className="flex h-full w-[320px] shrink-0 flex-col border-l border-(--border-default) bg-(--bg-surface)">
      {/* Header */}
      <div className="flex h-12 items-center border-b border-(--border-default) px-4">
        <User size={16} className="mr-2 text-(--text-tertiary)" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-(--text-primary)">Contato</h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 size={20} className="animate-spin text-(--text-tertiary)" />
          </div>
        ) : !lead?.has_lead ? (
          /* ── Estado sem lead vinculado ─────────────────────────────── */
          <div className="space-y-4">
            {/* Attendee info */}
            <div className="flex flex-col items-center gap-2 pb-2">
              {lead?.attendee_profile_picture_url ? (
                <Image
                  src={lead.attendee_profile_picture_url}
                  alt={lead.attendee_name || "Contato"}
                  width={64}
                  height={64}
                  unoptimized
                  className="h-16 w-16 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-(--bg-overlay)">
                  <User size={24} className="text-(--text-tertiary)" aria-hidden="true" />
                </div>
              )}
              <h4 className="text-base font-semibold text-(--text-primary)">
                {lead?.attendee_name || "Desconhecido"}
              </h4>
            </div>

            {/* LinkedIn profile link */}
            {lead?.attendee_profile_url && (
              <a
                href={lead.attendee_profile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-md border border-(--border-default) bg-(--bg-overlay) px-3 py-2 text-xs font-medium text-(--accent) transition-colors hover:bg-(--accent-subtle)"
              >
                <Linkedin size={14} aria-hidden="true" />
                Ver perfil no LinkedIn
                <ExternalLink size={10} className="ml-auto" aria-hidden="true" />
              </a>
            )}

            {/* Info box */}
            <div className="rounded-md border border-dashed border-(--border-default) bg-(--bg-overlay) p-3 text-center">
              <p className="text-xs text-(--text-secondary)">
                Este contato não está cadastrado na base de leads.
              </p>
            </div>

            {/* Action buttons */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={handleCreateLead}
                disabled={quickCreate.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-(--accent) px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-(--accent)/90 disabled:opacity-50"
              >
                {quickCreate.isPending ? (
                  <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                ) : (
                  <UserPlus size={14} aria-hidden="true" />
                )}
                Cadastrar como Lead
              </button>

              <button
                type="button"
                onClick={handleSendCRM}
                disabled={sendCRM.isPending || crmSent}
                className="flex w-full items-center justify-center gap-2 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--bg-overlay) disabled:opacity-50"
              >
                {crmSent ? (
                  <>
                    <Check size={14} className="text-emerald-500" aria-hidden="true" />
                    Enviado ao CRM
                  </>
                ) : sendCRM.isPending ? (
                  <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                ) : (
                  <>
                    <Send size={14} aria-hidden="true" />
                    Enviar para CRM
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          /* ── Estado com lead vinculado ─────────────────────────────── */
          <div className="space-y-4">
            {/* Avatar + Name & title */}
            <div className="flex flex-col items-center gap-2 pb-2">
              {lead.attendee_profile_picture_url ? (
                <Image
                  src={lead.attendee_profile_picture_url}
                  alt={lead.name || "Lead"}
                  width={64}
                  height={64}
                  unoptimized
                  className="h-16 w-16 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-(--bg-overlay)">
                  <User size={24} className="text-(--text-tertiary)" aria-hidden="true" />
                </div>
              )}
              <div className="text-center">
                <h4 className="text-base font-semibold text-(--text-primary)">
                  {lead.name ?? "Sem nome"}
                </h4>
                {lead.job_title && (
                  <p className="text-sm text-(--text-secondary)">{lead.job_title}</p>
                )}
                {lead.company && (
                  <p className="mt-0.5 flex items-center justify-center gap-1 text-sm text-(--text-secondary)">
                    <Building2 size={12} aria-hidden="true" />
                    {lead.company}
                  </p>
                )}
              </div>
            </div>

            {/* Status + Score */}
            <div className="flex items-center justify-center gap-2">
              {lead.status && (
                <span className="rounded-full bg-(--accent-subtle) px-2.5 py-0.5 text-xs font-medium text-(--accent-subtle-fg)">
                  {lead.status}
                </span>
              )}
              {lead.score != null && (
                <span className="flex items-center gap-1 text-xs text-(--text-secondary)">
                  <Star size={11} className="text-amber-500" aria-hidden="true" />
                  {lead.score.toFixed(0)} pts
                </span>
              )}
            </div>

            {/* Pending tasks */}
            {lead.pending_tasks_count > 0 && (
              <a
                href="/tarefas"
                className="flex items-center gap-2 rounded-md border border-(--warning)/30 bg-(--warning)/5 px-3 py-2 text-xs font-medium text-(--warning) transition-colors hover:bg-(--warning)/10"
              >
                <ClipboardList size={14} aria-hidden="true" />
                {lead.pending_tasks_count} tarefa{lead.pending_tasks_count > 1 ? "s" : ""} pendente{lead.pending_tasks_count > 1 ? "s" : ""}
              </a>
            )}

            {/* Send to CRM */}
            <button
              type="button"
              onClick={handleSendCRM}
              disabled={sendCRM.isPending || crmSent}
              className="flex w-full items-center justify-center gap-2 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-xs font-medium text-(--text-primary) transition-colors hover:bg-(--bg-overlay) disabled:opacity-50"
            >
              {crmSent ? (
                <>
                  <Check size={14} className="text-emerald-500" aria-hidden="true" />
                  Enviado ao CRM
                </>
              ) : sendCRM.isPending ? (
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
              ) : (
                <>
                  <Send size={14} aria-hidden="true" />
                  Enviar para CRM
                </>
              )}
            </button>

            {/* Contact details */}
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
                Contato
              </p>

              {lead.linkedin_url && (
                <InfoRow
                  icon={Linkedin}
                  label="LinkedIn"
                  value="Perfil"
                  href={lead.linkedin_url}
                />
              )}
              {lead.email_corporate && (
                <InfoRow icon={Mail} label="Email corp." value={lead.email_corporate} />
              )}
              {lead.email_personal && (
                <InfoRow icon={Mail} label="Email pessoal" value={lead.email_personal} />
              )}
              {lead.phone && (
                <InfoRow icon={Phone} label="Telefone" value={lead.phone} />
              )}
              {lead.city && (
                <InfoRow icon={MapPin} label="Cidade" value={lead.city} />
              )}
            </div>

            {/* Business info */}
            {(lead.segment ?? lead.industry) && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
                  Empresa
                </p>
                {lead.segment && (
                  <InfoRow icon={Target} label="Segmento" value={lead.segment} />
                )}
                {lead.industry && (
                  <InfoRow icon={Factory} label="Indústria" value={lead.industry} />
                )}
              </div>
            )}

            {/* Notes */}
            {lead.notes && (
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
                  Observações
                </p>
                <p className="text-xs text-(--text-secondary) whitespace-pre-wrap">
                  {lead.notes}
                </p>
              </div>
            )}

            {/* Link to lead page */}
            {lead.lead_id && (
              <Link
                href={`/leads/${lead.lead_id}`}
                className="block text-center text-xs text-(--accent) hover:underline"
              >
                Ver detalhes completos do lead →
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Helper ────────────────────────────────────────────────────────────

function InfoRow({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ElementType
  label: string
  value: string
  href?: string
}) {
  const content = href ? (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-(--accent) hover:underline"
    >
      {value}
    </a>
  ) : (
    <span className="text-(--text-primary)">{value}</span>
  )

  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon size={12} className="shrink-0 text-(--text-tertiary)" aria-hidden="true" />
      <span className="text-(--text-secondary)">{label}:</span>
      {content}
    </div>
  )
}
