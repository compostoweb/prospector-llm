import { cn, channelLabel } from "@/lib/utils"
import { Mail, Linkedin, UserPlus } from "lucide-react"

interface BadgeChannelProps {
  channel: string
  className?: string
}

const channelIcon: Record<string, React.ReactNode> = {
  linkedin_dm: <Linkedin size={11} aria-hidden="true" />,
  linkedin_connect: <UserPlus size={11} aria-hidden="true" />,
  email: <Mail size={11} aria-hidden="true" />,
}

export function BadgeChannel({ channel, className }: BadgeChannelProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[var(--radius-full)] border border-[var(--border-default)] bg-[var(--bg-overlay)] px-2 py-0.5 text-xs font-medium text-[var(--text-secondary)]",
        className,
      )}
    >
      {channelIcon[channel] ?? null}
      {channelLabel(channel)}
    </span>
  )
}
