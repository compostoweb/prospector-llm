"use client"

import React, { useState, useRef } from "react"
import { localDateToUTC } from "@/lib/date"
import {
  addMonths,
  startOfMonth,
  startOfDay,
  endOfMonth,
  eachWeekOfInterval,
  endOfWeek,
  addDays,
  setHours,
  setMinutes,
  isBefore,
  isAfter,
  format,
  isSameMonth,
} from "date-fns"
import { ptBR } from "date-fns/locale"
import {
  Sparkles,
  ArrowLeft,
  ArrowRight,
  Check,
  RefreshCw,
  AlertTriangle,
  Calendar,
  ChevronDown,
  ChevronRight,
  Loader2,
  CheckCircle2,
  XCircle,
  Shuffle,
  ArrowLeftRight,
} from "lucide-react"
import {
  useGeneratePost,
  useImprovePost,
  useCreateContentPost,
  useContentThemes,
  useMarkThemeUsed,
  useThemeSuggestions,
  useVaryTheme,
  useApprovePost,
  useSchedulePost,
  type PostPillar,
  type HookType,
  type ContentTheme,
} from "@/lib/api/hooks/use-content"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { PillarBadge } from "@/components/content/post-badges"
import { cn } from "@/lib/utils"

// ── Constants ─────────────────────────────────────────────────────────

const HOOK_OPTIONS: { value: HookType; label: string }[] = [
  { value: "loop_open", label: "Loop aberto" },
  { value: "contrarian", label: "Contrário" },
  { value: "identification", label: "Identificação" },
  { value: "shortcut", label: "Atalho" },
  { value: "benefit", label: "Benefício" },
  { value: "data", label: "Dado" },
]

const STEP_LABELS = ["Planejar", "Temas", "Configurar", "Gerar", "Revisar", "Agendar"]

const PILLAR_CYCLE: PostPillar[] = ["authority", "case", "vision"]

// Day-of-week offsets from Monday (weekStartsOn: 1) by posts/week
const DAY_PREFS: Record<number, number[]> = {
  1: [1], // Tue
  2: [1, 3], // Tue, Thu
  3: [0, 1, 3], // Mon, Tue, Thu
  4: [0, 1, 2, 3], // Mon–Thu
  5: [0, 1, 2, 3, 4], // Mon–Fri
}

// ── Types ─────────────────────────────────────────────────────────────

interface AiContentWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface PlanSlot {
  weekNum: number
  pillar: PostPillar
  themeSource: "bank" | "free"
  themeId: string | null
  freeTheme: string
  generatedText: string | null
  hookUsed: string | null
  charCount: number
  violations: string[]
  editedBody: string | null
  title: string
  publishDate: string
  genStatus: "pending" | "done" | "error"
  genError: string | null
}

interface WizardState {
  targetMonth: string
  postsPerWeek: number
  planSlots: PlanSlot[]
  hookType: HookType | "auto"
  temperature: number
  useReferences: boolean
  generating: boolean
  genProgress: number
  expandedSlot: number | null
}

const INITIAL_STATE: WizardState = {
  targetMonth: "",
  postsPerWeek: 2,
  planSlots: [],
  hookType: "auto",
  temperature: 0.8,
  useReferences: false,
  generating: false,
  genProgress: 0,
  expandedSlot: null,
}

