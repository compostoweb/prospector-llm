import { cn } from "@/lib/utils"

export type ReplyMatchSource =
  | "email_message_id"
  | "unipile_message_id"
  | "provider_thread_id"
  | "email_subject"
  | "email_subject_similar"
  | "fallback_single_cadence"
  | "ambiguous_reply_hold"
  | "manual_review"
  | null

interface ReplyMatchSourceMeta {
  shortLabel: string
  label: string
  description: string
  className: string
}

const REPLY_MATCH_SOURCE_META: Record<Exclude<ReplyMatchSource, null>, ReplyMatchSourceMeta> = {
  email_message_id: {
    shortLabel: "Match por Message-ID",
    label: "Message-ID do email",
    description:
      "O reply trouxe a referência técnica da mensagem enviada. Este é o sinal mais forte.",
    className: "border-(--success) bg-(--success-subtle) text-(--success-subtle-fg)",
  },
  unipile_message_id: {
    shortLabel: "Match por ID do provedor",
    label: "ID bruto do provedor",
    description:
      "O vínculo foi resolvido pelo identificador externo retornado pelo provedor de envio.",
    className: "border-(--success) bg-(--success-subtle) text-(--success-subtle-fg)",
  },
  provider_thread_id: {
    shortLabel: "Match por thread",
    label: "Thread do provedor",
    description:
      "O reply caiu na mesma thread do provedor. É um sinal forte, mas abaixo do Message-ID.",
    className: "border-(--info) bg-(--info-subtle) text-(--info-subtle-fg)",
  },
  email_subject: {
    shortLabel: "Match por assunto",
    label: "Assunto do email",
    description:
      "Sem referências técnicas, o vínculo foi inferido pelo assunto normalizado. É um sinal intermediário.",
    className: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  },
  email_subject_similar: {
    shortLabel: "Match por assunto similar",
    label: "Assunto similar",
    description:
      "Sem referências técnicas, o vínculo foi inferido por assunto muito parecido. Use a auditoria se o lead estiver em múltiplas cadências.",
    className: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  },
  fallback_single_cadence: {
    shortLabel: "Fallback por cadência única",
    label: "Única cadência enviada",
    description:
      "Sem referências técnicas, havia só uma cadência elegível. Trate este vínculo como fraco.",
    className: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  },
  ambiguous_reply_hold: {
    shortLabel: "Hold por ambiguidade",
    label: "Cadência em hold",
    description:
      "O reply bateu com mais de uma cadência possível, então os próximos steps candidatos foram pausados até revisão.",
    className: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  },
  manual_review: {
    shortLabel: "Vinculado manualmente",
    label: "Revisão manual",
    description: "O vínculo foi definido manualmente na auditoria de replies.",
    className: "border-(--accent-border) bg-(--accent-subtle) text-(--accent-subtle-fg)",
  },
}

const DEFAULT_REPLY_MATCH_SOURCE_META: ReplyMatchSourceMeta = {
  shortLabel: "Sem vínculo automático",
  label: "Sem vínculo automático",
  description:
    "Nenhuma referência confiável foi encontrada para vincular este reply automaticamente.",
  className: "border-(--info) bg-(--info-subtle) text-(--info-subtle-fg)",
}

export function getReplyMatchSourceMeta(source: string | null | undefined): ReplyMatchSourceMeta {
  if (!source) {
    return DEFAULT_REPLY_MATCH_SOURCE_META
  }

  return (
    REPLY_MATCH_SOURCE_META[source as Exclude<ReplyMatchSource, null>] ?? {
      shortLabel: source,
      label: source,
      description: "Fonte de match automático registrada pelo backend.",
      className: "border-(--accent-border) bg-(--accent-subtle) text-(--accent-subtle-fg)",
    }
  )
}

interface ReplyMatchSourceBadgeProps {
  source: string | null | undefined
  className?: string
  short?: boolean
}

export function ReplyMatchSourceBadge({
  source,
  className,
  short = false,
}: ReplyMatchSourceBadgeProps) {
  const meta = getReplyMatchSourceMeta(source)

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-(--radius-full) border px-2 py-0.5 text-xs font-medium",
        meta.className,
        className,
      )}
      title={meta.description}
    >
      {short ? meta.shortLabel : meta.label}
    </span>
  )
}
