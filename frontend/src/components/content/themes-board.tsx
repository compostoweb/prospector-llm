"use client"

import { useState, type FormEvent } from "react"
import { useRouter } from "next/navigation"
import type { Route } from "next"
import { CheckCircle2, Filter, Lightbulb, Loader2, Plus, Sparkles, Trash2 } from "lucide-react"
import {
  useContentThemes,
  useCreateTheme,
  useDeleteTheme,
  useMarkThemeUsed,
  type ContentTheme,
  type PostPillar,
} from "@/lib/api/hooks/use-content"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

const PILLAR_OPTIONS: Array<{ value: PostPillar | "all"; label: string }> = [
  { value: "all", label: "Todos os pilares" },
  { value: "authority", label: "Autoridade" },
  { value: "case", label: "Caso" },
  { value: "vision", label: "Visão" },
]

const CREATE_PILLAR_OPTIONS: Array<{ value: PostPillar; label: string }> = [
  { value: "authority", label: "Autoridade" },
  { value: "case", label: "Caso" },
  { value: "vision", label: "Visão" },
]

const USAGE_OPTIONS = [
  { value: "all", label: "Todos os status" },
  { value: "fresh", label: "Disponíveis" },
  { value: "used", label: "Usados" },
] as const

type UsageFilter = (typeof USAGE_OPTIONS)[number]["value"]

function buildGenerateRoute(theme: ContentTheme): Route {
  const params = new URLSearchParams({
    theme: theme.title,
    pillar: theme.pillar,
    themeId: theme.id,
  })
  return `/content/gerar?${params.toString()}` as Route
}

function formatDate(date: string | null): string {
  if (!date) {
    return "—"
  }
  return new Date(date).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}

