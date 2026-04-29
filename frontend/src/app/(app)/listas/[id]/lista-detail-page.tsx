"use client"

import { useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import {
  useLeadList,
  useRemoveLeadListMembers,
  useAddLeadListMembers,
  useUpdateLeadList,
} from "@/lib/api/hooks/use-lead-lists"
import { useLeads, type Lead } from "@/lib/api/hooks/use-leads"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  ArrowLeft,
  Loader2,
  Plus,
  Trash2,
  Search,
  Users,
  AlertTriangle,
  ListFilter,
  Mail,
  Pencil,
  Linkedin,
} from "lucide-react"
import { cn } from "@/lib/utils"

const statusLabel: Record<string, string> = {
  raw: "Novo",
  enriched: "Enriquecido",
  in_cadence: "Em cadência",
  converted: "Convertido",
  archived: "Arquivado",
}

const statusClass: Record<string, string> = {
  raw: "bg-(--neutral-subtle) text-(--neutral-subtle-fg)",
  enriched: "bg-(--info-subtle) text-(--info-subtle-fg)",
  in_cadence: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
  converted: "bg-(--success-subtle) text-(--success-subtle-fg)",
  archived: "bg-(--neutral-subtle) text-(--text-disabled)",
}

export default function ListaDetailPage() {
  const params = useParams()
  const router = useRouter()
  const listId = params.id as string

  const { data: list, isLoading, isError } = useLeadList(listId)
  const { mutate: removeMembers, isPending: removing } = useRemoveLeadListMembers()
  const { mutate: addMembers, isPending: adding } = useAddLeadListMembers()
  const { mutate: updateList, isPending: updatingList } = useUpdateLeadList()

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [addOpen, setAddOpen] = useState(false)
  const [addSearch, setAddSearch] = useState("")
  const [memberSearch, setMemberSearch] = useState("")
  const [addSelected, setAddSelected] = useState<Set<string>>(new Set())
  const [editOpen, setEditOpen] = useState(false)
  const [editName, setEditName] = useState("")
  const [editDescription, setEditDescription] = useState("")

  // Buscar leads disponíveis para adicionar
  const leadsParams: import("@/lib/api/hooks/use-leads").LeadListParams = { page_size: 100 }
  if (addSearch) leadsParams.search = addSearch
  const { data: allLeads, isLoading: loadingLeads } = useLeads(leadsParams)

  // IDs já na lista
  const memberIds = new Set(list?.leads.map((l) => l.id) ?? [])

  // Leads que NÃO estão na lista (disponíveis para add)
  const availableLeads = allLeads?.items.filter((l) => !memberIds.has(l.id)) ?? []
  const filteredMembers = useMemo(() => {
    const query = memberSearch.trim().toLowerCase()
    if (!query) return list?.leads ?? []

    return (list?.leads ?? []).filter((lead) => {
      const haystack = [lead.name, lead.job_title, lead.company, lead.email_corporate]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()

      return haystack.includes(query)
    })
  }, [list?.leads, memberSearch])
  const overlappingCadenceLeads = filteredMembers.filter(
    (lead) => lead.has_multiple_active_cadences,
  )

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    const visibleIds = filteredMembers.map((lead) => lead.id)
    const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selected.has(id))

    if (allVisibleSelected) {
      setSelected(new Set())
    } else {
      setSelected(new Set(visibleIds))
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
          setAddSearch("")
        },
      },
    )
  }

  function openEdit() {
    setEditName(list?.name ?? "")
    setEditDescription(list?.description ?? "")
    setEditOpen(true)
  }

  function handleEditSave() {
    const body: import("@/lib/api/hooks/use-lead-lists").UpdateLeadListBody = {}
    const trimmedName = editName.trim()
    const trimmedDesc = editDescription.trim()
    if (trimmedName) body.name = trimmedName
    if (trimmedDesc) body.description = trimmedDesc
    updateList({ id: listId, body }, { onSuccess: () => setEditOpen(false) })
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
        <Button variant="ghost" size="sm" onClick={openEdit} title="Editar lista">
          <Pencil size={14} />
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Total de leads</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-(--text-primary)">{list.lead_count}</p>
            <p className="mt-1 text-xs text-(--text-tertiary)">Membros ativos nesta lista</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Selecionados</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-(--text-primary)">{selected.size}</p>
            <p className="mt-1 text-xs text-(--text-tertiary)">Prontos para remoção em massa</p>
          </CardContent>
        </Card>
        <Card className="md:col-span-2 xl:col-span-1">
          <CardHeader>
            <CardTitle>Ações rápidas</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => setAddOpen(true)}>
              <Plus size={14} />
              Adicionar leads
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRemove}
              disabled={selected.size === 0 || removing}
              className="text-(--danger)"
            >
              {removing ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              Remover selecionados
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="gap-4 border-b border-(--border-subtle) pb-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Leads da lista</CardTitle>
              <p className="mt-1 text-xs text-(--text-tertiary)">
                Gestão em lote com busca, seleção e acesso rápido ao perfil de cada lead.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {selected.size > 0 && (
                <span className="rounded-(--radius-full) bg-(--accent-subtle) px-2.5 py-1 text-xs font-medium text-(--accent-subtle-fg)">
                  {selected.size} selecionado{selected.size !== 1 ? "s" : ""}
                </span>
              )}
              <Button size="sm" onClick={() => setAddOpen(true)}>
                <Plus size={14} />
                Adicionar leads
              </Button>
            </div>
          </div>

          <div className="relative max-w-md">
            <ListFilter
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            />
            <Input
              value={memberSearch}
              onChange={(e) => setMemberSearch(e.target.value)}
              placeholder="Filtrar por nome, empresa, cargo ou email"
              className="pl-9"
            />
          </div>

          {overlappingCadenceLeads.length > 0 && (
            <div className="flex items-start gap-3 rounded-lg border border-(--warning) bg-(--warning-subtle) px-4 py-3 text-sm text-(--warning-subtle-fg)">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
              <div>
                <p className="font-medium">
                  Esta lista contém leads em múltiplas cadências ativas.
                </p>
                <p className="mt-1 text-xs text-(--warning-subtle-fg)">
                  Use o alerta por linha para revisar esses casos antes de interpretar replies
                  automáticos.
                </p>
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent className="p-0">
          {list.leads.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <Users size={32} className="text-(--text-tertiary)" />
              <p className="text-sm font-medium text-(--text-primary)">Nenhum lead nesta lista</p>
              <p className="text-xs text-(--text-tertiary)">
                Adicione leads para organizar sua prospecção.
              </p>
            </div>
          ) : filteredMembers.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <Search size={28} className="text-(--text-tertiary)" />
              <p className="text-sm font-medium text-(--text-primary)">Nenhum lead encontrado</p>
              <p className="text-xs text-(--text-tertiary)">
                Ajuste o filtro para visualizar outros membros desta lista.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-215 text-sm">
                <thead>
                  <tr className="border-b border-(--border-default) bg-(--accent)">
                    <th className="w-12 px-4 py-3">
                      <Checkbox
                        checked={
                          selected.size === filteredMembers.length && filteredMembers.length > 0
                        }
                        onCheckedChange={toggleAll}
                        aria-label="Selecionar todos"
                        className="border-white/70 hover:border-amber-300"
                      />
                    </th>
                    <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                      Lead
                    </th>
                    <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                      Empresa
                    </th>
                    <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                      Contato
                    </th>
                    <th className="px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wide text-(--text-invert)">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-(--border-subtle)">
                  {filteredMembers.map((lead) => (
                    <tr key={lead.id} className="transition-colors hover:bg-(--bg-overlay)">
                      <td className="px-4 py-3">
                        <Checkbox
                          checked={selected.has(lead.id)}
                          onCheckedChange={() => toggleSelected(lead.id)}
                          aria-label={`Selecionar ${lead.name}`}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => router.push(`/leads/${lead.id}`)}
                          className="text-left"
                        >
                          <p className="font-medium text-(--text-primary) hover:text-(--accent)">
                            {lead.name}
                          </p>
                          <p className="mt-1 text-xs text-(--text-tertiary)">
                            {lead.job_title ?? "Sem cargo"}
                          </p>
                          {lead.has_multiple_active_cadences && (
                            <div
                              className="mt-2 inline-flex max-w-56 items-center gap-1.5 rounded-(--radius-full) bg-(--warning-subtle) px-2.5 py-1 text-[11px] font-medium text-(--warning-subtle-fg)"
                              title={lead.active_cadences
                                .map((cadence) => cadence.name)
                                .join(" • ")}
                            >
                              <AlertTriangle size={12} aria-hidden="true" />
                              <span>{lead.active_cadence_count} cadências ativas</span>
                            </div>
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-(--text-secondary)">{lead.company ?? "—"}</td>
                      <td className="px-4 py-3">
                        <div className="space-y-1.5 text-(--text-secondary)">
                          <div className="flex items-center gap-2">
                            <Mail
                              size={13}
                              aria-hidden="true"
                              className="shrink-0 text-(--text-tertiary)"
                            />
                            <span className="text-xs">
                              {lead.email_corporate ?? "Sem email corporativo"}
                            </span>
                          </div>
                          {lead.linkedin_url && (
                            <div className="flex items-center gap-2">
                              <Linkedin
                                size={13}
                                aria-hidden="true"
                                className="shrink-0 text-(--text-tertiary)"
                              />
                              <a
                                href={lead.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="max-w-48 truncate text-xs text-(--accent) hover:underline"
                                title={lead.linkedin_url}
                                onClick={(e) => e.stopPropagation()}
                              >
                                {lead.linkedin_url
                                  .replace(/^https?:\/\/(www\.)?linkedin\.com\/in\//, "")
                                  .replace(/\/$/, "") || "Ver perfil"}
                              </a>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "inline-flex rounded-(--radius-full) px-2 py-0.5 text-xs font-medium",
                            statusClass[lead.status] ?? statusClass.raw,
                          )}
                        >
                          {statusLabel[lead.status] ?? lead.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

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
              value={addSearch}
              onChange={(e) => setAddSearch(e.target.value)}
              placeholder="Buscar por nome, empresa…"
              className="pl-9"
            />
          </div>

          {/* Available leads list */}
          <div className="max-h-72 overflow-y-auto rounded-md border border-(--border-default)">
            {loadingLeads ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 size={16} className="animate-spin text-(--text-tertiary)" />
              </div>
            ) : availableLeads.length === 0 ? (
              <p className="py-6 text-center text-sm text-(--text-tertiary)">
                {addSearch ? "Nenhum lead encontrado" : "Todos os leads já estão na lista"}
              </p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {availableLeads.map((lead: Lead) => (
                    <tr
                      key={lead.id}
                      className="cursor-pointer border-b border-(--border-subtle) last:border-0 hover:bg-(--bg-overlay)"
                      onClick={() => toggleAddSelected(lead.id)}
                    >
                      <td className="w-10 px-3 py-2">
                        <Checkbox
                          checked={addSelected.has(lead.id)}
                          onCheckedChange={() => toggleAddSelected(lead.id)}
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
                setAddSearch("")
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

      {/* Dialog: Editar lista */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Editar lista</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-(--text-secondary)">Nome</label>
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Nome da lista"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-(--text-secondary)">Descrição</label>
              <Textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Descrição opcional"
                rows={3}
                className="resize-none"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" size="sm" onClick={() => setEditOpen(false)}>
              Cancelar
            </Button>
            <Button size="sm" disabled={!editName.trim() || updatingList} onClick={handleEditSave}>
              {updatingList && <Loader2 size={14} className="animate-spin" />}
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
