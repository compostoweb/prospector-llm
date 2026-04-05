"use client"

import { useState } from "react"
import {
  useConversationLead,
  useQuickCreateLead,
  useSendToCRM,
  useRecentActivity,
  useCadenceHistory,
  useLeadTags,
  useAddTag,
  useRemoveTag,
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
  Crown,
  Users,
  Globe,
  Activity,
  Tag,
  X,
  Plus,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  ArrowUpRight,
  ArrowDownLeft,
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { cn } from "@/lib/utils"

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
    sendCRM.mutate({ chatId }, { onSuccess: () => setCrmSent(true) })
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
              <div className="text-center">
                <div className="flex items-center justify-center gap-1.5">
                  <h4 className="text-base font-semibold text-(--text-primary)">
                    {lead?.attendee_name || "Membro LinkedIn"}
                  </h4>
                  {lead?.attendee_is_premium && (
                    <Crown size={14} className="text-amber-500" aria-hidden="true" />
                  )}
                </div>
                {lead?.attendee_headline && (
                  <p className="mt-1 text-xs leading-relaxed text-(--text-secondary)">
                    {lead.attendee_headline}
                  </p>
                )}
              </div>
            </div>

            {/* Location & connections */}
            {(lead?.attendee_location ?? lead?.attendee_connections_count != null) && (
              <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-(--text-tertiary)">
                {lead?.attendee_location && (
                  <span className="flex items-center gap-1">
                    <MapPin size={11} aria-hidden="true" />
                    {lead.attendee_location}
                  </span>
                )}
                {lead?.attendee_connections_count != null && (
                  <span className="flex items-center gap-1">
                    <Users size={11} aria-hidden="true" />
                    {lead.attendee_connections_count.toLocaleString("pt-BR")} conexões
                  </span>
                )}
                {lead?.attendee_shared_connections_count != null &&
                  lead.attendee_shared_connections_count > 0 && (
                    <span className="flex items-center gap-1">
                      <Users size={11} aria-hidden="true" />
                      {lead.attendee_shared_connections_count} em comum
                    </span>
                  )}
              </div>
            )}

            {/* Websites */}
            {lead?.attendee_websites && lead.attendee_websites.length > 0 && (
              <div className="space-y-1">
                {lead.attendee_websites.map((url) => (
                  <a
                    key={url}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-xs text-(--accent) hover:underline"
                  >
                    <Globe size={11} aria-hidden="true" />
                    <span className="truncate">{url.replace(/^https?:\/\/(www\.)?/, "")}</span>
                    <ExternalLink size={9} className="shrink-0" aria-hidden="true" />
                  </a>
                ))}
              </div>
            )}

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

            {/* Contact email from Unipile */}
            {lead?.attendee_email && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
                  Contato
                </p>
                <InfoRow icon={Mail} label="Email" value={lead.attendee_email} />
              </div>
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
                <div className="flex items-center justify-center gap-1.5">
                  <h4 className="text-base font-semibold text-(--text-primary)">
                    {lead.name ?? "Sem nome"}
                  </h4>
                  {lead.attendee_is_premium && (
                    <Crown size={14} className="text-amber-500" aria-hidden="true" />
                  )}
                </div>
                {(lead.job_title ?? lead.attendee_headline) && (
                  <p className="mt-1 text-xs leading-relaxed text-(--text-secondary)">
                    {lead.job_title ?? lead.attendee_headline}
                  </p>
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

            {/* Location & connections (from Unipile) */}
            {(lead.attendee_location ?? lead.attendee_connections_count != null) && (
              <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-(--text-tertiary)">
                {(lead.city ?? lead.attendee_location) && (
                  <span className="flex items-center gap-1">
                    <MapPin size={11} aria-hidden="true" />
                    {lead.city ?? lead.attendee_location}
                  </span>
                )}
                {lead.attendee_connections_count != null && (
                  <span className="flex items-center gap-1">
                    <Users size={11} aria-hidden="true" />
                    {lead.attendee_connections_count.toLocaleString("pt-BR")} conexões
                  </span>
                )}
                {lead.attendee_shared_connections_count != null &&
                  lead.attendee_shared_connections_count > 0 && (
                    <span className="flex items-center gap-1">
                      <Users size={11} aria-hidden="true" />
                      {lead.attendee_shared_connections_count} em comum
                    </span>
                  )}
              </div>
            )}

            {/* Websites */}
            {lead.attendee_websites && lead.attendee_websites.length > 0 && (
              <div className="space-y-1">
                {lead.attendee_websites.map((url) => (
                  <a
                    key={url}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-xs text-(--accent) hover:underline"
                  >
                    <Globe size={11} aria-hidden="true" />
                    <span className="truncate">{url.replace(/^https?:\/\/(www\.)?/, "")}</span>
                    <ExternalLink size={9} className="shrink-0" aria-hidden="true" />
                  </a>
                ))}
              </div>
            )}

            {/* Tags */}
            <TagsSection chatId={chatId} />

            {/* Pending tasks */}
            {lead.pending_tasks_count > 0 && (
              <a
                href="/tarefas"
                className="flex items-center gap-2 rounded-md border border-(--warning)/30 bg-(--warning)/5 px-3 py-2 text-xs font-medium text-(--warning) transition-colors hover:bg-(--warning)/10"
              >
                <ClipboardList size={14} aria-hidden="true" />
                {lead.pending_tasks_count} tarefa{lead.pending_tasks_count > 1 ? "s" : ""} pendente
                {lead.pending_tasks_count > 1 ? "s" : ""}
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
                <InfoRow icon={Linkedin} label="LinkedIn" value="Perfil" href={lead.linkedin_url} />
              )}
              {lead.email_corporate && (
                <InfoRow icon={Mail} label="Email corp." value={lead.email_corporate} />
              )}
              {lead.email_personal && (
                <InfoRow icon={Mail} label="Email pessoal" value={lead.email_personal} />
              )}
              {!lead.email_corporate && !lead.email_personal && lead.attendee_email && (
                <InfoRow icon={Mail} label="Email" value={lead.attendee_email} />
              )}
              {lead.phone && <InfoRow icon={Phone} label="Telefone" value={lead.phone} />}
              {lead.city && <InfoRow icon={MapPin} label="Cidade" value={lead.city} />}
            </div>

            {/* Business info */}
            {(lead.segment ?? lead.industry) && (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
                  Empresa
                </p>
                {lead.segment && <InfoRow icon={Target} label="Segmento" value={lead.segment} />}
                {lead.industry && (
                  <InfoRow icon={Factory} label="Indústria" value={lead.industry} />
                )}
              </div>
            )}

            {/* Recent Activity */}
            <RecentActivitySection chatId={chatId} />

            {/* Cadence History */}
            <CadenceHistorySection chatId={chatId} />

            {/* Notes */}
            {lead.notes && (
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
                  Observações
                </p>
                <p className="text-xs text-(--text-secondary) whitespace-pre-wrap">{lead.notes}</p>
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

// ── Tags Section ──────────────────────────────────────────────────────

const TAG_COLORS = [
  "#6366f1",
  "#ec4899",
  "#f59e0b",
  "#10b981",
  "#3b82f6",
  "#8b5cf6",
  "#ef4444",
  "#14b8a6",
  "#f97316",
  "#06b6d4",
]

const TAG_COLOR_CLASS_MAP: Record<string, { pill: string; swatch: string }> = {
  "#6366f1": { pill: "contact-tag-pill-indigo", swatch: "contact-tag-swatch-indigo" },
  "#ec4899": { pill: "contact-tag-pill-pink", swatch: "contact-tag-swatch-pink" },
  "#f59e0b": { pill: "contact-tag-pill-amber", swatch: "contact-tag-swatch-amber" },
  "#10b981": { pill: "contact-tag-pill-emerald", swatch: "contact-tag-swatch-emerald" },
  "#3b82f6": { pill: "contact-tag-pill-blue", swatch: "contact-tag-swatch-blue" },
  "#8b5cf6": { pill: "contact-tag-pill-violet", swatch: "contact-tag-swatch-violet" },
  "#ef4444": { pill: "contact-tag-pill-red", swatch: "contact-tag-swatch-red" },
  "#14b8a6": { pill: "contact-tag-pill-teal", swatch: "contact-tag-swatch-teal" },
  "#f97316": { pill: "contact-tag-pill-orange", swatch: "contact-tag-swatch-orange" },
  "#06b6d4": { pill: "contact-tag-pill-cyan", swatch: "contact-tag-swatch-cyan" },
}

function getTagColorClasses(color: string | null | undefined): { pill: string; swatch: string } {
  return (
    TAG_COLOR_CLASS_MAP[color ?? ""] ?? {
      pill: "contact-tag-pill-default",
      swatch: "contact-tag-swatch-default",
    }
  )
}

function TagsSection({ chatId }: { chatId: string }) {
  const { data: tags } = useLeadTags(chatId)
  const addTag = useAddTag()
  const removeTag = useRemoveTag()
  const [showInput, setShowInput] = useState(false)
  const [newTagName, setNewTagName] = useState("")
  const [selectedColor, setSelectedColor] = useState(TAG_COLORS[0])

  function handleAdd() {
    const name = newTagName.trim()
    if (!name) return
    addTag.mutate(
      { chatId, name, color: selectedColor },
      {
        onSuccess: () => {
          setNewTagName("")
          setShowInput(false)
        },
      },
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">Tags</p>
        <button
          type="button"
          onClick={() => setShowInput(!showInput)}
          title="Adicionar tag"
          className="rounded p-0.5 text-(--text-tertiary) transition-colors hover:text-(--text-primary)"
        >
          <Plus size={12} aria-hidden="true" />
        </button>
      </div>

      {/* Existing tags */}
      {tags && tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag.id}
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium text-white",
                getTagColorClasses(tag.color).pill,
              )}
            >
              {tag.name}
              <button
                type="button"
                onClick={() => removeTag.mutate({ chatId, tagId: tag.id })}
                title={`Remover tag ${tag.name}`}
                className="ml-0.5 rounded-full p-0.5 transition-colors hover:bg-white/20"
              >
                <X size={8} aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Add tag input */}
      {showInput && (
        <div className="space-y-2 rounded-md border border-(--border-default) bg-(--bg-overlay) p-2">
          <input
            type="text"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAdd()
            }}
            placeholder="Nome da tag..."
            className="w-full rounded border border-(--border-default) bg-(--bg-surface) px-2 py-1 text-xs text-(--text-primary) placeholder:text-(--text-tertiary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
          />
          <div className="flex flex-wrap gap-1">
            {TAG_COLORS.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setSelectedColor(color)}
                title={`Cor ${color}`}
                className={cn(
                  "contact-tag-swatch h-4 w-4 rounded-full transition-transform",
                  getTagColorClasses(color).swatch,
                  selectedColor === color && "contact-tag-swatch-selected",
                )}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={handleAdd}
            disabled={!newTagName.trim() || addTag.isPending}
            className="flex w-full items-center justify-center gap-1.5 rounded bg-(--accent) px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
          >
            {addTag.isPending ? (
              <Loader2 size={10} className="animate-spin" aria-hidden="true" />
            ) : (
              <Tag size={10} aria-hidden="true" />
            )}
            Adicionar
          </button>
        </div>
      )}
    </div>
  )
}

// ── Recent Activity Section ───────────────────────────────────────────

const CHANNEL_LABELS: Record<string, string> = {
  linkedin_connect: "Conexão",
  linkedin_dm: "DM LinkedIn",
  email: "Email",
}

function RecentActivitySection({ chatId }: { chatId: string }) {
  const { data } = useRecentActivity(chatId)
  const [open, setOpen] = useState(false)

  if (!data?.items || data.items.length === 0) return null

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-xs font-medium uppercase tracking-wider text-(--text-tertiary) transition-colors hover:text-(--text-secondary)"
      >
        <span className="flex items-center gap-1.5">
          <Activity size={11} aria-hidden="true" />
          Atividade recente
        </span>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      {open && (
        <div className="space-y-1.5">
          {data.items.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-2 rounded-md bg-(--bg-overlay) px-2.5 py-2"
            >
              <div className="mt-0.5 shrink-0">
                {item.direction === "outbound" ? (
                  <ArrowUpRight size={11} className="text-(--accent)" aria-hidden="true" />
                ) : (
                  <ArrowDownLeft size={11} className="text-emerald-500" aria-hidden="true" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-medium text-(--text-secondary)">
                    {CHANNEL_LABELS[item.channel] ?? item.channel}
                  </span>
                  {item.intent && (
                    <span className="rounded bg-(--accent-subtle) px-1 py-px text-[9px] font-medium text-(--accent-subtle-fg)">
                      {item.intent}
                    </span>
                  )}
                </div>
                {item.content_preview && (
                  <p className="mt-0.5 line-clamp-2 text-[10px] text-(--text-tertiary)">
                    {item.content_preview}
                  </p>
                )}
                <p className="mt-0.5 text-[9px] text-(--text-tertiary)">
                  {new Date(item.created_at).toLocaleDateString("pt-BR", {
                    day: "2-digit",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Cadence History Section ──────────────────────────────────────────

function CadenceHistorySection({ chatId }: { chatId: string }) {
  const { data } = useCadenceHistory(chatId)
  const [open, setOpen] = useState(false)

  if (!data?.items || data.items.length === 0) return null

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-xs font-medium uppercase tracking-wider text-(--text-tertiary) transition-colors hover:text-(--text-secondary)"
      >
        <span className="flex items-center gap-1.5">
          <MessageSquare size={11} aria-hidden="true" />
          Cadências
        </span>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      {open && (
        <div className="space-y-2">
          {data.items.map((c) => {
            const pct =
              c.total_steps > 0 ? Math.round((c.completed_steps / c.total_steps) * 100) : 0
            return (
              <div
                key={c.cadence_id}
                className="rounded-md border border-(--border-default) bg-(--bg-overlay) p-2.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-(--text-primary)">
                    {c.cadence_name}
                  </span>
                  <span
                    className={`rounded-full px-1.5 py-px text-[9px] font-medium ${
                      c.is_active
                        ? "bg-emerald-500/10 text-emerald-600"
                        : "bg-(--bg-overlay) text-(--text-tertiary)"
                    }`}
                  >
                    {c.is_active ? "Ativa" : "Finalizada"}
                  </span>
                </div>
                <p className="mt-0.5 text-[10px] text-(--text-tertiary)">
                  {c.mode} · {c.completed_steps}/{c.total_steps} steps
                </p>
                {/* Progress bar */}
                <progress
                  className="contact-sidebar-progress mt-1.5 w-full"
                  value={pct}
                  max={100}
                />
                {c.last_step_at && (
                  <p className="mt-1 text-[9px] text-(--text-tertiary)">
                    Último step:{" "}
                    {new Date(c.last_step_at).toLocaleDateString("pt-BR", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
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
