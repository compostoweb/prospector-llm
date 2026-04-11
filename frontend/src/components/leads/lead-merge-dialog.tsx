"use client"

import { useEffect, useMemo, useState } from "react"
import { GitMerge, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { type Lead, useMergeLeads } from "@/lib/api/hooks/use-leads"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"

interface LeadMergeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  leads: Lead[]
  onMerged?: (mergedLeadId: string) => void
}

export function LeadMergeDialog({ open, onOpenChange, leads, onMerged }: LeadMergeDialogProps) {
  const mergeLeads = useMergeLeads()
  const suggestion = useMemo(() => suggestPrimaryLead(leads), [leads])
  const [primaryLeadId, setPrimaryLeadId] = useState<string>(suggestion?.id ?? "")

  useEffect(() => {
    setPrimaryLeadId(suggestion?.id ?? "")
  }, [suggestion])

  async function handleMerge() {
    if (!primaryLeadId) return

    const secondaryIds = leads.filter((lead) => lead.id !== primaryLeadId).map((lead) => lead.id)
    if (secondaryIds.length === 0) return

    try {
      const result = await mergeLeads.mutateAsync({
        primary_lead_id: primaryLeadId,
        secondary_lead_ids: secondaryIds,
      })
      toast.success("Leads mesclados com sucesso")
      onMerged?.(result.lead.id)
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao mesclar leads")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Mesclar leads</DialogTitle>
          <DialogDescription>
            Escolha o lead principal. Os demais terão listas, interações e histórico migrados para
            ele.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border border-(--border-default) bg-(--bg-overlay) p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-(--text-primary)">
              <Sparkles size={14} aria-hidden="true" className="text-(--accent)" />
              Sugestão automática
            </div>
            <p className="mt-2 text-sm text-(--text-secondary)">
              {suggestion
                ? `${suggestion.name} foi sugerido como lead principal por ter o cadastro mais completo.`
                : "Selecione manualmente qual lead deve permanecer como principal."}
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-(--text-primary)">Lead principal</label>
            <Select value={primaryLeadId} onValueChange={setPrimaryLeadId}>
              <SelectTrigger>
                <SelectValue placeholder="Selecione o lead principal" />
              </SelectTrigger>
              <SelectContent>
                {leads.map((lead) => (
                  <SelectItem key={lead.id} value={lead.id}>
                    {lead.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            {leads.map((lead) => {
              const isPrimary = lead.id === primaryLeadId
              return (
                <div
                  key={lead.id}
                  className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-(--text-primary)">{lead.name}</p>
                        {isPrimary && <Badge>Sugerido principal</Badge>}
                      </div>
                      <p className="mt-1 text-xs text-(--text-secondary)">
                        {[lead.job_title, lead.company, lead.email_corporate ?? lead.email_personal]
                          .filter(Boolean)
                          .join(" • ") || "Sem dados de contato"}
                      </p>
                    </div>
                    <Badge variant={isPrimary ? "default" : "outline"}>
                      {isPrimary ? "Principal" : "Será incorporado"}
                    </Badge>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleMerge} disabled={!primaryLeadId || mergeLeads.isPending}>
            <GitMerge size={14} aria-hidden="true" />
            Mesclar selecionados
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function suggestPrimaryLead(leads: Lead[]): Lead | null {
  if (leads.length === 0) return null

  return (
    [...leads].sort((left, right) => scoreLeadForMerge(right) - scoreLeadForMerge(left))[0] ?? null
  )
}

function scoreLeadForMerge(lead: Lead) {
  let score = 0
  if (lead.email_corporate || lead.email_personal) score += 3
  if (lead.phone) score += 2
  if (lead.linkedin_url) score += 2
  if (lead.company) score += 1
  if (lead.job_title) score += 1
  if (lead.website || lead.company_domain) score += 1
  if (lead.status === "in_cadence") score += 2
  if (lead.status === "converted") score += 3
  score += lead.lead_lists.length
  score += lead.score ?? 0
  return score
}
