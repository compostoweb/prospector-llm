import { cn, channelLabel } from "@/lib/utils"
import {
  Mail,
  Linkedin,
  UserPlus,
  ClipboardList,
  ThumbsUp,
  MessageSquare,
  Send,
} from "lucide-react"

interface BadgeChannelProps {
  channel: string
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

export function BadgeChannel({ channel, className }: BadgeChannelProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-(--radius-full) border border-(--border-default) bg-(--bg-overlay) px-2 py-0.5 text-xs font-medium text-(--text-secondary)",
        className,
      )}
    >
      {channelIcon[channel] ?? null}
      {channelLabel(channel)}
    </span>
  )
}
