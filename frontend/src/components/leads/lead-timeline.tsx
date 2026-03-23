import { formatRelativeTime } from "@/lib/utils"
import { BadgeIntent } from "@/components/shared/badge-intent"
import { BadgeChannel } from "@/components/shared/badge-channel"
import { EmptyState } from "@/components/shared/empty-state"
import { Clock } from "lucide-react"
import type { LeadStep } from "@/lib/api/hooks/use-leads"

const stepStatusLabel: Record<LeadStep["status"], string> = {
  pending: "Agendado",
  sent: "Enviado",
  replied: "Respondido",
  skipped: "Ignorado",
  failed: "Falhou",
}

const stepStatusClass: Record<LeadStep["status"], string> = {
  pending: "bg-[var(--neutral-subtle)] text-[var(--neutral-subtle-fg)]",
  sent: "bg-[var(--info-subtle)] text-[var(--info-subtle-fg)]",
  replied: "bg-[var(--success-subtle)] text-[var(--success-subtle-fg)]",
  skipped: "bg-[var(--neutral-subtle)] text-[var(--text-disabled)]",
  failed: "bg-[var(--danger-subtle)] text-[var(--danger-subtle-fg)]",
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
            <div className="h-8 w-8 animate-pulse rounded-full bg-[var(--bg-overlay)]" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-32 animate-pulse rounded bg-[var(--bg-overlay)]" />
              <div className="h-12 animate-pulse rounded bg-[var(--bg-overlay)]" />
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
            {index < steps.length - 1 && (
              <div className="mt-1 h-full w-px bg-[var(--border-subtle)]" />
            )}
          </div>

          {/* Conteúdo */}
          <div className="min-w-0 flex-1 pb-4">
            <div className="flex flex-wrap items-center gap-2">
              <BadgeChannel channel={step.channel} />
              <span
                className={`inline-flex rounded-[var(--radius-full)] px-2 py-0.5 text-xs font-medium ${stepStatusClass[step.status]}`}
              >
                {stepStatusLabel[step.status]}
              </span>
              {step.sent_at && (
                <time dateTime={step.sent_at} className="text-xs text-[var(--text-tertiary)]">
                  {formatRelativeTime(step.sent_at)}
                </time>
              )}
            </div>

            {step.message_content && (
              <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-overlay)] px-3 py-2">
                <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
                  {step.message_content}
                </p>
              </div>
            )}

            {step.reply_content && (
              <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--success-subtle)] bg-[var(--success-subtle)] px-3 py-2">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[var(--success-subtle-fg)]">
                  Resposta
                </p>
                <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
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
