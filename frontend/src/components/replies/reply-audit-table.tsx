"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { AlertTriangle, ChevronRight, Loader2, ShieldAlert } from "lucide-react"
import { toast } from "sonner"
import { BadgeChannel } from "@/components/shared/badge-channel"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  useLeadSteps,
  useLinkLeadReplyAudit,
  useReviewLeadReplyAudit,
} from "@/lib/api/hooks/use-leads"
import {
  getReplyMatchSourceMeta,
  ReplyMatchSourceBadge,
} from "@/components/replies/reply-match-source-badge"
import { formatRelativeTime } from "@/lib/utils"

export type ReplyAuditStatus = "ambiguous" | "unmatched" | "low_confidence"

export interface ReplyAuditTableItem {
  interactionId: string
  leadId: string
  leadName: string
  leadCompany: string | null
  leadJobTitle: string | null
  leadHasMultipleActiveCadences: boolean
  leadActiveCadenceCount: number
  channel: string
  createdAt: string
  replyMatchStatus: ReplyAuditStatus
  replyMatchSource: string | null
  replyMatchSentCadenceCount: number | null
  contentText: string | null
}

interface ReplyAuditTableProps {
  items: ReplyAuditTableItem[]
  emptyTitle: string
  emptyDescription: string
  isLoading?: boolean
  cadenceId?: string
  showLeadColumn?: boolean
}

interface AuditTableRow {
  item: ReplyAuditTableItem
  preview: string
}

type ReplyAuditFilter = "all" | ReplyAuditStatus
type ReplyAuditChannelFilter = "all" | string

const statusLabel: Record<ReplyAuditStatus, string> = {
  ambiguous: "Ambíguo",
  unmatched: "Sem vínculo automático",
  low_confidence: "Vínculo fraco",
}

const statusClass: Record<ReplyAuditStatus, string> = {
  ambiguous: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  unmatched: "border-(--border-default) bg-(--bg-overlay) text-(--text-secondary)",
  low_confidence: "border-(--info) bg-(--info-subtle) text-(--info-subtle-fg)",
}

function buildAuditPreview(content: string | null): string {
  const normalized = (content ?? "").replace(/\s+/g, " ").trim()
  if (!normalized) {
    return "Sem conteúdo textual disponível."
  }
  if (normalized.length <= 132) {
    return normalized
  }
  return `${normalized.slice(0, 129)}...`
}

function formatChannelLabel(channel: string): string {
  const labels: Record<string, string> = {
    email: "Email",
    linkedin_dm: "LinkedIn DM",
    linkedin_connect: "LinkedIn Connect",
    linkedin_inmail: "LinkedIn InMail",
  }
  return labels[channel] ?? channel
}

function replyCandidateStepChannels(channel: string): string[] {
  if (channel === "linkedin_dm") {
    return ["linkedin_dm", "linkedin_connect"]
  }
  return [channel]
}

function getReplyAuditStatusFilterLabel(filter: ReplyAuditFilter): string {
  if (filter === "all") {
    return "Todos os status"
  }
  return statusLabel[filter]
}

function getReplyAuditChannelFilterLabel(filter: ReplyAuditChannelFilter): string {
  if (filter === "all") {
    return "Todos os canais"
  }
  return formatChannelLabel(filter)
}

