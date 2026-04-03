"use client"

import { cn } from "@/lib/utils"
import type { PostStatus, PostPillar } from "@/lib/api/hooks/use-content"

// ── Status badge ──────────────────────────────────────────────────────

const STATUS_STYLES: Record<PostStatus, string> = {
  draft: "bg-(--bg-overlay) text-(--text-secondary)",
  approved: "bg-(--info-subtle) text-(--info-subtle-fg)",
  scheduled: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
  published: "bg-(--success-subtle) text-(--success-subtle-fg)",
  failed: "bg-(--danger-subtle) text-(--danger-subtle-fg)",
}

const STATUS_LABELS: Record<PostStatus, string> = {
  draft: "Rascunho",
  approved: "Aprovado",
  scheduled: "Agendado",
  published: "Publicado",
  failed: "Falhou",
}

interface StatusBadgeProps {
  status: PostStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        STATUS_STYLES[status],
        className,
      )}
    >
      {STATUS_LABELS[status]}
    </span>
  )
}

// ── Pillar badge ──────────────────────────────────────────────────────

const PILLAR_STYLES: Record<PostPillar, string> = {
  authority: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
  case: "bg-(--success-subtle) text-(--success-subtle-fg)",
  vision: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
}

const PILLAR_LABELS: Record<PostPillar, string> = {
  authority: "Autoridade",
  case: "Caso",
  vision: "Visão",
}

interface PillarBadgeProps {
  pillar: PostPillar
  className?: string
}

export function PillarBadge({ pillar, className }: PillarBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        PILLAR_STYLES[pillar],
        className,
      )}
    >
      {PILLAR_LABELS[pillar]}
    </span>
  )
}
