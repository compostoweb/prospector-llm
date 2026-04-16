"use client"

import { useState } from "react"
import { ArrowDown, ArrowUp, ArrowUpDown, Eye, Trash2, Users } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn, formatRelativeTime, truncate } from "@/lib/utils"
import type { LeadList } from "@/lib/api/hooks/use-lead-lists"

type SortKey = "lead_count" | "created_at" | "updated_at"
type SortDir = "asc" | "desc"

function sortLists(lists: LeadList[], key: SortKey, dir: SortDir): LeadList[] {
  const sorted = [...lists]
  const mul = dir === "asc" ? 1 : -1
  return sorted.sort((a, b) => {
    if (key === "lead_count") return mul * (a.lead_count - b.lead_count)
    return mul * (new Date(a[key]).getTime() - new Date(b[key]).getTime())
  })
}

interface LeadListsTableProps {
  lists: LeadList[]
  isDeleting?: boolean
  onDelete: (id: string) => void
  onOpen: (id: string) => void
}

export function LeadListsTable({
  lists,
  isDeleting = false,
  onDelete,
  onOpen,
}: LeadListsTableProps) {
  const gridCols = "grid-cols-[minmax(260px,1.7fr)_110px_130px_130px_150px] min-w-[860px]"

  const [sortKey, setSortKey] = useState<SortKey>("updated_at")
  const [sortDir, setSortDir] = useState<SortDir>("desc")

  function handleSort(key: SortKey, dir: SortDir) {
    setSortKey(key)
    setSortDir(dir)
  }

  function SortColumnHeader({
    label,
    colKey,
    align = "left",
  }: {
    label: string
    colKey: SortKey
    align?: "left" | "center"
  }) {
    const active = sortKey === colKey
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className={cn(
              "flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide transition-colors hover:text-amber-300",
              align === "center" && "mx-auto",
              active ? "text-amber-300" : "text-(--text-invert)",
            )}
          >
            {label}
            {active ? (
              sortDir === "desc" ? (
                <ArrowDown className="h-3 w-3" />
              ) : (
                <ArrowUp className="h-3 w-3" />
              )
            ) : (
              <ArrowUpDown className="h-3 w-3 opacity-60" />
            )}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-44">
          <DropdownMenuItem
            onSelect={() => handleSort(colKey, "asc")}
            className={sortKey === colKey && sortDir === "asc" ? "font-medium text-(--accent)" : ""}
          >
            <ArrowUp className="mr-2 h-3 w-3" />
            Crescente
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={() => handleSort(colKey, "desc")}
            className={
              sortKey === colKey && sortDir === "desc" ? "font-medium text-(--accent)" : ""
            }
          >
            <ArrowDown className="mr-2 h-3 w-3" />
            Decrescente
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  const sortedLists = sortLists(lists, sortKey, sortDir)

  return (
    <div className="overflow-x-auto rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
      <div
        className={cn(
          "grid items-center gap-3 border-b border-(--border-default) bg-(--accent) px-4 py-3 text-[11px] font-medium uppercase tracking-wide text-(--text-invert)",
          gridCols,
        )}
      >
        <span>Lista</span>
        <SortColumnHeader label="Leads" colKey="lead_count" align="center" />
        <SortColumnHeader label="Criada" colKey="created_at" />
        <SortColumnHeader label="Atualizada" colKey="updated_at" />
        <span className="text-right">Ações</span>
      </div>

      <div className="divide-y divide-(--border-subtle)">
        {sortedLists.map((list) => (
          <div
            key={list.id}
            className={cn(
              "grid items-center gap-3 px-4 py-3 transition-colors hover:bg-(--bg-overlay)",
              gridCols,
            )}
          >
            <div className="min-w-0">
              <button
                type="button"
                onClick={() => onOpen(list.id)}
                className="block w-full text-left"
              >
                <p className="truncate text-sm font-semibold text-(--text-primary)">{list.name}</p>
                <p className="mt-1 text-xs text-(--text-secondary)">
                  {list.description ? truncate(list.description, 120) : "Sem descrição"}
                </p>
              </button>
            </div>

            <div className="flex items-center justify-center gap-1 text-sm font-semibold text-(--text-primary)">
              <Users size={14} aria-hidden="true" className="text-(--text-tertiary)" />
              {list.lead_count}
            </div>

            <div className="text-xs text-(--text-secondary)">
              {formatRelativeTime(list.created_at)}
            </div>

            <div className="text-xs text-(--text-secondary)">
              {formatRelativeTime(list.updated_at)}
            </div>

            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 px-2 text-xs"
                onClick={() => onOpen(list.id)}
              >
                <Eye size={13} aria-hidden="true" />
                Abrir
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-(--text-tertiary) hover:text-(--danger)"
                onClick={() => onDelete(list.id)}
                disabled={isDeleting}
                aria-label="Excluir lista"
              >
                <Trash2 size={14} aria-hidden="true" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
