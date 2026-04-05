import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/** Merge de classes Tailwind com deduplicação */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/** Formata data de forma relativa: "agora", "há 3 min", "há 2h", "há 3 dias", "12 jan" */
export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHours = Math.floor(diffMin / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSec < 60) return "agora"
  if (diffMin < 60) return `há ${diffMin} min`
  if (diffHours < 24) return `há ${diffHours}h`
  if (diffDays < 7) return `há ${diffDays} dias`

  return d.toLocaleDateString("pt-BR", { day: "numeric", month: "short" })
}

/** Score numérico → variante semântica de cor */
export function scoreVariant(score: number): "success" | "warning" | "danger" {
  if (score >= 71) return "success"
  if (score >= 41) return "warning"
  return "danger"
}

/** Trunca string ao tamanho `max`, adicionando "…" */
export function truncate(str: string, max: number): string {
  if (str.length <= max) return str
  return str.slice(0, max - 1) + "…"
}

/** Canal de envio → label legível em português */
export function channelLabel(channel: string): string {
  const map: Record<string, string> = {
    linkedin_connect: "LinkedIn Connect",
    linkedin_dm: "LinkedIn DM",
    linkedin_post_reaction: "Reação em Post",
    linkedin_post_comment: "Comentário em Post",
    linkedin_inmail: "InMail",
    email: "E-mail",
    manual_task: "Tarefa Manual",
  }
  return map[channel] ?? channel
}

type IntentVariant = "success" | "warning" | "danger" | "neutral" | "info"

/** Intent da resposta → label + variante de cor */
export function intentConfig(intent: string): { label: string; variant: IntentVariant } {
  const map: Record<string, { label: string; variant: IntentVariant }> = {
    interest: { label: "Interesse", variant: "success" },
    objection: { label: "Objeção", variant: "warning" },
    not_interested: { label: "Sem interesse", variant: "danger" },
    neutral: { label: "Neutro", variant: "neutral" },
    out_of_office: { label: "Ausente", variant: "info" },
  }
  return map[intent] ?? { label: intent, variant: "neutral" }
}

/** Converte string em slug URL-friendly */
export function slugify(str: string): string {
  return str
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
}

/** Formata valor em reais (BRL) */
export function formatBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value)
}

export { formatDateBR } from "@/lib/date"
