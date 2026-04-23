"use client"

import { BadgeChannel } from "@/components/shared/badge-channel"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  TASK_SLA_CONFIG,
  formatTaskAge,
  formatTaskDateTime,
  getTaskSlaState,
  type TaskSlaFilter,
} from "@/components/tarefas/task-queue-utils"
import type { ManualTask, ManualTaskStatus } from "@/lib/api/hooks/use-manual-tasks"
import { cn } from "@/lib/utils"
import {
  CheckCircle,
  ChevronRight,
  Clock3,
  Filter,
  Send,
  SkipForward,
  Sparkles,
} from "lucide-react"

type TaskScope = "actionable" | "history" | "all" | ManualTaskStatus

interface TasksTableProps {
  tasks: ManualTask[]
  selectedTaskId?: string | null
  statusFilter: TaskScope
  channelFilter: ManualTask["channel"] | "all"
  slaFilter: TaskSlaFilter
  onSelectTask: (taskId: string) => void
  onOpenTask: (taskId: string) => void
  onStatusFilterChange: (value: TaskScope) => void
  onChannelFilterChange: (value: ManualTask["channel"] | "all") => void
  onSlaFilterChange: (value: TaskSlaFilter) => void
}

const STATUS_CONFIG: Record<
  ManualTaskStatus,
  { label: string; icon: React.ElementType; className: string }
> = {
  pending: {
    label: "Pendente",
    icon: Clock3,
    className: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
  },
  content_generated: {
    label: "Pronta para envio",
    icon: Sparkles,
    className: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
  },
  sent: {
    label: "Enviada",
    icon: Send,
    className: "bg-(--success-subtle) text-(--success-subtle-fg)",
  },
  done_external: {
    label: "Feita externamente",
    icon: CheckCircle,
    className: "bg-(--success-subtle) text-(--success-subtle-fg)",
  },
  skipped: {
    label: "Pulada",
    icon: SkipForward,
    className: "bg-(--bg-overlay) text-(--text-secondary)",
  },
}

const STATUS_FILTER_OPTIONS: Array<{ value: TaskScope; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "actionable", label: "Na fila agora" },
  { value: "history", label: "Histórico" },
  { value: "pending", label: "Pendentes" },
  { value: "content_generated", label: "Prontas para envio" },
  { value: "sent", label: "Enviadas" },
  { value: "done_external", label: "Feitas externamente" },
  { value: "skipped", label: "Puladas" },
]

const CHANNEL_FILTER_OPTIONS: Array<{ value: ManualTask["channel"] | "all"; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "linkedin_dm", label: "LinkedIn DM" },
  { value: "email", label: "Email" },
  { value: "linkedin_connect", label: "LinkedIn Connect" },
  { value: "manual_task", label: "Tarefa manual" },
]

const SLA_FILTER_OPTIONS: Array<{ value: TaskSlaFilter; label: string }> = [
  { value: "all", label: "Todos" },
  { value: "fresh", label: "No prazo" },
  { value: "attention", label: "Atenção" },
  { value: "urgent", label: "Urgente" },
]

