export type TaskSlaFilter = "all" | "fresh" | "attention" | "urgent"
export type TaskSlaState = Exclude<TaskSlaFilter, "all">

const ATTENTION_HOURS = 24
const URGENT_HOURS = 72

export const TASK_SLA_CONFIG: Record<
  TaskSlaState,
  { label: string; badgeClassName: string; rowClassName: string }
> = {
  fresh: {
    label: "No prazo",
    badgeClassName: "bg-(--info-subtle) text-(--info-subtle-fg)",
    rowClassName: "",
  },
  attention: {
    label: "Atenção",
    badgeClassName: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
    rowClassName: "bg-(--warning-subtle)/35",
  },
  urgent: {
    label: "Urgente",
    badgeClassName: "bg-(--danger-subtle) text-(--danger-subtle-fg)",
    rowClassName: "bg-(--danger-subtle)/35",
  },
}

export function getTaskAgeHours(createdAt: string, now = Date.now()): number {
  const created = new Date(createdAt).getTime()
  return Math.max(0, Math.floor((now - created) / (1000 * 60 * 60)))
}

export function formatTaskAge(createdAt: string, now = Date.now()): string {
  const diffHours = getTaskAgeHours(createdAt, now)
  if (diffHours < 24) {
    return `${diffHours}h`
  }

  return `${Math.floor(diffHours / 24)}d`
}

export function formatTaskDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—"
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

export function getTaskSlaState(createdAt: string, now = Date.now()): TaskSlaState {
  const diffHours = getTaskAgeHours(createdAt, now)
  if (diffHours >= URGENT_HOURS) {
    return "urgent"
  }
  if (diffHours >= ATTENTION_HOURS) {
    return "attention"
  }
  return "fresh"
}

export function getNextTaskId(taskIdsInOrder: string[], currentTaskId: string): string | null {
  const currentIndex = taskIdsInOrder.indexOf(currentTaskId)
  if (currentIndex < 0) {
    return null
  }

  return taskIdsInOrder[currentIndex + 1] ?? null
}

export function getPreviousTaskId(taskIdsInOrder: string[], currentTaskId: string): string | null {
  const currentIndex = taskIdsInOrder.indexOf(currentTaskId)
  if (currentIndex < 0) {
    return null
  }

  return taskIdsInOrder[currentIndex - 1] ?? null
}

export function getTaskSelectionAfterAdvance(
  taskIdsInOrder: string[],
  currentTaskId: string,
): string | null {
  const currentIndex = taskIdsInOrder.indexOf(currentTaskId)
  if (currentIndex < 0) {
    return null
  }

  return taskIdsInOrder[currentIndex + 1] ?? taskIdsInOrder[currentIndex - 1] ?? currentTaskId
}
