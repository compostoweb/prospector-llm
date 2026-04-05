"use client"

import { useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Sparkles, Copy, Check, Save, AlertTriangle, RefreshCw } from "lucide-react"
import {
  useGeneratePost,
  useCreateContentPost,
  useMarkThemeUsed,
  useThemeSuggestions,
  type PostPillar,
  type HookType,
  type GeneratePostVariation,
} from "@/lib/api/hooks/use-content"
import { Button } from "@/components/ui/button"
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

function parsePillarParam(value: string | null): PostPillar | null {
  if (value === "authority" || value === "case" || value === "vision") {
    return value
  }
  return null
}

export default function GerarPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Form state
  const [theme, setTheme] = useState("")
  const [pillar, setPillar] = useState<PostPillar>("authority")
  const [hookType, setHookType] = useState<HookType | "auto">("auto")
  const [variations, setVariations] = useState(3)
  const [useReferences, setUseReferences] = useState(false)
  const [temperature, setTemperature] = useState(0.8)
  const [linkedThemeId, setLinkedThemeId] = useState<string | null>(null)
  const [themeSyncWarning, setThemeSyncWarning] = useState<string | null>(null)

  // Results state
  const [results, setResults] = useState<GeneratePostVariation[]>([])
  const [savedIds, setSavedIds] = useState<Set<number>>(new Set())
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)

  const generate = useGeneratePost()
  const createPost = useCreateContentPost()
  const markThemeUsed = useMarkThemeUsed()
  const { data: suggestions } = useThemeSuggestions()

  useEffect(() => {
    const nextTheme = searchParams.get("theme")
    const nextThemeId = searchParams.get("themeId")
    const nextPillar = parsePillarParam(searchParams.get("pillar"))

    if (!nextTheme && !nextThemeId && !nextPillar) {
      return
    }

    if (nextTheme) {
      setTheme(nextTheme)
      setResults([])
      setSavedIds(new Set())
      setCopiedIdx(null)
    }
    if (nextPillar) {
      setPillar(nextPillar)
    }
    setLinkedThemeId(nextThemeId)
    setThemeSyncWarning(null)
  }, [searchParams])

  async function handleGenerate() {
    const res = await generate.mutateAsync({
      theme,
      pillar,
      hook_type: hookType === "auto" ? null : hookType,
      variations,
      use_references: useReferences,
      temperature,
    })
    setResults(res.variations)
    setSavedIds(new Set())
  }

  async function handleSave(idx: number) {
    const variation = results[idx]
    if (!variation) return
    const createdPost = await createPost.mutateAsync({
      title: `${theme.slice(0, 80)} — variação ${idx + 1}`,
      body: variation.text,
      pillar,
      hook_type: (variation.hook_type_used as HookType) || null,
      character_count: variation.character_count,
    })
    setSavedIds((prev) => new Set([...prev, idx]))

    if (!linkedThemeId) {
      return
    }

    try {
      await markThemeUsed.mutateAsync({
        themeId: linkedThemeId,
        postId: createdPost.id,
      })
      setLinkedThemeId(null)
      setThemeSyncWarning(null)
      router.replace("/content/gerar")
    } catch {
      setThemeSyncWarning(
        "O post foi salvo, mas o tema não foi marcado como usado. Você pode ajustar isso na aba Temas.",
      )
    }
  }

  async function handleCopy(idx: number) {
    const variation = results[idx]
    if (!variation) return
    await navigator.clipboard.writeText(variation.text)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  return (
    <div className="grid min-h-150 grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
      {/* Painel esquerdo — formulário */}
      <div className="flex h-fit flex-col gap-5 rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-(--accent)" />
          <span className="text-sm font-medium text-(--text-primary)">Configurar geração</span>
        </div>

        {linkedThemeId && (
          <div className="rounded-md border border-(--accent)/20 bg-(--accent-subtle) px-3 py-2.5">
            <p className="text-sm font-medium text-(--accent-subtle-fg)">Tema vindo do banco</p>
            <p className="mt-1 text-xs text-(--accent-subtle-fg)/80">
              Ao salvar a primeira variação, este tema será marcado como usado automaticamente.
            </p>
          </div>
        )}

        {themeSyncWarning && (
          <div className="flex items-start gap-2 rounded-md border border-(--warning)/30 bg-(--warning)/5 px-3 py-2.5 text-xs text-(--warning)">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{themeSyncWarning}</span>
          </div>
        )}

        {/* Sugestões de temas */}
        {suggestions && suggestions.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-(--text-tertiary) font-medium uppercase tracking-wide">
              Sugestões baseadas nos seus leads
            </p>
            <div className="flex flex-col gap-1.5">
              {suggestions.slice(0, 3).map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    setTheme(s.theme.title)
                    setPillar(s.theme.pillar)
                  }}
                  className="flex items-start gap-2 rounded-md border border-(--border-subtle) bg-(--bg-overlay) p-2.5 text-left transition-colors hover:border-(--accent)"
                >
                  <PillarBadge pillar={s.theme.pillar} className="mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-(--text-primary) truncate">
                      {s.theme.title}
                    </p>
                    <p className="text-xs text-(--text-tertiary)">{s.reason}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Tema */}
        <div className="grid gap-1.5">
          <Label htmlFor="theme">Tema do post</Label>
          <Textarea
            id="theme"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            placeholder="Ex: Como reduzir o tempo de onboarding de clientes sem contratar mais pessoas"
            rows={3}
            className="resize-none text-sm"
          />
        </div>

        {/* Pilar */}
        <div className="grid gap-2">
          <Label>Pilar</Label>
          <div className="grid grid-cols-3 gap-2">
            {PILLAR_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setPillar(o.value)}
                className={cn(
                  "flex flex-col gap-1 rounded-md border p-2.5 text-left transition-colors",
                  pillar === o.value
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

        {/* Gancho */}
        <div className="grid gap-1.5">
          <Label>Tipo de gancho</Label>
          <Select value={hookType} onValueChange={(v) => setHookType(v as HookType | "auto")}>
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

        {/* Variações + temperatura */}
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-1.5">
            <Label>Variações</Label>
            <Select
              value={String(variations)}
              onValueChange={(v) => setVariations(parseInt(v, 10))}
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
            <Label>Criatividade: {temperature.toFixed(1)}</Label>
            <input
              aria-label="Nível de criatividade"
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="mt-2 w-full accent-(--accent)"
            />
          </div>
        </div>

        {/* Usar referências */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-(--text-primary)">Usar posts de referência</p>
            <p className="text-xs text-(--text-tertiary)">Few-shot com posts de alto engajamento</p>
          </div>
          <Switch checked={useReferences} onCheckedChange={setUseReferences} />
        </div>

        <Button
          onClick={handleGenerate}
          disabled={!theme.trim() || generate.isPending}
          className="gap-2"
        >
          {generate.isPending ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Gerando…
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Gerar {variations} variação{variations > 1 ? "ões" : ""}
            </>
          )}
        </Button>
      </div>

      {/* Painel direito — resultados */}
      <div className="flex flex-col gap-4">
        {generate.isPending && (
          <div className="flex flex-col gap-3">
            {Array.from({ length: variations }).map((_, i) => (
              <div
                key={i}
                className="h-48 rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 animate-pulse"
              />
            ))}
          </div>
        )}

        {!generate.isPending && results.length === 0 && (
          <div className="flex h-full min-h-75 items-center justify-center rounded-lg border border-(--border-subtle) bg-(--bg-surface)">
            <div className="text-center">
              <Sparkles className="h-8 w-8 text-(--text-tertiary) mx-auto mb-3" />
              <p className="text-sm text-(--text-secondary)">
                Preencha o tema e clique em Gerar para ver as variações
              </p>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="flex flex-col gap-3">
            {results.map((variation, idx) => (
              <VariationCard
                key={idx}
                variation={variation}
                index={idx}
                isSaved={savedIds.has(idx)}
                isCopied={copiedIdx === idx}
                isSaving={createPost.isPending}
                onSave={() => handleSave(idx)}
                onCopy={() => handleCopy(idx)}
              />
            ))}
          </div>
        )}

        {generate.isError && (
          <div className="flex items-center gap-2 rounded-md bg-(--danger-subtle) p-3 text-sm text-(--danger-subtle-fg)">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Erro ao gerar posts. Verifique as configurações do LLM.
          </div>
        )}
      </div>
    </div>
  )
}

// ── Variation Card ────────────────────────────────────────────────────

interface VariationCardProps {
  variation: GeneratePostVariation
  index: number
  isSaved: boolean
  isCopied: boolean
  isSaving: boolean
  onSave: () => void
  onCopy: () => void
}

function VariationCard({
  variation,
  index,
  isSaved,
  isCopied,
  isSaving,
  onSave,
  onCopy,
}: VariationCardProps) {
  const charWarning = variation.character_count > 3000

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-(--text-secondary)">Variação {index + 1}</span>
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
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1" onClick={onCopy}>
            {isCopied ? (
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
            onClick={onSave}
            disabled={isSaved || isSaving}
            variant={isSaved ? "outline" : "default"}
          >
            {isSaved ? (
              <>
                <Check className="h-3.5 w-3.5 text-(--success)" />
                Salvo
              </>
            ) : (
              <>
                <Save className="h-3.5 w-3.5" />
                Salvar
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Texto */}
      <pre className="text-sm text-(--text-primary) whitespace-pre-wrap font-sans leading-relaxed">
        {variation.text}
      </pre>

      {/* Violações */}
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
}
