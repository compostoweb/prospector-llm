"use client"

import Link from "next/link"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import { FlaskConical, Loader2, BarChart2, Settings2, Play, Pause, ListTodo } from "lucide-react"
import { CadenceDetailAnalytics } from "@/components/cadencias/cadence-detail-analytics"
import { useCadence, useToggleCadence } from "@/lib/api/hooks/use-cadences"
import { CadenceForm } from "@/components/cadencias/cadence-form"
import { CadenceStepsEditor } from "@/components/cadencias/cadence-steps-editor"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type Tab = "visao-geral" | "configuracao" | "passos"

const TABS: { key: Tab; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { key: "visao-geral", label: "Visão Geral", icon: BarChart2 },
  { key: "configuracao", label: "Configuração", icon: Settings2 },
  { key: "passos", label: "Passos", icon: ListTodo },
]

export default function CadenciaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const searchParams = useSearchParams()
  const tab = (searchParams.get("tab") as Tab) ?? "visao-geral"
  const { data: cadence, isLoading, error } = useCadence(id)
  const toggleCadence = useToggleCadence()

  function setTab(t: Tab) {
    const params = new URLSearchParams(searchParams.toString())
    params.set("tab", t)
    router.replace(`?${params.toString()}`)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-(--text-tertiary)" />
      </div>
    )
  }

  if (error || !cadence) {
    return (
      <div className="py-20 text-center text-sm text-(--text-secondary)">
        Cadência não encontrada.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
            Cadência
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-(--text-primary)">{cadence.name}</h1>
          {cadence.description && (
            <p className="mt-1 max-w-2xl text-sm text-(--text-secondary)">{cadence.description}</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span
              className={cn(
                "rounded-full px-2.5 py-1 font-medium",
                cadence.is_active
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-(--bg-overlay) text-(--text-secondary)",
              )}
            >
              {cadence.is_active ? "Ativa" : "Inativa"}
            </span>
            <span className="rounded-full bg-(--accent-subtle) px-2.5 py-1 font-medium text-(--accent-subtle-fg)">
              {cadence.cadence_type === "email_only" ? "Só e-mail" : "Multicanal"}
            </span>
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-(--text-secondary)">
              {cadence.llm_provider === "openai" ? "OpenAI" : "Gemini"} · {cadence.llm_model}
            </span>
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-(--text-secondary)">
              {cadence.mode === "automatic" ? "Automática" : "Semi-manual"}
            </span>
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-(--text-secondary)">
              {cadence.steps_template?.length ?? 0} passo
              {(cadence.steps_template?.length ?? 0) === 1 ? "" : "s"}
            </span>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Link
          href={`/cadencias/${cadence.id}/sandbox`}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-2.5 text-sm font-medium text-(--text-primary) shadow-(--shadow-sm) transition-colors hover:border-(--accent) hover:text-(--accent)"
        >
          <FlaskConical size={15} aria-hidden="true" />
          Abrir sandbox
        </Link>

        <button
          type="button"
          disabled={toggleCadence.isPending}
          onClick={() =>
            toggleCadence.mutate(
              { id: cadence.id, is_active: !cadence.is_active },
              {
                onSuccess: () =>
                  toast.success(
                    cadence.is_active ? "Cadência pausada" : "Cadência ativada",
                  ),
                onError: () => toast.error("Falha ao alterar status da cadência"),
              },
            )
          }
          className={cn(
            "inline-flex shrink-0 items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium shadow-(--shadow-sm) transition-colors disabled:opacity-60",
            cadence.is_active
              ? "border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-400 dark:hover:bg-amber-900/30"
              : "border-green-300 bg-green-50 text-green-700 hover:bg-green-100 dark:border-green-700 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/30",
          )}
        >
          {toggleCadence.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : cadence.is_active ? (
            <Pause size={14} />
          ) : (
            <Play size={14} />
          )}
          {cadence.is_active ? "Pausar" : "Ativar"}
        </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-(--border-default)">
        <nav className="flex gap-0" aria-label="Abas da cadência">
          {TABS.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={cn(
                  "flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors -mb-px",
                  tab === t.key
                    ? "border-(--accent) text-(--accent)"
                    : "border-transparent text-(--text-secondary) hover:border-(--border-default) hover:text-(--text-primary)",
                )}
              >
                <Icon size={14} className="shrink-0" />
                {t.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab content */}
      {tab === "visao-geral" && <CadenceDetailAnalytics cadence={cadence} />}
      {tab === "configuracao" && <CadenceForm cadence={cadence} />}
      {tab === "passos" && <CadenceStepsEditor cadence={cadence} />}
    </div>
  )
}
