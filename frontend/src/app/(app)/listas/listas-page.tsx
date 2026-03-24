"use client"

import { useState } from "react"
import { useLeadLists, useCreateLeadList, useDeleteLeadList } from "@/lib/api/hooks/use-lead-lists"
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
import { Loader2, Plus, Trash2, List, Users, AlertTriangle } from "lucide-react"
import { formatRelativeTime } from "@/lib/utils"

export default function LeadListsPage() {
  const { data: lists, isLoading, isError } = useLeadLists()
  const { mutate: createList, isPending: creating } = useCreateLeadList()
  const { mutate: deleteList } = useDeleteLeadList()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

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

      {/* Grid */}
      {lists && lists.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {lists.map((list) => (
            <Card key={list.id}>
              <CardHeader className="flex-row items-start justify-between">
                <CardTitle className="text-sm">{list.name}</CardTitle>
                <button
                  type="button"
                  onClick={() => deleteList(list.id)}
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
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1 text-xs text-(--text-tertiary)">
                    <Users size={12} aria-hidden="true" />
                    {list.lead_count} lead{list.lead_count !== 1 ? "s" : ""}
                  </span>
                  <span className="text-[11px] text-(--text-tertiary)">
                    {formatRelativeTime(list.created_at)}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