export function ThemesBoard() {
  const router = useRouter()
  const { data: themes = [], isLoading } = useContentThemes()
  const createTheme = useCreateTheme()
  const markThemeUsed = useMarkThemeUsed()
  const deleteTheme = useDeleteTheme()

  const [pillarFilter, setPillarFilter] = useState<PostPillar | "all">("all")
  const [usageFilter, setUsageFilter] = useState<UsageFilter>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [createOpen, setCreateOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [createPillar, setCreatePillar] = useState<PostPillar>("authority")

  const filteredThemes = themes.filter((theme) => {
    if (pillarFilter !== "all" && theme.pillar !== pillarFilter) return false
    if (usageFilter === "fresh") return !theme.used
    if (usageFilter === "used") return theme.used
    if (searchQuery.trim()) {
      return theme.title.toLowerCase().includes(searchQuery.trim().toLowerCase())
    }
    return true
  })

  const totalThemes = themes.length
  const availableThemes = themes.filter((theme) => !theme.used).length
  const usedThemes = themes.filter((theme) => theme.used).length

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const nextTitle = title.trim()
    if (!nextTitle) {
      return
    }

    await createTheme.mutateAsync({ title: nextTitle, pillar: createPillar })
    setTitle("")
    setCreatePillar("authority")
    setCreateOpen(false)
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3 md:grid-cols-3">
        <SummaryCard label="Temas no banco" value={String(totalThemes)} />
        <SummaryCard label="Disponíveis" value={String(availableThemes)} accent="success" />
        <SummaryCard label="Usados" value={String(usedThemes)} accent="warning" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
        <div>
          <h2 className="text-sm font-semibold text-(--text-primary)">Banco de temas</h2>
          <p className="mt-1 text-xs text-(--text-tertiary)">
            Organize temas editoriais, acompanhe o que já foi usado e envie direto para a geração
            com IA.
          </p>
          <p className="mt-2 text-xs text-(--text-tertiary)">
            O banco inicial é carregado automaticamente com os temas estratégicos da Composto Web e
            o histórico já publicado.
          </p>
        </div>

        <Button size="sm" className="gap-1.5" onClick={() => setCreateOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          Novo tema
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
        <div className="flex items-center gap-2 text-(--text-tertiary)">
          <Filter className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wide">Filtros</span>
        </div>

        <Input
          placeholder="Buscar tema…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-8 w-52 text-xs"
        />

        <Select
          value={pillarFilter}
          onValueChange={(value) => setPillarFilter(value as PostPillar | "all")}
        >
          <SelectTrigger className="h-8 w-44 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PILLAR_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value} className="text-xs">
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={usageFilter} onValueChange={(value) => setUsageFilter(value as UsageFilter)}>
          <SelectTrigger className="h-8 w-44 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {USAGE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value} className="text-xs">
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="flex h-56 items-center justify-center rounded-lg border border-(--border-default) bg-(--bg-surface)">
          <Loader2 className="h-5 w-5 animate-spin text-(--text-tertiary)" />
        </div>
      ) : filteredThemes.length === 0 ? (
        <div className="flex min-h-80 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-(--border-default) bg-(--bg-surface) px-6 text-center">
          <Lightbulb className="h-9 w-9 text-(--text-tertiary)" />
          <div>
            <p className="text-sm font-medium text-(--text-primary)">Nenhum tema encontrado</p>
            <p className="mt-1 text-xs text-(--text-tertiary)">
              Ajuste os filtros ou cadastre um novo tema para abastecer a geração com IA.
            </p>
          </div>
        </div>
      ) : (
        <ThemePillarBoard
          themes={filteredThemes}
          pillarFilter={pillarFilter}
          isMarking={markThemeUsed.isPending}
          markingId={markThemeUsed.isPending ? markThemeUsed.variables?.themeId : undefined}
          isDeleting={deleteTheme.isPending}
          deletingId={deleteTheme.isPending ? deleteTheme.variables : undefined}
          onGenerate={(theme) => router.push(buildGenerateRoute(theme))}
          onMarkUsed={(themeId) => markThemeUsed.mutate({ themeId })}
          onDelete={(themeId) => deleteTheme.mutate(themeId)}
        />
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Novo tema editorial</DialogTitle>
            <DialogDescription>
              Cadastre um tema para reutilizar na geração de posts do LinkedIn.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreate} className="flex flex-col gap-4 py-2">
            <div className="grid gap-1.5">
              <Label htmlFor="theme-title">Tema</Label>
              <Input
                id="theme-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Ex: O custo invisível de operar com sistemas desconectados"
              />
            </div>

            <div className="grid gap-1.5">
              <Label>Pilar</Label>
              <Select
                value={createPillar}
                onValueChange={(value) => setCreatePillar(value as PostPillar)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CREATE_PILLAR_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={!title.trim() || createTheme.isPending}>
                {createTheme.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                    Salvando…
                  </>
                ) : (
                  "Salvar tema"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

const PILLAR_COLUMNS: Array<{
  pillar: PostPillar
  label: string
  headerClass: string
  borderClass: string
}> = [
  {
    pillar: "authority",
    label: "Autoridade",
    headerClass:
      "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800",
    borderClass: "border-l-blue-400",
  },
  {
    pillar: "case",
    label: "Caso",
    headerClass:
      "bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800",
    borderClass: "border-l-green-400",
  },
  {
    pillar: "vision",
    label: "Visão",
    headerClass:
      "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
    borderClass: "border-l-orange-400",
  },
]

function ThemePillarBoard({
  themes,
  pillarFilter,
  isMarking,
  markingId,
  isDeleting,
  deletingId,
  onGenerate,
  onMarkUsed,
  onDelete,
}: {
  themes: ContentTheme[]
  pillarFilter: PostPillar | "all"
  isMarking: boolean
  markingId: string | undefined
  isDeleting: boolean
  deletingId: string | undefined
  onGenerate: (theme: ContentTheme) => void
  onMarkUsed: (themeId: string) => void
  onDelete: (themeId: string) => void
}) {
  const visibleColumns =
    pillarFilter === "all"
      ? PILLAR_COLUMNS
      : PILLAR_COLUMNS.filter((c) => c.pillar === pillarFilter)

  return (
    <div className={cn("grid gap-4", pillarFilter === "all" ? "md:grid-cols-3" : "md:grid-cols-1")}>
      {visibleColumns.map((col) => {
        const colThemes = themes
          .filter((t) => t.pillar === col.pillar)
          .sort((a, b) => {
            if (a.used !== b.used) return a.used ? 1 : -1
            return a.title.localeCompare(b.title, "pt-BR")
          })
        return (
          <div key={col.pillar} className="flex flex-col gap-2">
            <div
              className={cn(
                "flex items-center justify-between rounded-lg border px-3 py-2",
                col.headerClass,
              )}
            >
              <span className="text-xs font-semibold uppercase tracking-wide">{col.label}</span>
              <span className="text-xs font-medium">{colThemes.length}</span>
            </div>
            {colThemes.length === 0 ? (
              <p className="py-6 text-center text-xs text-(--text-tertiary)">Nenhum tema</p>
            ) : (
              colThemes.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  borderClass={col.borderClass}
                  isMarking={isMarking && markingId === theme.id}
                  isDeleting={isDeleting && deletingId === theme.id}
                  onGenerate={() => onGenerate(theme)}
                  onMarkUsed={() => onMarkUsed(theme.id)}
                  onDelete={() => onDelete(theme.id)}
                />
              ))
            )}
          </div>
        )
      })}
    </div>
  )
}

function SummaryCard({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent?: "success" | "warning"
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)",
        accent === "success" && "border-(--success)/20 bg-(--success-subtle)",
        accent === "warning" && "border-(--warning)/20 bg-(--warning-subtle)",
      )}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-(--text-primary)">{value}</p>
    </div>
  )
}

