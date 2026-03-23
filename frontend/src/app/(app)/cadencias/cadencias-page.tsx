"use client"

import Link from "next/link"
import { useCadences, useToggleCadence } from "@/lib/api/hooks/use-cadences"
import { EmptyState } from "@/components/shared/empty-state"
import { Plus, GitBranch, Users, CheckCircle, Power } from "lucide-react"
import { cn } from "@/lib/utils"

export default function CadenciasPage() {
  const { data: cadences, isLoading } = useCadences()
  const toggleCadence = useToggleCadence()

  function handleToggle(id: string, current: boolean) {
    void toggleCadence.mutate({ id, is_active: !current })
  }

  return (
    <div className="space-y-5">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">Cadências</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Sequências de mensagens automatizadas
          </p>
        </div>
        <Link
          href="/cadencias/nova"
          className="flex items-center gap-1.5 rounded-[var(--radius-md)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)]"
        >
          <Plus size={14} aria-hidden="true" />
          Nova cadência
        </Link>
      </div>

      {/* Lista */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-40 animate-pulse rounded-[var(--radius-lg)] bg-[var(--bg-overlay)]"
            />
          ))}
        </div>
      ) : cadences && cadences.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {cadences.map((cadence) => (
            <div
              key={cadence.id}
              className="relative flex flex-col rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-[var(--shadow-sm)]"
            >
              {/* Header do card */}
              <div className="flex items-start justify-between gap-2">
                <Link href={`/cadencias/${cadence.id}`} className="min-w-0">
                  <p className="truncate font-semibold text-[var(--text-primary)] hover:underline">
                    {cadence.name}
                  </p>
                  {cadence.description && (
                    <p className="mt-0.5 line-clamp-2 text-xs text-[var(--text-secondary)]">
                      {cadence.description}
                    </p>
                  )}
                </Link>

                {/* Toggle ativo/inativo */}
                <button
                  type="button"
                  onClick={() => handleToggle(cadence.id, cadence.is_active)}
                  aria-label={cadence.is_active ? "Desativar cadência" : "Ativar cadência"}
                  aria-pressed={cadence.is_active}
                  disabled={toggleCadence.isPending}
                  className={cn(
                    "shrink-0 transition-colors disabled:opacity-50",
                    cadence.is_active ? "text-[var(--success)]" : "text-[var(--text-disabled)]",
                  )}
                >
                  <Power size={16} aria-hidden="true" />
                </button>
              </div>

              {/* Stats */}
              <div className="mt-4 grid grid-cols-3 divide-x divide-[var(--border-subtle)]">
                <Stat icon={Users} label="Total" value={cadence.leads_total} />
                <Stat icon={GitBranch} label="Em andamento" value={cadence.leads_in_progress} />
                <Stat icon={CheckCircle} label="Convertidos" value={cadence.leads_converted} />
              </div>

              {/* LLM info */}
              <p className="mt-4 text-xs text-[var(--text-tertiary)]">
                {cadence.llm_provider === "openai" ? "OpenAI" : "Gemini"} · {cadence.llm_model} ·{" "}
                {cadence.steps.length} passo
                {cadence.steps.length !== 1 ? "s" : ""}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={GitBranch}
          title="Nenhuma cadência criada"
          description="Crie uma cadência para começar a prospectar"
          action={
            <Link
              href="/cadencias/nova"
              className="inline-flex items-center gap-1.5 rounded-[var(--radius-md)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
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
      <Icon size={13} className="text-[var(--text-tertiary)]" aria-hidden="true" />
      <span className="text-sm font-semibold text-[var(--text-primary)]">{value}</span>
      <span className="text-[10px] text-[var(--text-tertiary)]">{label}</span>
    </div>
  )
}
