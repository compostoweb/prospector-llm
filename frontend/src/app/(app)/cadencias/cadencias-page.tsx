"use client"

import { useState } from "react"
import Link from "next/link"
import { useSession } from "next-auth/react"
import { useCadenceOverview } from "@/lib/api/hooks/use-cadence-analytics"
import { useCadences, useToggleCadence } from "@/lib/api/hooks/use-cadences"
import { EmptyState } from "@/components/shared/empty-state"
import {
  Plus,
  GitBranch,
  Users,
  CheckCircle,
  Power,
  FlaskConical,
  Mail,
  Layers,
  TrendingUp,
} from "lucide-react"
import { cn } from "@/lib/utils"

type CadenceFilter = "all" | "mixed" | "email_only"

function KPICard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: "true" }>
  label: string
  value: number | string
  sub?: string
}) {
  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
      <div className="flex items-center gap-2 text-(--text-secondary)">
        <Icon size={14} aria-hidden="true" />
        <span className="text-xs">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-bold text-(--text-primary)">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-(--text-tertiary)">{sub}</p>}
    </div>
  )
}

export default function CadenciasPage() {
  const [filter, setFilter] = useState<CadenceFilter>("all")
  const { status } = useSession()
  const cadenceType = filter === "all" ? undefined : (filter as "mixed" | "email_only")
  const { data: cadences, isLoading, error: cadencesError } = useCadences(cadenceType)
  const { data: overview, isLoading: loadingOverview } = useCadenceOverview()
  const toggleCadence = useToggleCadence()
  const isPageLoading = status === "loading" || isLoading || loadingOverview

  const overviewMap = new Map((overview ?? []).map((item) => [item.cadence_id, item]))

  // KPI aggregation (always over all cadences for context)
  const { data: allCadences } = useCadences()
  const totalCadences = allCadences?.length ?? 0
  const totalLeads = (overview ?? []).reduce((sum, o) => sum + o.total_leads, 0)
  const totalActive = (overview ?? []).reduce((sum, o) => sum + o.leads_active, 0)
  const totalConverted = (overview ?? []).reduce((sum, o) => sum + o.leads_converted, 0)

  function handleToggle(id: string, current: boolean) {
    void toggleCadence.mutate({ id, is_active: !current })
  }

  return (
    <div className="space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Cadências</h1>
          <p className="text-sm text-(--text-secondary)">Sequências de mensagens automatizadas</p>
        </div>
        <Link
          href="/cadencias/nova"
          className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={14} aria-hidden="true" />
          Nova cadência
        </Link>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KPICard icon={Layers} label="Cadências" value={totalCadences} />
        <KPICard icon={Users} label="Total de leads" value={totalLeads} />
        <KPICard
          icon={GitBranch}
          label="Em andamento"
          value={totalActive}
          sub={totalLeads > 0 ? `${Math.round((totalActive / totalLeads) * 100)}% do total` : undefined}
        />
        <KPICard
          icon={TrendingUp}
          label="Convertidos"
          value={totalConverted}
          sub={totalLeads > 0 ? `${Math.round((totalConverted / totalLeads) * 100)}% do total` : undefined}
        />
      </div>

      {/* Filtro por tipo */}
      <div className="flex gap-1 rounded-md border border-(--border-default) bg-(--bg-overlay) p-1 w-fit">
        {(
          [
            { key: "all", label: "Todas" },
            { key: "mixed", label: "Mistas" },
            { key: "email_only", label: "Só E-mail" },
          ] as const
        ).map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={cn(
              "rounded px-3 py-1 text-xs font-medium transition-colors",
              filter === key
                ? "bg-(--bg-surface) text-(--text-primary) shadow-sm"
                : "text-(--text-secondary) hover:text-(--text-primary)",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Lista */}
      {isPageLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 animate-pulse rounded-lg bg-(--bg-overlay)" />
          ))}
        </div>
      ) : cadencesError ? (
        <EmptyState
          icon={GitBranch}
          title="Não foi possível carregar as cadências"
          description="A API não respondeu como esperado. Recarregue a página e confirme se o backend está ativo."
          action={
            <Link
              href="/cadencias"
              className="inline-flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              Tentar novamente
            </Link>
          }
        />
      ) : cadences && cadences.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cadences.map((cadence) => {
            const metrics = overviewMap.get(cadence.id)

            return (
              <div
                key={cadence.id}
                className="relative flex flex-col rounded-lg border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm) transition-shadow hover:shadow-(--shadow-md)"
              >
                {/* Header do card */}
                <div className="flex items-start justify-between gap-2">
                  <Link href={`/cadencias/${cadence.id}`} className="min-w-0">
                    <p className="truncate font-semibold text-(--text-primary) hover:underline">
                      {cadence.name}
                    </p>
                    {cadence.description && (
                      <p className="mt-0.5 line-clamp-2 text-xs text-(--text-secondary)">
                        {cadence.description}
                      </p>
                    )}
                    <div className="mt-1.5 flex flex-wrap items-center gap-1">
                      {cadence.cadence_type === "email_only" ? (
                        <span className="inline-flex items-center gap-1 rounded bg-(--accent)/10 px-1.5 py-0.5 text-[10px] font-medium text-(--accent)">
                          <Mail size={9} aria-hidden="true" />
                          Só E-mail
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-900/20 dark:text-violet-300">
                          <Layers size={9} aria-hidden="true" />
                          Multicanal
                        </span>
                      )}
                      <span className="rounded bg-(--bg-overlay) px-1.5 py-0.5 text-[10px] text-(--text-tertiary)">
                        {cadence.mode === "automatic" ? "Auto" : "Semi-manual"}
                      </span>
                    </div>
                  </Link>

                  {/* Toggle ativo/inativo */}
                  <button
                    type="button"
                    onClick={() => handleToggle(cadence.id, cadence.is_active)}
                    aria-label={cadence.is_active ? "Desativar cadência" : "Ativar cadência"}
                    disabled={toggleCadence.isPending}
                    className={cn(
                      "shrink-0 transition-colors disabled:opacity-50",
                      cadence.is_active ? "text-(--success)" : "text-(--text-disabled)",
                    )}
                  >
                    <Power size={16} aria-hidden="true" />
                  </button>
                </div>

                {/* Stats */}
                <div className="mt-4 grid grid-cols-3 divide-x divide-(--border-subtle)">
                  <Stat icon={Users} label="Total" value={metrics?.total_leads ?? 0} />
                  <Stat icon={GitBranch} label="Em andamento" value={metrics?.leads_active ?? 0} />
                  <Stat
                    icon={CheckCircle}
                    label="Convertidos"
                    value={metrics?.leads_converted ?? 0}
                  />
                </div>

                {/* LLM info + Sandbox link */}
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-xs text-(--text-tertiary)">
                    {cadence.llm_provider === "openai" ? "OpenAI" : "Gemini"} · {cadence.llm_model}{" "}
                    · {cadence.steps_template?.length ?? 0} passo
                    {(cadence.steps_template?.length ?? 0) !== 1 ? "s" : ""}
                  </p>
                  <Link
                    href={`/cadencias/${cadence.id}/sandbox`}
                    className="flex items-center gap-1 text-xs text-(--text-tertiary) transition-colors hover:text-(--accent)"
                  >
                    <FlaskConical size={12} aria-hidden="true" />
                    Sandbox
                  </Link>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <EmptyState
          icon={GitBranch}
          title="Nenhuma cadência criada"
          description="Crie uma cadência para começar a prospectar"
          action={
            <Link
              href="/cadencias/nova"
              className="inline-flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              <Plus size={14} aria-hidden="true" />
              Nova cadência
            </Link>
          }
        />
      )}
    </div>
  )
}

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: "true" }>
  label: string
  value: number
}) {
  return (
    <div className="flex flex-col items-center gap-0.5 px-2">
      <Icon size={13} className="text-(--text-tertiary)" aria-hidden="true" />
      <span className="text-sm font-semibold text-(--text-primary)">{value}</span>
      <span className="text-[10px] text-(--text-tertiary)">{label}</span>
    </div>
  )
}