function ThemeCard({
  theme,
  borderClass,
  isMarking,
  isDeleting,
  onGenerate,
  onMarkUsed,
  onDelete,
}: {
  theme: ContentTheme
  borderClass: string
  isMarking: boolean
  isDeleting: boolean
  onGenerate: () => void
  onMarkUsed: () => void
  onDelete: () => void
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border-l-4 border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)",
        borderClass,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                theme.used
                  ? "bg-(--warning-subtle) text-(--warning-subtle-fg)"
                  : "bg-(--success-subtle) text-(--success-subtle-fg)",
              )}
            >
              {theme.used ? "Usado" : "Disponível"}
            </span>
            {theme.is_custom && (
              <span className="inline-flex items-center rounded-full bg-(--bg-overlay) px-2 py-0.5 text-xs font-medium text-(--text-secondary)">
                Custom
              </span>
            )}
          </div>
          <h3 className="mt-2 text-sm font-semibold text-(--text-primary) leading-snug">
            {theme.title}
          </h3>
        </div>

        {theme.is_custom && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-(--text-tertiary) hover:text-(--danger)"
            onClick={onDelete}
            disabled={isDeleting}
            aria-label="Excluir tema"
          >
            {isDeleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>

      <div className="grid gap-2 text-xs text-(--text-tertiary) grid-cols-2">
        <div>
          <p className="font-medium uppercase tracking-wide">Último uso</p>
          <p className="mt-0.5 text-(--text-secondary)">{formatDate(theme.used_at)}</p>
        </div>
        <div>
          <p className="font-medium uppercase tracking-wide">Origem</p>
          <p className="mt-0.5 text-(--text-secondary)">{theme.is_custom ? "App" : "Sistema"}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" className="gap-1.5" onClick={onGenerate}>
          <Sparkles className="h-3.5 w-3.5" />
          Gerar com IA
        </Button>

        {!theme.used && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={onMarkUsed}
            disabled={isMarking}
          >
            {isMarking ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Atualizando…
              </>
            ) : (
              <>
                <CheckCircle2 className="h-3.5 w-3.5" />
                Marcar como usado
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}
