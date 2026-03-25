"use client"

import { useState } from "react"
import {
  useRegenerateStep,
  useApproveStep,
  useRejectStep,
  useSimulateReply,
  type SandboxStep,
} from "@/lib/api/hooks/use-sandbox"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Check,
  X,
  RefreshCw,
  MessageSquareReply,
  Loader2,
  Volume2,
  Mail,
  Linkedin,
  AlertTriangle,
  Clock,
  Send,
} from "lucide-react"
import { channelLabel, intentConfig } from "@/lib/utils"

interface SandboxStepCardProps {
  step: SandboxStep
}

const STATUS_BADGE: Record<
  string,
  { label: string; variant: "default" | "success" | "warning" | "danger" | "info" | "neutral" }
> = {
  pending: { label: "Pendente", variant: "neutral" },
  generating: { label: "Gerando…", variant: "info" },
  generated: { label: "Gerado", variant: "default" },
  approved: { label: "Aprovado", variant: "success" },
  rejected: { label: "Rejeitado", variant: "danger" },
}

const CHANNEL_ICON: Record<string, typeof Mail> = {
  linkedin_connect: Linkedin,
  linkedin_dm: Linkedin,
  email: Mail,
}

export function SandboxStepCard({ step }: SandboxStepCardProps) {
  const regenerate = useRegenerateStep()
  const approve = useApproveStep()
  const reject = useRejectStep()
  const simulateReply = useSimulateReply()

  const [replyMode, setReplyMode] = useState<"auto" | "manual" | null>(null)
  const [manualReply, setManualReply] = useState("")

  const status = STATUS_BADGE[step.status as keyof typeof STATUS_BADGE] ?? {
    label: step.status,
    variant: "neutral" as const,
  }
  const ChannelIcon = CHANNEL_ICON[step.channel] ?? Mail

  const leadName = step.fictitious_lead_data?.name ?? "Lead"
  const leadCompany = step.fictitious_lead_data?.company ?? ""

  function handleSimulateReply() {
    if (!replyMode) return
    simulateReply.mutate({
      stepId: step.id,
      mode: replyMode,
      ...(replyMode === "manual" ? { reply_text: manualReply } : {}),
    })
  }

  return (
    <div className="rounded-md border border-(--border-default) bg-(--bg-surface) p-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ChannelIcon size={14} className="text-(--text-tertiary)" aria-hidden="true" />
          <span className="text-xs font-semibold text-(--text-tertiary)">
            PASSO {step.step_number}
          </span>
          <span className="text-xs text-(--text-disabled)">·</span>
          <span className="text-xs text-(--text-secondary)">{channelLabel(step.channel)}</span>
          <span className="text-xs text-(--text-disabled)">·</span>
          <span className="text-xs text-(--text-secondary)">Dia {step.day_offset}</span>
        </div>
        <Badge variant={status.variant}>{status.label}</Badge>
      </div>

      {/* Lead info */}
      <p className="mt-2 text-xs text-(--text-secondary)">
        Para: <span className="font-medium text-(--text-primary)">{leadName}</span>
        {leadCompany && <span className="text-(--text-tertiary)"> · {leadCompany}</span>}
      </p>

      {/* Email subject */}
      {step.email_subject && (
        <p className="mt-1 text-xs text-(--text-tertiary)">
          Assunto: <span className="italic">{step.email_subject}</span>
        </p>
      )}

      {/* Message content */}
      {step.message_content ? (
        <div className="mt-3 rounded-md bg-(--bg-overlay) p-3">
          <p className="whitespace-pre-wrap text-sm text-(--text-primary)">
            {step.message_content}
          </p>
        </div>
      ) : step.status === "pending" ? (
        <p className="mt-3 text-xs italic text-(--text-disabled)">
          Mensagem será gerada ao clicar em &quot;Gerar todas&quot;
        </p>
      ) : null}

      {/* Audio preview */}
      {step.audio_preview_url && (
        <div className="mt-2 flex items-center gap-2">
          <Volume2 size={14} className="text-(--text-tertiary)" aria-hidden="true" />
          <audio controls src={step.audio_preview_url} className="h-8 flex-1" preload="none">
            <track kind="captions" />
          </audio>
        </div>
      )}

      {/* Rate limit warning */}
      {step.is_rate_limited && (
        <div className="mt-2 flex items-center gap-2 rounded-md bg-(--warning-subtle) px-3 py-2 text-xs text-(--warning-subtle-fg)">
          <AlertTriangle size={14} aria-hidden="true" />
          <div>
            <span className="font-medium">Rate limit atingido</span>
            {step.rate_limit_reason && (
              <span className="text-(--text-secondary)"> — {step.rate_limit_reason}</span>
            )}
            {step.adjusted_scheduled_at && (
              <p className="mt-0.5">
                <Clock size={11} className="mr-1 inline" aria-hidden="true" />
                Reagendado: {new Date(step.adjusted_scheduled_at).toLocaleString("pt-BR")}
              </p>
            )}
          </div>
        </div>
      )}

      {/* LLM Info */}
      {step.llm_provider && (
        <p className="mt-2 text-[11px] text-(--text-disabled)">
          {step.llm_provider}/{step.llm_model} · {step.tokens_in ?? 0}+{step.tokens_out ?? 0} tokens
        </p>
      )}

      {/* Simulated Reply */}
      {step.simulated_reply && (
        <div className="mt-3 rounded-md border border-(--border-subtle) bg-(--bg-overlay) p-3">
          <div className="mb-1 flex items-center gap-2">
            <MessageSquareReply size={12} className="text-(--text-tertiary)" aria-hidden="true" />
            <span className="text-xs font-medium text-(--text-secondary)">Resposta simulada</span>
            {step.simulated_intent && (
              <Badge variant={intentConfig(step.simulated_intent).variant}>
                {intentConfig(step.simulated_intent).label}
                {step.simulated_confidence != null && (
                  <span className="ml-1 opacity-70">
                    {Math.round(step.simulated_confidence * 100)}%
                  </span>
                )}
              </Badge>
            )}
          </div>
          <p className="whitespace-pre-wrap text-sm text-(--text-primary)">
            {step.simulated_reply}
          </p>
          {step.simulated_reply_summary && (
            <p className="mt-1 text-xs italic text-(--text-tertiary)">
              {step.simulated_reply_summary}
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      {step.status === "generated" && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => approve.mutate(step.id)}
            disabled={approve.isPending}
          >
            <Check size={12} aria-hidden="true" />
            Aprovar
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => reject.mutate(step.id)}
            disabled={reject.isPending}
          >
            <X size={12} aria-hidden="true" />
            Rejeitar
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => regenerate.mutate({ stepId: step.id })}
            disabled={regenerate.isPending}
          >
            {regenerate.isPending ? (
              <Loader2 size={12} className="animate-spin" aria-hidden="true" />
            ) : (
              <RefreshCw size={12} aria-hidden="true" />
            )}
            Regenerar
          </Button>

          {/* Reply simulation toggle */}
          {!step.simulated_reply && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setReplyMode(replyMode ? null : "auto")}
            >
              <MessageSquareReply size={12} aria-hidden="true" />
              Simular resposta
            </Button>
          )}
        </div>
      )}

      {/* Reply simulation form */}
      {replyMode && !step.simulated_reply && (
        <div className="mt-3 space-y-2 rounded-md border border-dashed border-(--border-default) p-3">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setReplyMode("auto")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                replyMode === "auto"
                  ? "bg-(--accent) text-white"
                  : "bg-(--bg-overlay) text-(--text-secondary) hover:bg-(--bg-surface)"
              }`}
            >
              Automática (IA)
            </button>
            <button
              type="button"
              onClick={() => setReplyMode("manual")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                replyMode === "manual"
                  ? "bg-(--accent) text-white"
                  : "bg-(--bg-overlay) text-(--text-secondary) hover:bg-(--bg-surface)"
              }`}
            >
              Manual
            </button>
          </div>

          {replyMode === "manual" && (
            <textarea
              value={manualReply}
              onChange={(e) => setManualReply(e.target.value)}
              placeholder="Digite a resposta simulada do lead…"
              rows={2}
              className="w-full resize-none rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) placeholder:text-(--text-tertiary) focus:border-(--accent) focus:outline-none"
            />
          )}

          <Button
            size="sm"
            onClick={handleSimulateReply}
            disabled={simulateReply.isPending || (replyMode === "manual" && !manualReply.trim())}
          >
            {simulateReply.isPending ? (
              <Loader2 size={12} className="animate-spin" aria-hidden="true" />
            ) : (
              <Send size={12} aria-hidden="true" />
            )}
            {replyMode === "auto" ? "Gerar resposta via IA" : "Classificar resposta"}
          </Button>
        </div>
      )}
    </div>
  )
}
