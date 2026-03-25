"use client"

import { useState } from "react"
import {
  useManualTasks,
  useManualTaskStats,
  type ManualTaskStatus,
  type TaskChannel,
} from "@/lib/api/hooks/use-manual-tasks"
import { EmptyState } from "@/components/shared/empty-state"
import { TaskCard } from "@/components/tarefas/task-card"
import { TaskDetailDialog } from "@/components/tarefas/task-detail-dialog"
import { ClipboardList } from "lucide-react"
import { cn } from "@/lib/utils"

const STATUS_TABS: { label: string; value: ManualTaskStatus | "all" }[] = [
  { label: "Todas", value: "all" },
  { label: "Pendentes", value: "pending" },
  { label: "Com conteúdo", value: "content_generated" },
  { label: "Enviadas", value: "sent" },
  { label: "Feitas externamente", value: "done_external" },
  { label: "Puladas", value: "skipped" },
]

const CHANNEL_OPTIONS: { label: string; value: TaskChannel | "all" }[] = [
  { label: "Todos canais", value: "all" },
  { label: "LinkedIn DM", value: "linkedin_dm" },
  { label: "Email", value: "email" },
  { label: "LinkedIn Connect", value: "linkedin_connect" },
]

export default function TarefasPage() {
  const [statusFilter, setStatusFilter] = useState<ManualTaskStatus | "all">("all")
  const [channelFilter, setChannelFilter] = useState<TaskChannel | "all">("all")
  const [page, setPage] = useState(1)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  const { data: stats } = useManualTaskStats()
  const { data, isLoading } = useManualTasks({
    status: statusFilter === "all" ? undefined : statusFilter,
    channel: channelFilter === "all" ? undefined : channelFilter,
    page,
    page_size: 20,
  })

  const tasks = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / 20)

  return (
    <div className="space-y-5">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-lg font-semibold text-(--text-primary)">Tarefas manuais</h1>
        <p className="text-sm text-(--text-secondary)">
          Fila de mensagens da cadência semi-automática
        </p>
      </div>

      {/* Stats resumidas */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Pendentes" value={stats.pending} color="text-(--warning)" />
          <StatCard label="Com conteúdo" value={stats.content_generated} color="text-(--accent)" />
          <StatCard label="Enviadas" value={stats.sent} color="text-(--success)" />
          <StatCard label="Ext. / Puladas" value={stats.done_external} />
        </div>
      )}

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3">
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

        {/* Channel filter */}
        <select
          value={channelFilter}
          onChange={(e) => {
            setChannelFilter(e.target.value as TaskChannel | "all")
            setPage(1)
          }}
          aria-label="Filtrar por canal"
          className="h-8 rounded-md border border-(--border-default) bg-transparent px-2 text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--ring)"
        >
          {CHANNEL_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Count */}
        <span className="ml-auto text-xs text-(--text-tertiary)">
          {total} tarefa{total !== 1 && "s"}
        </span>
      </div>

      {/* Lista */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-lg bg-(--bg-overlay)" />
          ))}
        </div>
      ) : tasks.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={() => setSelectedTaskId(task.id)}
            />
          ))}
        </div>
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
      {selectedTaskId && (
        <TaskDetailDialog
          taskId={selectedTaskId}
          open={!!selectedTaskId}
          onClose={() => setSelectedTaskId(null)}
        />
      )}
    </div>
  )
}

// ── Stat card inline ──────────────────────────────────────────────────

function StatCard({
  label,
  value,
  color,
}: {
  label: string
  value: number
  color?: string
}) {
  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-3">
      <p className="text-xs text-(--text-secondary)">{label}</p>
      <p className={cn("mt-1 text-xl font-semibold", color ?? "text-(--text-primary)")}>
        {value}
      </p>
    </div>
  )
}
