"use client"

import { useEffect, useMemo, useState } from "react"
import {
  Loader2,
  Play,
  AlertCircle,
  Search,
  MessageSquareText,
  Users,
  BookOpen,
  Plus,
  X,
  History,
  SlidersHorizontal,
  FileText,
  ExternalLink,
  ChevronRight,
  MessageCircle,
  Repeat2,
  BookmarkCheck,
  ThumbsUp,
} from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { HookBadge, PillarBadge } from "@/components/content/post-badges"
import { useContentThemes, type ContentTheme } from "@/lib/api/hooks/use-content"
import { cn } from "@/lib/utils"
import { PostReferenceCard } from "./post-reference-card"
import { IcpPostCard } from "./icp-post-card"
import { LinkedPostSelector } from "./linked-post-selector"
import {
  engagementKeys,
  useEngagementPosts,
  useEngagementSession,
  useEngagementSessions,
  useRunScan,
  useUnmarkCommentPosted,
} from "@/lib/api/hooks/use-content-engagement"
import type { EngagementPost, EngagementSession, EngagementSessionDetail, SessionStatus } from "@/lib/content-engagement/types"
import type { EngagementComment } from "@/lib/content-engagement/types"
import { toast } from "sonner"

// ── Skeleton do scan em andamento ─────────────────────────────────────────────

const STEP_LABELS: Record<number, string> = {
  1: "Buscando posts de referência...",
  2: "Buscando posts de decisores ICP...",
  3: "Analisando posts com IA...",
  4: "Gerando sugestões de comentários...",
}

const STEP_PROGRESS_WIDTH: Record<number, string> = {
  1: "w-1/4",
  2: "w-1/2",
  3: "w-3/4",
  4: "w-full",
}

const HISTORY_PAGE_SIZE = 8

const STATUS_META: Record<SessionStatus, { label: string; className: string }> = {
  running: {
    label: "Em andamento",
    className: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
  },
  completed: {
    label: "Concluído",
    className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  },
  partial: {
    label: "Parcial",
    className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  },
  failed: {
    label: "Falhou",
    className: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  },
}

