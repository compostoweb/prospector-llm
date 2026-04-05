"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { FlaskConical, Loader2 } from "lucide-react"
import { CadenceDetailAnalytics } from "@/components/cadencias/cadence-detail-analytics"
import { useCadence } from "@/lib/api/hooks/use-cadences"
import { CadenceForm } from "@/components/cadencias/cadence-form"

export default function CadenciaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: cadence, isLoading, error } = useCadence(id)

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
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
            Operação da cadência
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-(--text-primary)">{cadence.name}</h1>
          <p className="mt-2 max-w-3xl text-sm text-(--text-secondary)">
            Monitore resposta, canais, steps e testes A/B sem sair da tela de edição.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 font-medium text-(--text-primary)">
              {cadence.is_active ? "Ativa" : "Inativa"}
            </span>
            <span className="rounded-full bg-(--accent-subtle) px-2.5 py-1 font-medium text-(--accent-subtle-fg)">
              {cadence.cadence_type === "email_only" ? "Só e-mail" : "Multicanal"}
            </span>
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-(--text-secondary)">
              {cadence.llm_provider === "openai" ? "OpenAI" : "Gemini"} · {cadence.llm_model}
            </span>
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-(--text-secondary)">
              {cadence.steps_template?.length ?? 0} passo
              {(cadence.steps_template?.length ?? 0) === 1 ? "" : "s"}
            </span>
          </div>
        </div>

        <Link
          href={`/cadencias/${cadence.id}/sandbox`}
          className="inline-flex items-center gap-2 rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-2.5 text-sm font-medium text-(--text-primary) shadow-(--shadow-sm) transition-colors hover:border-(--accent) hover:text-(--accent)"
        >
          <FlaskConical size={15} aria-hidden="true" />
          Abrir sandbox
        </Link>
      </div>

      <CadenceDetailAnalytics cadence={cadence} />

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-(--text-primary)">Configuração</h2>
          <p className="text-sm text-(--text-secondary)">
            Ajuste contexto, canais, contas e templates desta cadência.
          </p>
        </div>

        <CadenceForm cadence={cadence} />
      </section>
    </div>
  )
}
