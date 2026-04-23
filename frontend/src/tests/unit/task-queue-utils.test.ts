import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  formatTaskAge,
  formatTaskDateTime,
  getNextTaskId,
  getPreviousTaskId,
  getTaskSelectionAfterAdvance,
  getTaskSlaState,
} from "@/components/tarefas/task-queue-utils"

describe("task queue utils", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date("2026-04-23T12:00:00Z"))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("classifica SLA fresh, attention e urgent", () => {
    expect(getTaskSlaState("2026-04-23T08:00:00Z")).toBe("fresh")
    expect(getTaskSlaState("2026-04-22T00:00:00Z")).toBe("attention")
    expect(getTaskSlaState("2026-04-19T00:00:00Z")).toBe("urgent")
  })

  it("formata idade em horas ou dias", () => {
    expect(formatTaskAge("2026-04-23T09:00:00Z")).toBe("3h")
    expect(formatTaskAge("2026-04-20T12:00:00Z")).toBe("3d")
  })

  it("formata datas operacionais e trata ausente", () => {
    expect(formatTaskDateTime(null)).toBe("—")
    expect(formatTaskDateTime("2026-04-23T09:15:00Z")).toMatch(/23\/04\/2026/)
  })

  it("retorna a próxima tarefa da fila", () => {
    expect(getNextTaskId(["a", "b", "c"], "b")).toBe("c")
    expect(getNextTaskId(["a", "b", "c"], "c")).toBeNull()
  })

  it("retorna a tarefa anterior da fila", () => {
    expect(getPreviousTaskId(["a", "b", "c"], "b")).toBe("a")
    expect(getPreviousTaskId(["a", "b", "c"], "a")).toBeNull()
  })

  it("avança a seleção para próxima, anterior ou mantém atual", () => {
    expect(getTaskSelectionAfterAdvance(["a", "b", "c"], "b")).toBe("c")
    expect(getTaskSelectionAfterAdvance(["a", "b", "c"], "c")).toBe("b")
    expect(getTaskSelectionAfterAdvance(["a"], "a")).toBe("a")
  })
})
