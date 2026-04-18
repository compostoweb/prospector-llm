"use client"

import { memo } from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import {
  Mail,
  Linkedin,
  Music,
  Volume2,
  MousePointerClick,
  MessageSquare,
  ClipboardList,
  FileText,
  Copy,
  Trash2,
  ChevronUp,
  ChevronDown,
  AlertCircle,
} from "lucide-react"
import type { CadenceChannel, StepType } from "@/lib/api/hooks/use-cadences"
import { cn } from "@/lib/utils"

export interface StepNodeData {
  index: number
  channel: CadenceChannel
  stepType: StepType | null
  dayOffset: number
  messageTemplate: string
  manualTaskType: string | null
  manualTaskDetail: string | null
  audioFileId: string | null
  emailTemplateId: string | null
  useVoice: boolean
  isSelected: boolean
  isInvalid: boolean
  invalidReason: string | null
  isFirst: boolean
  isLast: boolean
  totalSteps: number
  onSelect: (index: number) => void
  onDelete: (index: number) => void
  onDuplicate: (index: number) => void
  onMoveUp: (index: number) => void
  onMoveDown: (index: number) => void
}

// Paleta estática por canal (Tailwind classes)
const CHANNEL_CONFIG: Record<
  CadenceChannel,
  {
    label: string
    pillBg: string
    pillText: string
    pillBorder: string
    panelBg: string
    panelBorder: string
    accentWash: string
    badgeColor: string
    icon: React.ReactNode
  }
> = {
  linkedin_connect: {
    label: "Connect",
    pillBg: "bg-blue-100",
    pillText: "text-blue-700",
    pillBorder: "border-blue-200",
    panelBg: "bg-blue-50/80",
    panelBorder: "border-blue-100",
    accentWash: "from-blue-100 via-blue-50/70 to-white",
    badgeColor: "bg-blue-500",
    icon: <Linkedin size={11} className="shrink-0" />,
  },
  linkedin_dm: {
    label: "DM",
    pillBg: "bg-blue-100",
    pillText: "text-blue-700",
    pillBorder: "border-blue-200",
    panelBg: "bg-blue-50/80",
    panelBorder: "border-blue-100",
    accentWash: "from-blue-100 via-blue-50/70 to-white",
    badgeColor: "bg-blue-500",
    icon: <MessageSquare size={11} className="shrink-0" />,
  },
  linkedin_post_reaction: {
    label: "Reação",
    pillBg: "bg-blue-100",
    pillText: "text-blue-700",
    pillBorder: "border-blue-200",
    panelBg: "bg-blue-50/80",
    panelBorder: "border-blue-100",
    accentWash: "from-blue-100 via-blue-50/70 to-white",
    badgeColor: "bg-blue-500",
    icon: <MousePointerClick size={11} className="shrink-0" />,
  },
  linkedin_post_comment: {
    label: "Comentário",
    pillBg: "bg-blue-100",
    pillText: "text-blue-700",
    pillBorder: "border-blue-200",
    panelBg: "bg-blue-50/80",
    panelBorder: "border-blue-100",
    accentWash: "from-blue-100 via-blue-50/70 to-white",
    badgeColor: "bg-blue-500",
    icon: <MessageSquare size={11} className="shrink-0" />,
  },
  linkedin_inmail: {
    label: "InMail",
    pillBg: "bg-blue-100",
    pillText: "text-blue-700",
    pillBorder: "border-blue-200",
    panelBg: "bg-blue-50/80",
    panelBorder: "border-blue-100",
    accentWash: "from-blue-100 via-blue-50/70 to-white",
    badgeColor: "bg-blue-500",
    icon: <Linkedin size={11} className="shrink-0" />,
  },
  email: {
    label: "E-mail",
    pillBg: "bg-emerald-100",
    pillText: "text-emerald-700",
    pillBorder: "border-emerald-200",
    panelBg: "bg-emerald-50/80",
    panelBorder: "border-emerald-100",
    accentWash: "from-emerald-100 via-emerald-50/70 to-white",
    badgeColor: "bg-emerald-500",
    icon: <Mail size={11} className="shrink-0" />,
  },
  manual_task: {
    label: "Tarefa",
    pillBg: "bg-amber-100",
    pillText: "text-amber-700",
    pillBorder: "border-amber-200",
    panelBg: "bg-amber-50/80",
    panelBorder: "border-amber-100",
    accentWash: "from-amber-100 via-amber-50/70 to-white",
    badgeColor: "bg-amber-500",
    icon: <ClipboardList size={11} className="shrink-0" />,
  },
}