function parseMonthString(monthStr: string): { year: number; monthIndex: number } | null {
  const [yearPart, monthPart] = monthStr.split("-")
  const year = Number(yearPart)
  const month = Number(monthPart)

  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) {
    return null
  }

  return {
    year,
    monthIndex: month - 1,
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

function getMonthOptions(): { value: string; label: string }[] {
  const now = new Date()
  return [0, 1, 2, 3].map((offset) => {
    const date = addMonths(now, offset)
    return {
      value: format(date, "yyyy-MM"),
      label: format(date, "MMMM yyyy", { locale: ptBR }),
    }
  })
}

function getWeeksOfMonth(monthStr: string): { weekNum: number; start: Date; end: Date }[] {
  const parsedMonth = parseMonthString(monthStr)
  if (!parsedMonth) return []

  const ms = startOfMonth(new Date(parsedMonth.year, parsedMonth.monthIndex, 1))
  const me = endOfMonth(ms)
  const weeks = eachWeekOfInterval({ start: ms, end: me }, { weekStartsOn: 1 })
  return weeks.map((ws, i) => ({
    weekNum: i + 1,
    start: isBefore(ws, ms) ? ms : ws,
    end: isAfter(endOfWeek(ws, { weekStartsOn: 1 }), me) ? me : endOfWeek(ws, { weekStartsOn: 1 }),
  }))
}

function buildPlanSlots(monthStr: string, postsPerWeek: number): PlanSlot[] {
  const weeks = getWeeksOfMonth(monthStr)
  const now = new Date()
  const parsedMonth = parseMonthString(monthStr)
  if (!parsedMonth) return []

  const monthDate = new Date(parsedMonth.year, parsedMonth.monthIndex, 1)
  const isCurrentMonth = isSameMonth(now, monthDate)

  const slots: PlanSlot[] = []
  let pi = 0
  for (const week of weeks) {
    // Skip weeks with no plannable future days (end is today or earlier)
    const tomorrow = addDays(startOfDay(now), 1)
    if (isCurrentMonth && isBefore(week.end, tomorrow)) continue
    for (let p = 0; p < postsPerWeek; p++) {
      const pillar = PILLAR_CYCLE[pi % PILLAR_CYCLE.length] ?? "authority"
      slots.push({
        weekNum: week.weekNum,
        pillar,
        themeSource: "free",
        themeId: null,
        freeTheme: "",
        generatedText: null,
        hookUsed: null,
        charCount: 0,
        violations: [],
        editedBody: null,
        title: "",
        publishDate: "",
        genStatus: "pending",
        genError: null,
      })
      pi++
    }
  }
  return slots
}

function buildSuggestedDates(
  slots: PlanSlot[],
  monthStr: string,
  postsPerWeek: number,
): PlanSlot[] {
  const now = new Date()
  const parsedMonth = parseMonthString(monthStr)
  if (!parsedMonth) return slots

  const ms = startOfMonth(new Date(parsedMonth.year, parsedMonth.monthIndex, 1))
  const me = endOfMonth(ms)
  const weeks = eachWeekOfInterval({ start: ms, end: me }, { weekStartsOn: 1 })
  const prefs = DAY_PREFS[postsPerWeek] ?? [1]
  const updated = slots.map((s) => ({ ...s }))
  let si = 0
  for (const ws of weeks) {
    for (const dayOff of prefs) {
      if (si >= updated.length) break
      const date = addDays(ws, dayOff)
      if (isBefore(date, ms) || isAfter(date, me)) continue
      const dateAt9 = setHours(setMinutes(date, 0), 9)
      // Skip dates already in the past
      if (isBefore(dateAt9, now)) continue
      const currentSlot = updated[si]
      if (!currentSlot) continue
      updated[si] = {
        ...currentSlot,
        publishDate: format(dateAt9, "yyyy-MM-dd'T'HH:mm"),
      }
      si++
    }
  }
  return updated
}

// ── Main Component ────────────────────────────────────────────────────

export function AiContentWizard({ open, onOpenChange }: AiContentWizardProps) {
  const [step, setStep] = useState(1)
  const [state, setState] = useState<WizardState>(INITIAL_STATE)
  const [improveInstruction, setImproveInstruction] = useState("")
  const [creatingProgress, setCreatingProgress] = useState(0)
  const [isCreating, setIsCreating] = useState(false)

  const generate = useGeneratePost()
  const improve = useImprovePost()
  const createPost = useCreateContentPost()
  const markThemeUsed = useMarkThemeUsed()
  const approvePost = useApprovePost()
  const schedulePost = useSchedulePost()
  const { data: themes } = useContentThemes({ used: false })
  const { data: allThemes } = useContentThemes()

  const abortRef = useRef(false)

  function update(partial: Partial<WizardState>) {
    setState((prev) => ({ ...prev, ...partial }))
  }

  function updateSlot(index: number, partial: Partial<PlanSlot>) {
    setState((prev) => {
      const slots = prev.planSlots.map((s, i) => (i === index ? { ...s, ...partial } : s))
      return { ...prev, planSlots: slots }
    })
  }

  function handleClose() {
    abortRef.current = true
    onOpenChange(false)
    setTimeout(() => {
      setStep(1)
      setState(INITIAL_STATE)
      setImproveInstruction("")
      setCreatingProgress(0)
      setIsCreating(false)
      abortRef.current = false
    }, 200)
  }

  function canAdvance(): boolean {
    switch (step) {
      case 1:
        return state.targetMonth !== "" && state.planSlots.length > 0
      case 2:
        return state.planSlots.every(
          (s) =>
            (s.themeSource === "bank" && s.themeId) ||
            (s.themeSource === "free" && s.freeTheme.trim().length >= 3),
        )
      case 3:
        return true
      case 4:
        return !state.generating && state.planSlots.some((s) => s.genStatus === "done")
      case 5:
        return state.planSlots.some((s) => s.genStatus === "done")
      case 6:
        return true
      default:
        return false
    }
  }

  // ── Batch generation ──────────────────────────────────

  async function startGeneration() {
    const CONCURRENCY = 3
    const slotsSnapshot = state.planSlots
    setState((prev) => ({ ...prev, generating: true, genProgress: 0 }))
    abortRef.current = false

    const pending = slotsSnapshot
      .map((s, i) => ({ slot: s, index: i }))
      .filter(({ slot }) => slot.genStatus !== "done")

    let done = 0
    for (let i = 0; i < pending.length; i += CONCURRENCY) {
      if (abortRef.current) break
      const chunk = pending.slice(i, i + CONCURRENCY)
      const results = await Promise.allSettled(
        chunk.map(async ({ slot, index }) => {
          const themeText =
            slot.themeSource === "bank"
              ? (themes?.find((t) => t.id === slot.themeId)?.title ?? slot.freeTheme)
              : slot.freeTheme
          const res = await generate.mutateAsync({
            theme: themeText,
            pillar: slot.pillar,
            hook_type: state.hookType === "auto" ? null : state.hookType,
            variations: 1,
            use_references: state.useReferences,
            temperature: state.temperature,
          })
          const v = res.variations[0]
          if (!v) throw new Error("Nenhuma variação retornada")
          return { index, variation: v }
        }),
      )

      results.forEach((r, j) => {
        done++
        if (r.status === "fulfilled") {
          const { index, variation } = r.value
          const slot = slotsSnapshot[index]
          if (!slot) {
            setState((prev) => ({ ...prev, genProgress: done }))
            return
          }
          updateSlot(index, {
            generatedText: variation.text,
            hookUsed: variation.hook_type_used,
            charCount: variation.character_count,
            violations: variation.violations,
            genStatus: "done",
            genError: null,
            title: slot.freeTheme,
          })
        } else {
          const failedItem = chunk[j]
          if (failedItem) {
            updateSlot(failedItem.index, {
              genStatus: "error",
              genError: r.reason instanceof Error ? r.reason.message : "Erro desconhecido",
            })
          }
        }
        setState((prev) => ({ ...prev, genProgress: done }))
      })
    }

    setState((prev) => ({ ...prev, generating: false }))
  }

  // ── Retry single ──

  async function handleRetrySlot(index: number) {
    const slot = state.planSlots[index]
    if (!slot) return
    updateSlot(index, { genStatus: "pending", genError: null })

    const themeText =
      slot.themeSource === "bank"
        ? (themes?.find((t) => t.id === slot.themeId)?.title ?? slot.freeTheme)
        : slot.freeTheme

    try {
      const res = await generate.mutateAsync({
        theme: themeText,
        pillar: slot.pillar,
        hook_type: state.hookType === "auto" ? null : state.hookType,
        variations: 1,
        use_references: state.useReferences,
        temperature: state.temperature,
      })
      const v = res.variations[0]
      if (!v) throw new Error("Nenhuma variação retornada")
      updateSlot(index, {
        generatedText: v.text,
        hookUsed: v.hook_type_used,
        charCount: v.character_count,
        violations: v.violations,
        genStatus: "done",
        genError: null,
        title: slot.freeTheme,
      })
    } catch (err) {
      updateSlot(index, {
        genStatus: "error",
        genError: err instanceof Error ? err.message : "Erro desconhecido",
      })
    }
  }

  // ── Improve slot ──

  async function handleImproveSlot(index: number) {
    if (!improveInstruction.trim()) return
    const slot = state.planSlots[index]
    if (!slot) return
    const body = slot.editedBody ?? slot.generatedText ?? ""
    const res = await improve.mutateAsync({ body, instruction: improveInstruction })
    updateSlot(index, { editedBody: res.text, charCount: res.character_count })
    setImproveInstruction("")
  }

  // ── Re-generate single ──

  async function handleRegenSlot(index: number) {
    updateSlot(index, { genStatus: "pending", genError: null, editedBody: null })
    await handleRetrySlot(index)
  }

  // ── Create all ──

  async function handleCreateAll(withDates: boolean) {
    setIsCreating(true)
    setCreatingProgress(0)

    const doneSlots = state.planSlots.filter((s) => s.genStatus === "done")
    let done = 0

    for (const slot of doneSlots) {
      try {
        const body = slot.editedBody ?? slot.generatedText ?? ""
        const createdPost = await createPost.mutateAsync({
          title: slot.title,
          body,
          pillar: slot.pillar,
          hook_type: (slot.hookUsed as HookType) || null,
          character_count: body.length,
          publish_date: withDates && slot.publishDate ? localDateToUTC(slot.publishDate) : null,
        })
        if (withDates && slot.publishDate) {
          try {
            await approvePost.mutateAsync(createdPost.id)
            await schedulePost.mutateAsync(createdPost.id)
          } catch {
            // Created as draft if scheduling fails
          }
        }
        if (slot.themeId) {
          try {
            await markThemeUsed.mutateAsync({ themeId: slot.themeId, postId: createdPost.id })
          } catch {
            // Non-blocking
          }
        }
      } catch {
        // Skip failed slot
      }
      done++
      setCreatingProgress(done)
    }

    handleClose()
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="max-w-5xl max-h-[95vh] overflow-y-auto min-h-[50vh]">
        <DialogHeader className="pb-4">
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-(--accent)" />
            Planejar e gerar com IA
          </DialogTitle>
        </DialogHeader>

        {/* Stepper */}
        <div className="flex items-center gap-1 mb-2">
          {STEP_LABELS.map((label, i) => {
            const stepNum = i + 1
            const isActive = step === stepNum
            const isDone = step > stepNum
            return (
              <div key={label} className="flex items-center gap-1 flex-1">
                <div
                  className={cn(
                    "flex items-center justify-center h-6 w-6 rounded-full text-xs font-medium shrink-0 transition-colors",
                    isActive
                      ? "bg-(--accent) text-white"
                      : isDone
                        ? "bg-(--success) text-white"
                        : "bg-(--bg-overlay) text-(--text-tertiary)",
                  )}
                >
                  {isDone ? <Check className="h-3 w-3" /> : stepNum}
                </div>
                <span
                  className={cn(
                    "text-xs truncate hidden sm:inline",
                    isActive ? "text-(--text-primary) font-medium" : "text-(--text-tertiary)",
                  )}
                >
                  {label}
                </span>
                {i < STEP_LABELS.length - 1 && (
                  <div
                    className={cn(
                      "h-px flex-1 mx-1",
                      isDone ? "bg-(--success)" : "bg-(--border-subtle)",
                    )}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* Step Content */}
        <div className="min-h-75">
          {step === 1 && <PlanStep state={state} update={update} />}
          {step === 2 && (
            <ThemePlanStep
              state={state}
              updateSlot={updateSlot}
              themes={themes ?? []}
              allThemes={allThemes ?? []}
            />
          )}
          {step === 3 && <BatchConfigStep state={state} update={update} />}
          {step === 4 && <BatchGenerateStep state={state} onRetry={handleRetrySlot} />}
          {step === 5 && (
            <BatchReviewStep
              state={state}
              updateSlot={updateSlot}
              expandedSlot={state.expandedSlot}
              setExpandedSlot={(idx) => update({ expandedSlot: idx })}
              improveInstruction={improveInstruction}
              setImproveInstruction={setImproveInstruction}
              onImprove={handleImproveSlot}
              onRegen={handleRegenSlot}
              isImproving={improve.isPending}
            />
          )}
          {step === 6 && (
            <BatchScheduleStep
              state={state}
              updateSlot={updateSlot}
              onSuggestDates={() => {
                const updated = buildSuggestedDates(
                  state.planSlots,
                  state.targetMonth,
                  state.postsPerWeek,
                )
                update({ planSlots: updated })
              }}
              isCreating={isCreating}
              creatingProgress={creatingProgress}
              onCreate={handleCreateAll}
            />
          )}
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between pt-3 border-t border-(--border-subtle)">
          <div>
            {step > 1 && !state.generating && !isCreating && (
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => setStep(step - 1)}
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Voltar
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={handleClose}
              disabled={state.generating || isCreating}
            >
              Cancelar
            </Button>
            {step >= 4 && step < 6 && !state.generating && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => {
                  abortRef.current = true
                  setState((prev) => ({
                    ...prev,
                    planSlots: prev.planSlots.map((s) => ({
                      ...s,
                      genStatus: "pending" as const,
                      genError: null,
                      generatedText: null,
                      editedBody: null,
                    })),
                    generating: false,
                    genProgress: 0,
                  }))
                  setStep(1)
                }}
              >
                Recomeçar
              </Button>
            )}
            {step <= 2 && (
              <Button
                size="sm"
                className="gap-1 text-xs"
                onClick={() => setStep(step + 1)}
                disabled={!canAdvance()}
              >
                Próximo
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            )}
            {step === 3 && (
              <Button
                size="sm"
                className="gap-1 text-xs"
                onClick={() => {
                  setStep(4)
                  startGeneration()
                }}
                disabled={!canAdvance()}
              >
                <Sparkles className="h-3.5 w-3.5" />
                Gerar posts
              </Button>
            )}
            {step === 4 && !state.generating && canAdvance() && (
              <Button size="sm" className="gap-1 text-xs" onClick={() => setStep(5)}>
                Próximo
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            )}
            {step === 5 && (
              <Button
                size="sm"
                className="gap-1 text-xs"
                onClick={() => setStep(6)}
                disabled={!canAdvance()}
              >
                Próximo
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── Step 1: Plan ──────────────────────────────────────────────────────

interface PlanStepProps {
  state: WizardState
  update: (p: Partial<WizardState>) => void
}

function PlanStep({ state, update }: PlanStepProps) {
  const monthOptions = getMonthOptions()

  function handleMonthChange(month: string) {
    const slots = month ? buildPlanSlots(month, state.postsPerWeek) : []
    update({ targetMonth: month, planSlots: slots })
  }

  function handlePostsPerWeekChange(n: number) {
    const slots = state.targetMonth ? buildPlanSlots(state.targetMonth, n) : []
    update({ postsPerWeek: n, planSlots: slots })
  }

  // Check if current month is selected
  const isCurrentMonth = state.targetMonth === format(new Date(), "yyyy-MM")

  // Total weeks in month vs slots generated (to show skipped weeks info)
  const totalWeeks = state.targetMonth ? getWeeksOfMonth(state.targetMonth).length : 0

  // Group by week for preview
  const weekGroups = new Map<number, PlanSlot[]>()
  for (const s of state.planSlots) {
    const arr = weekGroups.get(s.weekNum) ?? []
    arr.push(s)
    weekGroups.set(s.weekNum, arr)
  }

  const skippedWeeks = totalWeeks - weekGroups.size

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-(--text-secondary)">
        Selecione o mês e quantos posts por semana deseja gerar.
      </p>

      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-1.5">
          <Label>Mês alvo</Label>
          <Select value={state.targetMonth} onValueChange={handleMonthChange}>
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Selecione o mês" />
            </SelectTrigger>
            <SelectContent>
              {monthOptions.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  <span className="capitalize">{o.label}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label>Posts por semana</Label>
          <Select
            value={String(state.postsPerWeek)}
            onValueChange={(v) => handlePostsPerWeekChange(parseInt(v, 10))}
          >
            <SelectTrigger className="text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[1, 2, 3, 4, 5].map((n) => (
                <SelectItem key={n} value={String(n)}>
                  {n} post{n > 1 ? "s" : ""} / semana
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {state.planSlots.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium text-(--text-secondary) uppercase tracking-wide">
            Preview — {state.planSlots.length} posts em {weekGroups.size} semanas
          </p>
          {isCurrentMonth && skippedWeeks > 0 && (
            <p className="text-[11px] text-(--text-tertiary)">
              {skippedWeeks} semana{skippedWeeks > 1 ? "s" : ""} já passou
              {skippedWeeks > 1 ? "ram" : ""} — somente semanas restantes serão planejadas.
            </p>
          )}
          <div className="grid grid-cols-2 gap-2 max-h-52 overflow-y-auto">
            {Array.from(weekGroups.entries()).map(([weekNum, slots]) => (
              <div
                key={weekNum}
                className="rounded-md border border-(--border-subtle) bg-(--bg-overlay) p-2.5"
              >
                <p className="text-xs font-medium text-(--text-primary) mb-1.5">Semana {weekNum}</p>
                <div className="flex flex-wrap gap-1">
                  {slots.map((s, i) => (
                    <PillarBadge key={i} pillar={s.pillar} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Step 2: Theme Plan ────────────────────────────────────────────────

interface ThemePlanStepProps {
  state: WizardState
  updateSlot: (index: number, partial: Partial<PlanSlot>) => void
  themes: ContentTheme[]
  allThemes: ContentTheme[]
}

function ThemePlanStep({ state, updateSlot, themes, allThemes }: ThemePlanStepProps) {
  const { isFetching: isSuggesting, refetch: fetchSuggestions } = useThemeSuggestions()
  const { mutateAsync: varyTheme } = useVaryTheme()
  const [loadingVariations, setLoadingVariations] = React.useState<Set<number>>(new Set())

  const weekGroups = new Map<number, { slot: PlanSlot; index: number }[]>()
  state.planSlots.forEach((s, i) => {
    const arr = weekGroups.get(s.weekNum) ?? []
    arr.push({ slot: s, index: i })
    weekGroups.set(s.weekNum, arr)
  })

  // Build lookup for bank theme status
  const themeMap = new Map(allThemes.map((t) => [t.id, t]))

  // Count available unused themes
  const usedIdsInSlots = new Set(state.planSlots.filter((s) => s.themeId).map((s) => s.themeId))
  const availableCount = themes.filter((t) => !usedIdsInSlots.has(t.id)).length
  const emptySlots = state.planSlots.filter(
    (s) => !s.themeId && s.freeTheme.trim().length < 3,
  ).length

  function cyclePillar(index: number) {
    const slot = state.planSlots[index]
    if (!slot) return
    const ci = PILLAR_CYCLE.indexOf(slot.pillar)
    const next = PILLAR_CYCLE[(ci + 1) % PILLAR_CYCLE.length] ?? PILLAR_CYCLE[0] ?? "authority"
    updateSlot(index, { pillar: next })
  }

  function fillFromBank() {
    const usedIds = new Set(state.planSlots.filter((s) => s.themeId).map((s) => s.themeId))
    const available: Record<PostPillar, ContentTheme[]> = {
      authority: [],
      case: [],
      vision: [],
    }
    for (const t of themes) {
      if (!usedIds.has(t.id)) {
        available[t.pillar].push(t)
      }
    }

    for (let i = 0; i < state.planSlots.length; i++) {
      const slot = state.planSlots[i]
      if (!slot) continue
      if (slot.themeId || slot.freeTheme.trim().length >= 3) continue
      const pool = available[slot.pillar]
      if (pool.length > 0) {
        const theme = pool.shift()
        if (!theme) continue
        updateSlot(i, {
          themeSource: "bank",
          themeId: theme.id,
          freeTheme: theme.title,
        })
      }
    }
  }

  async function handleGenerateAndFill() {
    const result = await fetchSuggestions()
    if (!result.data || result.data.length === 0) return

    // Collect all theme titles and IDs already in slots
    const usedTitles = new Set(
      state.planSlots
        .filter((s) => s.freeTheme.trim().length >= 3)
        .map((s) => s.freeTheme.trim().toLowerCase()),
    )
    const usedIds = new Set(state.planSlots.filter((s) => s.themeId).map((s) => s.themeId))

    // Deduplicate suggestions pool by theme ID
    const pool = result.data.filter((s, i, arr) => {
      if (usedIds.has(s.theme.id)) return false
      if (usedTitles.has(s.theme.title.trim().toLowerCase())) return false
      return arr.findIndex((x) => x.theme.id === s.theme.id) === i
    })

    for (let i = 0; i < state.planSlots.length; i++) {
      const slot = state.planSlots[i]
      if (!slot) continue
      if (slot.themeId || slot.freeTheme.trim().length >= 3) continue
      if (pool.length === 0) break

      // Prefer a suggestion matching the slot's pillar
      const matchIdx = pool.findIndex((s) => s.theme.pillar === slot.pillar)
      const idx = matchIdx >= 0 ? matchIdx : 0
      const suggestion = pool.splice(idx, 1)[0]
      if (!suggestion) continue

      usedTitles.add(suggestion.theme.title.trim().toLowerCase())
      usedIds.add(suggestion.theme.id)
      updateSlot(i, {
        themeSource: "bank",
        themeId: suggestion.theme.id,
        freeTheme: suggestion.theme.title,
        pillar: suggestion.theme.pillar,
      })
    }
  }

  /** AI variation: call LLM to rephrase/re-angle the current slot theme */
  async function handleAIVariation(index: number) {
    const slot = state.planSlots[index]
    if (!slot) return
    const currentTitle = slot.freeTheme.trim()
    if (currentTitle.length < 3) return

    setLoadingVariations((prev) => new Set(prev).add(index))
    try {
      const result = await varyTheme({ theme_title: currentTitle, pillar: slot.pillar })
      if (result.variation) {
        updateSlot(index, {
          themeSource: "free",
          themeId: null,
          freeTheme: result.variation,
        })
      }
    } finally {
      setLoadingVariations((prev) => {
        const next = new Set(prev)
        next.delete(index)
        return next
      })
    }
  }

  /** Rotate this slot to a different unused bank theme for the same pillar */
  function handleVariation(index: number) {
    const slot = state.planSlots[index]
    if (!slot) return

    // Gather all IDs currently assigned (except this slot)
    const otherIds = new Set(
      state.planSlots.filter((s, i) => i !== index && s.themeId).map((s) => s.themeId),
    )

    // Find unused themes for this pillar
    const pool = themes.filter(
      (t) => t.pillar === slot.pillar && !otherIds.has(t.id) && t.id !== slot.themeId,
    )
    // If no same-pillar themes, try any pillar
    const candidate = pool[0] ?? themes.find((t) => !otherIds.has(t.id) && t.id !== slot.themeId)

    if (candidate) {
      updateSlot(index, {
        themeSource: "bank",
        themeId: candidate.id,
        freeTheme: candidate.title,
        pillar: candidate.pillar,
      })
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-(--text-secondary)">
            Defina o tema de cada post. Clique no pilar para alternar.
          </p>
          <p className="text-[11px] text-(--text-tertiary) mt-0.5">
            {availableCount} tema{availableCount !== 1 ? "s" : ""} disponíve
            {availableCount !== 1 ? "is" : "l"} no banco
            {emptySlots > 0 &&
              ` · ${emptySlots} slot${emptySlots !== 1 ? "s" : ""} vazio${emptySlots !== 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {themes.length > 0 && (
            <Button variant="outline" size="sm" className="text-xs gap-1" onClick={fillFromBank}>
              Preencher com banco
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="text-xs gap-1"
            onClick={handleGenerateAndFill}
            disabled={isSuggesting}
          >
            {isSuggesting ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                Gerando…
              </>
            ) : (
              <>
                <Sparkles className="h-3 w-3" />
                Sugerir com IA
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-3 max-h-96 overflow-y-auto pr-1">
        {Array.from(weekGroups.entries()).map(([weekNum, items]) => (
          <div key={weekNum}>
            <p className="text-xs font-medium text-(--text-tertiary) uppercase tracking-wide mb-1.5">
              Semana {weekNum}
            </p>
            <div className="flex flex-col gap-2">
              {items.map(({ slot, index }) => {
                const bankTheme = slot.themeId ? themeMap.get(slot.themeId) : null
                return (
                  <div
                    key={index}
                    className="flex items-center gap-2 rounded-md border border-(--border-subtle) p-2 min-w-0"
                  >
                    {/* Pillar toggle — highlighted as clickable */}
                    <button
                      type="button"
                      onClick={() => cyclePillar(index)}
                      title="Clique para alternar pilar"
                      className="shrink-0 group relative"
                    >
                      <PillarBadge
                        pillar={slot.pillar}
                        className="ring-1 ring-(--border-default) group-hover:ring-2 group-hover:ring-(--accent) cursor-pointer transition-all"
                      />
                      <ArrowLeftRight className="absolute -bottom-1 -right-1 h-2.5 w-2.5 text-(--text-tertiary) group-hover:text-(--accent) bg-(--bg-surface) rounded-full" />
                    </button>

                    <Input
                      value={slot.freeTheme}
                      onChange={(e) =>
                        updateSlot(index, {
                          freeTheme: e.target.value,
                          themeSource: "free",
                          themeId: null,
                        })
                      }
                      placeholder="Tema do post..."
                      className="flex-1 h-8 text-xs"
                    />

                    {/* Bank status badge */}
                    {slot.themeId && bankTheme && (
                      <span
                        className={cn(
                          "text-[10px] px-1.5 py-0.5 rounded-full shrink-0 font-medium",
                          bankTheme.used
                            ? "bg-(--warning-subtle) text-(--warning-subtle-fg)"
                            : "bg-(--success-subtle) text-(--success-subtle-fg)",
                        )}
                      >
                        {bankTheme.used ? "já utilizado" : "disponível"}
                      </span>
                    )}

                    {/* Variation button */}
                    <button
                      type="button"
                      onClick={() => handleVariation(index)}
                      title="Trocar por tema do banco"
                      className="shrink-0 p-1 rounded-md text-(--text-tertiary) hover:text-(--accent) hover:bg-(--bg-overlay) transition-colors"
                    >
                      <Shuffle className="h-3.5 w-3.5" />
                    </button>

                    {/* AI variation button */}
                    <button
                      type="button"
                      onClick={() => handleAIVariation(index)}
                      disabled={loadingVariations.has(index) || slot.freeTheme.trim().length < 3}
                      title="Gerar variação com IA"
                      className="shrink-0 p-1 rounded-md text-(--text-tertiary) hover:text-(--accent) hover:bg-(--bg-overlay) transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {loadingVariations.has(index) ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Step 3: Config ────────────────────────────────────────────────────

interface BatchConfigStepProps {
  state: WizardState
  update: (p: Partial<WizardState>) => void
}

function BatchConfigStep({ state, update }: BatchConfigStepProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-md border border-(--accent)/20 bg-(--accent-subtle) px-3 py-2.5">
        <p className="text-xs text-(--accent-subtle-fg)">
          Configurações aplicadas a <strong>{state.planSlots.length} posts</strong>
        </p>
      </div>

      {/* Hook type */}
      <div className="grid gap-1.5">
        <Label>Tipo de gancho</Label>
        <Select
          value={state.hookType}
          onValueChange={(v) => update({ hookType: v as HookType | "auto" })}
        >
          <SelectTrigger className="text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">Automático (IA escolhe)</SelectItem>
            {HOOK_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Temperature */}
      <div className="grid gap-1.5">
        <Label>Criatividade: {state.temperature.toFixed(1)}</Label>
        <input
          aria-label="Nível de criatividade"
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={state.temperature}
          onChange={(e) => update({ temperature: parseFloat(e.target.value) })}
          className="mt-2 w-full accent-(--accent)"
        />
      </div>

      {/* References */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-(--text-primary)">Usar posts de referência</p>
          <p className="text-xs text-(--text-tertiary)">Few-shot com posts de alto engajamento</p>
        </div>
        <Switch
          checked={state.useReferences}
          onCheckedChange={(v) => update({ useReferences: v })}
        />
      </div>
    </div>
  )
}

// ── Step 4: Batch Generate ────────────────────────────────────────────

interface BatchGenerateStepProps {
  state: WizardState
  onRetry: (index: number) => void
}

function BatchGenerateStep({ state, onRetry }: BatchGenerateStepProps) {
  const total = state.planSlots.length
  const done = state.planSlots.filter((s) => s.genStatus === "done").length
  const errors = state.planSlots.filter((s) => s.genStatus === "error").length
  const pct = total > 0 ? Math.round(((done + errors) / total) * 100) : 0

  return (
    <div className="flex flex-col gap-4">
      {state.generating ? (
        <div className="flex items-center gap-2 text-sm text-(--text-primary)">
          <Loader2 className="h-4 w-4 animate-spin text-(--accent)" />
          Gerando: {state.genProgress} de {total}…
        </div>
      ) : (
        <p className="text-sm text-(--text-secondary)">
          {done} de {total} gerados com sucesso
          {errors > 0 && <span className="text-(--danger)"> · {errors} com erro</span>}
        </p>
      )}

      {/* Progress bar */}
      <div className="h-2 rounded-full bg-(--bg-overlay) overflow-hidden">
        <div
          className="h-full rounded-full bg-(--accent) transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Slot list */}
      <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto">
        {state.planSlots.map((slot, i) => (
          <div
            key={i}
            className="flex items-center gap-2 rounded-md border border-(--border-subtle) px-3 py-2 text-xs"
          >
            {slot.genStatus === "done" && (
              <CheckCircle2 className="h-3.5 w-3.5 text-(--success) shrink-0" />
            )}
            {slot.genStatus === "error" && (
              <XCircle className="h-3.5 w-3.5 text-(--danger) shrink-0" />
            )}
            {slot.genStatus === "pending" && (
              <Loader2 className="h-3.5 w-3.5 text-(--text-tertiary) animate-spin shrink-0" />
            )}
            <PillarBadge pillar={slot.pillar} className="shrink-0" />
            <span className="text-(--text-primary) line-clamp-2 flex-1 min-w-0">
              {slot.freeTheme || "(sem tema)"}
            </span>
            {slot.genStatus === "done" && (
              <span className="text-(--text-tertiary) shrink-0">{slot.charCount} chars</span>
            )}
            {slot.genStatus === "error" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-[11px] gap-1 shrink-0"
                onClick={() => onRetry(i)}
              >
                <RefreshCw className="h-3 w-3" />
                Tentar
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Step 5: Batch Review ──────────────────────────────────────────────

interface BatchReviewStepProps {
  state: WizardState
  updateSlot: (index: number, partial: Partial<PlanSlot>) => void
  expandedSlot: number | null
  setExpandedSlot: (idx: number | null) => void
  improveInstruction: string
  setImproveInstruction: (v: string) => void
  onImprove: (index: number) => void
  onRegen: (index: number) => void
  isImproving: boolean
}

function BatchReviewStep({
  state,
  updateSlot,
  expandedSlot,
  setExpandedSlot,
  improveInstruction,
  setImproveInstruction,
  onImprove,
  onRegen,
  isImproving,
}: BatchReviewStepProps) {
  const doneSlots = state.planSlots
    .map((s, i) => ({ slot: s, index: i }))
    .filter(({ slot }) => slot.genStatus === "done")

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-(--text-secondary)">
        Revise e edite os {doneSlots.length} posts gerados.
      </p>

      <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1">
        {doneSlots.map(({ slot, index }) => {
          const isExpanded = expandedSlot === index
          const body = slot.editedBody ?? slot.generatedText ?? ""
          const isOverLimit = body.length > 3000

          return (
            <div
              key={index}
              className="rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)"
            >
              {/* Header */}
              <button
                type="button"
                onClick={() => setExpandedSlot(isExpanded ? null : index)}
                className="flex items-center gap-2 w-full p-3 text-left"
              >
                {isExpanded ? (
                  <ChevronDown className="h-3.5 w-3.5 text-(--text-tertiary) shrink-0" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 text-(--text-tertiary) shrink-0" />
                )}
                <PillarBadge pillar={slot.pillar} className="shrink-0" />
                <span className="text-xs font-medium text-(--text-primary) line-clamp-2 flex-1 min-w-0">
                  <span className="text-(--text-tertiary) mr-1">Sem {slot.weekNum} ·</span>
                  {slot.freeTheme || slot.title || `Post ${slot.weekNum}`}
                </span>
                <span
                  className={cn(
                    "text-[11px] shrink-0",
                    isOverLimit ? "text-(--danger)" : "text-(--text-tertiary)",
                  )}
                >
                  {body.length} chars
                </span>
              </button>

              {/* Expanded body */}
              {isExpanded && (
                <div className="px-3 pb-3 flex flex-col gap-2 border-t border-(--border-subtle) pt-2">
                  {/* Title */}
                  <Input
                    value={slot.title}
                    onChange={(e) => updateSlot(index, { title: e.target.value })}
                    placeholder="Título interno"
                    className="h-8 text-xs"
                  />

                  {/* Body */}
                  <Textarea
                    value={body}
                    onChange={(e) =>
                      updateSlot(index, {
                        editedBody: e.target.value,
                        charCount: e.target.value.length,
                      })
                    }
                    rows={8}
                    className="resize-none font-mono text-xs"
                  />

                  {/* Actions */}
                  <div className="flex items-center justify-between">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-[11px] gap-1"
                      onClick={() => onRegen(index)}
                    >
                      <RefreshCw className="h-3 w-3" />
                      Re-gerar
                    </Button>
                    <span
                      className={cn(
                        "text-[11px]",
                        isOverLimit ? "text-(--danger) font-medium" : "text-(--text-tertiary)",
                      )}
                    >
                      {body.length} / 3.000
                    </span>
                  </div>

                  {/* Improve */}
                  <div className="flex flex-col gap-2 rounded-md border border-(--accent)/30 bg-(--accent)/5 p-2.5">
                    <div className="flex items-center gap-1 text-xs text-(--accent)">
                      <Sparkles className="h-3 w-3" />
                      Melhorar com IA
                    </div>
                    <div className="flex gap-2">
                      <Input
                        value={improveInstruction}
                        onChange={(e) => setImproveInstruction(e.target.value)}
                        placeholder="Ex: Reduza para 1000 chars mantendo o gancho"
                        className="flex-1 h-7 text-xs"
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                            onImprove(index)
                          }
                        }}
                      />
                      <Button
                        size="sm"
                        className="h-7 text-[11px] gap-1"
                        onClick={() => onImprove(index)}
                        disabled={!improveInstruction.trim() || isImproving}
                      >
                        {isImproving ? (
                          <RefreshCw className="h-3 w-3 animate-spin" />
                        ) : (
                          <Check className="h-3 w-3" />
                        )}
                        Aplicar
                      </Button>
                    </div>
                  </div>

                  {/* Violations */}
                  {slot.violations.length > 0 && (
                    <div className="flex flex-col gap-1">
                      {slot.violations.map((v, vi) => (
                        <div
                          key={vi}
                          className="flex items-start gap-1.5 rounded-md bg-(--warning-subtle) px-2 py-1 text-xs text-(--warning-subtle-fg)"
                        >
                          <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
                          {v}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Step 6: Batch Schedule ────────────────────────────────────────────

interface BatchScheduleStepProps {
  state: WizardState
  updateSlot: (index: number, partial: Partial<PlanSlot>) => void
  onSuggestDates: () => void
  isCreating: boolean
  creatingProgress: number
  onCreate: (withDates: boolean) => void
}

function BatchScheduleStep({
  state,
  updateSlot,
  onSuggestDates,
  isCreating,
  creatingProgress,
  onCreate,
}: BatchScheduleStepProps) {
  const doneSlots = state.planSlots
    .map((s, i) => ({ slot: s, index: i }))
    .filter(({ slot }) => slot.genStatus === "done")
  const allHaveDates = doneSlots.every(({ slot }) => slot.publishDate)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-(--text-secondary)">Agende os {doneSlots.length} posts.</p>
        <Button variant="outline" size="sm" className="text-xs gap-1" onClick={onSuggestDates}>
          <Calendar className="h-3 w-3" />
          Sugerir datas
        </Button>
      </div>

      {/* Slot dates */}
      <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
        {doneSlots.map(({ slot, index }) => (
          <div
            key={index}
            className="flex items-center gap-2 rounded-md border border-(--border-subtle) px-3 py-2"
          >
            <PillarBadge pillar={slot.pillar} className="shrink-0" />
            <span className="text-xs text-(--text-primary) line-clamp-2 flex-1 min-w-0">
              <span className="text-(--text-tertiary) mr-1">Sem {slot.weekNum} ·</span>
              {slot.freeTheme || slot.title || `Post ${index + 1}`}
            </span>
            <Input
              type="datetime-local"
              value={slot.publishDate}
              onChange={(e) => updateSlot(index, { publishDate: e.target.value })}
              className="w-48 h-7 text-xs shrink-0"
            />
          </div>
        ))}
      </div>

      {isCreating && (
        <div className="flex items-center gap-2 text-sm text-(--text-primary)">
          <Loader2 className="h-4 w-4 animate-spin text-(--accent)" />
          Criando: {creatingProgress} de {doneSlots.length}…
        </div>
      )}

      <p className="text-xs text-(--text-tertiary)">
        Posts agendados são automaticamente aprovados. Sem data, serão criados como rascunho.
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2 justify-end">
        <Button
          variant="outline"
          size="sm"
          className="text-xs gap-1"
          onClick={() => onCreate(false)}
          disabled={isCreating}
        >
          {isCreating ? "Criando…" : "Criar rascunhos"}
        </Button>
        {allHaveDates && (
          <Button
            size="sm"
            className="text-xs gap-1"
            onClick={() => onCreate(true)}
            disabled={isCreating}
          >
            <Calendar className="h-3.5 w-3.5" />
            {isCreating ? "Agendando…" : "Criar e agendar todos"}
          </Button>
        )}
      </div>
    </div>
  )
}
