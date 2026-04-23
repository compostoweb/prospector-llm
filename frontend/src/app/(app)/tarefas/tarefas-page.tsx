"use client"

import { useDeferredValue, useEffect, useState } from "react"
import { AnalyticsPeriodFilter } from "@/components/shared/analytics-period-filter"
import { type TaskSlaFilter } from "@/components/tarefas/task-queue-utils"
import {
  useManualTasks,
  useManualTaskStats,
  type ManualTaskStatus,
  type TaskChannel,
} from "@/lib/api/hooks/use-manual-tasks"
import { buildDateFilterValue, getRangeQueryFromFilter } from "@/lib/analytics-period"
import { EmptyState } from "@/components/shared/empty-state"
import { TaskCard } from "@/components/tarefas/task-card"
import { TaskDetailDialog } from "@/components/tarefas/task-detail-dialog"
import { TasksTable } from "@/components/tarefas/tasks-table"
import { Input } from "@/components/ui/input"
import { ClipboardList, LayoutGrid, List, Search } from "lucide-react"
import { cn } from "@/lib/utils"

type TaskScope = "actionable" | "history" | ManualTaskStatus | "all"
type TaskViewMode = "table" | "grid"

const TASK_VIEW_MODE_KEY = "prospector:tasks:view-mode"

const STATUS_TABS: { label: string; value: TaskScope }[] = [
  { label: "Na fila agora", value: "actionable" },
  { label: "Histórico", value: "history" },
  { label: "Todas", value: "all" },
  { label: "Pendentes", value: "pending" },
  { label: "Prontas para envio", value: "content_generated" },
  { label: "Enviadas", value: "sent" },
  { label: "Feitas externamente", value: "done_external" },
  { label: "Puladas", value: "skipped" },
]

const CHANNEL_OPTIONS: { label: string; value: TaskChannel | "all" }[] = [
  { label: "Todos canais", value: "all" },
  { label: "LinkedIn DM", value: "linkedin_dm" },
  { label: "Email", value: "email" },
  { label: "LinkedIn Connect", value: "linkedin_connect" },
  { label: "Tarefa manual", value: "manual_task" },
]

function getTaskScopeDescription(scope: TaskScope, total: number): string {
  const taskWord = total === 1 ? "tarefa" : "tarefas"

  switch (scope) {
    case "actionable":
      return `${total} ${taskWord} podem ser executadas agora. Priorize esta fila para manter o ritmo operacional.`
    case "history":
      return `${total} ${taskWord} já foram concluídas, enviadas ou puladas. Esta aba consolida o histórico recente da operação.`
    case "all":
      return `${total} ${taskWord} estão visíveis nesta visão completa, combinando fila ativa e histórico.`
    case "pending":
      return `${total} ${taskWord} ainda aguardam geração de conteúdo antes da execução.`
    case "content_generated":
      return `${total} ${taskWord} já estão prontas para revisão final e envio.`
    case "sent":
      return `${total} ${taskWord} já foram enviadas pelo sistema e ficam disponíveis para consulta.`
    case "done_external":
      return `${total} ${taskWord} foram concluídas fora do sistema e registradas para auditoria.`
    case "skipped":
      return `${total} ${taskWord} foram puladas e permanecem no histórico para acompanhamento.`
    default:
      return `${total} ${taskWord} nesta visão.`
  }
}

