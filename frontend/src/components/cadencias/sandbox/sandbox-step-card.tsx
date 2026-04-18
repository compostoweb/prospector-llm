"use client"

import { useState } from "react"
import {
  useRegenerateStep,
  useApproveStep,
  useRejectStep,
  useSendSandboxStepTestEmail,
  useSimulateReply,
  type SandboxStep,
} from "@/lib/api/hooks/use-sandbox"
import type { TestEmailTransportSummary } from "@/lib/cadences/test-email-transport"
import { buildTestEmailSuccessMessage } from "@/lib/cadences/test-email-transport"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SendTestEmailDialog } from "@/components/cadencias/send-test-email-dialog"
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
import { toast } from "sonner"

interface SandboxStepCardProps {
  step: SandboxStep
  emailTransportSummary: TestEmailTransportSummary
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

const STEP_TYPE_LABELS: Record<string, string> = {
  linkedin_connect: "Convite de Conexão",
  linkedin_dm_first: "Primeira abordagem",
  linkedin_dm_post_connect: "Pós-conexão",
  linkedin_dm_post_connect_voice: "Pós-conexão com áudio",
  linkedin_dm_voice: "DM com áudio",
  linkedin_dm_followup: "Follow-up",
  linkedin_dm_breakup: "Despedida",
  email_first: "Primeiro e-mail",
  email_followup: "Follow-up",
  email_breakup: "Despedida",
}

const GENERATION_MODE_LABELS: Record<string, string> = {
  llm: "Gerado por IA",
  message_template: "Template fixo da etapa",
  email_template: "Template salvo de e-mail",
}

const UNATTRIBUTED_SOURCE_PATTERN =
  /\b(um estudo recente|uma pesquisa recente|um levantamento recente|um relatório recente|dados recentes mostram|um estudo sobre|pesquisas recentes mostram|estudos recentes mostram)\b/i

export function SandboxStepCard({ step, emailTransportSummary }: SandboxStepCardProps) {
  const regenerate = useRegenerateStep()
  const approve = useApproveStep()
  const reject = useRejectStep()
  const simulateReply = useSimulateReply()
  const sendTestEmail = useSendSandboxStepTestEmail()

  const [replyMode, setReplyMode] = useState<"auto" | "manual" | null>(null)
  const [manualReply, setManualReply] = useState("")
  const [testEmailOpen, setTestEmailOpen] = useState(false)

  const status = STATUS_BADGE[step.status as keyof typeof STATUS_BADGE] ?? {
    label: step.status,
    variant: "neutral" as const,
  }
  const ChannelIcon = CHANNEL_ICON[step.channel] ?? Mail
  const compositionContext = step.composition_context
  const editorialValidation = compositionContext?.editorial_validation

  const leadName = step.lead_name ?? step.fictitious_lead_data?.name ?? "Lead"
  const leadCompany = step.lead_company ?? step.fictitious_lead_data?.company ?? ""
  const leadJobTitle = step.lead_job_title ?? step.fictitious_lead_data?.job_title ?? ""
  const hasClientSourceWarning = Boolean(
    step.message_content &&
    UNATTRIBUTED_SOURCE_PATTERN.test(step.message_content) &&
    !compositionContext?.source_company_news_preview,
  )

  function handleSimulateReply() {
    if (!replyMode) return
    simulateReply.mutate({
      stepId: step.id,
      mode: replyMode,
      ...(replyMode === "manual" ? { reply_text: manualReply } : {}),
    })
  }

  function handleSendTestEmail(toEmail: string) {
    sendTestEmail.mutate(
      {
        stepId: step.id,
        to_email: toEmail,
      },
      {
        onSuccess: (result) => {
          setTestEmailOpen(false)
          toast.success(
            buildTestEmailSuccessMessage({
              toEmail: result.to_email,
              summary: emailTransportSummary,
              providerType: result.provider_type,
            }),
          )
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : "Falha ao enviar teste")
        },
      },
    )
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
          {step.step_type && STEP_TYPE_LABELS[step.step_type] && (
            <>
              <span className="text-xs text-(--text-disabled)">·</span>
              <Badge variant="info" className="text-[10px] px-1.5 py-0">
                {STEP_TYPE_LABELS[step.step_type]}
              </Badge>
            </>
          )}
          {step.use_voice && (
            <>
              <span className="text-xs text-(--text-disabled)">·</span>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600">
                <Volume2 size={12} aria-hidden="true" />
                Áudio
              </span>
            </>
          )}
          <span className="text-xs text-(--text-disabled)">·</span>
          <span className="text-xs text-(--text-secondary)">Dia {step.day_offset}</span>
        </div>
        <Badge variant={status.variant}>{status.label}</Badge>
      </div>

      {/* Lead info */}
      <p className="mt-2 text-xs text-(--text-secondary)">
        Para: <span className="font-medium text-(--text-primary)">{leadName}</span>
        {leadCompany && <span className="text-(--text-tertiary)"> · {leadCompany}</span>}
        {leadJobTitle && <span className="text-(--text-tertiary)"> · {leadJobTitle}</span>}
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

      {compositionContext && (
        <div className="mt-3 rounded-md border border-(--border-subtle) bg-(--bg-overlay) p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--text-tertiary)">
              Composição
            </span>
            <Badge variant="info">
              {GENERATION_MODE_LABELS[compositionContext.generation_mode] ??
                compositionContext.generation_mode}
            </Badge>
            {compositionContext.copy_method && (
              <Badge variant="default">Método {compositionContext.copy_method}</Badge>
            )}
            <Badge variant={compositionContext.few_shot_applied ? "success" : "neutral"}>
              {compositionContext.few_shot_applied ? "Few-shot ativo" : "Sem few-shot"}
            </Badge>
          </div>

          <div className="mt-2 space-y-1 text-xs text-(--text-secondary)">
            {(compositionContext.playbook_sector || compositionContext.playbook_role) && (
              <p>
                Playbook: {compositionContext.playbook_sector ?? "setor livre"}
                {compositionContext.playbook_role ? ` · ${compositionContext.playbook_role}` : ""}
              </p>
            )}
            {compositionContext.matched_role && (
              <p>
                Cargo usado no few-shot: {compositionContext.matched_role}
                {compositionContext.few_shot_method
                  ? ` · ${compositionContext.few_shot_method}`
                  : ""}
              </p>
            )}
            <p>
              Sinais:{" "}
              {compositionContext.has_site_summary
                ? "site/contexto externo"
                : "sem pesquisa externa"}
              {compositionContext.has_recent_posts
                ? " · posts recentes do lead"
                : " · sem posts recentes"}
            </p>
            {compositionContext.source_site_summary_preview && (
              <p>Pesquisa da empresa: {compositionContext.source_site_summary_preview}</p>
            )}
            {compositionContext.source_recent_posts_preview && (
              <p>Posts usados: {compositionContext.source_recent_posts_preview}</p>
            )}
            {compositionContext.source_company_news_preview && (
              <p>Fonte externa nomeada: {compositionContext.source_company_news_preview}</p>
            )}
          </div>

          {(editorialValidation?.issues.length || hasClientSourceWarning) && (
            <div className="mt-3 rounded-md border border-(--warning-subtle-fg) bg-(--warning-subtle) px-3 py-2 text-xs text-(--warning-subtle-fg)">
              <p className="font-medium">Atenção editorial</p>
              {editorialValidation?.issues.map((issue) => (
                <p key={`${step.id}-${issue.code}`} className="mt-1">
                  {issue.message}
                </p>
              ))}
              {!editorialValidation?.issues.length && hasClientSourceWarning && (
                <p className="mt-1">
                  O texto menciona estudo ou dado externo sem fonte explícita no contexto salvo
                  deste step.
                </p>
              )}
            </div>
          )}
        </div>
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
      {(step.status === "generated" || (step.channel === "email" && step.message_content)) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {step.status === "generated" && (
            <>
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
            </>
          )}

          {step.channel === "email" && step.message_content && (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setTestEmailOpen(true)}
                disabled={sendTestEmail.isPending}
                className="shrink-0"
              >
                {sendTestEmail.isPending ? (
                  <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                ) : (
                  <Mail size={12} aria-hidden="true" />
                )}
                Enviar teste por e-mail
              </Button>

              {/* Badge informativo ao lado do botão enviar teste por e-mail
              
              <div className="min-w-0 flex-1 rounded-md border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2 text-[11px] text-(--text-secondary)">
                <p className="font-medium text-(--text-primary)">
                  Conta do teste: {emailTransportSummary.shortLabel}
                </p>
                <p className="mt-1">{emailTransportSummary.hint}</p>
              </div> */}
            </div>
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

      <SendTestEmailDialog
        open={testEmailOpen}
        onOpenChange={setTestEmailOpen}
        onSubmit={handleSendTestEmail}
        isPending={sendTestEmail.isPending}
        contextLabel={`Passo ${step.step_number} · ${leadName}`}
        subjectPreview={step.email_subject}
        suggestedEmails={step.fictitious_lead_data?.email ? [step.fictitious_lead_data.email] : []}
        transportLabel={emailTransportSummary.label}
        transportHint={emailTransportSummary.hint}
      />
    </div>
  )
}