export function TasksTable({
  tasks,
  selectedTaskId,
  statusFilter,
  channelFilter,
  slaFilter,
  onSelectTask,
  onOpenTask,
  onStatusFilterChange,
  onChannelFilterChange,
  onSlaFilterChange,
}: TasksTableProps) {
  const currentStatusLabel =
    STATUS_FILTER_OPTIONS.find((option) => option.value === statusFilter)?.label ?? "Status"
  const currentChannelLabel =
    CHANNEL_FILTER_OPTIONS.find((option) => option.value === channelFilter)?.label ?? "Canal"
  const currentSlaLabel =
    SLA_FILTER_OPTIONS.find((option) => option.value === slaFilter)?.label ?? "SLA"

  return (
    <div className="overflow-x-auto rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
      <table className="min-w-7xl w-full text-sm">
        <thead>
          <tr className="border-b border-(--border-default) bg-(--accent)">
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Lead
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Empresa
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              <TableHeaderFilter
                label="Canal"
                activeLabel={currentChannelLabel}
                isActive={channelFilter !== "all"}
              >
                {CHANNEL_FILTER_OPTIONS.map((option) => (
                  <DropdownMenuItem
                    key={option.value}
                    onSelect={() => onChannelFilterChange(option.value)}
                    className={channelFilter === option.value ? "font-medium text-(--accent)" : ""}
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </TableHeaderFilter>
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              <TableHeaderFilter
                label="Status"
                activeLabel={currentStatusLabel}
                isActive={statusFilter !== "all"}
              >
                {STATUS_FILTER_OPTIONS.map((option) => (
                  <DropdownMenuItem
                    key={option.value}
                    onSelect={() => onStatusFilterChange(option.value)}
                    className={statusFilter === option.value ? "font-medium text-(--accent)" : ""}
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </TableHeaderFilter>
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Cadência
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Passo
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Idade
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              <TableHeaderFilter
                label="SLA"
                activeLabel={currentSlaLabel}
                isActive={slaFilter !== "all"}
              >
                {SLA_FILTER_OPTIONS.map((option) => (
                  <DropdownMenuItem
                    key={option.value}
                    onSelect={() => onSlaFilterChange(option.value)}
                    className={slaFilter === option.value ? "font-medium text-(--accent)" : ""}
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </TableHeaderFilter>
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Datas
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Conteúdo
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
              Ação
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-(--border-subtle)">
          {tasks.map((task) => {
            const statusConfig = STATUS_CONFIG[task.status]
            const StatusIcon = statusConfig.icon
            const slaState = getTaskSlaState(task.created_at)
            const slaConfig = TASK_SLA_CONFIG[slaState]
            const isSelected = selectedTaskId === task.id
            const executionAt =
              task.sent_at ??
              (task.status === "skipped" || task.status === "done_external"
                ? task.updated_at
                : null)

            return (
              <tr
                key={task.id}
                className={cn(
                  "cursor-pointer transition-colors hover:bg-(--bg-overlay)",
                  slaConfig.rowClassName,
                  isSelected && "bg-(--accent-subtle)/50",
                )}
                onClick={() => {
                  onSelectTask(task.id)
                  onOpenTask(task.id)
                }}
              >
                <td className="px-4 py-3 align-top">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-(--text-primary)">
                      {task.lead?.name ?? "Lead desconhecido"}
                    </p>
                    <p className="mt-1 text-xs text-(--text-tertiary)">
                      {task.lead?.job_title ?? "Sem cargo informado"}
                    </p>
                  </div>
                </td>
                <td className="px-4 py-3 align-top text-(--text-secondary)">
                  {task.lead?.company ?? "—"}
                </td>
                <td className="px-4 py-3 align-top">
                  <BadgeChannel channel={task.channel} manualTaskType={task.manual_task_type} />
                </td>
                <td className="px-4 py-3 align-top">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-(--radius-full) px-2 py-1 text-xs font-medium",
                      statusConfig.className,
                    )}
                  >
                    <StatusIcon size={12} aria-hidden="true" />
                    {statusConfig.label}
                  </span>
                </td>
                <td className="px-4 py-3 align-top">
                  <div className="max-w-52">
                    <p className="truncate text-(--text-primary)">{task.cadence_name ?? "—"}</p>
                  </div>
                </td>
                <td className="px-4 py-3 align-top text-(--text-secondary)">
                  Passo {task.step_number}
                </td>
                <td className="px-4 py-3 align-top text-(--text-secondary)">
                  {formatTaskAge(task.created_at)}
                </td>
                <td className="px-4 py-3 align-top">
                  <span
                    className={cn(
                      "inline-flex rounded-(--radius-full) px-2 py-1 text-xs font-medium",
                      slaConfig.badgeClassName,
                    )}
                  >
                    {slaConfig.label}
                  </span>
                </td>
                <td className="px-4 py-3 align-top">
                  <div className="space-y-2 text-xs">
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-(--text-tertiary)">
                        Prevista
                      </p>
                      <p className="text-(--text-secondary)">
                        {formatTaskDateTime(task.created_at)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-(--text-tertiary)">
                        Execução
                      </p>
                      <p className="text-(--text-secondary)">{formatTaskDateTime(executionAt)}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 align-top">
                  <p className="line-clamp-2 max-w-md text-xs text-(--text-secondary)">
                    {task.edited_text ??
                      task.generated_text ??
                      task.manual_task_detail ??
                      "Sem conteúdo gerado ainda."}
                  </p>
                </td>
                <td className="px-4 py-3 align-top text-right">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-xs font-medium text-(--accent) hover:underline"
                    onClick={(event) => {
                      event.stopPropagation()
                      onSelectTask(task.id)
                      onOpenTask(task.id)
                    }}
                  >
                    Abrir
                    <ChevronRight size={12} aria-hidden="true" />
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function TableHeaderFilter({
  label,
  activeLabel,
  isActive,
  children,
}: {
  label: string
  activeLabel: string
  isActive: boolean
  children: React.ReactNode
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium uppercase tracking-wide transition-colors",
            isActive
              ? "bg-white/14 text-(--text-invert) ring-1 ring-white/20 hover:bg-white/18"
              : "text-(--text-invert) hover:text-amber-300",
          )}
        >
          {isActive ? activeLabel : label}
          <Filter className="h-3 w-3" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-44">
        {children}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
