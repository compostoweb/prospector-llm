"use client"

import { useMemo } from "react"
import Link from "next/link"
import { AlertTriangle, History, MessageSquare, ShieldAlert, Workflow } from "lucide-react"
import { BadgeChannel } from "@/components/shared/badge-channel"
import { EmptyState } from "@/components/shared/empty-state"
import { ReplyMatchSourceBadge } from "@/components/replies/reply-match-source-badge"
import { ReplyAuditTable, type ReplyAuditTableItem } from "@/components/replies/reply-audit-table"
import {
  useCadenceReplyManagement,
  type CadenceReplyEvent,
} from "@/lib/api/hooks/use-cadence-analytics"
import { formatRelativeTime } from "@/lib/utils"

interface CadenceReplyManagementProps {
  cadenceId: string
}

interface ReplyLeadSummary {
  lead: CadenceReplyEvent["lead"]
  firstReply: CadenceReplyEvent
  latestReply: CadenceReplyEvent
  eventCount: number
  channels: string[]
  steps: number[]
}

const intentLabel: Record<string, string> = {
  interest: "Interesse",
  objection: "Objeção",
  not_interested: "Sem interesse",
  neutral: "Neutro",
  out_of_office: "Fora do escritório",
}

function buildReplyLeadSummaries(replies: CadenceReplyEvent[]): ReplyLeadSummary[] {
  const grouped = new Map<string, ReplyLeadSummary>()

  for (const reply of replies) {
    const existing = grouped.get(reply.lead.id)
    if (!existing) {
      grouped.set(reply.lead.id, {
        lead: reply.lead,
        firstReply: reply,
        latestReply: reply,
        eventCount: 1,
        channels: [reply.channel],
        steps: reply.step_number != null ? [reply.step_number] : [],
      })
      continue
    }

    existing.eventCount += 1
    if (new Date(reply.replied_at).getTime() < new Date(existing.firstReply.replied_at).getTime()) {
      existing.firstReply = reply
    }
    if (
      new Date(reply.replied_at).getTime() > new Date(existing.latestReply.replied_at).getTime()
    ) {
      existing.latestReply = reply
    }
    if (!existing.channels.includes(reply.channel)) {
      existing.channels.push(reply.channel)
    }
    if (reply.step_number != null && !existing.steps.includes(reply.step_number)) {
      existing.steps.push(reply.step_number)
    }
  }

  return Array.from(grouped.values())
}

function renderLeadSubtitle(summary: ReplyLeadSummary): string {
  const fragments = [summary.lead.company, summary.lead.job_title].filter(Boolean)
  return fragments.join(" · ") || "Lead sem empresa/cargo preenchidos"
}

function buildReplyPreview(replyText: string | null): string {
  const normalized = (replyText ?? "").replace(/\s+/g, " ").trim()
  if (!normalized) {
    return "Sem conteúdo textual disponível."
  }
  if (normalized.length <= 120) {
    return normalized
  }
  return `${normalized.slice(0, 117)}...`
}

function renderPipedriveStatus(reply: CadenceReplyEvent) {
  if (!reply.pipedrive_sync_status) {
    return null
  }

  const statusMeta: Record<string, { label: string; className: string }> = {
    synced: {
      label: reply.pipedrive_deal_id ? `Pipedrive #${reply.pipedrive_deal_id}` : "Pipedrive ok",
      className: "border-emerald-200 bg-emerald-50 text-emerald-700",
    },
    syncing: {
      label: "Pipedrive enviando",
      className: "border-sky-200 bg-sky-50 text-sky-700",
    },
    failed: {
      label: "Pipedrive falhou",
      className: "border-rose-200 bg-rose-50 text-rose-700",
    },
    skipped: {
      label: "Pipedrive ignorado",
      className: "border-gray-200 bg-gray-50 text-gray-600",
    },
  }
  const meta = statusMeta[reply.pipedrive_sync_status] ?? {
    label: reply.pipedrive_sync_status,
    className: "border-gray-200 bg-gray-50 text-gray-600",
  }

  return (
    <span
      className={`inline-flex rounded-(--radius-full) border px-2 py-0.5 text-xs ${meta.className}`}
    >
      {meta.label}
    </span>
  )
}

