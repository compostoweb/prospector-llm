"use client"

import { useState } from "react"
import Link from "next/link"
import {
  useLeadLists,
  useCreateLeadList,
  useDeleteLeadList,
  useUpdateLeadList,
} from "@/lib/api/hooks/use-lead-lists"
import type { LeadList } from "@/lib/api/hooks/use-lead-lists"
import { LeadListsTable } from "@/components/listas/lead-lists-table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Loader2,
  Plus,
  Trash2,
  List,
  Users,
  AlertTriangle,
  LayoutGrid,
  Table2,
  Pencil,
} from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { formatRelativeTime } from "@/lib/utils"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"

export default function LeadListsPage() {
  const { data: lists, isLoading, isError } = useLeadLists()
  const { mutate: createList, isPending: creating } = useCreateLeadList()
  const deleteListMutation = useDeleteLeadList()
  const { mutate: updateList, isPending: updating } = useUpdateLeadList()
  const router = useRouter()

  const [open, setOpen] = useState(false)
  const [view, setView] = useState<"table" | "grid">("table")
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

  const [editOpen, setEditOpen] = useState(false)
  const [editingList, setEditingList] = useState<LeadList | null>(null)
  const [editName, setEditName] = useState("")
  const [editDescription, setEditDescription] = useState("")

  function openEdit(list: LeadList) {
    setEditingList(list)
    setEditName(list.name)
    setEditDescription(list.description ?? "")
    setEditOpen(true)
  }

  function handleEditSave() {
    if (!editingList) return
    updateList(
      {
        id: editingList.id,
        body: {
          name: editName.trim() || undefined,
          description: editDescription.trim() || undefined,
        },
      },
      { onSuccess: () => setEditOpen(false) },
    )
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    createList(
      { name: name.trim(), description: description.trim() || null },
      {
        onSuccess: () => {
          setName("")
          setDescription("")
          setOpen(false)
        },
      },
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Listas de Leads</h1>
          <p className="text-sm text-(--text-secondary)">
            {lists ? `${lists.length} lista${lists.length !== 1 ? "s" : ""}` : "Carregando…"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-md border border-(--border-default) overflow-hidden h-8">
            <button
              type="button"
              aria-label="Visão em tabela"
              onClick={() => setView("table")}
              className={cn(
                "px-2.5 h-full flex items-center transition-colors",
                view === "table"
                  ? "bg-(--accent) text-white"
                  : "text-(--text-secondary) hover:bg-(--bg-overlay)",
              )}
            >
              <Table2 className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              aria-label="Visão em cards"
              onClick={() => setView("grid")}
              className={cn(
                "px-2.5 h-full flex items-center transition-colors",
                view === "grid"
                  ? "bg-(--accent) text-white"
                  : "text-(--text-secondary) hover:bg-(--bg-overlay)",
              )}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </button>
          </div>

          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus size={14} aria-hidden="true" />
                Nova Lista
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Criar lista</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="list-name">Nome *</Label>
                  <Input
                    id="list-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ex: SaaS Brasil"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="list-desc">Descrição</Label>
                  <Input
                    id="list-desc"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Descrição opcional"
                  />
                </div>
                <DialogFooter>
                  <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
                    Cancelar
                  </Button>
                  <Button type="submit" size="sm" disabled={creating || !name.trim()}>
                    {creating && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
                    Criar
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>
      {/* Loading */}
      {isLoading && (
        <div className="flex h-40 items-center justify-center">
          <Loader2
            size={20}
            className="animate-spin text-(--text-tertiary)"
            aria-label="Carregando"
          />
        </div>
      )}
      {/* Error */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <AlertTriangle size={32} className="text-(--danger)" aria-hidden="true" />
          <p className="text-sm font-medium text-(--text-primary)">Erro ao carregar listas</p>
          <p className="text-xs text-(--text-tertiary)">
            Verifique sua conexão ou tente novamente.
          </p>
        </div>
      )}
      {/* Empty */}
      {!isLoading && lists?.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <List size={32} className="text-(--text-tertiary)" aria-hidden="true" />
          <p className="text-sm font-medium text-(--text-primary)">Nenhuma lista ainda</p>
          <p className="text-xs text-(--text-tertiary)">
            Crie uma lista para organizar seus leads.
          </p>
        </div>
      )}
      {/* Conteúdo */}
      {lists &&
        lists.length > 0 &&
        (view === "table" ? (
          <LeadListsTable
            lists={lists}
            isDeleting={deleteListMutation.isPending}
            onDelete={(id) => deleteListMutation.mutate(id)}
            onOpen={(id) => router.push(`/listas/${id}`)}
            onEdit={openEdit}
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {lists.map((list) => (
              <Card key={list.id} className="transition-colors hover:border-(--accent)">
                <CardHeader className="flex-row items-start justify-between gap-3">
                  <div className="min-w-0">
                    <CardTitle className="truncate text-sm">{list.name}</CardTitle>
                    <p className="mt-1 text-xs text-(--text-tertiary)">
                      Atualizada {formatRelativeTime(list.updated_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => openEdit(list)}
                    className="shrink-0 rounded-md p-1 text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                    aria-label="Editar lista"
                  >
                    <Pencil size={13} aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteListMutation.mutate(list.id)}
                    className="shrink-0 rounded-md p-1 text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--danger)"
                    aria-label="Excluir lista"
                  >
                    <Trash2 size={13} aria-hidden="true" />
                  </button>
                </CardHeader>
                <CardContent>
                  {list.description && (
                    <p className="mb-3 text-xs text-(--text-secondary)">{list.description}</p>
                  )}
                  <div className="mb-4 flex items-center justify-between">
                    <span className="flex items-center gap-1 text-xs text-(--text-tertiary)">
                      <Users size={12} aria-hidden="true" />
                      {list.lead_count} lead{list.lead_count !== 1 ? "s" : ""}
                    </span>
                    <span className="text-[11px] text-(--text-tertiary)">
                      {formatRelativeTime(list.created_at)}
                    </span>
                  </div>
                  <Button asChild variant="outline" className="w-full">
                    <Link href={`/listas/${list.id}`}>Abrir lista</Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ))}
      {/* Dialog: Editar lista */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Editar lista</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit-name">Nome *</Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Nome da lista"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-desc">Descrição</Label>
              <Textarea
                id="edit-desc"
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
            <Button size="sm" disabled={!editName.trim() || updating} onClick={handleEditSave}>
              {updating && <Loader2 size={14} className="animate-spin" />}
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>{" "}
    </div>
  )
}