export default function TarefasPage() {
  const [statusFilter, setStatusFilter] = useState<TaskScope>("actionable")
  const [channelFilter, setChannelFilter] = useState<TaskChannel | "all">("all")
  const [slaFilter, setSlaFilter] = useState<TaskSlaFilter>("all")
  const [searchText, setSearchText] = useState("")
  const [viewMode, setViewMode] = useState<TaskViewMode>("table")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [dateFilter, setDateFilter] = useState(() =>
    buildDateFilterValue({ id: "last_30_days", label: "30 dias", days: 30 }),
  )
  const [page, setPage] = useState(1)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [openTaskId, setOpenTaskId] = useState<string | null>(null)

  const deferredSearchText = useDeferredValue(searchText)

  useEffect(() => {
    if (typeof window === "undefined") {
      return
    }
    const storedMode = window.localStorage.getItem(TASK_VIEW_MODE_KEY)
    if (storedMode === "table" || storedMode === "grid") {
      setViewMode(storedMode)
    }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined") {
      return
    }
    window.localStorage.setItem(TASK_VIEW_MODE_KEY, viewMode)
  }, [viewMode])

  const statusParams =
    statusFilter === "actionable"
      ? (["pending", "content_generated"] as ManualTaskStatus[])
      : statusFilter === "history"
        ? (["sent", "done_external", "skipped"] as ManualTaskStatus[])
        : undefined
  const dateRangeQuery = getRangeQueryFromFilter(dateFilter)
  const dateQueryParams = {
    start_date: dateRangeQuery.startDate,
    end_date: dateRangeQuery.endDate,
  }

  const { data: stats } = useManualTaskStats(dateQueryParams)
  const { data, isLoading } = useManualTasks({
    status:
      statusFilter === "all" || statusFilter === "actionable" || statusFilter === "history"
        ? undefined
        : statusFilter,
    statuses: statusParams,
    channel: channelFilter === "all" ? undefined : channelFilter,
    sla: slaFilter === "all" ? undefined : slaFilter,
    search: deferredSearchText.trim() || undefined,
    start_date: dateQueryParams.start_date,
    end_date: dateQueryParams.end_date,
    sort_by: "created_at",
    sort_dir: sortDir,
    page,
    page_size: 20,
  })

  const tasks = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / 20)
  const taskIdsInOrder = tasks.map((task) => task.id)
  const activeScopeDescription = getTaskScopeDescription(statusFilter, total)

  useEffect(() => {
    if (tasks.length === 0) {
      if (selectedTaskId !== null) {
        setSelectedTaskId(null)
      }
      if (openTaskId !== null) {
        setOpenTaskId(null)
      }
      return
    }

    if (selectedTaskId && !taskIdsInOrder.includes(selectedTaskId)) {
      setSelectedTaskId(taskIdsInOrder[0] ?? null)
    }

    if (openTaskId && !taskIdsInOrder.includes(openTaskId)) {
      setOpenTaskId(null)
    }
  }, [openTaskId, selectedTaskId, taskIdsInOrder, tasks.length])

  return (
    <div className="space-y-5">
      {/* Cabeçalho */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Tarefas manuais</h1>
          <p className="text-xs text-(--text-secondary)">
            Fila operacional para executar, revisar e avançar tarefa por tarefa.
          </p>
        </div>
        <AnalyticsPeriodFilter
          value={dateFilter}
          onChange={(next) => {
            setDateFilter(next)
            setPage(1)
          }}
          className="w-full sm:ml-4 sm:w-auto sm:min-w-80"
        />
      </div>

      {/* Stats resumidas */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          <StatCard label="Pendentes" value={stats.pending} tone="warning" />
          <StatCard label="Prontas para envio" value={stats.content_generated} tone="accent" />
          <StatCard label="Enviadas" value={stats.sent} tone="success" />
          <StatCard label="Feitas externamente" value={stats.done_external} tone="info" />
          <StatCard label="Puladas" value={stats.skipped} tone="neutral" />
        </div>
      )}

      {/* Filtros */}
      <div className="flex flex-col gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-3 shadow-(--shadow-sm)">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-64 flex-1">
            <Search
              size={14}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            />
            <Input
              value={searchText}
              onChange={(event) => {
                setSearchText(event.target.value)
                setPage(1)
              }}
              placeholder="Buscar por lead, empresa ou cadência"
              className="pl-9"
            />
          </div>

          <select
            value={channelFilter}
            onChange={(e) => {
              setChannelFilter(e.target.value as TaskChannel | "all")
              setPage(1)
            }}
            aria-label="Filtrar por canal"
            className="h-9 rounded-md border border-(--border-default) bg-transparent px-3 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--ring)"
          >
            {CHANNEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <select
            value={sortDir}
            onChange={(e) => {
              setSortDir(e.target.value as "asc" | "desc")
              setPage(1)
            }}
            aria-label="Ordenar tarefas"
            className="h-9 rounded-md border border-(--border-default) bg-transparent px-3 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--ring)"
          >
            <option value="asc">Mais antigas primeiro</option>
            <option value="desc">Mais recentes primeiro</option>
          </select>

          <select
            value={slaFilter}
            onChange={(e) => {
              setSlaFilter(e.target.value as TaskSlaFilter)
              setPage(1)
            }}
            aria-label="Filtrar por SLA"
            className="h-9 rounded-md border border-(--border-default) bg-transparent px-3 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--ring)"
          >
            <option value="all">Todo SLA</option>
            <option value="fresh">No prazo</option>
            <option value="attention">Atenção 24h+</option>
            <option value="urgent">Urgente 72h+</option>
          </select>

          <div className="flex items-center gap-1 rounded-md border border-(--border-default) p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={cn(
                "rounded p-1.5 transition-colors",
                viewMode === "table"
                  ? "bg-(--accent) text-white"
                  : "text-(--text-tertiary) hover:text-(--text-secondary)",
              )}
              title="Visualização em tabela"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={cn(
                "rounded p-1.5 transition-colors",
                viewMode === "grid"
                  ? "bg-(--accent) text-white"
                  : "text-(--text-tertiary) hover:text-(--text-secondary)",
              )}
              title="Visualização em cards"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>

          <span className="ml-auto text-xs text-(--text-tertiary)">
            {total} tarefa{total !== 1 && "s"}
          </span>
        </div>

        {/* Status tabs */}
        <div className="flex gap-1 rounded-md border border-(--border-default) bg-(--bg-surface) p-0.5">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => {
                setStatusFilter(tab.value)
                setPage(1)
              }}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                statusFilter === tab.value
                  ? "bg-(--accent) text-white"
                  : "text-(--text-secondary) hover:text-(--text-primary)",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <p className="text-sm text-(--text-secondary) pl-2">{activeScopeDescription}</p>
      </div>

      {/* Lista */}
      {isLoading ? (
        <div
          className={cn(
            viewMode === "table"
              ? "space-y-2"
              : "grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3",
          )}
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "animate-pulse rounded-lg bg-(--bg-overlay)",
                viewMode === "table" ? "h-14" : "h-36",
              )}
            />
          ))}
        </div>
      ) : tasks.length > 0 ? (
        viewMode === "table" ? (
          <TasksTable
            tasks={tasks}
            selectedTaskId={selectedTaskId}
            statusFilter={statusFilter}
            channelFilter={channelFilter}
            slaFilter={slaFilter}
            onSelectTask={setSelectedTaskId}
            onOpenTask={setOpenTaskId}
            onStatusFilterChange={(value) => {
              setStatusFilter(value)
              setPage(1)
            }}
            onChannelFilterChange={(value) => {
              setChannelFilter(value)
              setPage(1)
            }}
            onSlaFilterChange={(value) => {
              setSlaFilter(value)
              setPage(1)
            }}
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                isSelected={selectedTaskId === task.id}
                onClick={() => {
                  setSelectedTaskId(task.id)
                  setOpenTaskId(task.id)
                }}
              />
            ))}
          </div>
        )
      ) : (
        <EmptyState
          icon={ClipboardList}
          title="Nenhuma tarefa encontrada"
          description="As tarefas aparecem quando as conexões LinkedIn são aceitas em cadências semi-automáticas."
        />
      )}

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-md border border-(--border-default) px-3 py-1.5 text-xs text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="text-xs text-(--text-tertiary)">
            {page} de {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-md border border-(--border-default) px-3 py-1.5 text-xs text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) disabled:opacity-40"
          >
            Próxima
          </button>
        </div>
      )}

      {/* Dialog de detalhe */}
      {openTaskId && (
        <TaskDetailDialog
          taskId={openTaskId}
          open={!!openTaskId}
          taskIdsInOrder={taskIdsInOrder}
          onAdvanceSelection={setSelectedTaskId}
          onClose={() => setOpenTaskId(null)}
          onOpenTask={setOpenTaskId}
        />
      )}
    </div>
  )
}

