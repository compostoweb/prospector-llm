"use client"

import { cn } from "@/lib/utils"
import type { PostStatus, PostPillar, HookType } from "@/lib/api/hooks/use-content"

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

// ── Hook badge ────────────────────────────────────────────────────────

const HOOK_STYLES: Record<HookType, string> = {
  loop_open: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  contrarian: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
  identification: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
  shortcut: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  benefit: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  data: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
}

const HOOK_LABELS: Record<HookType, string> = {
  loop_open: "Loop aberto",
  contrarian: "Contrário",
  identification: "Identificação",
  shortcut: "Atalho",
  benefit: "Benefício",
  data: "Dado",
}

interface HookBadgeProps {
  hook: HookType
  className?: string
}

export function HookBadge({ hook, className }: HookBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        HOOK_STYLES[hook],
        className,
      )}
    >
      {HOOK_LABELS[hook]}
    </span>
  )
}
