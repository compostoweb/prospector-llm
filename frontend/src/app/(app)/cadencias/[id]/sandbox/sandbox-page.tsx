"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { useCadence } from "@/lib/api/hooks/use-cadences"
import { useEmailAccounts } from "@/lib/api/hooks/use-email-accounts"
import {
  useSandboxRuns,
  useSandboxRun,
  useGenerateSandbox,
  useDeleteSandboxRun,
  type SandboxRun,
} from "@/lib/api/hooks/use-sandbox"
import { SandboxCreateDialog } from "@/components/cadencias/sandbox/sandbox-create-dialog"
import { SandboxTimeline } from "@/components/cadencias/sandbox/sandbox-timeline"
import { SandboxActionsBar } from "@/components/cadencias/sandbox/sandbox-actions-bar"
import { SandboxPipedrivePreview } from "@/components/cadencias/sandbox/sandbox-pipedrive-preview"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { buildTestEmailTransportSummary } from "@/lib/cadences/test-email-transport"
import { ArrowLeft, Plus, Trash2, Loader2 } from "lucide-react"
import { formatRelativeTime } from "@/lib/utils"

const STATUS_MAP: Record<
  string,
  { label: string; variant: "default" | "success" | "warning" | "danger" | "info" }
> = {
  running: { label: "Em execução", variant: "info" },
  completed: { label: "Concluído", variant: "default" },
  approved: { label: "Aprovado", variant: "success" },
  rejected: { label: "Rejeitado", variant: "danger" },
}

export default function SandboxPage() {
  const params = useParams<{ id: string }>()
  const cadenceId = params.id

  const { data: runs, isLoading: runsLoading } = useSandboxRuns(cadenceId)
  const deleteSandbox = useDeleteSandboxRun(cadenceId)
  const generateSandbox = useGenerateSandbox()

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const { data: selectedRun } = useSandboxRun(selectedRunId)
  const cadenceQuery = useCadence(selectedRun?.cadence_id ?? "")
  const emailAccountsQuery = useEmailAccounts()
  const testEmailTransport = buildTestEmailTransportSummary({
    cadence: cadenceQuery.data,
    emailAccounts: emailAccountsQuery.data?.accounts,
    isCadenceLoading: cadenceQuery.isLoading,
    isEmailAccountsLoading: emailAccountsQuery.isLoading,
  })

  function handleCreated(run: SandboxRun) {
    setSelectedRunId(run.id)
    setCreateOpen(false)
  }

  function handleDelete(runId: string) {
    if (selectedRunId === runId) setSelectedRunId(null)
    deleteSandbox.mutate(runId)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href={`/cadencias/${cadenceId}`}
            className="flex items-center gap-1 text-sm text-(--text-secondary) transition-colors hover:text-(--text-primary)"
          >
            <ArrowLeft size={14} aria-hidden="true" />
            Voltar
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-(--text-primary)">Sandbox</h1>
            <p className="text-sm text-(--text-secondary)">Teste sua cadência antes de ativar</p>
          </div>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="sm">
          <Plus size={14} aria-hidden="true" />
          Novo teste
        </Button>
      </div>

      {/* Lista de runs */}
      {runsLoading ? (
        <div className="flex items-center gap-2 text-sm text-(--text-secondary)">
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          Carregando…
        </div>
      ) : runs && runs.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {runs.map((run) => {
            const st = STATUS_MAP[run.status] ?? { label: run.status, variant: "info" as const }
            return (
              <button
                key={run.id}
                type="button"
                onClick={() => setSelectedRunId(run.id)}
                className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors ${
                  selectedRunId === run.id
                    ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                    : "border-(--border-default) bg-(--bg-surface) text-(--text-primary) hover:border-(--accent)"
                }`}
              >
                <Badge variant={st.variant}>{st.label}</Badge>
                <span className="text-xs text-(--text-tertiary)">
                  {run.steps_count} passos · {formatRelativeTime(run.created_at)}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(run.id)
                  }}
                  className="ml-1 text-(--text-disabled) transition-colors hover:text-(--danger)"
                  aria-label="Excluir run"
                >
                  <Trash2 size={12} aria-hidden="true" />
                </button>
              </button>
            )
          })}
        </div>
      ) : (
        !selectedRunId && (
          <div className="rounded-lg border border-dashed border-(--border-default) bg-(--bg-surface) px-6 py-10 text-center">
            <p className="text-sm text-(--text-secondary)">
              Nenhum teste criado ainda. Clique em &quot;Novo teste&quot; para começar.
            </p>
          </div>
        )
      )}

      {/* Run selecionado — detalhe */}
      {selectedRun && (
        <div className="space-y-5">
          {/* Actions bar */}
          <SandboxActionsBar
            run={selectedRun}
            onGenerate={() => generateSandbox.mutate(selectedRun.id)}
            isGenerating={generateSandbox.isPending}
          />

          {/* Timeline dos steps */}
          <SandboxTimeline run={selectedRun} emailTransportSummary={testEmailTransport} />

          {/* Pipedrive dry-run */}
          <SandboxPipedrivePreview run={selectedRun} />
        </div>
      )}

      {/* Dialog de criação */}
      <SandboxCreateDialog
        cadenceId={cadenceId}
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={handleCreated}
      />
    </div>
  )
}
