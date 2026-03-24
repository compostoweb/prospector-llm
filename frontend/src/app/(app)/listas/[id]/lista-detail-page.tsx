"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import {
  useLeadList,
  useRemoveLeadListMembers,
  useAddLeadListMembers,
} from "@/lib/api/hooks/use-lead-lists"
import { useLeads, type Lead } from "@/lib/api/hooks/use-leads"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { ArrowLeft, Loader2, Plus, Trash2, Search, Users, AlertTriangle } from "lucide-react"

export default function ListaDetailPage() {
  const params = useParams()
  const router = useRouter()
  const listId = params.id as string

  const { data: list, isLoading, isError } = useLeadList(listId)
  const { mutate: removeMembers, isPending: removing } = useRemoveLeadListMembers()
  const { mutate: addMembers, isPending: adding } = useAddLeadListMembers()

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [addOpen, setAddOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [addSelected, setAddSelected] = useState<Set<string>>(new Set())

  // Buscar leads disponíveis para adicionar
  const leadsParams: import("@/lib/api/hooks/use-leads").LeadListParams = { page_size: 100 }
  if (search) leadsParams.search = search
  const { data: allLeads, isLoading: loadingLeads } = useLeads(leadsParams)

  // IDs já na lista
  const memberIds = new Set(list?.leads.map((l) => l.id) ?? [])

  // Leads que NÃO estão na lista (disponíveis para add)
  const availableLeads = allLeads?.items.filter((l) => !memberIds.has(l.id)) ?? []

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (!list) return
    if (selected.size === list.leads.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(list.leads.map((l) => l.id)))
    }
  }

  function handleRemove() {
    if (selected.size === 0) return
    removeMembers(
      { listId, leadIds: Array.from(selected) },
      { onSuccess: () => setSelected(new Set()) },
    )
  }

  function toggleAddSelected(id: string) {
    setAddSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleAdd() {
    if (addSelected.size === 0) return
    addMembers(
      { listId, leadIds: Array.from(addSelected) },
      {
        onSuccess: () => {
          setAddSelected(new Set())
          setAddOpen(false)
          setSearch("")
        },
      },
    )
  }

  // ── Loading / Error ──

  if (isLoading) {
    return (
      <div className="flex h-60 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-(--text-tertiary)" />
      </div>
    )
  }

  if (isError || !list) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <AlertTriangle size={32} className="text-(--danger)" />
        <p className="text-sm font-medium text-(--text-primary)">Erro ao carregar lista</p>
        <Button variant="outline" size="sm" onClick={() => router.back()}>
          Voltar
        </Button>
      </div>
    )
  }

  // ── Render ──

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push("/listas")}>
          <ArrowLeft size={14} />
        </Button>
        <div className="flex-1">
          <h1 className="text-lg font-semibold text-(--text-primary)">{list.name}</h1>
          {list.description && (
            <p className="text-sm text-(--text-secondary)">{list.description}</p>
          )}
        </div>
        <span className="flex items-center gap-1 text-sm text-(--text-tertiary)">
          <Users size={14} />
          {list.lead_count} lead{list.lead_count !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRemove}
              disabled={removing}
              className="text-(--danger)"
            >
              {removing ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              Remover {selected.size} selecionado{selected.size !== 1 ? "s" : ""}
            </Button>
          )}
        </div>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <Plus size={14} />
          Adicionar leads
        </Button>
      </div>

      {/* Lead table */}
      {list.leads.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Users size={32} className="text-(--text-tertiary)" />
          <p className="text-sm font-medium text-(--text-primary)">Nenhum lead nesta lista</p>
          <p className="text-xs text-(--text-tertiary)">
            Adicione leads para organizar sua prospecção.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-(--border)">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-(--border) bg-(--bg-surface)">
                <th className="w-10 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selected.size === list.leads.length && list.leads.length > 0}
                    onChange={toggleAll}
                    className="rounded border-(--border)"
                    aria-label="Selecionar todos"
                  />
                </th>
                <th className="px-3 py-2 text-left font-medium text-(--text-secondary)">Nome</th>
                <th className="hidden px-3 py-2 text-left font-medium text-(--text-secondary) md:table-cell">
                  Cargo
                </th>
                <th className="hidden px-3 py-2 text-left font-medium text-(--text-secondary) sm:table-cell">
                  Empresa
                </th>
                <th className="hidden px-3 py-2 text-left font-medium text-(--text-secondary) lg:table-cell">
                  Email
                </th>
                <th className="px-3 py-2 text-left font-medium text-(--text-secondary)">Status</th>
              </tr>
            </thead>
            <tbody>
              {list.leads.map((lead) => (
                <tr
                  key={lead.id}
                  className="border-b border-(--border) last:border-0 hover:bg-(--bg-overlay)"
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selected.has(lead.id)}
                      onChange={() => toggleSelected(lead.id)}
                      className="rounded border-(--border)"
                      aria-label={`Selecionar ${lead.name}`}
                    />
                  </td>
                  <td className="px-3 py-2 font-medium text-(--text-primary)">{lead.name}</td>
                  <td className="hidden px-3 py-2 text-(--text-secondary) md:table-cell">
                    {lead.job_title ?? "—"}
                  </td>
                  <td className="hidden px-3 py-2 text-(--text-secondary) sm:table-cell">
                    {lead.company ?? "—"}
                  </td>
                  <td className="hidden px-3 py-2 text-(--text-secondary) lg:table-cell">
                    {lead.email_corporate ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <span className="inline-flex rounded-full bg-(--bg-overlay) px-2 py-0.5 text-[11px] font-medium text-(--text-secondary)">
                      {lead.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Dialog: Adicionar leads */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Adicionar leads à lista</DialogTitle>
          </DialogHeader>

          {/* Search */}
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nome, empresa…"
              className="pl-9"
            />
          </div>

          {/* Available leads list */}
          <div className="max-h-72 overflow-y-auto rounded-md border border-(--border)">
            {loadingLeads ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 size={16} className="animate-spin text-(--text-tertiary)" />
              </div>
            ) : availableLeads.length === 0 ? (
              <p className="py-6 text-center text-sm text-(--text-tertiary)">
                {search ? "Nenhum lead encontrado" : "Todos os leads já estão na lista"}
              </p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {availableLeads.map((lead: Lead) => (
                    <tr
                      key={lead.id}
                      className="cursor-pointer border-b border-(--border) last:border-0 hover:bg-(--bg-overlay)"
                      onClick={() => toggleAddSelected(lead.id)}
                    >
                      <td className="w-10 px-3 py-2">
                        <input
                          type="checkbox"
                          checked={addSelected.has(lead.id)}
                          readOnly
                          className="rounded border-(--border)"
                          aria-label={`Selecionar ${lead.name}`}
                        />
                      </td>
                      <td className="px-3 py-2 font-medium text-(--text-primary)">{lead.name}</td>
                      <td className="hidden px-3 py-2 text-(--text-secondary) sm:table-cell">
                        {lead.company ?? "—"}
                      </td>
                      <td className="hidden px-3 py-2 text-(--text-secondary) md:table-cell">
                        {lead.email_corporate ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {addSelected.size > 0 && (
            <p className="text-sm text-(--text-secondary)">
              {addSelected.size} lead{addSelected.size !== 1 ? "s" : ""} selecionado
              {addSelected.size !== 1 ? "s" : ""}
            </p>
          )}

          <DialogFooter>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setAddOpen(false)
                setAddSelected(new Set())
                setSearch("")
              }}
            >
              Cancelar
            </Button>
            <Button size="sm" disabled={addSelected.size === 0 || adding} onClick={handleAdd}>
              {adding && <Loader2 size={14} className="animate-spin" />}
              Adicionar {addSelected.size > 0 ? addSelected.size : ""} lead
              {addSelected.size !== 1 ? "s" : ""}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