function formatHistoryDate(value: string) {
  return new Date(value).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function formatLinkedPostLabel(linkedPostId: string | null) {
  if (!linkedPostId) return "Sem vínculo"
  return `Post ${linkedPostId.slice(0, 8)}`
}

function SessionStatusBadge({ status }: { status: SessionStatus }) {
  const meta = STATUS_META[status]
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold", meta.className)}>
      {status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
      {meta.label}
    </span>
  )
}

function ActiveConfigurationSummary({
  linkedPostId,
  selectedThemesCount,
  manualKeywordsCount,
  effectiveKeywords,
}: {
  linkedPostId: string | null
  selectedThemesCount: number
  manualKeywordsCount: number
  effectiveKeywords: string[]
}) {
  const hasConfiguration = !!linkedPostId || effectiveKeywords.length > 0

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) px-5 py-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">Configuração ativa</p>
          <p className="mt-0.5 text-xs text-(--text-secondary)">
            {hasConfiguration
              ? "O próximo scan vai usar os filtros e contexto abaixo."
              : "Nenhum filtro extra aplicado. O próximo scan usará a estratégia padrão."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] font-medium text-(--text-secondary)">
          <span className="inline-flex items-center gap-1 rounded-full bg-(--bg-overlay) px-2.5 py-1">
            <FileText className="h-3 w-3" />
            {linkedPostId ? "Post vinculado" : "Sem post vinculado"}
          </span>
          <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1">
            {selectedThemesCount} tema{selectedThemesCount !== 1 ? "s" : ""}
          </span>
          <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1">
            {manualKeywordsCount} keyword{manualKeywordsCount !== 1 ? "s" : ""} manual{manualKeywordsCount !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {effectiveKeywords.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {effectiveKeywords.slice(0, 6).map((keyword) => (
            <span
              key={keyword}
              className="inline-flex items-center rounded-full border border-(--border-default) bg-(--bg-sunken) px-2.5 py-1 text-xs text-(--text-secondary)"
            >
              {keyword}
            </span>
          ))}
          {effectiveKeywords.length > 6 && (
            <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-tertiary)">
              +{effectiveKeywords.length - 6}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function ScanConfigurationPanel({
  linkedPostId,
  onLinkedPostChange,
  themes,
  selectedThemeIds,
  onToggleTheme,
  keywordInput,
  onKeywordInputChange,
  onKeywordInputKeyDown,
  onAddKeyword,
  manualKeywords,
  onRemoveKeyword,
  effectiveKeywords,
  disabled,
}: {
  linkedPostId: string | null
  onLinkedPostChange: (postId: string | null) => void
  themes: ContentTheme[]
  selectedThemeIds: string[]
  onToggleTheme: (themeId: string) => void
  keywordInput: string
  onKeywordInputChange: (value: string) => void
  onKeywordInputKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void
  onAddKeyword: () => void
  manualKeywords: string[]
  onRemoveKeyword: (keyword: string) => void
  effectiveKeywords: string[]
  disabled: boolean
}) {
  return (
    <div className="space-y-4">
      <LinkedPostSelector
        value={linkedPostId}
        onChange={onLinkedPostChange}
        disabled={disabled}
      />

      <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-(--text-primary)">Configuração do scan</p>
            <p className="text-xs text-(--text-secondary) mt-0.5">
              Selecione temas do banco e adicione palavras-chave manuais para deixar a busca mais precisa.
            </p>
          </div>
          {effectiveKeywords.length > 0 && (
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-[11px] font-medium text-(--text-secondary)">
              {effectiveKeywords.length} keyword{effectiveKeywords.length !== 1 ? "s" : ""} ativa{effectiveKeywords.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">Temas do banco</p>
          <div className="flex max-h-52 flex-wrap gap-2 overflow-y-auto pr-1">
            {themes.map((theme) => {
              const isSelected = selectedThemeIds.includes(theme.id)
              return (
                <button
                  key={theme.id}
                  type="button"
                  onClick={() => onToggleTheme(theme.id)}
                  disabled={disabled}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition-colors",
                    isSelected
                      ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                      : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--accent)",
                    theme.used && !isSelected && "opacity-70",
                  )}
                >
                  <PillarBadge pillar={theme.pillar} className="px-1.5 py-0 text-[10px]" />
                  <span>{theme.title}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">Palavras-chave manuais</p>
          <div className="flex gap-2">
            <Input
              value={keywordInput}
              onChange={(event) => onKeywordInputChange(event.target.value)}
              onKeyDown={onKeywordInputKeyDown}
              placeholder="Ex.: automação comercial, ERP, IA aplicada"
              disabled={disabled}
            />
            <Button
              type="button"
              variant="outline"
              className="gap-1.5"
              onClick={onAddKeyword}
              disabled={disabled || !keywordInput.trim()}
            >
              <Plus className="h-3.5 w-3.5" />
              Adicionar
            </Button>
          </div>
          {manualKeywords.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {manualKeywords.map((keyword) => (
                <span
                  key={keyword}
                  className="inline-flex items-center gap-1.5 rounded-full border border-(--border-default) bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-secondary)"
                >
                  {keyword}
                  <button
                    type="button"
                    className="rounded-full p-0.5 text-(--text-muted) transition hover:bg-(--bg-muted) hover:text-(--text-primary)"
                    onClick={() => onRemoveKeyword(keyword)}
                    aria-label={`Remover palavra-chave ${keyword}`}
                    title={`Remover palavra-chave ${keyword}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {effectiveKeywords.length > 0 && (
          <div className="rounded-lg border border-(--border-default) bg-(--bg-sunken) px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-(--text-tertiary)">Busca efetiva desta execução</p>
            <p className="mt-1 text-sm text-(--text-secondary)">
              {effectiveKeywords.join(" • ")}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function SessionHistoryTable({
  sessions,
  activeSessionId,
  onSelectSession,
  statusFilter,
  onStatusFilterChange,
  page,
  onPrevPage,
  onNextPage,
  canGoNext,
  isLoading,
}: {
  sessions: EngagementSession[]
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
  statusFilter: SessionStatus | "all"
  onStatusFilterChange: (status: SessionStatus | "all") => void
  page: number
  onPrevPage: () => void
  onNextPage: () => void
  canGoNext: boolean
  isLoading: boolean
}) {
  const filteredSessions = statusFilter === "all"
    ? sessions
    : sessions.filter((session) => session.status === statusFilter)

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-5 space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-(--text-primary)">Histórico de buscas</p>
          <p className="text-xs text-(--text-secondary) mt-0.5">
            Sessões paginadas com filtro de status e acesso direto ao resultado.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["all", "running", "completed", "partial", "failed"] as const).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => onStatusFilterChange(status)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                statusFilter === status
                  ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                  : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:border-(--accent) hover:text-(--text-primary)",
              )}
            >
              {status === "all" ? "Todos" : STATUS_META[status].label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-(--border-default)">
        <table className="min-w-full divide-y divide-(--border-default)">
          <thead className="bg-(--bg-overlay)">
            <tr className="text-left text-[11px] uppercase tracking-wider text-(--text-tertiary)">
              <th className="px-4 py-3 font-semibold">Data</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Post vinculado</th>
              <th className="px-4 py-3 font-semibold text-right">Referências</th>
              <th className="px-4 py-3 font-semibold text-right">ICP</th>
              <th className="px-4 py-3 font-semibold text-right">Comentários</th>
              <th className="px-4 py-3 font-semibold text-right">Ação</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-(--border-default) bg-(--bg-surface)">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <tr key={index} className="animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 w-28 rounded bg-(--bg-overlay)" /></td>
                  <td className="px-4 py-3"><div className="h-5 w-24 rounded-full bg-(--bg-overlay)" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-24 rounded bg-(--bg-overlay)" /></td>
                  <td className="px-4 py-3 text-right"><div className="ml-auto h-4 w-8 rounded bg-(--bg-overlay)" /></td>
                  <td className="px-4 py-3 text-right"><div className="ml-auto h-4 w-8 rounded bg-(--bg-overlay)" /></td>
                  <td className="px-4 py-3 text-right"><div className="ml-auto h-4 w-8 rounded bg-(--bg-overlay)" /></td>
                  <td className="px-4 py-3 text-right"><div className="ml-auto h-8 w-16 rounded bg-(--bg-overlay)" /></td>
                </tr>
              ))
            ) : filteredSessions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-(--text-secondary)">
                  Nenhuma sessão encontrada para este filtro nesta página.
                </td>
              </tr>
            ) : (
              filteredSessions.map((session) => {
                const isActive = session.id === activeSessionId
                return (
                  <tr
                    key={session.id}
                    className={cn(
                      "transition-colors hover:bg-(--bg-overlay)",
                      isActive && "bg-(--accent-subtle)/60",
                    )}
                  >
                    <td className="px-4 py-3 text-sm text-(--text-primary)">{formatHistoryDate(session.created_at)}</td>
                    <td className="px-4 py-3"><SessionStatusBadge status={session.status} /></td>
                    <td className="px-4 py-3 text-sm text-(--text-secondary)">{formatLinkedPostLabel(session.linked_post_id)}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-(--text-primary)">{session.references_found}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-(--text-primary)">{session.icp_posts_found}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-(--text-primary)">{session.comments_generated}</td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        type="button"
                        variant={isActive ? "default" : "outline"}
                        size="sm"
                        onClick={() => onSelectSession(session.id)}
                      >
                        Ver
                      </Button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-(--text-tertiary)">Página {page}</p>
        <div className="flex items-center gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onPrevPage} disabled={page === 1 || isLoading}>
            Anterior
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={onNextPage} disabled={!canGoNext || isLoading}>
            Próxima
          </Button>
        </div>
      </div>
    </div>
  )
}

function ScanningState({ currentStep }: { currentStep?: number | null }) {
  const stepLabel = currentStep ? STEP_LABELS[currentStep] : undefined
  const progressWidthClass = currentStep ? STEP_PROGRESS_WIDTH[currentStep] : "w-0"

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 rounded-xl border border-(--border-default) bg-(--bg-surface) px-6 py-5 shadow-sm">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-50 dark:bg-indigo-900/20">
          <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-(--text-primary)">Escaneando LinkedIn...</p>
            {currentStep && (
              <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                Etapa {currentStep}/4
              </span>
            )}
          </div>
          <p className="text-xs text-(--text-secondary) mt-0.5">
            {stepLabel ?? "Buscando posts relevantes, analisando com IA e gerando sugestões de comentários"}
          </p>
          {currentStep && (
            <div className="mt-3 h-1.5 w-full rounded-full bg-(--bg-overlay) overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full bg-indigo-500 transition-all duration-500 ease-out",
                  progressWidthClass,
                )}
              />
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-6 space-y-4 animate-pulse">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-(--bg-overlay)" />
              <div className="space-y-1.5 flex-1">
                <div className="h-4 w-32 rounded bg-(--bg-overlay)" />
                <div className="h-3 w-48 rounded bg-(--bg-overlay)" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-3.5 w-full rounded bg-(--bg-overlay)" />
              <div className="h-3.5 w-4/5 rounded bg-(--bg-overlay)" />
              <div className="h-3.5 w-2/3 rounded bg-(--bg-overlay)" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Summary bar ───────────────────────────────────────────────────────────────

function SummaryBar({ session }: { session: EngagementSessionDetail }) {
  const stats = [
    {
      icon: BookOpen,
      label: "Referências",
      value: session.references_found,
      color: "text-indigo-600 dark:text-indigo-400",
      bg: "bg-indigo-50 dark:bg-indigo-900/20",
      border: "border-indigo-200 dark:border-indigo-800",
    },
    {
      icon: Users,
      label: "Posts de ICP",
      value: session.icp_posts_found,
      color: "text-sky-600 dark:text-sky-400",
      bg: "bg-sky-50 dark:bg-sky-900/20",
      border: "border-sky-200 dark:border-sky-800",
    },
    {
      icon: MessageSquareText,
      label: "Comentários",
      value: session.comments_generated,
      color: "text-emerald-600 dark:text-emerald-400",
      bg: "bg-emerald-50 dark:bg-emerald-900/20",
      border: "border-emerald-200 dark:border-emerald-800",
    },
  ]

  return (
    <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <SessionStatusBadge status={session.status} />
          <span className="text-xs text-(--text-secondary)">
            {formatHistoryDate(session.created_at)}
          </span>
          <span className="hidden text-(--text-tertiary) sm:inline">•</span>
          <span className="text-xs text-(--text-secondary)">
            {formatLinkedPostLabel(session.linked_post_id)}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          {stats.map(({ icon: Icon, label, value, color, bg, border }) => (
            <div
              key={label}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-1.5",
                bg,
                border,
              )}
            >
              <Icon className={cn("h-3.5 w-3.5", color)} />
              <span className={cn("text-sm font-bold leading-none", color)}>{value}</span>
              <span className="text-xs text-(--text-secondary)">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function CompactMetric({
  icon: Icon,
  value,
}: {
  icon: typeof ThumbsUp
  value: number
}) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-(--text-tertiary)">
      <Icon className="h-3 w-3" />
      {value.toLocaleString("pt-BR")}
    </span>
  )
}

function ReferenceListRow({
  post,
  onOpen,
}: {
  post: EngagementPost
  onOpen: () => void
}) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-(--bg-overlay)">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-(--text-primary)">{post.author_name ?? "Autor desconhecido"}</p>
          {post.hook_type && <HookBadge hook={post.hook_type} />}
          {post.pillar && <PillarBadge pillar={post.pillar} />}
          {post.is_saved && (
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
              <BookmarkCheck className="h-3 w-3" />
              Salvo
            </span>
          )}
        </div>
        {post.author_title && (
          <p className="mt-0.5 text-xs text-(--text-secondary)">{post.author_title}</p>
        )}
        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-(--text-secondary)">{post.post_text}</p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <CompactMetric icon={ThumbsUp} value={post.likes} />
          <CompactMetric icon={MessageCircle} value={post.comments} />
          <CompactMetric icon={Repeat2} value={post.shares} />
          {post.engagement_score != null && post.engagement_score > 0 && (
            <span className="text-xs font-medium text-(--text-secondary)">Score {post.engagement_score}</span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {post.post_url && (
          <a
            href={post.post_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir post no LinkedIn"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-(--border-default) text-(--text-secondary) transition-colors hover:bg-(--bg-overlay)"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={onOpen}>
          Ver
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}

function IcpListRow({
  post,
  onOpen,
}: {
  post: EngagementPost
  onOpen: () => void
}) {
  const comments = post.suggested_comments ?? []
  const wasCommented = comments.some((comment) => comment.status === "posted")

  return (
    <div
      onClick={onOpen}
      className={cn(
        "flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-(--bg-overlay)",
        wasCommented && "bg-emerald-50/40 dark:bg-emerald-900/10",
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {wasCommented && (
            <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
              Comentário postado
            </span>
          )}
          <p className="text-sm font-semibold text-(--text-primary)">{post.author_name ?? "Autor desconhecido"}</p>
          {comments.length > 0 && (
            <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2 py-0.5 text-[10px] font-semibold text-(--text-secondary)">
              {comments.length} comentário{comments.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        {post.author_title && (
          <p className="mt-0.5 text-xs text-(--text-secondary)">{post.author_title}</p>
        )}
        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-(--text-secondary)">{post.post_text}</p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <CompactMetric icon={ThumbsUp} value={post.likes} />
          <CompactMetric icon={MessageCircle} value={post.comments} />
          <CompactMetric icon={Repeat2} value={post.shares} />
          {post.what_to_replicate && (
            <span className="line-clamp-1 text-xs text-amber-700 dark:text-amber-300">
              Ângulo: {post.what_to_replicate}
            </span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {post.post_url && (
          <a
            href={post.post_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir post no LinkedIn"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-(--border-default) text-(--text-secondary) transition-colors hover:bg-(--bg-overlay)"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={(event) => {
            event.stopPropagation()
            onOpen()
          }}
        >
          Abrir
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}

interface PostedCommentEntry {
  comment: EngagementComment
  post: EngagementPost
}

function PostedCommentsModal({
  open,
  onOpenChange,
  entries,
  onOpenPost,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  entries: PostedCommentEntry[]
  onOpenPost: (post: EngagementPost) => void
}) {
  const unmarkPosted = useUnmarkCommentPosted()

  async function handleUndo(commentId: string) {
    try {
      await unmarkPosted.mutateAsync(commentId)
      toast.success("Marcação desfeita")
    } catch {
      toast.error("Não foi possível desfazer a marcação")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Comentários marcados como postados</DialogTitle>
          <DialogDescription>
            Gerencie os comentários já marcados como enviados nesta sessão.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-x-auto rounded-lg border border-(--border-default)">
          <table className="min-w-full divide-y divide-(--border-default)">
            <thead className="bg-(--bg-overlay)">
              <tr className="text-left text-[11px] uppercase tracking-wider text-(--text-tertiary)">
                <th className="px-4 py-3 font-semibold">Sessão</th>
                <th className="px-4 py-3 font-semibold">Post</th>
                <th className="px-4 py-3 font-semibold">Comentário feito</th>
                <th className="px-4 py-3 font-semibold">Link</th>
                <th className="px-4 py-3 font-semibold text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-(--border-default) bg-(--bg-surface)">
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-(--text-secondary)">
                    Nenhum comentário marcado como postado em nenhuma sessão.
                  </td>
                </tr>
              ) : (
                entries.map(({ comment, post }) => (
                  <tr key={comment.id} className="align-top">
                    <td className="px-4 py-3">
                      <span className="text-sm text-(--text-secondary)">
                        {formatHistoryDate(comment.posted_at ?? comment.created_at)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-(--text-primary)">{post.author_name ?? "Autor desconhecido"}</p>
                        {post.author_title && (
                          <p className="text-xs text-(--text-secondary)">{post.author_title}</p>
                        )}
                        <p className="line-clamp-2 text-xs text-(--text-tertiary)">{post.post_text}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <p className="line-clamp-4 text-sm leading-relaxed text-(--text-primary)">{comment.comment_text}</p>
                    </td>
                    <td className="px-4 py-3">
                      {post.post_url ? (
                        <a
                          href={post.post_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm text-(--accent) hover:underline"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          Abrir post
                        </a>
                      ) : (
                        <span className="text-sm text-(--text-tertiary)">Sem link</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            onOpenPost(post)
                            onOpenChange(false)
                          }}
                        >
                          Ver detalhe
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUndo(comment.id)}
                          disabled={unmarkPosted.isPending}
                        >
                          Desfazer
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function PostDetailDrawer({
  post,
  onClose,
}: {
  post: EngagementPost | null
  onClose: () => void
}) {
  return (
    <Dialog open={!!post} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="left-auto right-0 top-0 h-dvh w-full max-w-3xl translate-x-0 translate-y-0 overflow-y-auto rounded-none border-l border-(--border-default) p-0">
        {post ? (
          <div className="space-y-0">
            <DialogHeader className="border-b border-(--border-default) px-6 py-5">
              <DialogTitle>{post.post_type === "icp" ? "Post de ICP" : "Referência"}</DialogTitle>
              <DialogDescription>
                {post.author_name ?? "Autor desconhecido"}
                {post.author_title ? ` · ${post.author_title}` : ""}
              </DialogDescription>
            </DialogHeader>
            <div className="p-6">
              {post.post_type === "icp" ? <IcpPostCard post={post} /> : <PostReferenceCard post={post} />}
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

// ── Resultados do scan ─────────────────────────────────────────────────────────

function SessionResults({
  session,
  onOpenPost,
}: {
  session: EngagementSessionDetail
  onOpenPost: (postId: string) => void
}) {
  const referencePosts = session.posts.filter((p) => p.post_type === "reference")
  const icpPosts = session.posts.filter((p) => p.post_type === "icp")
  const [activeTab, setActiveTab] = useState<"icp" | "references">(
    icpPosts.length > 0 ? "icp" : "references"
  )

  return (
    <div className="space-y-4">
      <SummaryBar session={session} />

      {session.status === "partial" && session.error_message && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-300/60 bg-amber-50 dark:bg-amber-900/10 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <p className="text-sm text-amber-700 dark:text-amber-300">{session.error_message}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-(--border-default)">
        {(
          [
            { key: "icp" as const, label: "Posts de ICP", count: icpPosts.length, icon: Users },
            { key: "references" as const, label: "Referências", count: referencePosts.length, icon: BookOpen },
          ] as const
        ).map(({ key, label, count, icon: TabIcon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === key
                ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-(--text-secondary) hover:text-(--text-primary)"
            )}
          >
            <TabIcon className="h-3.5 w-3.5" />
            {label}
            <span className={cn(
              "rounded-full px-2 py-0.5 text-xs font-semibold",
              activeTab === key
                ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
                : "bg-(--bg-overlay) text-(--text-secondary)"
            )}>
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div>
        {activeTab === "icp" && (
          icpPosts.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-center">
              <Users className="mb-3 h-8 w-8 text-(--text-tertiary)" />
              <p className="text-sm text-(--text-secondary)">Nenhum post de ICP encontrado neste scan.</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-surface) divide-y divide-(--border-default)">
              {icpPosts.map((post) => (
                <IcpListRow key={post.id} post={post} onOpen={() => onOpenPost(post.id)} />
              ))}
            </div>
          )
        )}
        {activeTab === "references" && (
          referencePosts.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-center">
              <BookOpen className="mb-3 h-8 w-8 text-(--text-tertiary)" />
              <p className="text-sm text-(--text-secondary)">Nenhuma referência encontrada neste scan.</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-surface) divide-y divide-(--border-default)">
              {referencePosts.map((post) => (
                <ReferenceListRow key={post.id} post={post} onOpen={() => onOpenPost(post.id)} />
              ))}
            </div>
          )
        )}
      </div>
    </div>
  )
}

// ── Componente principal ───────────────────────────────────────────────────────

export default function EngagementHubPage() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [linkedPostId, setLinkedPostId] = useState<string | null>(null)
  const [selectedThemeIds, setSelectedThemeIds] = useState<string[]>([])
  const [keywordInput, setKeywordInput] = useState("")
  const [manualKeywords, setManualKeywords] = useState<string[]>([])
  const [historyPage, setHistoryPage] = useState(1)
  const [historyStatusFilter, setHistoryStatusFilter] = useState<SessionStatus | "all">("all")
  const [configOpen, setConfigOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [postedCommentsOpen, setPostedCommentsOpen] = useState(false)
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: sessions } = useEngagementSessions({ page: 1, limit: HISTORY_PAGE_SIZE })
  const { data: historySessions = [], isLoading: isHistoryLoading } = useEngagementSessions({
    page: historyPage,
    limit: HISTORY_PAGE_SIZE,
  })
  const { data: allIcpPosts = [] } = useEngagementPosts(undefined, "icp")
  const { data: themes } = useContentThemes()
  const runScan = useRunScan()

  // Mantem um unico observer de sessao para evitar polling/states antigos competindo entre si.
  const effectiveSessionId = activeSessionId ?? sessions?.[0]?.id ?? null
  const { data: displaySession, isLoading } = useEngagementSession(effectiveSessionId)
  const selectedPost = useMemo(
    () => displaySession?.posts.find((post) => post.id === selectedPostId) ?? null,
    [displaySession?.posts, selectedPostId],
  )
  const postedCommentEntries = useMemo(
    () => allIcpPosts
      .flatMap((post) =>
        (post.suggested_comments ?? [])
          .filter((comment) => comment.status === "posted")
          .map((comment) => ({ comment, post })),
      )
      .sort((left, right) => {
        const leftTime = new Date(left.comment.posted_at ?? left.comment.created_at).getTime()
        const rightTime = new Date(right.comment.posted_at ?? right.comment.created_at).getTime()
        return rightTime - leftTime
      }),
    [allIcpPosts],
  )
  const isRunning = displaySession?.status === "running"
  const isTimedOut =
    isRunning &&
    displaySession?.created_at != null &&
    Date.now() - new Date(displaySession.created_at).getTime() > 5 * 60 * 1000
  const isScanPending = runScan.isPending
  const selectedThemes = useMemo(
    () => (themes ?? []).filter((theme) => selectedThemeIds.includes(theme.id)),
    [selectedThemeIds, themes],
  )
  const effectiveKeywords = useMemo(() => {
    const seen = new Set<string>()
    return [...selectedThemes.map((theme) => theme.title), ...manualKeywords].filter((keyword) => {
      const normalized = keyword.trim().toLowerCase()
      if (!normalized || seen.has(normalized)) return false
      seen.add(normalized)
      return true
    })
  }, [manualKeywords, selectedThemes])

  // Quando o scan completa, atualiza a lista de sessões para remover o spinner
  useEffect(() => {
    if (displaySession && displaySession.status !== "running") {
      queryClient.invalidateQueries({ queryKey: engagementKeys.sessions() })
    }
  }, [displaySession?.status, queryClient])

  function toggleTheme(themeId: string) {
    setSelectedThemeIds((current) =>
      current.includes(themeId)
        ? current.filter((id) => id !== themeId)
        : [...current, themeId],
    )
  }

  function addKeyword() {
    const keyword = keywordInput.trim()
    if (!keyword) return
    setManualKeywords((current) => {
      if (current.some((item) => item.toLowerCase() === keyword.toLowerCase())) return current
      return [...current, keyword]
    })
    setKeywordInput("")
  }

  function removeKeyword(keyword: string) {
    setManualKeywords((current) => current.filter((item) => item !== keyword))
  }

  function handleKeywordInputKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault()
      addKeyword()
    }
  }

  async function handleRunScan() {
    const payload = {
      linked_post_id: linkedPostId,
      ...(effectiveKeywords.length > 0 ? { keywords: effectiveKeywords } : {}),
    }
    const result = await runScan.mutateAsync(payload)
    setActiveSessionId(result.session_id)
    setHistoryPage(1)
    queryClient.invalidateQueries({ queryKey: engagementKeys.all })
  }

  function handleOpenPostInSession(post: EngagementPost) {
    setActiveSessionId(post.session_id)
    setSelectedPostId(post.id)
  }

  const canGoNextHistoryPage = historySessions.length === HISTORY_PAGE_SIZE

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 dark:bg-indigo-900/20">
            <Search className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-(--text-primary)">Engajamento LinkedIn</h1>
            <p className="text-xs text-(--text-secondary)">
              Garimpagem de posts + sugestões de comentários para decisores do ICP
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          <Button
            type="button"
            className="gap-2 border border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200"
            onClick={() => setPostedCommentsOpen(true)}
          >
            <MessageCircle className="h-4 w-4" />
            Gerenciar postados
            <span className="rounded-full bg-white/70 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
              {postedCommentEntries.length}
            </span>
          </Button>
          <Button type="button" variant="outline" className="gap-2" onClick={() => setConfigOpen(true)}>
            <SlidersHorizontal className="h-4 w-4" />
            Configurar scan
          </Button>
          <Button
            onClick={handleRunScan}
            disabled={isScanPending || isRunning}
            className="shrink-0 gap-2"
          >
            {isScanPending || isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {isRunning ? "Escaneando..." : "Iniciando..."}
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Novo Scan
              </>
            )}
          </Button>
          <Button type="button" variant="outline" className="gap-2" onClick={() => setHistoryOpen(true)}>
            <History className="h-4 w-4" />
            Histórico de buscas
          </Button>
        </div>
      </div>

      <ActiveConfigurationSummary
        linkedPostId={linkedPostId}
        selectedThemesCount={selectedThemeIds.length}
        manualKeywordsCount={manualKeywords.length}
        effectiveKeywords={effectiveKeywords}
      />

      {/* Estado principal */}
      {isRunning && !isTimedOut ? (
        <ScanningState currentStep={displaySession?.current_step} />
      ) : isTimedOut ? (
        <div className="flex items-start gap-3 rounded-xl border border-red-300/50 bg-red-50 dark:bg-red-900/10 px-5 py-4">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-medium text-red-700 dark:text-red-300">Scan expirou</p>
            <p className="text-xs text-red-600/80 dark:text-red-400/80 mt-0.5">
              O scan demorou demais. Verifique se o worker Celery está rodando e tente novamente.
            </p>
          </div>
        </div>
      ) : isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-40 w-full rounded-xl bg-(--bg-overlay) animate-pulse" />
          ))}
        </div>
      ) : displaySession ? (
        <SessionResults session={displaySession} onOpenPost={setSelectedPostId} />
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-(--border-default) py-20 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-(--bg-overlay)">
            <Search className="h-6 w-6 text-(--text-tertiary)" />
          </div>
          <p className="text-base font-medium text-(--text-primary)">Nenhum scan realizado</p>
          <p className="mt-1 text-sm text-(--text-secondary) max-w-sm">
            Clique em &quot;Novo Scan&quot; para garimpar posts relevantes e gerar sugestões de comentários.
          </p>
        </div>
      )}

      {/* Erro de scan */}
      {runScan.isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-300/50 bg-red-50 dark:bg-red-900/10 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
          <p className="text-sm text-red-700 dark:text-red-300">
            {runScan.error?.message ?? "Erro ao iniciar o scan."}
          </p>
        </div>
      )}

      <PostDetailDrawer post={selectedPost} onClose={() => setSelectedPostId(null)} />
      <PostedCommentsModal
        open={postedCommentsOpen}
        onOpenChange={setPostedCommentsOpen}
        entries={postedCommentEntries}
        onOpenPost={handleOpenPostInSession}
      />

      <Dialog open={configOpen} onOpenChange={setConfigOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Configurar scan</DialogTitle>
            <DialogDescription>
              Ajuste post vinculado, temas e palavras-chave sem ocupar espaço da página principal.
            </DialogDescription>
          </DialogHeader>

          <ScanConfigurationPanel
            linkedPostId={linkedPostId}
            onLinkedPostChange={setLinkedPostId}
            themes={themes ?? []}
            selectedThemeIds={selectedThemeIds}
            onToggleTheme={toggleTheme}
            keywordInput={keywordInput}
            onKeywordInputChange={setKeywordInput}
            onKeywordInputKeyDown={handleKeywordInputKeyDown}
            onAddKeyword={addKeyword}
            manualKeywords={manualKeywords}
            onRemoveKeyword={removeKeyword}
            effectiveKeywords={effectiveKeywords}
            disabled={isScanPending || isRunning}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Histórico de buscas</DialogTitle>
            <DialogDescription>
              Consulte sessões anteriores e troque rapidamente o resultado exibido na tela.
            </DialogDescription>
          </DialogHeader>

          <SessionHistoryTable
            sessions={historySessions}
            activeSessionId={effectiveSessionId}
            onSelectSession={(sessionId) => {
              setActiveSessionId(sessionId)
              setHistoryOpen(false)
            }}
            statusFilter={historyStatusFilter}
            onStatusFilterChange={(status) => {
              setHistoryStatusFilter(status)
              setHistoryPage(1)
            }}
            page={historyPage}
            onPrevPage={() => setHistoryPage((current) => Math.max(1, current - 1))}
            onNextPage={() => setHistoryPage((current) => current + 1)}
            canGoNext={canGoNextHistoryPage}
            isLoading={isHistoryLoading}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
