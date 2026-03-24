"use client"

import { useState } from "react"
import { useCreateLead, type CreateLeadBody } from "@/lib/api/hooks/use-leads"
import { useLeadLists, useAddLeadListMembers } from "@/lib/api/hooks/use-lead-lists"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, Plus } from "lucide-react"

const empty: CreateLeadBody = {
  name: "",
  linkedin_url: null,
  company: null,
  website: null,
  email_corporate: null,
  phone: null,
  segment: null,
  city: null,
  job_title: null,
  notes: null,
}

export function LeadCreateDialog() {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<CreateLeadBody>({ ...empty })
  const [enrich, setEnrich] = useState(true)
  const [selectedListId, setSelectedListId] = useState<string>("")
  const { mutate, isPending } = useCreateLead()
  const { data: lists } = useLeadLists()
  const { mutate: addToList } = useAddLeadListMembers()

  function set(field: keyof CreateLeadBody, value: string) {
    setForm((prev) => ({ ...prev, [field]: value || null }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) return
    mutate(
      { body: form, enrich },
      {
        onSuccess: (lead) => {
          if (selectedListId) {
            addToList({ listId: selectedListId, leadIds: [lead.id] })
          }
          setForm({ ...empty })
          setSelectedListId("")
          setOpen(false)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus size={14} aria-hidden="true" />
          Novo Lead
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Criar lead</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Nome (obrigatório) */}
          <div className="space-y-1.5">
            <Label htmlFor="lead-name">Nome *</Label>
            <Input
              id="lead-name"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="João da Silva"
              required
            />
          </div>

          {/* LinkedIn */}
          <div className="space-y-1.5">
            <Label htmlFor="lead-linkedin">LinkedIn URL</Label>
            <Input
              id="lead-linkedin"
              value={form.linkedin_url ?? ""}
              onChange={(e) => set("linkedin_url", e.target.value)}
              placeholder="https://linkedin.com/in/joao"
            />
          </div>

          {/* Grid 2 colunas */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="lead-company">Empresa</Label>
              <Input
                id="lead-company"
                value={form.company ?? ""}
                onChange={(e) => set("company", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lead-website">Website</Label>
              <Input
                id="lead-website"
                value={form.website ?? ""}
                onChange={(e) => set("website", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lead-email">Email corporativo</Label>
              <Input
                id="lead-email"
                type="email"
                value={form.email_corporate ?? ""}
                onChange={(e) => set("email_corporate", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lead-phone">Telefone</Label>
              <Input
                id="lead-phone"
                value={form.phone ?? ""}
                onChange={(e) => set("phone", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lead-segment">Segmento</Label>
              <Input
                id="lead-segment"
                value={form.segment ?? ""}
                onChange={(e) => set("segment", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lead-city">Cidade</Label>
              <Input
                id="lead-city"
                value={form.city ?? ""}
                onChange={(e) => set("city", e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="lead-job">Cargo</Label>
            <Input
              id="lead-job"
              value={form.job_title ?? ""}
              onChange={(e) => set("job_title", e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="lead-notes">Notas</Label>
            <textarea
              id="lead-notes"
              className="flex w-full rounded-md border border-(--border) bg-transparent px-3 py-2 text-sm placeholder:text-(--text-tertiary) focus:outline-none focus:ring-1 focus:ring-(--ring)"
              rows={2}
              value={form.notes ?? ""}
              onChange={(e) => set("notes", e.target.value)}
              placeholder="Observações sobre o lead..."
            />
          </div>

          {/* Lista (opcional) */}
          <div className="space-y-1.5">
            <Label htmlFor="lead-list">Adicionar à lista</Label>
            <select
              id="lead-list"
              value={selectedListId}
              onChange={(e) => setSelectedListId(e.target.value)}
              aria-label="Selecionar lista"
              className="flex h-9 w-full rounded-md border border-(--border) bg-transparent px-3 py-1 text-sm text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--ring)"
            >
              <option value="">Nenhuma lista</option>
              {lists?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>

          {/* Enriquecer checkbox */}
          <label className="flex items-center gap-2 text-sm text-(--text-secondary)">
            <input
              type="checkbox"
              checked={enrich}
              onChange={(e) => setEnrich(e.target.checked)}
              className="rounded border-(--border)"
            />
            Enriquecer após criar
          </label>

          <DialogFooter>
            <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" size="sm" disabled={isPending || !form.name.trim()}>
              {isPending && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
              Criar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
