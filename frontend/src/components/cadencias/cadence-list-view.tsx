"use client"

import Link from "next/link"
import {
  ExternalLink,
  FlaskConical,
  Layers,
  Mail,
  MoreHorizontal,
  Power,
  Trash2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn, formatRelativeTime, truncate } from "@/lib/utils"
import type { Cadence } from "@/lib/api/hooks/use-cadences"
import type { CadenceOverview } from "@/lib/api/hooks/use-cadence-analytics"

interface CadenceListItem {
  cadence: Cadence
  metrics?: CadenceOverview | undefined
}

interface CadenceListViewProps {
  items: CadenceListItem[]
  isToggling?: boolean
  isDeleting?: boolean
  onToggle: (id: string, current: boolean) => void
  onDelete: (cadence: Cadence) => void
}

function cadenceTypeLabel(type: Cadence["cadence_type"]): string {
  return type === "email_only" ? "Só e-mail" : "Multicanal"
}

function cadenceModeLabel(mode: Cadence["mode"]): string {
  return mode === "automatic" ? "Automático" : "Semi-manual"
}

export function CadenceListView({
  items,
  isToggling = false,
  isDeleting = false,
  onToggle,
  onDelete,
}: CadenceListViewProps) {
  const gridCols =
    "grid-cols-[minmax(300px,1.7fr)_100px_100px_90px_70px_80px_100px_90px_85px_95px_170px] min-w-[1380px]"

  return (
    <div className="overflow-x-auto rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
      <div
        className={cn(
          "grid items-center gap-3 border-b border-(--border-default) bg-(--accent) px-4 py-3 text-[11px] font-medium uppercase tracking-wide text-white",
          gridCols,
        )}
      >
        <span>Cadência</span>
        <span>Tipo</span>
        <span>Modo</span>
        <span>Status</span>
        <span className="text-center">Leads</span>
        <span className="text-center">Ativos</span>
        <span className="text-center">Finalizados</span>
        <span className="text-center">Respostas</span>
        <span className="text-center">Pausados</span>
        <span className="text-center">Convertidos</span>
        <span className="text-right">Ações</span>
      </div>

      <div className="divide-y divide-(--border-subtle)">
        {items.map(({ cadence, metrics }) => {
          const typeIsEmail = cadence.cadence_type === "email_only"

          return (
            <div
              key={cadence.id}
              className={cn(
                "grid items-center gap-3 px-4 py-3 transition-colors hover:bg-(--bg-overlay)",
                gridCols,
              )}
            >
              <div className="min-w-0">
                <div className="flex items-start gap-3">
                  <span
                    className={cn(
                      "mt-1 inline-flex h-2.5 w-2.5 shrink-0 rounded-full",
                      cadence.is_active ? "bg-(--success)" : "bg-(--text-disabled)",
                    )}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/cadencias/${cadence.id}`}
                      className="block truncate text-sm font-semibold text-(--text-primary) hover:text-(--accent)"
                    >
                      {cadence.name}
                    </Link>
                    <p className="mt-1 text-xs text-(--text-secondary)">
                      {cadence.description ? truncate(cadence.description, 110) : "Sem descrição"}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-(--text-tertiary)">
                      <span>
                        {cadence.llm_provider === "openai"
                          ? "OpenAI"
                          : cadence.llm_provider === "gemini"
                            ? "Gemini"
                            : cadence.llm_provider === "anthropic"
                              ? "Anthropic"
                              : "OpenRouter"}{" "}
                        · {cadence.llm_model}
                      </span>
                      <span>•</span>
                      <span>
                        {cadence.steps_template?.length ?? 0} passo
                        {(cadence.steps_template?.length ?? 0) !== 1 ? "s" : ""}
                      </span>
                      <span>•</span>
                      <span>Atualizada {formatRelativeTime(cadence.updated_at)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-(--radius-full) px-2.5 py-1 text-xs font-medium",
                    typeIsEmail
                      ? "bg-(--info-subtle) text-(--info-subtle-fg)"
                      : "bg-(--accent-subtle) text-(--accent-subtle-fg)",
                  )}
                >
                  {typeIsEmail ? (
                    <Mail size={12} aria-hidden="true" />
                  ) : (
                    <Layers size={12} aria-hidden="true" />
                  )}
                  {cadenceTypeLabel(cadence.cadence_type)}
                </span>
              </div>

              <div>
                <span className="inline-flex rounded-(--radius-full) bg-(--bg-overlay) px-2.5 py-1 text-xs font-medium text-(--text-secondary)">
                  {cadenceModeLabel(cadence.mode)}
                </span>
              </div>

              <div>
                <span
                  className={cn(
                    "inline-flex rounded-(--radius-full) px-2.5 py-1 text-xs font-medium",
                    cadence.is_active
                      ? "bg-(--success-subtle) text-(--success-subtle-fg)"
                      : "bg-(--bg-overlay) text-(--text-secondary)",
                  )}
                >
                  {cadence.is_active ? "Ativa" : "Pausada"}
                </span>
              </div>

              <div className="text-center text-sm font-semibold text-(--text-primary)">
                {metrics?.total_leads ?? 0}
              </div>

              <div className="text-center text-sm font-semibold text-(--text-primary)">
                {metrics?.leads_active ?? 0}
              </div>

              <div className="text-center text-sm font-semibold text-(--text-primary)">
                {metrics?.leads_finished ?? 0}
              </div>

              <div className="text-center text-sm font-semibold text-(--text-primary)">
                {metrics?.replies ?? 0}
              </div>

              <div className="text-center text-sm font-semibold text-(--text-primary)">
                {metrics?.leads_paused ?? 0}
              </div>

              <div className="text-center text-sm font-semibold text-(--text-primary)">
                {metrics?.leads_converted ?? 0}
              </div>

              <div className="flex items-center justify-end gap-2 whitespace-nowrap">
                <Button
                  type="button"
                  variant={cadence.is_active ? "outline" : "default"}
                  size="sm"
                  onClick={() => onToggle(cadence.id, cadence.is_active)}
                  aria-label={cadence.is_active ? "Desativar cadência" : "Ativar cadência"}
                  disabled={isToggling}
                  className={cn(
                    "h-8 px-2.5 text-xs",
                    cadence.is_active
                      ? "border-(--success) text-(--success) hover:bg-(--success-subtle) hover:text-(--success)"
                      : "bg-(--accent) text-white hover:opacity-90",
                  )}
                >
                  <Power size={14} aria-hidden="true" />
                  {cadence.is_active ? "Desativar" : "Ativar"}
                </Button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      aria-label="Mais ações da cadência"
                    >
                      <MoreHorizontal size={15} aria-hidden="true" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem asChild>
                      <Link href={`/cadencias/${cadence.id}`}>
                        <ExternalLink size={14} aria-hidden="true" />
                        Abrir cadência
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link href={`/cadencias/${cadence.id}/sandbox`}>
                        <FlaskConical size={14} aria-hidden="true" />
                        Abrir sandbox
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => onDelete(cadence)}
                      disabled={isDeleting}
                      className="text-(--danger) focus:text-(--danger)"
                    >
                      <Trash2 size={14} aria-hidden="true" />
                      Excluir cadência
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