export function CadenceReplyManagement({ cadenceId }: CadenceReplyManagementProps) {
  const query = useCadenceReplyManagement(cadenceId)
  const replies = useMemo(() => query.data?.replies ?? [], [query.data?.replies])
  const auditItems = useMemo(() => query.data?.audit_items ?? [], [query.data?.audit_items])
  const replyLeadSummaries = buildReplyLeadSummaries(replies)
  const normalizedAuditItems = useMemo<ReplyAuditTableItem[]>(
    () =>
      auditItems.map((item) => ({
        interactionId: item.interaction_id,
        leadId: item.lead.id,
        leadName: item.lead.name,
        leadCompany: item.lead.company,
        leadJobTitle: item.lead.job_title,
        leadHasMultipleActiveCadences: item.lead.has_multiple_active_cadences,
        leadActiveCadenceCount: item.lead.active_cadence_count,
        channel: item.channel,
        createdAt: item.created_at,
        replyMatchStatus: item.reply_match_status,
        replyMatchSource: item.reply_match_source,
        replyMatchSentCadenceCount: item.reply_match_sent_cadence_count,
        contentText: item.content_text,
        candidateSteps: item.candidate_steps,
      })),
    [auditItems],
  )

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <article className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
          <div className="flex items-center gap-2 text-(--accent)">
            <MessageSquare size={16} aria-hidden="true" />
            <p className="text-xs font-semibold uppercase tracking-[0.14em]">Leads com reply</p>
          </div>
          <p className="mt-3 text-3xl font-semibold text-(--text-primary)">
            {replyLeadSummaries.length}
          </p>
          <p className="mt-1 text-sm text-(--text-secondary)">
            Leads únicos com pelo menos uma resposta vinculada a esta cadência.
          </p>
        </article>

        <article className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
          <div className="flex items-center gap-2 text-(--accent)">
            <History size={16} aria-hidden="true" />
            <p className="text-xs font-semibold uppercase tracking-[0.14em]">Eventos de reply</p>
          </div>
          <p className="mt-3 text-3xl font-semibold text-(--text-primary)">{replies.length}</p>
          <p className="mt-1 text-sm text-(--text-secondary)">
            Histórico bruto para validar em qual step e canal a resposta aconteceu.
          </p>
        </article>

        <article className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
          <div className="flex items-center gap-2 text-(--warning)">
            <ShieldAlert size={16} aria-hidden="true" />
            <p className="text-xs font-semibold uppercase tracking-[0.14em]">Auditoria pendente</p>
          </div>
          <p className="mt-3 text-3xl font-semibold text-(--text-primary)">{auditItems.length}</p>
          <p className="mt-1 text-sm text-(--text-secondary)">
            Replies ambíguos ou sem vínculo automático para esta base de leads.
          </p>
        </article>
      </div>

      <section className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
        <div className="mb-4 flex items-start gap-3">
          <div className="rounded-full bg-(--accent-subtle) p-2 text-(--accent-subtle-fg)">
            <Workflow size={16} aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-(--text-primary)">Leads respondidos</h2>
            <p className="text-xs text-(--text-secondary)">
              A tabela separa a primeira resposta contabilizada do histórico bruto de eventos para
              evitar distorção nas métricas da cadência.
            </p>
          </div>
        </div>

        {query.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-28 animate-pulse rounded-lg bg-(--bg-overlay)" />
            ))}
          </div>
        ) : replyLeadSummaries.length === 0 ? (
          <EmptyState
            icon={MessageSquare}
            title="Nenhum lead respondeu esta cadência"
            description="Quando um reply for vinculado a esta cadência, ele aparecerá aqui com atalho para o histórico completo."
            className="px-4 py-10"
          />
        ) : (
          <>
            <div className="hidden overflow-x-auto lg:block">
              <table className="min-w-full border-separate border-spacing-0 text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-[0.14em] text-(--text-tertiary)">
                    <th className="border-b border-(--border-subtle) px-4 py-3 font-semibold">
                      Lead
                    </th>
                    <th className="border-b border-(--border-subtle) px-4 py-3 font-semibold">
                      1ª resposta contabilizada
                    </th>
                    <th className="border-b border-(--border-subtle) px-4 py-3 font-semibold">
                      Última interação
                    </th>
                    <th className="border-b border-(--border-subtle) px-4 py-3 font-semibold">
                      Canais
                    </th>
                    <th className="border-b border-(--border-subtle) px-4 py-3 font-semibold">
                      Eventos
                    </th>
                    <th className="border-b border-(--border-subtle) px-4 py-3 font-semibold">
                      Último reply
                    </th>
                    <th className="border-b border-(--border-subtle) px-4 py-3 font-semibold">
                      Ação
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {replyLeadSummaries.map((summary) => {
                    const sortedSteps = [...summary.steps].sort((left, right) => left - right)
                    const firstReply = summary.firstReply
                    const latestReply = summary.latestReply

                    return (
                      <tr key={summary.lead.id} className="align-top">
                        <td className="border-b border-(--border-subtle) px-4 py-4">
                          <div className="min-w-56 space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <Link
                                href={`/leads/${summary.lead.id}`}
                                className="text-sm font-semibold text-(--text-primary) transition-colors hover:text-(--accent)"
                              >
                                {summary.lead.name}
                              </Link>
                              {summary.lead.has_multiple_active_cadences ? (
                                <span className="inline-flex items-center gap-1 rounded-(--radius-full) border border-(--warning) bg-(--warning-subtle) px-2 py-0.5 text-[11px] font-medium text-(--warning-subtle-fg)">
                                  <AlertTriangle size={12} aria-hidden="true" />
                                  {summary.lead.active_cadence_count} cadências ativas
                                </span>
                              ) : null}
                            </div>
                            <p className="text-sm text-(--text-secondary)">
                              {renderLeadSubtitle(summary)}
                            </p>
                          </div>
                        </td>
                        <td className="border-b border-(--border-subtle) px-4 py-4">
                          <div className="min-w-52 space-y-2">
                            <time
                              dateTime={firstReply.replied_at}
                              className="block font-medium text-(--text-primary)"
                            >
                              {formatRelativeTime(firstReply.replied_at)}
                            </time>
                            <div className="flex flex-wrap items-center gap-2">
                              <BadgeChannel channel={firstReply.channel} />
                              {firstReply.step_number != null ? (
                                <span className="rounded-(--radius-full) border border-(--border-default) bg-(--bg-overlay) px-2 py-0.5 text-xs text-(--text-secondary)">
                                  Step #{firstReply.step_number}
                                </span>
                              ) : null}
                            </div>
                            {firstReply.reply_match_source ? (
                              <ReplyMatchSourceBadge source={firstReply.reply_match_source} short />
                            ) : null}
                          </div>
                        </td>
                        <td className="border-b border-(--border-subtle) px-4 py-4">
                          <div className="min-w-44 space-y-1 text-sm">
                            <time
                              dateTime={latestReply.replied_at}
                              className="block text-(--text-primary)"
                            >
                              {formatRelativeTime(latestReply.replied_at)}
                            </time>
                            <p className="text-(--text-secondary)">
                              {latestReply.intent
                                ? (intentLabel[latestReply.intent] ?? latestReply.intent)
                                : "Intent não classificado"}
                            </p>
                            {renderPipedriveStatus(latestReply)}
                            <p className="text-xs text-(--text-tertiary)">
                              {sortedSteps.length > 0
                                ? `Steps ${sortedSteps.map((step) => `#${step}`).join(", ")}`
                                : "Step não identificado"}
                            </p>
                          </div>
                        </td>
                        <td className="border-b border-(--border-subtle) px-4 py-4">
                          <div className="flex min-w-36 flex-wrap gap-2">
                            {summary.channels.map((channel) => (
                              <BadgeChannel
                                key={`${summary.lead.id}-${channel}`}
                                channel={channel}
                              />
                            ))}
                          </div>
                        </td>
                        <td className="border-b border-(--border-subtle) px-4 py-4">
                          <div className="min-w-28">
                            <p className="font-medium text-(--text-primary)">
                              {summary.eventCount}
                            </p>
                            <p className="text-xs text-(--text-secondary)">histórico bruto</p>
                          </div>
                        </td>
                        <td className="border-b border-(--border-subtle) px-4 py-4">
                          <p className="min-w-72 whitespace-pre-wrap text-sm leading-relaxed text-(--text-secondary)">
                            {buildReplyPreview(latestReply.reply_text)}
                          </p>
                        </td>
                        <td className="border-b border-(--border-subtle) px-4 py-4">
                          <Link
                            href={`/leads/${summary.lead.id}`}
                            className="inline-flex items-center rounded-lg border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:border-(--accent) hover:text-(--accent)"
                          >
                            Abrir histórico
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="space-y-3 lg:hidden">
              {replyLeadSummaries.map((summary) => {
                const firstReply = summary.firstReply
                const latestReply = summary.latestReply

                return (
                  <article
                    key={summary.lead.id}
                    className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4"
                  >
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          href={`/leads/${summary.lead.id}`}
                          className="text-sm font-semibold text-(--text-primary) transition-colors hover:text-(--accent)"
                        >
                          {summary.lead.name}
                        </Link>
                        {summary.lead.has_multiple_active_cadences ? (
                          <span className="inline-flex items-center gap-1 rounded-(--radius-full) border border-(--warning) bg-(--warning-subtle) px-2 py-0.5 text-[11px] font-medium text-(--warning-subtle-fg)">
                            <AlertTriangle size={12} aria-hidden="true" />
                            {summary.lead.active_cadence_count} cadências ativas
                          </span>
                        ) : null}
                      </div>

                      <p className="text-sm text-(--text-secondary)">
                        {renderLeadSubtitle(summary)}
                      </p>

                      <div className="grid gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-3 text-sm">
                        <div>
                          <p className="text-xs uppercase tracking-[0.12em] text-(--text-tertiary)">
                            1ª resposta contabilizada
                          </p>
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            <span className="font-medium text-(--text-primary)">
                              {formatRelativeTime(firstReply.replied_at)}
                            </span>
                            <BadgeChannel channel={firstReply.channel} />
                            {firstReply.step_number != null ? (
                              <span className="rounded-(--radius-full) border border-(--border-default) bg-(--bg-overlay) px-2 py-0.5 text-xs text-(--text-secondary)">
                                Step #{firstReply.step_number}
                              </span>
                            ) : null}
                            {firstReply.reply_match_source ? (
                              <ReplyMatchSourceBadge source={firstReply.reply_match_source} short />
                            ) : null}
                          </div>
                        </div>

                        <div>
                          <p className="text-xs uppercase tracking-[0.12em] text-(--text-tertiary)">
                            Última interação
                          </p>
                          <p className="mt-2 font-medium text-(--text-primary)">
                            {formatRelativeTime(latestReply.replied_at)}
                          </p>
                          <p className="text-sm text-(--text-secondary)">
                            {latestReply.intent
                              ? (intentLabel[latestReply.intent] ?? latestReply.intent)
                              : "Intent não classificado"}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs uppercase tracking-[0.12em] text-(--text-tertiary)">
                            Canais e eventos
                          </p>
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            {summary.channels.map((channel) => (
                              <BadgeChannel
                                key={`${summary.lead.id}-${channel}`}
                                channel={channel}
                              />
                            ))}
                            <span className="rounded-(--radius-full) border border-(--border-default) bg-(--bg-overlay) px-2 py-0.5 text-xs text-(--text-secondary)">
                              {summary.eventCount} evento{summary.eventCount === 1 ? "" : "s"}
                            </span>
                          </div>
                        </div>
                      </div>

                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-(--text-secondary)">
                        {buildReplyPreview(latestReply.reply_text)}
                      </p>

                      <Link
                        href={`/leads/${summary.lead.id}`}
                        className="inline-flex items-center rounded-lg border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:border-(--accent) hover:text-(--accent)"
                      >
                        Abrir histórico
                      </Link>
                    </div>
                  </article>
                )
              })}
            </div>
          </>
        )}
      </section>

      <section className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
        <div className="mb-4 flex items-start gap-3">
          <div className="rounded-full bg-(--warning-subtle) p-2 text-(--warning-subtle-fg)">
            <ShieldAlert size={16} aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-(--text-primary)">Auditoria de replies</h2>
            <p className="text-xs text-(--text-secondary)">
              Visualize a fila em formato compacto e abra o detalhe apenas quando precisar tratar um
              inbound específico.
            </p>
          </div>
        </div>

        {query.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, index) => (
              <div key={index} className="h-24 animate-pulse rounded-lg bg-(--bg-overlay)" />
            ))}
          </div>
        ) : auditItems.length === 0 ? (
          <EmptyState
            icon={ShieldAlert}
            title="Nenhum reply pendente de auditoria"
            description="Quando um inbound ficar ambíguo ou sem vínculo automático para esta base, ele aparecerá aqui."
            className="px-4 py-10"
          />
        ) : (
          <ReplyAuditTable
            items={normalizedAuditItems}
            cadenceId={cadenceId}
            emptyTitle="Nenhum reply pendente de auditoria"
            emptyDescription="Quando um inbound ficar ambíguo ou sem vínculo automático para esta base, ele aparecerá aqui."
          />
        )}
      </section>
    </div>
  )
}
