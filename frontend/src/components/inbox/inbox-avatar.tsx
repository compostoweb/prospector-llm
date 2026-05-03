"use client"

import { User } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"

interface InboxAvatarProps {
  src?: string | null | undefined
  alt: string
  fallbackLabel?: string | null | undefined
  className?: string | undefined
  fallbackClassName?: string | undefined
  iconClassName?: string | undefined
}

function getInitials(label?: string | null): string {
  if (!label) return ""

  const parts = label
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)

  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("")
}

export function InboxAvatar({
  src,
  alt,
  fallbackLabel,
  className,
  fallbackClassName,
  iconClassName,
}: InboxAvatarProps) {
  const initials = getInitials(fallbackLabel ?? alt)

  return (
    <Avatar className={cn("shrink-0", className)}>
      {src ? <AvatarImage src={src} alt={alt} /> : null}
      <AvatarFallback
        className={cn("bg-(--bg-overlay) text-(--text-secondary)", fallbackClassName)}
      >
        {initials ? (
          <span className="text-[0.72em] font-semibold uppercase">{initials}</span>
        ) : (
          <User className={cn("size-[0.95em]", iconClassName)} aria-hidden="true" />
        )}
      </AvatarFallback>
    </Avatar>
  )
}