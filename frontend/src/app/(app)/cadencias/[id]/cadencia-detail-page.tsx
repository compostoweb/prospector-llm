"use client"

import { useState } from "react"
import Link from "next/link"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import {
  FlaskConical,
  Loader2,
  BarChart2,
  Settings2,
  Play,
  Pause,
  ListTodo,
  Info,
} from "lucide-react"
import { CadenceDetailAnalytics } from "@/components/cadencias/cadence-detail-analytics"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useCadence, useToggleCadence } from "@/lib/api/hooks/use-cadences"
import { CadenceForm } from "@/components/cadencias/cadence-form"
import { CadenceStepsEditor } from "@/components/cadencias/cadence-steps-editor"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type Tab = "visao-geral" | "configuracao" | "passos"

const TABS: {
  key: Tab
  label: string
  icon: React.ComponentType<{ size?: number; className?: string }>
}[] = [
  { key: "visao-geral", label: "Visão Geral", icon: BarChart2 },
  { key: "configuracao", label: "Configuração", icon: Settings2 },
  { key: "passos", label: "Passos", icon: ListTodo },
]

export default function CadenciaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [timingInfoOpen, setTimingInfoOpen] = useState(false)
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
            <Badge variant={cadence.is_active ? "success" : "warning"} className="px-2.5 py-1">
              {cadence.is_active ? "Ativa" : "Pausada"}
            </Badge>
            <Badge variant="default" className="px-2.5 py-1">
              {cadence.cadence_type === "email_only" ? "Só e-mail" : "Multicanal"}
            </Badge>
            <Badge variant="neutral" className="px-2.5 py-1">
              {cadence.llm_provider === "openai"
                ? "OpenAI"
                : cadence.llm_provider === "gemini"
                  ? "Gemini"
                  : cadence.llm_provider === "anthropic"
                    ? "Anthropic"
                    : "OpenRouter"}{" "}
              · {cadence.llm_model}
            </Badge>
            <Badge variant={cadence.mode === "automatic" ? "info" : "warning"} className="px-2.5 py-1">
              {cadence.mode === "automatic" ? "Automática" : "Semi-automática"}
            </Badge>
            <Badge variant="outline" className="px-2.5 py-1">
              {cadence.steps_template?.length ?? 0} passo
              {(cadence.steps_template?.length ?? 0) === 1 ? "" : "s"}
            </Badge>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Dialog open={timingInfoOpen} onOpenChange={setTimingInfoOpen}>
            <DialogTrigger asChild>
              <button
                type="button"
                className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-(--info-subtle) bg-(--info-subtle) px-3 py-2 text-sm font-medium text-(--info-subtle-fg) shadow-(--shadow-sm) transition-opacity hover:opacity-90"
                aria-label="Como funciona o disparo"
                title="Como funciona o disparo"
              >
                <Info size={14} aria-hidden="true" />
                Disparo
              </button>
            </DialogTrigger>

            <DialogContent className="max-w-xl">
              <DialogHeader>
                <DialogTitle>Janela de disparo</DialogTitle>
                <DialogDescription>
                  Tempos típicos considerando Beat e workers ativos.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 text-sm text-(--text-secondary)">
                <div className="rounded-xl border border-(--border-subtle) bg-(--bg-overlay) px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-(--text-tertiary)">
                    Ao iniciar a cadência
                  </p>
                  <p className="mt-1">
                    A cadência processa o tick a cada 1 minuto. Quando você inicia, passos já
                    vencidos entram na fila no próximo ciclo, normalmente em até 1 minuto.
                  </p>
                </div>

                <div className="rounded-xl border border-(--border-subtle) bg-(--bg-overlay) px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-(--text-tertiary)">
                    Novos leads na lista vinculada
                  </p>
                  <p className="mt-1">
                    A matrícula automática roda nesse tick e o primeiro passo de dia 0 costuma sair
                    no tick seguinte, normalmente em até cerca de 2 minutos mais o tempo da fila de
                    dispatch.
                  </p>
                </div>
              </div>
            </DialogContent>
          </Dialog>

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
                    toast.success(cadence.is_active ? "Cadência pausada" : "Cadência iniciada"),
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
            {cadence.is_active ? "Pausar" : "Iniciar"}
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
