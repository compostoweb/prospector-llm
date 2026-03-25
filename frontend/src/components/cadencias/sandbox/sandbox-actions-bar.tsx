"use client"

import {
  useApproveRun,
  useStartFromSandbox,
  useSandboxTimeline,
  type SandboxRun,
} from "@/lib/api/hooks/use-sandbox"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Loader2,
  Wand2,
  CheckCheck,
  Rocket,
  Clock,
  CheckCircle,
  XCircle,
  FileText,
} from "lucide-react"

interface SandboxActionsBarProps {
  run: SandboxRun
  onGenerate: () => void
  isGenerating: boolean
}

export function SandboxActionsBar({ run, onGenerate, isGenerating }: SandboxActionsBarProps) {
  const approveRun = useApproveRun()
  const startFromSandbox = useStartFromSandbox()
  const { refetch: refetchTimeline, isFetching: timelineLoading } = useSandboxTimeline(run.id)

  const total = run.steps.length
  const pending = run.steps.filter((s) => s.status === "pending").length
  const generated = run.steps.filter((s) => s.status === "generated").length
  const approved = run.steps.filter((s) => s.status === "approved").length
  const rejected = run.steps.filter((s) => s.status === "rejected").length
  const rateLimited = run.steps.filter((s) => s.is_rate_limited).length

  const allGenerated = total > 0 && pending === 0
  const canApproveAll = generated > 0
  const canStart = run.status === "approved"

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
      {/* Stats row */}
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs">
        <StatPill icon={FileText} label="Total" value={total} />
        <StatPill icon={Clock} label="Pendentes" value={pending} />
        <StatPill icon={CheckCircle} label="Gerados" value={generated} color="text-(--accent)" />
        <StatPill icon={CheckCheck} label="Aprovados" value={approved} color="text-(--success)" />
        <StatPill icon={XCircle} label="Rejeitados" value={rejected} color="text-(--danger)" />
        {rateLimited > 0 && <Badge variant="warning">{rateLimited} rate-limited</Badge>}
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Generate all */}
        {pending > 0 && (
          <Button size="sm" onClick={onGenerate} disabled={isGenerating}>
            {isGenerating ? (
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
            ) : (
              <Wand2 size={14} aria-hidden="true" />
            )}
            {isGenerating ? "Gerando…" : `Gerar todas (${pending})`}
          </Button>
        )}

        {/* Approve all generated */}
        {canApproveAll && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => approveRun.mutate(run.id)}
            disabled={approveRun.isPending}
          >
            {approveRun.isPending ? (
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
            ) : (
              <CheckCheck size={14} aria-hidden="true" />
            )}
            Aprovar todas ({generated})
          </Button>
        )}

        {/* Recalculate timeline with rate limits */}
        {allGenerated && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetchTimeline()}
            disabled={timelineLoading}
          >
            {timelineLoading ? (
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
            ) : (
              <Clock size={14} aria-hidden="true" />
            )}
            Recalcular timeline
          </Button>
        )}

        {/* Start cadence from sandbox */}
        {canStart && (
          <Button
            size="sm"
            onClick={() => startFromSandbox.mutate(run.id)}
            disabled={startFromSandbox.isPending}
            className="bg-(--success) hover:bg-(--success)/90"
          >
            {startFromSandbox.isPending ? (
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
            ) : (
              <Rocket size={14} aria-hidden="true" />
            )}
            {startFromSandbox.isPending ? "Iniciando…" : "Aprovar e iniciar cadência"}
          </Button>
        )}
      </div>
    </div>
  )
}

function StatPill({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof FileText
  label: string
  value: number
  color?: string
}) {
  return (
    <div className="flex items-center gap-1">
      <Icon size={12} className={color ?? "text-(--text-tertiary)"} aria-hidden="true" />
      <span className="text-(--text-secondary)">{label}:</span>
      <span className={`font-semibold ${color ?? "text-(--text-primary)"}`}>{value}</span>
    </div>
  )
}
