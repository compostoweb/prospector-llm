"use client"

import { Trash2 } from "lucide-react"
import { toast } from "sonner"
import { type ReactNode } from "react"
import { usePermanentDeleteLead, type Lead } from "@/lib/api/hooks/use-leads"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

interface LeadDeleteDialogProps {
  lead: Lead
  trigger?: ReactNode
  onDeleted?: () => void
}

export function LeadDeleteDialog({ lead, trigger, onDeleted }: LeadDeleteDialogProps) {
  const deleteLead = usePermanentDeleteLead()

  async function handleDelete() {
    try {
      await deleteLead.mutateAsync(lead.id)
      toast.success("Lead excluído definitivamente")
      onDeleted?.()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao excluir lead")
    }
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        {trigger ?? (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-(--text-tertiary) hover:text-(--danger)"
          >
            <Trash2 size={14} aria-hidden="true" />
          </Button>
        )}
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Excluir lead definitivamente?</AlertDialogTitle>
          <AlertDialogDescription>
            {lead.name} será removido do sistema. Essa ação não pode ser desfeita.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction
            className="bg-(--danger) text-white hover:opacity-90"
            onClick={handleDelete}
          >
            Excluir definitivamente
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
