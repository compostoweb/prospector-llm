"use client"

import { useEffect, useState } from "react"
import { Pencil, Loader2 } from "lucide-react"
import { useUpdateLead, type Lead } from "@/lib/api/hooks/use-leads"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button, type ButtonProps } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

interface LeadEditDialogProps {
  lead: Lead
  size?: ButtonProps["size"]
  variant?: ButtonProps["variant"]
  iconOnly?: boolean
}

interface LeadEditFormState {
  name: string
  linkedin_url: string
  company: string
  website: string
  email_corporate: string
  email_personal: string
  phone: string
  segment: string
  city: string
  location: string
  job_title: string
  notes: string
}

function buildFormState(lead: Lead): LeadEditFormState {
  return {
    name: lead.name,
    linkedin_url: lead.linkedin_url ?? "",
    company: lead.company ?? "",
    website: lead.website ?? "",
    email_corporate: lead.email_corporate ?? "",
    email_personal: lead.email_personal ?? "",
    phone: lead.phone ?? "",
    segment: lead.segment ?? "",
    city: lead.city ?? "",
    location: lead.location ?? "",
    job_title: lead.job_title ?? "",
    notes: lead.notes ?? "",
  }
}

export function LeadEditDialog({
  lead,
  size = "sm",
  variant = "outline",
  iconOnly = false,
}: LeadEditDialogProps) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<LeadEditFormState>(() => buildFormState(lead))
  const updateLead = useUpdateLead()

  useEffect(() => {
    if (open) {
      setForm(buildFormState(lead))
    }
  }, [lead, open])

  function setField(field: keyof LeadEditFormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function toNullable(value: string): string | null {
    const normalized = value.trim()
    return normalized ? normalized : null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) return

    updateLead.mutate(
      {
        id: lead.id,
        name: form.name.trim(),
        linkedin_url: toNullable(form.linkedin_url),
        company: toNullable(form.company),
        website: toNullable(form.website),
        email_corporate: toNullable(form.email_corporate),
        email_personal: toNullable(form.email_personal),
        phone: toNullable(form.phone),
        segment: toNullable(form.segment),
        city: toNullable(form.city),
        location: toNullable(form.location),
        job_title: toNullable(form.job_title),
        notes: toNullable(form.notes),
      },
      {
        onSuccess: () => setOpen(false),
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant={variant}
          size={iconOnly ? "icon" : size}
          aria-label={iconOnly ? "Editar lead" : undefined}
        >
          <Pencil size={14} aria-hidden="true" />
          {!iconOnly && "Editar"}
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Editar lead</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="lead-edit-name">Nome *</Label>
              <Input
                id="lead-edit-name"
                value={form.name}
                onChange={(e) => setField("name", e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="lead-edit-linkedin">LinkedIn URL</Label>
              <Input
                id="lead-edit-linkedin"
                value={form.linkedin_url}
                onChange={(e) => setField("linkedin_url", e.target.value)}
                placeholder="https://linkedin.com/in/..."
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-company">Empresa</Label>
              <Input
                id="lead-edit-company"
                value={form.company}
                onChange={(e) => setField("company", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-job">Cargo</Label>
              <Input
                id="lead-edit-job"
                value={form.job_title}
                onChange={(e) => setField("job_title", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-website">Website</Label>
              <Input
                id="lead-edit-website"
                value={form.website}
                onChange={(e) => setField("website", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-segment">Segmento</Label>
              <Input
                id="lead-edit-segment"
                value={form.segment}
                onChange={(e) => setField("segment", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-email-corporate">Email corporativo</Label>
              <Input
                id="lead-edit-email-corporate"
                type="email"
                value={form.email_corporate}
                onChange={(e) => setField("email_corporate", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-email-personal">Email pessoal</Label>
              <Input
                id="lead-edit-email-personal"
                type="email"
                value={form.email_personal}
                onChange={(e) => setField("email_personal", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-phone">Telefone</Label>
              <Input
                id="lead-edit-phone"
                value={form.phone}
                onChange={(e) => setField("phone", e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="lead-edit-city">Cidade</Label>
              <Input
                id="lead-edit-city"
                value={form.city}
                onChange={(e) => setField("city", e.target.value)}
              />
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="lead-edit-location">Localização</Label>
              <Input
                id="lead-edit-location"
                value={form.location}
                onChange={(e) => setField("location", e.target.value)}
              />
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <Label htmlFor="lead-edit-notes">Notas</Label>
              <Textarea
                id="lead-edit-notes"
                rows={4}
                value={form.notes}
                onChange={(e) => setField("notes", e.target.value)}
                placeholder="Observações sobre o lead"
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" size="sm" disabled={updateLead.isPending || !form.name.trim()}>
              {updateLead.isPending && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
              Salvar alterações
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}