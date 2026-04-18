import { formatRelativeTime } from "@/lib/utils"
import { BadgeIntent } from "@/components/shared/badge-intent"
import { BadgeChannel } from "@/components/shared/badge-channel"
import { EmptyState } from "@/components/shared/empty-state"
import { ClipboardList, Clock } from "lucide-react"
import type { LeadStep } from "@/lib/api/hooks/use-leads"

const stepStatusLabel: Record<LeadStep["status"], string> = {
  pending: "Agendado",
  sent: "Enviado",
  replied: "Respondido",
  skipped: "Ignorado",
  failed: "Falhou",
  content_generated: "Conteúdo gerado",
  done_external: "Executado fora do sistema",
}

const stepStatusClass: Record<LeadStep["status"], string> = {
  pending: "bg-(--neutral-subtle) text-(--neutral-subtle-fg)",
  sent: "bg-(--info-subtle) text-(--info-subtle-fg)",
  replied: "bg-(--success-subtle) text-(--success-subtle-fg)",
  skipped: "bg-(--neutral-subtle) text-(--text-disabled)",
  failed: "bg-(--danger-subtle) text-(--danger-subtle-fg)",
  content_generated: "bg-(--info-subtle) text-(--info-subtle-fg)",
  done_external: "bg-(--success-subtle) text-(--success-subtle-fg)",
}

const manualTaskTypeLabel: Record<string, string> = {
  call: "Ligação",
  linkedin_post_comment: "Comentário em post",
  whatsapp: "WhatsApp",
  other: "Outro",
}

interface LeadTimelineProps {
  steps: LeadStep[]
  isLoading?: boolean
}

export function LeadTimeline({ steps, isLoading }: LeadTimelineProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <div className="h-8 w-8 animate-pulse rounded-full bg-(--bg-overlay)" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-32 animate-pulse rounded bg-(--bg-overlay)" />
              <div className="h-12 animate-pulse rounded bg-(--bg-overlay)" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (steps.length === 0) {
    return (
      <EmptyState
        icon={Clock}
        title="Nenhuma atividade ainda"
        description="Os passos da cadência aparecem aqui"
      />
    )
  }

  return (
    <ol className="space-y-4">
      {steps.map((step, index) => (
        <li key={step.id} className="flex gap-3">
          {/* Linha vertical */}
          <div className="flex flex-col items-center">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${stepStatusClass[step.status]}`}
            >
              {step.step_number}
            </div>
            {index < steps.length - 1 && <div className="mt-1 h-full w-px bg-(--border-subtle)" />}
          </div>

          {/* Conteúdo */}
          <div className="min-w-0 flex-1 pb-4">
            <div className="flex flex-wrap items-center gap-2">
              <BadgeChannel channel={step.channel} />
              {step.item_kind === "manual_task" && (
                <span className="inline-flex items-center gap-1 rounded-(--radius-full) border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                  <ClipboardList size={11} aria-hidden="true" />
                  {step.manual_task_type
                    ? (manualTaskTypeLabel[step.manual_task_type] ?? step.manual_task_type)
                    : "Tarefa manual"}
                </span>
              )}
              <span
                className={`inline-flex rounded-(--radius-full) px-2 py-0.5 text-xs font-medium ${stepStatusClass[step.status]}`}
              >
                {stepStatusLabel[step.status]}
              </span>
              {step.sent_at && (
                <time dateTime={step.sent_at} className="text-xs text-(--text-tertiary)">
                  {formatRelativeTime(step.sent_at)}
                </time>
              )}
            </div>

            {step.message_content && (
              <div className="mt-2 rounded-md border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2">
                {step.item_kind === "manual_task" && (
                  <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-(--text-tertiary)">
                    Descrição da tarefa
                  </p>
                )}
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-(--text-secondary)">
                  {step.message_content}
                </p>
              </div>
            )}

            {step.item_kind === "manual_task" && step.notes && (
              <div className="mt-2 rounded-md border border-amber-100 bg-amber-50 px-3 py-2">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-amber-700">
                  Observações da execução
                </p>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-amber-800">
                  {step.notes}
                </p>
              </div>
            )}

            {step.reply_content && (
              <div className="mt-2 rounded-md border border-(--success-subtle) bg-(--success-subtle) px-3 py-2">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-(--success-subtle-fg)">
                  Resposta
                </p>
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-(--text-secondary)">
                  {step.reply_content}
                </p>
                {step.intent && (
                  <div className="mt-2">
                    <BadgeIntent intent={step.intent} />
                  </div>
                )}
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