// ── Stat card inline ──────────────────────────────────────────────────

type StatCardTone = "warning" | "accent" | "success" | "info" | "neutral"

function StatCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string
  value: number
  tone?: StatCardTone
}) {
  const toneStyles: Record<
    StatCardTone,
    {
      card: string
      badge: string
      dot: string
      value: string
    }
  > = {
    warning: {
      card: "border-(--warning)/15 bg-(--bg-surface)",
      badge: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
      dot: "bg-(--warning)",
      value: "text-(--warning)",
    },
    accent: {
      card: "border-(--accent-subtle-fg)/15 bg-(--bg-surface)",
      badge: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
      dot: "bg-(--accent)",
      value: "text-(--accent)",
    },
    success: {
      card: "border-(--success)/15 bg-(--bg-surface)",
      badge: "bg-(--success-subtle) text-(--success-subtle-fg)",
      dot: "bg-(--success)",
      value: "text-(--success)",
    },
    info: {
      card: "border-(--info)/15 bg-(--bg-surface)",
      badge: "bg-(--info-subtle) text-(--info-subtle-fg)",
      dot: "bg-(--info)",
      value: "text-(--info)",
    },
    neutral: {
      card: "border-(--border-default) bg-(--bg-surface)",
      badge: "bg-(--bg-overlay) text-(--text-secondary)",
      dot: "bg-(--text-tertiary)",
      value: "text-(--text-primary)",
    },
  }

  const styles = toneStyles[tone]

  return (
    <div className={cn("rounded-lg border px-4 py-3 shadow-(--shadow-sm)", styles.card)}>
      <div className="flex items-start justify-between gap-3">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-semibold",
            styles.badge,
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", styles.dot)} />
          {label}
        </span>
      </div>
      <p className={cn("mt-3 text-2xl font-semibold tracking-tight", styles.value)}>{value}</p>
    </div>
  )
}
