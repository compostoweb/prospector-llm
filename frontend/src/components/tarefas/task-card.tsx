"use client"

import { BadgeChannel } from "@/components/shared/badge-channel"
import {
  TASK_SLA_CONFIG,
  formatTaskAge,
  getTaskSlaState,
} from "@/components/tarefas/task-queue-utils"
import { cn } from "@/lib/utils"
import type { ManualTask, ManualTaskStatus } from "@/lib/api/hooks/use-manual-tasks"
import { Clock, Sparkles, Send, CheckCircle, SkipForward } from "lucide-react"

interface TaskCardProps {
  task: ManualTask
  onClick: () => void
  isSelected?: boolean
}

const STATUS_CONFIG: Record<
  ManualTaskStatus,
  { label: string; icon: React.ElementType; className: string }
> = {
  pending: {
    label: "Pendente",
    icon: Clock,
    className: "text-(--warning) bg-(--warning)/10",
  },
  content_generated: {
    label: "Conteúdo gerado",
    icon: Sparkles,
    className: "text-(--accent) bg-(--accent)/10",
  },
  sent: {
    label: "Enviada",
    icon: Send,
    className: "text-(--success) bg-(--success)/10",
  },
  done_external: {
    label: "Feita externamente",
    icon: CheckCircle,
    className: "text-(--success) bg-(--success)/10",
  },
  skipped: {
    label: "Pulada",
    icon: SkipForward,
    className: "text-(--text-tertiary) bg-(--bg-overlay)",
  },
}

export function TaskCard({ task, onClick, isSelected = false }: TaskCardProps) {
  const config = STATUS_CONFIG[task.status]
  const StatusIcon = config.icon
  const slaState = getTaskSlaState(task.created_at)
  const slaConfig = TASK_SLA_CONFIG[slaState]

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 text-left shadow-(--shadow-sm) transition-colors hover:border-(--border-hover)",
        isSelected && "border-(--accent) ring-1 ring-(--accent-subtle)",
      )}
    >
      {/* Header: lead + status */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-(--text-primary)">
            {task.lead?.name ?? "Lead desconhecido"}
          </p>
          {task.lead?.company && (
            <p className="truncate text-xs text-(--text-secondary)">{task.lead.company}</p>
          )}
        </div>
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
            config.className,
          )}
        >
          <StatusIcon size={10} aria-hidden="true" />
          {config.label}
        </span>
      </div>

      {/* Channel + step */}
      <div className="mt-3 flex items-center gap-2">
        <BadgeChannel channel={task.channel} />
        <span className="text-xs text-(--text-tertiary)">Passo {task.step_number}</span>
        <span
          className={cn(
            "inline-flex rounded-(--radius-full) px-2 py-0.5 text-[10px] font-medium",
            slaConfig.badgeClassName,
          )}
        >
          {slaConfig.label}
        </span>
      </div>

      {/* Preview do conteúdo */}
      {(task.edited_text ?? task.generated_text) && (
        <p className="mt-2 line-clamp-2 text-xs text-(--text-secondary)">
          {task.edited_text ?? task.generated_text}
        </p>
      )}

      <p className="mt-3 text-[11px] text-(--text-tertiary)">
        Na fila há {formatTaskAge(task.created_at)}
      </p>
    </button>
  )
}
