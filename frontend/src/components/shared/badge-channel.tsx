import { cn, channelLabel, manualTaskTypeLabel } from "@/lib/utils"
import {
  Mail,
  Linkedin,
  UserPlus,
  ClipboardList,
  ThumbsUp,
  MessageSquare,
  Send,
  Phone,
  MessageCircle,
  BellRing,
} from "lucide-react"

interface BadgeChannelProps {
  channel: string
  manualTaskType?: string | null
  className?: string
}

const channelIcon: Record<string, React.ReactNode> = {
  linkedin_dm: <Linkedin size={11} aria-hidden="true" />,
  linkedin_connect: <UserPlus size={11} aria-hidden="true" />,
  linkedin_post_reaction: <ThumbsUp size={11} aria-hidden="true" />,
  linkedin_post_comment: <MessageSquare size={11} aria-hidden="true" />,
  linkedin_inmail: <Send size={11} aria-hidden="true" />,
  email: <Mail size={11} aria-hidden="true" />,
  manual_task: <ClipboardList size={11} aria-hidden="true" />,
}

const manualTaskIcon: Record<string, React.ReactNode> = {
  call: <Phone size={11} aria-hidden="true" />,
  whatsapp: <MessageCircle size={11} aria-hidden="true" />,
  linkedin_post_comment: <BellRing size={11} aria-hidden="true" />,
  other: <ClipboardList size={11} aria-hidden="true" />,
}

const channelClassName: Record<string, string> = {
  linkedin_dm: "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)",
  linkedin_connect: "border-(--info) bg-(--info-subtle) text-(--info-subtle-fg)",
  linkedin_post_reaction: "border-(--success) bg-(--success-subtle) text-(--success-subtle-fg)",
  linkedin_post_comment: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  linkedin_inmail: "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)",
  email: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  manual_task: "border-(--border-default) bg-(--bg-overlay) text-(--text-primary)",
}

const manualTaskClassName: Record<string, string> = {
  call: "border-(--danger) bg-(--danger-subtle) text-(--danger-subtle-fg)",
  whatsapp: "border-(--success) bg-(--success-subtle) text-(--success-subtle-fg)",
  linkedin_post_comment: "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
  other: "border-(--info) bg-(--info-subtle) text-(--info-subtle-fg)",
}

export function BadgeChannel({ channel, manualTaskType, className }: BadgeChannelProps) {
  const manualTypeLabel = channel === "manual_task" ? manualTaskTypeLabel(manualTaskType) : null
  const label = manualTypeLabel ?? channelLabel(channel)
  const icon =
    channel === "manual_task" && manualTaskType
      ? (manualTaskIcon[manualTaskType] ?? channelIcon[channel] ?? null)
      : (channelIcon[channel] ?? null)

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-(--radius-full) border px-2 py-0.5 text-xs font-medium shadow-(--shadow-sm)",
        channel === "manual_task" && manualTaskType
          ? (manualTaskClassName[manualTaskType] ?? channelClassName[channel])
          : (channelClassName[channel] ??
              "border-(--border-default) bg-(--bg-overlay) text-(--text-secondary)"),
        className,
      )}
    >
      {icon}
      {label}
    </span>
  )
}