export function ReplyAuditTable({
  items,
  emptyTitle,
  emptyDescription,
  isLoading = false,
  cadenceId,
  showLeadColumn = true,
}: ReplyAuditTableProps) {
  const [selectedItem, setSelectedItem] = useState<ReplyAuditTableItem | null>(null)
  const [selectedStepId, setSelectedStepId] = useState<string | undefined>(undefined)
  const [statusFilter, setStatusFilter] = useState<ReplyAuditFilter>("all")
  const [channelFilter, setChannelFilter] = useState<ReplyAuditChannelFilter>("all")
  const auditRows = useMemo<AuditTableRow[]>(
    () => items.map((item) => ({ item, preview: buildAuditPreview(item.contentText) })),
    [items],
  )
  const { mutate: reviewReplyAudit, isPending: isReviewPending } = useReviewLeadReplyAudit()
  const { mutate: linkReplyAudit, isPending: isLinkPending } = useLinkLeadReplyAudit()
  const stepsQuery = useLeadSteps(selectedItem?.leadId ?? "")

  useEffect(() => {
    setSelectedStepId(undefined)
  }, [selectedItem?.interactionId])

  const channelOptions = useMemo(
    () => Array.from(new Set(auditRows.map(({ item }) => item.channel))).sort(),
    [auditRows],
  )

  const filteredRows = useMemo(() => {
    return auditRows.filter(({ item }) => {
      if (statusFilter !== "all" && item.replyMatchStatus !== statusFilter) {
        return false
      }
      if (channelFilter !== "all" && item.channel !== channelFilter) {
        return false
      }
      return true
    })
  }, [auditRows, channelFilter, statusFilter])

  const statusCounts = useMemo(() => {
    return auditRows.reduce<Record<ReplyAuditStatus, number>>(
      (counts, { item }) => {
        counts[item.replyMatchStatus] += 1
        return counts
      },
      { ambiguous: 0, unmatched: 0, low_confidence: 0 },
    )
  }, [auditRows])

  const channelCounts = useMemo(() => {
    return auditRows.reduce<Record<string, number>>((counts, { item }) => {
      counts[item.channel] = (counts[item.channel] ?? 0) + 1
      return counts
    }, {})
  }, [auditRows])

  const candidateSteps = useMemo(() => {
    if (!selectedItem || !stepsQuery.data) {
      return []
    }

    const allowedChannels = replyCandidateStepChannels(selectedItem.channel)
    return stepsQuery.data
      .filter(
        (step) =>
          step.item_kind === "cadence_step" &&
          allowedChannels.includes(step.channel) &&
          (step.sent_at != null || step.status === "replied"),
      )
      .sort((left, right) => {
        const leftTime = new Date(left.sent_at ?? left.scheduled_at).getTime()
        const rightTime = new Date(right.sent_at ?? right.scheduled_at).getTime()
        return rightTime - leftTime
      })
  }, [selectedItem, stepsQuery.data])

  const selectedStep = useMemo(
    () => candidateSteps.find((step) => step.id === selectedStepId) ?? null,
    [candidateSteps, selectedStepId],
  )
  const isMutating = isReviewPending || isLinkPending
  const selectedSourceMeta = selectedItem
    ? getReplyMatchSourceMeta(selectedItem.replyMatchSource)
    : null
  const filterToolbar = (
    <div className="overflow-x-auto">
      <div className="flex min-w-max items-center gap-3 rounded-lg border border-(--border-subtle) bg-(--bg-surface) px-3 py-3 shadow-(--shadow-sm)">
        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-(--text-tertiary)">
          Filtros
        </p>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button type="button" size="sm" variant="outline">
              Status: {getReplyAuditStatusFilterLabel(statusFilter)}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-56">
            <DropdownMenuLabel>Filtrar por status</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuRadioGroup
              value={statusFilter}
              onValueChange={(value) => setStatusFilter(value as ReplyAuditFilter)}
            >
              <DropdownMenuRadioItem value="all">Todos ({auditRows.length})</DropdownMenuRadioItem>
              {(["ambiguous", "unmatched", "low_confidence"] as const).map((status) => (
                <DropdownMenuRadioItem key={status} value={status}>
                  {statusLabel[status]} ({statusCounts[status]})
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button type="button" size="sm" variant="outline">
              Canal: {getReplyAuditChannelFilterLabel(channelFilter)}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-56">
            <DropdownMenuLabel>Filtrar por canal</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuRadioGroup value={channelFilter} onValueChange={setChannelFilter}>
              <DropdownMenuRadioItem value="all">
                Todos os canais ({auditRows.length})
              </DropdownMenuRadioItem>
              {channelOptions.map((channel) => (
                <DropdownMenuRadioItem key={channel} value={channel}>
                  {formatChannelLabel(channel)} ({channelCounts[channel] ?? 0})
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        {(statusFilter !== "all" || channelFilter !== "all") && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              setStatusFilter("all")
              setChannelFilter("all")
            }}
          >
            Limpar filtros
          </Button>
        )}
      </div>
    </div>
  )

  function handleReviewSelectedItem() {
    if (!selectedItem) {
      return
    }

    const reviewPayload = {
      leadId: selectedItem.leadId,
      interactionId: selectedItem.interactionId,
      ...(cadenceId ? { cadenceId } : {}),
    }

    reviewReplyAudit(reviewPayload, {
      onSuccess: () => {
        toast.success("Reply marcado como revisado")
        setSelectedItem(null)
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : "Falha ao revisar o reply")
      },
    })
  }

  function handleLinkSelectedItem() {
    if (!selectedItem || !selectedStep) {
      return
    }

    linkReplyAudit(
      {
        leadId: selectedItem.leadId,
        interactionId: selectedItem.interactionId,
        cadenceStepId: selectedStep.id,
        cadenceId: selectedStep.cadence_id,
      },
      {
        onSuccess: () => {
          toast.success("Reply vinculado como resposta")
          setSelectedItem(null)
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : "Falha ao vincular o reply")
        },
      },
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, index) => (
          <div key={index} className="h-24 animate-pulse rounded-lg bg-(--bg-overlay)" />
        ))}
      </div>
    )
  }

  if (auditRows.length === 0) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title={emptyTitle}
        description={emptyDescription}
        className="px-4 py-10"
      />
    )
  }

  if (filteredRows.length === 0) {
    return (
      <div className="space-y-3">
        {filterToolbar}
        <EmptyState
          icon={ShieldAlert}
          title="Nenhum item neste filtro"
          description="Ajuste os filtros de status ou canal para ver os replies pendentes desta fila de auditoria."
          className="px-4 py-10"
        />
      </div>
    )
  }

  return (
    <>
      <div className="space-y-3">
        {filterToolbar}

        <div className="overflow-hidden rounded-lg border border-(--accent-border) bg-(--bg-surface) shadow-(--shadow-sm)">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-208 text-left text-sm">
              <thead>
                <tr className="border-b border-(--accent-hover) bg-(--accent)">
                  {showLeadColumn ? (
                    <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                      Lead
                    </th>
                  ) : null}
                  <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                    Canal
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                    Detectado
                  </th>
                  <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                    Resumo
                  </th>
                  <th className="px-4 py-3 text-right text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                    Ação
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-(--border-subtle) bg-(--bg-surface)">
                {filteredRows.map(({ item, preview }) => (
                  <tr
                    key={item.interactionId}
                    className="cursor-pointer bg-(--bg-surface) text-(--text-secondary) transition-colors hover:bg-(--accent-subtle)"
                    onClick={() => setSelectedItem(item)}
                  >
                    {showLeadColumn ? (
                      <td className="px-4 py-3 align-top">
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-semibold text-(--text-primary)">{item.leadName}</p>
                            {item.leadHasMultipleActiveCadences ? (
                              <span className="inline-flex items-center gap-1 rounded-(--radius-full) border border-(--warning) bg-(--warning-subtle) px-2 py-0.5 text-[11px] font-medium text-(--warning-subtle-fg)">
                                <AlertTriangle size={11} aria-hidden="true" />
                                {item.leadActiveCadenceCount} cadências ativas
                              </span>
                            ) : null}
                          </div>
                          <p className="text-xs text-(--text-tertiary)">
                            {[item.leadCompany, item.leadJobTitle].filter(Boolean).join(" · ") ||
                              "Lead sem empresa/cargo preenchidos"}
                          </p>
                        </div>
                      </td>
                    ) : null}
                    <td className="px-4 py-3 align-top">
                      <BadgeChannel channel={item.channel} />
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`inline-flex items-center gap-1 rounded-(--radius-full) border px-2 py-0.5 text-xs font-medium ${statusClass[item.replyMatchStatus]}`}
                      >
                        <AlertTriangle size={12} aria-hidden="true" />
                        {statusLabel[item.replyMatchStatus]}
                      </span>
                    </td>
                    <td className="px-4 py-3 align-top text-xs text-(--text-tertiary)">
                      <time dateTime={item.createdAt}>{formatRelativeTime(item.createdAt)}</time>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <p className="max-w-xl text-sm leading-relaxed text-(--text-secondary)">
                        {preview}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-right align-top">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          setSelectedItem(item)
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-(--accent-border) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--accent) transition-colors hover:border-(--accent-hover) hover:bg-(--accent-subtle) hover:text-(--accent-hover)"
                      >
                        Tratar
                        <ChevronRight size={14} aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-2 p-2 md:hidden">
            {filteredRows.map(({ item, preview }) => (
              <button
                key={item.interactionId}
                type="button"
                onClick={() => setSelectedItem(item)}
                className="w-full rounded-lg border border-(--border-subtle) bg-(--bg-surface) p-3 text-left transition-colors hover:border-(--accent-border) hover:bg-(--accent-subtle)"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {showLeadColumn ? (
                    <p className="text-sm font-semibold text-(--text-primary)">{item.leadName}</p>
                  ) : null}
                  {showLeadColumn && item.leadHasMultipleActiveCadences ? (
                    <span className="inline-flex items-center gap-1 rounded-(--radius-full) border border-(--warning) bg-(--warning-subtle) px-2 py-0.5 text-[11px] font-medium text-(--warning-subtle-fg)">
                      <AlertTriangle size={11} aria-hidden="true" />
                      {item.leadActiveCadenceCount} cadências ativas
                    </span>
                  ) : null}
                  <BadgeChannel channel={item.channel} />
                  <span
                    className={`inline-flex items-center gap-1 rounded-(--radius-full) border px-2 py-0.5 text-xs font-medium ${statusClass[item.replyMatchStatus]}`}
                  >
                    <AlertTriangle size={12} aria-hidden="true" />
                    {statusLabel[item.replyMatchStatus]}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between gap-3 text-xs text-(--text-tertiary)">
                  <time dateTime={item.createdAt}>{formatRelativeTime(item.createdAt)}</time>
                  <span className="inline-flex items-center gap-1 font-medium text-(--accent)">
                    Abrir detalhe
                    <ChevronRight size={14} aria-hidden="true" />
                  </span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-(--text-secondary)">{preview}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      <Dialog open={selectedItem !== null} onOpenChange={(open) => !open && setSelectedItem(null)}>
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
          {selectedItem ? (
            <>
              <DialogHeader>
                <DialogTitle className="flex flex-wrap items-center gap-2 text-(--text-primary)">
                  <span>Tratamento do reply auditado</span>
                  <BadgeChannel channel={selectedItem.channel} />
                  <span
                    className={`inline-flex items-center gap-1 rounded-(--radius-full) border px-2 py-0.5 text-xs font-medium ${statusClass[selectedItem.replyMatchStatus]}`}
                  >
                    <AlertTriangle size={12} aria-hidden="true" />
                    {statusLabel[selectedItem.replyMatchStatus]}
                  </span>
                </DialogTitle>
                <DialogDescription>
                  Revise o contexto completo e marque como revisado quando este inbound já estiver
                  tratado.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-(--text-tertiary)">
                    Lead
                  </p>
                  <p className="mt-2 text-base font-semibold text-(--text-primary)">
                    {selectedItem.leadName}
                  </p>
                  <p className="mt-1 text-sm text-(--text-secondary)">
                    {[selectedItem.leadCompany, selectedItem.leadJobTitle]
                      .filter(Boolean)
                      .join(" · ") || "Sem empresa/cargo preenchidos"}
                  </p>
                  {selectedItem.leadHasMultipleActiveCadences ? (
                    <div className="mt-3 inline-flex items-center gap-1 rounded-(--radius-full) border border-(--warning) bg-(--warning-subtle) px-2 py-1 text-xs font-medium text-(--warning-subtle-fg)">
                      <AlertTriangle size={12} aria-hidden="true" />
                      {selectedItem.leadActiveCadenceCount} cadências ativas
                    </div>
                  ) : null}
                </div>

                <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-(--text-tertiary)">
                    Metadados
                  </p>
                  <div className="mt-2 space-y-2 text-sm text-(--text-secondary)">
                    <p>
                      <span className="font-medium text-(--text-primary)">Detectado:</span>{" "}
                      <time dateTime={selectedItem.createdAt}>
                        {formatRelativeTime(selectedItem.createdAt)}
                      </time>
                    </p>
                    <p>
                      <span className="font-medium text-(--text-primary)">Canal:</span>{" "}
                      {formatChannelLabel(selectedItem.channel)}
                    </p>
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-(--text-primary)">Fonte do vínculo:</span>
                        <ReplyMatchSourceBadge source={selectedItem.replyMatchSource} />
                      </div>
                      {selectedSourceMeta ? (
                        <p className="text-xs text-(--text-tertiary)">
                          {selectedSourceMeta.description}
                        </p>
                      ) : null}
                    </div>
                    {selectedItem.replyMatchSentCadenceCount != null ? (
                      <p>
                        <span className="font-medium text-(--text-primary)">
                          Cadências candidatas:
                        </span>{" "}
                        {selectedItem.replyMatchSentCadenceCount}
                      </p>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-(--text-tertiary)">
                    Conteúdo completo
                  </p>
                  <div className="mt-3 rounded-lg border border-(--border-subtle) bg-(--bg-surface) p-4">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-(--text-secondary)">
                      {selectedItem.contentText || "Sem conteúdo textual disponível."}
                    </p>
                  </div>
                </div>

                <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-(--text-tertiary)">
                        Tratamento
                      </p>
                      <p className="mt-2 text-sm text-(--text-secondary)">
                        Marcar como revisado apenas remove o item da fila de auditoria. Vincular
                        como resposta transforma este inbound em reply confiável do step escolhido.
                      </p>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-(--radius-full) border border-(--accent-border) bg-(--accent-subtle) px-2 py-1 text-xs font-medium text-(--accent-subtle-fg)">
                      {candidateSteps.length === 1
                        ? "1 step elegível"
                        : `${candidateSteps.length} steps elegíveis`}
                    </span>
                  </div>

                  <div className="mt-4 space-y-3">
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-(--text-tertiary)">
                        Step para vincular como resposta
                      </p>
                      <Select
                        {...(selectedStepId ? { value: selectedStepId } : {})}
                        onValueChange={setSelectedStepId}
                        disabled={stepsQuery.isLoading || candidateSteps.length === 0 || isMutating}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione o step correto" />
                        </SelectTrigger>
                        <SelectContent>
                          {candidateSteps.map((step) => {
                            const stepTime = step.sent_at ?? step.scheduled_at
                            const cadenceLabel = step.cadence_name ?? "Cadência sem nome"
                            return (
                              <SelectItem key={step.id} value={step.id}>
                                {`${cadenceLabel} · Step #${step.step_number} · ${formatChannelLabel(step.channel)} · ${formatRelativeTime(stepTime)}`}
                              </SelectItem>
                            )
                          })}
                        </SelectContent>
                      </Select>
                    </div>

                    {stepsQuery.isLoading ? (
                      <p className="text-xs text-(--text-tertiary)">
                        Carregando steps elegíveis...
                      </p>
                    ) : null}

                    {!stepsQuery.isLoading && candidateSteps.length === 0 ? (
                      <div className="rounded-lg border border-(--warning) bg-(--warning-subtle) px-3 py-2 text-xs text-(--warning-subtle-fg)">
                        Não encontrei nenhum step já enviado e compatível com este canal. Neste
                        caso, use apenas “Marcar como revisado”.
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>

              <DialogFooter className="gap-2 pt-2">
                <Link
                  href={`/leads/${selectedItem.leadId}`}
                  className="inline-flex items-center justify-center rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:border-(--accent) hover:text-(--accent)"
                >
                  Abrir lead
                </Link>
                <Button type="button" variant="outline" onClick={() => setSelectedItem(null)}>
                  Fechar
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReviewSelectedItem}
                  disabled={isMutating}
                >
                  {isReviewPending ? (
                    <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                  ) : null}
                  Marcar como revisado
                </Button>
                <Button
                  type="button"
                  onClick={handleLinkSelectedItem}
                  disabled={isMutating || !selectedStep}
                >
                  {isLinkPending ? (
                    <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                  ) : null}
                  Vincular como resposta
                </Button>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  )
}
