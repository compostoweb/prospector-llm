"use client"

import { useCadence, useDeleteCadence } from "@/lib/api/hooks/use-cadences"
import { CadenceForm } from "@/components/cadencias/cadence-form"
import { LeadTable } from "@/components/leads/lead-table"
import { useLeads } from "@/lib/api/hooks/use-leads"
import { ArrowLeft, Pencil, Trash2 } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { notFound } from "next/navigation"

interface Props {
  params: Promise<{ id: string }>
}

export default function CadenciaDetailPage({ params }: Props) {
  const { id } = params as unknown as { id: string }
  return <CadenciaDetailContent id={id} />
}

function CadenciaDetailContent({ id }: { id: string }) {
  const router = useRouter()
  const { data: cadence, isLoading, error } = useCadence(id)
  const deleteCadence = useDeleteCadence()
  const { data: leadsData, isLoading: loadingLeads } = useLeads({ cadence_id: id, page_size: 20 })
  const [editMode, setEditMode] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  if (error) return notFound()

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-[var(--radius-md)] bg-[var(--bg-overlay)]" />
        <div className="h-48 animate-pulse rounded-[var(--radius-lg)] bg-[var(--bg-overlay)]" />
      </div>
    )
  }

  if (!cadence) return null

  async function handleDelete() {
    await deleteCadence.mutateAsync(cadence!.id)
    router.push("/cadencias")
  }

  if (editMode) {
    return (
      <div className="mx-auto max-w-2xl">
        <button
          type="button"
          onClick={() => setEditMode(false)}
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Cancelar edição
        </button>
        <CadenceForm cadence={cadence} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            href="/cadencias"
            className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <ArrowLeft size={14} aria-hidden="true" />
            Cadências
          </Link>
          <h1 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">{cadence.name}</h1>
          {cadence.description && (
            <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{cadence.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setEditMode(true)}
            className="flex items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border-default)] px-3 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-overlay)]"
          >
            <Pencil size={13} aria-hidden="true" />
            Editar
          </button>
          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border-default)] px-3 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--danger)] hover:text-[var(--danger)]"
            >
              <Trash2 size={13} aria-hidden="true" />
              Excluir
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-[var(--radius-md)] border border-[var(--border-default)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-overlay)]"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteCadence.isPending}
                className="rounded-[var(--radius-md)] bg-[var(--danger)] px-3 py-2 text-xs font-medium text-white hover:opacity-90 disabled:opacity-60"
              >
                {deleteCadence.isPending ? "Excluindo…" : "Confirmar exclusão"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Info LLM + Passos */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
            Configuração LLM
          </p>
          <dl className="space-y-2 text-sm">
            <Row label="Provider" value={cadence.llm_provider === "openai" ? "OpenAI" : "Gemini"} />
            <Row label="Modelo" value={cadence.llm_model} />
            <Row label="Temperature" value={String(cadence.llm_temperature)} />
            <Row label="Máx. tokens" value={String(cadence.llm_max_tokens)} />
            <Row label="Passos" value={String(cadence.steps.length)} />
          </dl>
        </div>

        <div className="lg:col-span-2 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
            Passos
          </p>
          <ol className="space-y-2">
            {cadence.steps.map((step) => (
              <li key={step.step_number} className="flex items-center gap-3 text-sm">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-subtle)] text-[10px] font-bold text-[var(--accent-subtle-fg)]">
                  {step.step_number}
                </span>
                <span className="text-[var(--text-secondary)]">
                  {step.channel === "linkedin_connect"
                    ? "LinkedIn Connect"
                    : step.channel === "linkedin_dm"
                      ? "LinkedIn DM"
                      : "E-mail"}
                  {step.delay_days > 0 && (
                    <span className="ml-1 text-[var(--text-tertiary)]">· +{step.delay_days}d</span>
                  )}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Leads nesta cadência */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
          Leads nesta cadência
        </h2>
        <LeadTable leads={leadsData?.items ?? []} isLoading={loadingLeads} />
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-[var(--text-secondary)]">{label}</dt>
      <dd className="font-medium text-[var(--text-primary)]">{value}</dd>
    </div>
  )
}