const STEP_TYPE_LABELS: Partial<Record<StepType, string>> = {
  linkedin_connect: "Convite",
  linkedin_dm_first: "1ª abordagem",
  linkedin_dm_post_connect: "Pós-conexão",
  linkedin_dm_post_connect_voice: "Pós-conexão voz",
  linkedin_dm_voice: "DM com voz",
  linkedin_dm_followup: "Follow-up",
  linkedin_dm_breakup: "Breakup",
  linkedin_post_reaction: "Curtir post",
  linkedin_post_comment: "Comentar post",
  linkedin_inmail: "InMail",
  email_first: "Cold mail",
  email_followup: "Follow-up",
  email_breakup: "Breakup",
}

function truncate(text: string, max: number): string {
  if (!text) return ""
  return text.length > max ? text.slice(0, max) + "…" : text
}

function stopEvent(event: React.MouseEvent): void {
  event.stopPropagation()
}

export const StepNode = memo(function StepNode({ data }: NodeProps) {
  const d = data as unknown as StepNodeData
  const cfg = CHANNEL_CONFIG[d.channel] ?? CHANNEL_CONFIG.email
  const stepTypeLabel = d.stepType ? STEP_TYPE_LABELS[d.stepType] : null
  const hasManualText = d.messageTemplate.trim().length > 0
  const hasManualTaskDetail = (d.manualTaskDetail ?? "").trim().length > 0
  const supportingLabel = d.useVoice
    ? d.audioFileId
      ? "Audio gravado selecionado"
      : hasManualText
        ? "Mensagem via TTS"
        : "Audio sera gerado automaticamente"
    : d.channel === "manual_task"
      ? d.manualTaskType
        ? `Tarefa: ${d.manualTaskType}`
        : "Tarefa manual"
      : d.emailTemplateId
        ? "Template salvo"
        : hasManualText
          ? "Conteudo manual"
          : "Conteudo automatico"

  const previewText =
    d.channel === "manual_task"
      ? d.manualTaskDetail || null
      : d.useVoice && d.audioFileId
        ? "Audio gravado pronto para envio"
        : d.messageTemplate
          ? truncate(d.messageTemplate, 110)
          : d.emailTemplateId
            ? "Template salvo selecionado"
            : null

  const statusBadges = [
    d.channel.startsWith("linkedin")
      ? {
          key: "linkedin",
          label: "LinkedIn",
          icon: <Linkedin size={10} />,
          className: "border-blue-200 bg-blue-50 text-blue-700",
        }
      : null,
    d.useVoice
      ? {
          key: "audio",
          label: d.audioFileId ? "Gravado" : "TTS",
          icon: d.audioFileId ? <Music size={10} /> : <Volume2 size={10} />,
          className: "border-sky-200 bg-sky-50 text-sky-700",
          title: d.audioFileId
            ? "Este passo usa um audio gravado da biblioteca."
            : "Este passo usa TTS: o texto vira audio na hora do envio.",
        }
      : null,
    d.useVoice && d.audioFileId
      ? null
      : d.channel === "manual_task" && d.manualTaskType
        ? {
            key: "manual-task-type",
            label: d.manualTaskType,
            icon: <ClipboardList size={10} />,
            className: "border-amber-200 bg-amber-50 text-amber-700",
            title: hasManualTaskDetail
              ? (d.manualTaskDetail ?? undefined)
              : "Tipo operacional desta tarefa manual.",
          }
        : d.emailTemplateId
          ? {
              key: "template",
              label: "Template",
              icon: <FileText size={10} />,
              className: "border-emerald-200 bg-emerald-50 text-emerald-700",
              title: "O conteudo deste passo vem de um template salvo.",
            }
          : hasManualText
            ? {
                key: "texto",
                label: "Texto",
                icon: <FileText size={10} />,
                className: "border-slate-200 bg-white text-slate-600",
                title: d.useVoice
                  ? "Este texto sera usado como roteiro para gerar o audio via TTS."
                  : "Este passo usa texto configurado manualmente.",
              }
            : null,
    d.isInvalid
      ? {
          key: "alerta",
          label: "Alerta",
          icon: <AlertCircle size={10} />,
          className: "border-rose-200 bg-rose-50 text-rose-600",
          title: d.invalidReason ?? "Este passo requer atencao.",
        }
      : null,
  ].filter(Boolean) as Array<{
    key: string
    label: string
    icon: React.ReactNode
    className: string
    title?: string
  }>

  return (
    <div
      className={cn(
        "group relative w-100 cursor-grab overflow-visible rounded-[28px] bg-white transition-all duration-200 active:cursor-grabbing",
        "border",
        d.isSelected
          ? "border-blue-400 ring-4 ring-blue-100/70 shadow-xl shadow-blue-100/80"
          : "border-slate-200 shadow-lg shadow-slate-900/5 hover:border-slate-300 hover:shadow-xl",
      )}
    >
      <div
        className={cn(
          "pointer-events-none absolute inset-x-0 top-0 h-16 rounded-t-[28px] bg-linear-to-b",
          cfg.accentWash,
        )}
      />

      {/* Handle topo */}
      <Handle
        type="target"
        position={Position.Top}
        className="h-2.5! w-2.5! rounded-full! border-2! border-white! bg-gray-300!"
        style={{ top: -5 }}
      />

      {/* Drag handle strip — faixa fina para arrastar */}
      <div
        className="step-drag-handle relative z-10 flex cursor-grab justify-center rounded-t-[28px] pt-2.5 pb-1 active:cursor-grabbing select-none"
        title="Arraste para reposicionar"
      >
        <div className="flex gap-1">
          <div className="h-1.5 w-1.5 rounded-full bg-slate-300" />
          <div className="h-1.5 w-1.5 rounded-full bg-slate-300" />
          <div className="h-1.5 w-1.5 rounded-full bg-slate-300" />
          <div className="h-1.5 w-1.5 rounded-full bg-slate-300" />
          <div className="h-1.5 w-1.5 rounded-full bg-slate-300" />
          <div className="h-1.5 w-1.5 rounded-full bg-slate-300" />
        </div>
      </div>

      {/* Canal pill + número */}
      <div className="relative z-10 flex items-start justify-between px-5 pb-2">
        <div
          className={cn(
            "flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[13px] font-semibold shadow-sm",
            cfg.pillBg,
            cfg.pillText,
            cfg.pillBorder,
          )}
        >
          {cfg.icon}
          {cfg.label}
        </div>

        <span
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-full text-[16px] font-bold text-white ring-4 ring-white shadow-sm",
            cfg.badgeColor,
          )}
        >
          {d.index + 1}
        </span>
      </div>

      {/* Preview — clicável para abrir editor */}
      <div
        className="relative z-10 w-full px-5 pb-5 text-left"
        aria-label={`Editar passo ${d.index + 1}: ${cfg.label}`}
      >
        <div
          className={cn(
            "relative min-h-19 rounded-[22px] border px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]",
            cfg.panelBg,
            cfg.panelBorder,
          )}
        >
          <div className="absolute right-3 top-3 flex flex-col items-end gap-1.5">
            {statusBadges.map((badge) => (
              <span key={badge.key} className="group/badge relative">
                <span
                  title={badge.key === "alerta" ? undefined : badge.title}
                  aria-label={badge.title ?? badge.label}
                  tabIndex={badge.key === "alerta" ? 0 : undefined}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[10px] font-semibold shadow-sm backdrop-blur-sm outline-none",
                    badge.className,
                    badge.key === "alerta" &&
                      "cursor-help focus-visible:ring-2 focus-visible:ring-rose-200 focus-visible:ring-offset-2 focus-visible:ring-offset-white",
                  )}
                >
                  {badge.icon}
                  {badge.label}
                </span>

                {badge.key === "alerta" && badge.title ? (
                  <span className="pointer-events-none absolute right-[calc(100%+0.65rem)] top-1/2 z-30 w-60 -translate-y-1/2 translate-x-2 rounded-2xl border border-rose-200 bg-white/96 px-3 py-2.5 text-left text-[11px] font-medium leading-relaxed text-slate-700 opacity-0 shadow-xl shadow-rose-100/70 ring-1 ring-white/80 transition-all duration-150 group-hover/badge:translate-x-0 group-hover/badge:opacity-100 group-focus-within/badge:translate-x-0 group-focus-within/badge:opacity-100">
                    <span className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-rose-500">
                      <AlertCircle size={10} />
                      Atenção neste passo
                    </span>
                    <span className="block">{badge.title}</span>
                    <span className="absolute -right-1 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rotate-45 border-r border-b border-rose-200 bg-white/96" />
                  </span>
                ) : null}
              </span>
            ))}
          </div>

          {stepTypeLabel && (
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold",
                cfg.pillBg,
                cfg.pillText,
              )}
            >
              {stepTypeLabel}
            </span>
          )}

          {previewText ? (
            <p className="mt-2 pr-28 text-[15px] leading-[1.28] font-semibold tracking-[-0.02em] text-slate-700">
              {previewText}
            </p>
          ) : (
            <div className="mt-1.5 space-y-1">
              <p className="pr-28 text-[15px] font-medium italic leading-tight text-slate-500">
                Clique para configurar...
              </p>
              <p className="pr-28 text-[11px] font-medium text-slate-400">
                Defina conteudo, audio e configuracoes do passo
              </p>
            </div>
          )}

          <p className="mt-2 text-[12px] font-semibold text-slate-500">{supportingLabel}</p>
        </div>
      </div>

      {/* Ações — dentro do card para não serem cortadas no hover */}
      <div className="nodrag absolute -bottom-4 right-4 z-20 flex items-center gap-0.5 rounded-full border border-gray-200 bg-white/95 px-1.5 py-1 shadow-sm backdrop-blur-sm opacity-0 transition-opacity duration-150 group-hover:opacity-100">
        <button
          type="button"
          disabled={d.isFirst}
          onClick={(event) => {
            stopEvent(event)
            d.onMoveUp(d.index)
          }}
          className="nodrag rounded-full p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30"
          aria-label="Mover passo para cima"
          title="Mover para cima"
        >
          <ChevronUp size={12} />
        </button>
        <button
          type="button"
          disabled={d.isLast}
          onClick={(event) => {
            stopEvent(event)
            d.onMoveDown(d.index)
          }}
          className="nodrag rounded-full p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30"
          aria-label="Mover passo para baixo"
          title="Mover para baixo"
        >
          <ChevronDown size={12} />
        </button>
        <div className="mx-0.5 h-3 w-px bg-gray-200" />
        <button
          type="button"
          onClick={(event) => {
            stopEvent(event)
            d.onDuplicate(d.index)
          }}
          className="nodrag rounded-full p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          aria-label="Duplicar passo"
          title="Duplicar"
        >
          <Copy size={12} />
        </button>
        <button
          type="button"
          onClick={(event) => {
            stopEvent(event)
            d.onDelete(d.index)
          }}
          className="nodrag rounded-full p-1 text-gray-400 transition-colors hover:bg-rose-50 hover:text-rose-500"
          aria-label="Remover passo"
          title="Remover"
        >
          <Trash2 size={12} />
        </button>
      </div>

      {/* Handle base */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="h-2.5! w-2.5! rounded-full! border-2! border-white! bg-gray-300!"
        style={{ bottom: -5 }}
      />
    </div>
  )
})
