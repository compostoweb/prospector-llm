"use client"

import { useState } from "react"
import {
  Sparkles,
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  RefreshCw,
  AlertTriangle,
  Calendar,
} from "lucide-react"
import {
  useGeneratePost,
  useImprovePost,
  useCreateContentPost,
  useContentThemes,
  useMarkThemeUsed,
  useThemeSuggestions,
  useApprovePost,
  useSchedulePost,
  type PostPillar,
  type HookType,
  type GeneratePostVariation,
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

const PILLAR_OPTIONS: { value: PostPillar; label: string; desc: string }[] = [
  { value: "authority", label: "Autoridade", desc: "Ponto de vista diferenciado" },
  { value: "case", label: "Caso", desc: "História com resultado concreto" },
  { value: "vision", label: "Visão", desc: "Tendência ou futuro do setor" },
]

const HOOK_OPTIONS: { value: HookType; label: string }[] = [
  { value: "loop_open", label: "Loop aberto" },
  { value: "contrarian", label: "Contrário" },
  { value: "identification", label: "Identificação" },
  { value: "shortcut", label: "Atalho" },
  { value: "benefit", label: "Benefício" },
  { value: "data", label: "Dado" },
]

const STEP_LABELS = ["Tema", "Configurar", "Variações", "Editar", "Agendar"]

// ── Types ─────────────────────────────────────────────────────────────

interface AiContentWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface WizardState {
  // Step 1: Theme
  themeSource: "bank" | "suggestions" | "free"
  selectedThemeId: string | null
  freeTheme: string
  pillar: PostPillar
  // Step 2: Config
  hookType: HookType | "auto"
  variations: number
  temperature: number
  useReferences: boolean
  // Step 3: Variations
  results: GeneratePostVariation[]
  chosenIndex: number | null
  // Step 4: Edit
  body: string
  title: string
  hashtags: string
  // Step 5: Schedule
  publishDate: string
  weekNumber: string
}

const INITIAL_STATE: WizardState = {
  themeSource: "bank",
  selectedThemeId: null,
  freeTheme: "",
  pillar: "authority",
  hookType: "auto",
  variations: 3,
  temperature: 0.8,
  useReferences: false,
  results: [],
  chosenIndex: null,
  body: "",
  title: "",
  hashtags: "",
  publishDate: "",
  weekNumber: "",
}

// ── Main Component ────────────────────────────────────────────────────

export function AiContentWizard({ open, onOpenChange }: AiContentWizardProps) {
  const [step, setStep] = useState(1)
  const [state, setState] = useState<WizardState>(INITIAL_STATE)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const [improveOpen, setImproveOpen] = useState(false)
  const [instruction, setInstruction] = useState("")

  const generate = useGeneratePost()
  const improve = useImprovePost()
  const createPost = useCreateContentPost()
  const markThemeUsed = useMarkThemeUsed()
  const approvePost = useApprovePost()
  const schedulePost = useSchedulePost()
  const { data: themes } = useContentThemes({ used: false })
  const { data: suggestions } = useThemeSuggestions()

  function update(partial: Partial<WizardState>) {
    setState((prev) => ({ ...prev, ...partial }))
  }

  function handleClose() {
    onOpenChange(false)
    setTimeout(() => {
      setStep(1)
      setState(INITIAL_STATE)
      setCopiedIdx(null)
      setImproveOpen(false)
      setInstruction("")
    }, 200)
  }

  function getThemeText(): string {
    if (state.themeSource === "bank" || state.themeSource === "suggestions") {
      const t =
        themes?.find((th) => th.id === state.selectedThemeId) ??
        suggestions?.find((s) => s.theme.id === state.selectedThemeId)?.theme
      return t?.title ?? ""
    }
    return state.freeTheme
  }

  function canAdvance(): boolean {
    switch (step) {
      case 1:
        return state.themeSource === "free"
          ? state.freeTheme.trim().length >= 3
          : !!state.selectedThemeId
      case 2:
        return true
      case 3:
        return state.chosenIndex !== null
      case 4:
        return state.body.trim().length > 0 && state.title.trim().length > 0
      case 5:
        return true
      default:
        return false
    }
  }

  async function handleGenerate() {
    const res = await generate.mutateAsync({
      theme: getThemeText(),
      pillar: state.pillar,
      hook_type: state.hookType === "auto" ? null : state.hookType,
      variations: state.variations,
      use_references: state.useReferences,
      temperature: state.temperature,
    })
    update({ results: res.variations, chosenIndex: null })
    setStep(3)
  }

  function handleChooseVariation(idx: number) {
    const variation = state.results[idx]
    if (!variation) return
    update({
      chosenIndex: idx,
      body: variation.text,
      title: state.title || getThemeText().slice(0, 80),
    })
    setStep(4)
  }

  async function handleCopy(idx: number) {
    const variation = state.results[idx]
    if (!variation) return
    await navigator.clipboard.writeText(variation.text)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  async function handleImprove() {
    if (!instruction.trim()) return
    const res = await improve.mutateAsync({ body: state.body, instruction })
    update({ body: res.text })
    setImproveOpen(false)
    setInstruction("")
  }

  async function handleCreate(withDate: boolean) {
    const hookUsed =
      state.chosenIndex !== null ? state.results[state.chosenIndex]?.hook_type_used : null
    const createdPost = await createPost.mutateAsync({
      title: state.title,
      body: state.body,
      pillar: state.pillar,
      hook_type: (hookUsed as HookType) || null,
      hashtags: state.hashtags || null,
      character_count: state.body.length,
      publish_date: withDate && state.publishDate ? state.publishDate : null,
      week_number: state.weekNumber ? parseInt(state.weekNumber, 10) : null,
    })
    // Auto-approve + schedule when date is provided
    if (withDate && state.publishDate) {
      try {
        await approvePost.mutateAsync(createdPost.id)
        await schedulePost.mutateAsync(createdPost.id)
      } catch {
        // post created as draft, user can schedule manually
      }
    }
    if (state.selectedThemeId) {
      try {
        await markThemeUsed.mutateAsync({ themeId: state.selectedThemeId, postId: createdPost.id })
      } catch {
        // não bloqueia criação
      }
    }
    handleClose()
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
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
          {step === 1 && (
            <ThemeStep
              state={state}
              update={update}
              themes={themes ?? []}
              suggestions={suggestions ?? []}
            />
          )}
          {step === 2 && (
            <ConfigStep
              state={state}
              update={update}
              themeText={getThemeText()}
              isGenerating={generate.isPending}
              onGenerate={handleGenerate}
              generateError={generate.isError}
            />
          )}
          {step === 3 && (
            <VariationsStep
              results={state.results}
              copiedIdx={copiedIdx}
              onChoose={handleChooseVariation}
              onCopy={handleCopy}
              onRegenerate={() => setStep(2)}
            />
          )}
          {step === 4 && (
            <EditStep
              state={state}
              update={update}
              improveOpen={improveOpen}
              setImproveOpen={setImproveOpen}
              instruction={instruction}
              setInstruction={setInstruction}
              onImprove={handleImprove}
              isImproving={improve.isPending}
            />
          )}
          {step === 5 && (
            <ScheduleStep
              state={state}
              update={update}
              isCreating={createPost.isPending}
              onCreate={handleCreate}
            />
          )}
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between pt-3 border-t border-(--border-subtle)">
          <div>
            {step > 1 && step !== 3 && (
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
            {step === 3 && (
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => setStep(1)}
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Recomeçar
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="text-xs" onClick={handleClose}>
              Cancelar
            </Button>
            {(step === 1 || step === 4) && (
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
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── Step 1: Theme ─────────────────────────────────────────────────────

interface ThemeStepProps {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  themes: ContentTheme[]
  suggestions: { theme: ContentTheme; reason: string; lead_count: number; sector: string }[]
}

function ThemeStep({ state, update, themes, suggestions }: ThemeStepProps) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-(--text-secondary)">
        Escolha um tema do banco, use uma sugestão inteligente ou escreva livremente.
      </p>

      {/* Source tabs */}
      <div className="flex items-center gap-1 rounded-md border border-(--border-default) p-0.5 w-fit">
        {(
          [
            { key: "bank", label: "Banco de temas" },
            { key: "suggestions", label: "Sugestões IA" },
            { key: "free", label: "Tema livre" },
          ] as const
        ).map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => update({ themeSource: key, selectedThemeId: null })}
            className={cn(
              "text-xs px-3 py-1.5 rounded transition-colors",
              state.themeSource === key
                ? "bg-(--accent) text-white"
                : "text-(--text-secondary) hover:bg-(--bg-overlay)",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Bank */}
      {state.themeSource === "bank" && (
        <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
          {themes.length === 0 ? (
            <p className="text-xs text-(--text-tertiary) py-4 text-center">
              Nenhum tema disponível. Crie temas na aba Temas ou use tema livre.
            </p>
          ) : (
            themes.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => update({ selectedThemeId: t.id, pillar: t.pillar })}
                className={cn(
                  "flex items-start gap-2 rounded-md border p-2.5 text-left transition-colors",
                  state.selectedThemeId === t.id
                    ? "border-(--accent) bg-(--accent-subtle)"
                    : "border-(--border-subtle) hover:border-(--accent)/50",
                )}
              >
                <PillarBadge pillar={t.pillar} className="mt-0.5 shrink-0" />
                <span className="text-xs text-(--text-primary)">{t.title}</span>
              </button>
            ))
          )}
        </div>
      )}

      {/* Suggestions */}
      {state.themeSource === "suggestions" && (
        <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
          {suggestions.length === 0 ? (
            <p className="text-xs text-(--text-tertiary) py-4 text-center">
              Nenhuma sugestão disponível. Sugestões são baseadas nos seus leads ativos.
            </p>
          ) : (
            suggestions.map((s, i) => (
              <button
                key={i}
                type="button"
                onClick={() => update({ selectedThemeId: s.theme.id, pillar: s.theme.pillar })}
                className={cn(
                  "flex items-start gap-2 rounded-md border p-2.5 text-left transition-colors",
                  state.selectedThemeId === s.theme.id
                    ? "border-(--accent) bg-(--accent-subtle)"
                    : "border-(--border-subtle) hover:border-(--accent)/50",
                )}
              >
                <PillarBadge pillar={s.theme.pillar} className="mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-(--text-primary) truncate">
                    {s.theme.title}
                  </p>
                  <p className="text-[11px] text-(--text-tertiary)">{s.reason}</p>
                </div>
              </button>
            ))
          )}
        </div>
      )}

      {/* Free */}
      {state.themeSource === "free" && (
        <Textarea
          value={state.freeTheme}
          onChange={(e) => update({ freeTheme: e.target.value })}
          placeholder="Ex: Como reduzir o tempo de onboarding de clientes sem contratar mais pessoas"
          rows={3}
          className="resize-none text-sm"
        />
      )}

      {/* Pillar */}
      <div className="grid gap-2">
        <Label>Pilar</Label>
        <div className="grid grid-cols-3 gap-2">
          {PILLAR_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => update({ pillar: o.value })}
              className={cn(
                "flex flex-col gap-1 rounded-md border p-2.5 text-left transition-colors",
                state.pillar === o.value
                  ? "border-(--accent) bg-(--accent-subtle)"
                  : "border-(--border-default) hover:border-(--border-strong)",
              )}
            >
              <span className="text-xs font-medium text-(--text-primary)">{o.label}</span>
              <span className="text-[11px] text-(--text-tertiary) leading-tight">{o.desc}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Step 2: Config ────────────────────────────────────────────────────

interface ConfigStepProps {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  themeText: string
  isGenerating: boolean
  onGenerate: () => void
  generateError: boolean
}

function ConfigStep({
  state,
  update,
  themeText,
  isGenerating,
  onGenerate,
  generateError,
}: ConfigStepProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Theme summary */}
      <div className="rounded-md border border-(--accent)/20 bg-(--accent-subtle) px-3 py-2.5">
        <div className="flex items-center gap-2">
          <PillarBadge pillar={state.pillar} className="shrink-0" />
          <p className="text-xs font-medium text-(--accent-subtle-fg) truncate">{themeText}</p>
        </div>
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

      {/* Variations + temperature */}
      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-1.5">
          <Label>Variações</Label>
          <Select
            value={String(state.variations)}
            onValueChange={(v) => update({ variations: parseInt(v, 10) })}
          >
            <SelectTrigger className="text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[1, 2, 3, 4, 5].map((n) => (
                <SelectItem key={n} value={String(n)}>
                  {n} variação{n > 1 ? "ões" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
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

      {generateError && (
        <div className="flex items-center gap-2 rounded-md bg-(--danger-subtle) p-3 text-xs text-(--danger-subtle-fg)">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          Erro ao gerar. Verifique as configurações LLM.
        </div>
      )}

      {/* Generate button */}
      <Button onClick={onGenerate} disabled={isGenerating} className="gap-2">
        {isGenerating ? (
          <>
            <RefreshCw className="h-4 w-4 animate-spin" />
            Gerando {state.variations} variação{state.variations > 1 ? "ões" : ""}…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Gerar {state.variations} variação{state.variations > 1 ? "ões" : ""}
          </>
        )}
      </Button>
    </div>
  )
}

// ── Step 3: Variations ────────────────────────────────────────────────

interface VariationsStepProps {
  results: GeneratePostVariation[]
  copiedIdx: number | null
  onChoose: (idx: number) => void
  onCopy: (idx: number) => void
  onRegenerate: () => void
}

function VariationsStep({
  results,
  copiedIdx,
  onChoose,
  onCopy,
  onRegenerate,
}: VariationsStepProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-(--text-secondary)">
          {results.length} variação{results.length > 1 ? "ões" : ""} gerada
          {results.length > 1 ? "s" : ""}
        </p>
        <Button variant="outline" size="sm" className="text-xs gap-1" onClick={onRegenerate}>
          <RefreshCw className="h-3 w-3" />
          Re-gerar
        </Button>
      </div>

      <div className="flex flex-col gap-3 max-h-100 overflow-y-auto">
        {results.map((variation, idx) => {
          const charWarning = variation.character_count > 3000
          return (
            <div
              key={idx}
              className="flex flex-col gap-2 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-(--text-secondary)">
                    Variação {idx + 1}
                  </span>
                  <span
                    className={cn(
                      "rounded-md px-1.5 py-0.5 text-xs",
                      charWarning
                        ? "bg-(--danger-subtle) text-(--danger-subtle-fg)"
                        : "bg-(--bg-overlay) text-(--text-tertiary)",
                    )}
                  >
                    {variation.character_count} chars
                  </span>
                  {variation.hook_type_used && (
                    <span className="rounded-md bg-(--accent-subtle) px-1.5 py-0.5 text-xs text-(--accent-subtle-fg)">
                      {variation.hook_type_used}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs gap-1"
                    onClick={() => onCopy(idx)}
                  >
                    {copiedIdx === idx ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-(--success)" />
                        Copiado
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        Copiar
                      </>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    className="h-7 px-2 text-xs gap-1"
                    onClick={() => onChoose(idx)}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Escolher
                  </Button>
                </div>
              </div>
              <pre className="text-xs text-(--text-primary) whitespace-pre-wrap font-sans leading-relaxed max-h-32 overflow-y-auto">
                {variation.text}
              </pre>
              {variation.violations.length > 0 && (
                <div className="flex flex-col gap-1">
                  {variation.violations.map((v, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-1.5 rounded-md bg-(--warning-subtle) px-2 py-1 text-xs text-(--warning-subtle-fg)"
                    >
                      <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
                      {v}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Step 4: Edit ──────────────────────────────────────────────────────

interface EditStepProps {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  improveOpen: boolean
  setImproveOpen: (v: boolean) => void
  instruction: string
  setInstruction: (v: string) => void
  onImprove: () => void
  isImproving: boolean
}

function EditStep({
  state,
  update,
  improveOpen,
  setImproveOpen,
  instruction,
  setInstruction,
  onImprove,
  isImproving,
}: EditStepProps) {
  const charCount = state.body.length
  const isOverLimit = charCount > 3000
  const isTooShort = charCount > 0 && charCount < 900

  return (
    <div className="flex flex-col gap-4">
      {/* Title */}
      <div className="grid gap-1.5">
        <Label htmlFor="wiz-title">Título interno</Label>
        <Input
          id="wiz-title"
          value={state.title}
          onChange={(e) => update({ title: e.target.value })}
          placeholder="Ex: Semana 5 · Tema principal"
          required
        />
      </div>

      {/* Body */}
      <div className="grid gap-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Label htmlFor="wiz-body">Texto do post</Label>
            <button
              type="button"
              onClick={() => setImproveOpen(!improveOpen)}
              className="flex items-center gap-1 text-xs text-(--accent) hover:text-(--accent)/80 transition-colors"
            >
              <Sparkles className="h-3 w-3" />
              Melhorar com IA
            </button>
          </div>
          <span
            className={cn(
              "text-xs",
              isOverLimit
                ? "text-(--danger) font-medium"
                : isTooShort
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-(--text-tertiary)",
            )}
          >
            {charCount} / 3.000
            {isTooShort && " · abaixo do ideal (900–1500)"}
          </span>
        </div>

        {improveOpen && (
          <div className="flex flex-col gap-2 rounded-md border border-(--accent)/30 bg-(--accent)/5 p-3">
            <p className="text-xs text-(--text-secondary)">Instrução para a IA:</p>
            <Textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="Ex: Reduza para 1000 caracteres mantendo o gancho"
              rows={2}
              className="resize-none text-xs"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  onImprove()
                }
              }}
            />
            <div className="flex items-center gap-2 justify-end">
              <button
                type="button"
                onClick={() => {
                  setImproveOpen(false)
                  setInstruction("")
                }}
                className="text-xs text-(--text-tertiary) hover:text-(--text-secondary)"
              >
                Cancelar
              </button>
              <Button
                type="button"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={onImprove}
                disabled={!instruction.trim() || isImproving}
              >
                {isImproving ? (
                  <>
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    Melhorando…
                  </>
                ) : (
                  <>
                    <Check className="h-3 w-3" />
                    Aplicar
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        <Textarea
          id="wiz-body"
          value={state.body}
          onChange={(e) => update({ body: e.target.value })}
          placeholder="Texto do post gerado pela IA..."
          rows={10}
          className="resize-none font-mono text-sm"
        />
      </div>

      {/* Hashtags */}
      <div className="grid gap-1.5">
        <Label htmlFor="wiz-hashtags">Hashtags</Label>
        <Input
          id="wiz-hashtags"
          value={state.hashtags}
          onChange={(e) => update({ hashtags: e.target.value })}
          placeholder="#ia #processos #automacao"
        />
      </div>
    </div>
  )
}

// ── Step 5: Schedule ──────────────────────────────────────────────────

interface ScheduleStepProps {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  isCreating: boolean
  onCreate: (withDate: boolean) => void
}

function ScheduleStep({ state, update, isCreating, onCreate }: ScheduleStepProps) {
  const charCount = state.body.length
  const hookUsed =
    state.chosenIndex !== null ? state.results[state.chosenIndex]?.hook_type_used : null

  return (
    <div className="flex flex-col gap-4">
      {/* Summary */}
      <div className="rounded-md border border-(--border-default) bg-(--bg-overlay) p-3">
        <p className="text-xs font-medium text-(--text-secondary) uppercase tracking-wide mb-2">
          Resumo do post
        </p>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-(--text-tertiary)">Título:</span>{" "}
            <span className="text-(--text-primary) font-medium">{state.title}</span>
          </div>
          <div>
            <span className="text-(--text-tertiary)">Pilar:</span>{" "}
            <PillarBadge pillar={state.pillar} />
          </div>
          <div>
            <span className="text-(--text-tertiary)">Caracteres:</span>{" "}
            <span
              className={cn(
                "font-medium",
                charCount > 3000 ? "text-(--danger)" : "text-(--text-primary)",
              )}
            >
              {charCount}
            </span>
          </div>
          {hookUsed && (
            <div>
              <span className="text-(--text-tertiary)">Gancho:</span>{" "}
              <span className="text-(--text-primary)">{hookUsed}</span>
            </div>
          )}
        </div>
        <div className="mt-2 pt-2 border-t border-(--border-subtle)">
          <pre className="text-xs text-(--text-secondary) whitespace-pre-wrap font-sans leading-relaxed max-h-20 overflow-y-auto">
            {state.body.slice(0, 200)}
            {state.body.length > 200 && "…"}
          </pre>
        </div>
      </div>

      {/* Date/Time */}
      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="wiz-date">Data de publicação</Label>
          <Input
            id="wiz-date"
            type="datetime-local"
            value={state.publishDate}
            onChange={(e) => update({ publishDate: e.target.value })}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="wiz-week">Semana</Label>
          <Input
            id="wiz-week"
            type="number"
            min={1}
            max={54}
            value={state.weekNumber}
            onChange={(e) => update({ weekNumber: e.target.value })}
            placeholder="1–54"
          />
        </div>
      </div>

      <p className="text-xs text-(--text-tertiary)">
        Ao criar com data, o post será automaticamente aprovado e agendado.
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
          {isCreating ? "Criando…" : "Criar rascunho"}
        </Button>
        {state.publishDate && (
          <Button
            size="sm"
            className="text-xs gap-1"
            onClick={() => onCreate(true)}
            disabled={isCreating}
          >
            <Calendar className="h-3.5 w-3.5" />
            {isCreating ? "Agendando…" : "Agendar publicação"}
          </Button>
        )}
      </div>
    </div>
  )
}
