"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useCreateSandbox, type SandboxRun } from "@/lib/api/hooks/use-sandbox"
import { Loader2, Users, UserPlus, Shuffle } from "lucide-react"

interface SandboxCreateDialogProps {
  cadenceId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (run: SandboxRun) => void
}

type LeadMode = "fictitious" | "sample" | "custom"

export function SandboxCreateDialog({
  cadenceId,
  open,
  onOpenChange,
  onCreated,
}: SandboxCreateDialogProps) {
  const createSandbox = useCreateSandbox(cadenceId)

  const [leadMode, setLeadMode] = useState<LeadMode>("fictitious")
  const [leadCount, setLeadCount] = useState(3)

  async function handleCreate() {
    try {
      const run = await createSandbox.mutateAsync({
        lead_count: leadCount,
        use_fictitious: leadMode === "fictitious",
        lead_ids: null,
      })
      onCreated(run)
    } catch {
      // error handled by React Query
    }
  }

  const modes: { key: LeadMode; icon: typeof Users; label: string; desc: string }[] = [
    {
      key: "fictitious",
      icon: UserPlus,
      label: "Leads fictícios",
      desc: "Gera leads fictícios via IA com dados realistas",
    },
    {
      key: "sample",
      icon: Shuffle,
      label: "Amostra da lista",
      desc: "Usa leads reais da lista vinculada à cadência",
    },
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Novo teste no Sandbox</DialogTitle>
          <DialogDescription>Configure como gerar os leads e mensagens de teste.</DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Modo de leads */}
          <div className="space-y-2">
            <Label>Origem dos leads</Label>
            <div className="grid grid-cols-1 gap-2">
              {modes.map(({ key, icon: Icon, label, desc }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setLeadMode(key)}
                  className={`flex items-start gap-3 rounded-md border p-3 text-left transition-colors ${
                    leadMode === key
                      ? "border-(--accent) bg-(--accent-subtle)"
                      : "border-(--border-default) bg-(--bg-surface) hover:border-(--accent)"
                  }`}
                >
                  <Icon
                    size={16}
                    className={
                      leadMode === key ? "text-(--accent-subtle-fg)" : "text-(--text-tertiary)"
                    }
                    aria-hidden="true"
                  />
                  <div>
                    <p
                      className={`text-sm font-medium ${
                        leadMode === key ? "text-(--accent-subtle-fg)" : "text-(--text-primary)"
                      }`}
                    >
                      {label}
                    </p>
                    <p className="text-xs text-(--text-tertiary)">{desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Quantidade */}
          <div className="space-y-1.5">
            <Label htmlFor="lead-count">Quantidade de leads</Label>
            <div className="flex items-center gap-3">
              <input
                id="lead-count"
                type="range"
                min={1}
                max={10}
                value={leadCount}
                onChange={(e) => setLeadCount(Number(e.target.value))}
                aria-label="Quantidade de leads"
                className="flex-1 accent-(--accent)"
              />
              <span className="w-8 text-center text-sm font-semibold text-(--text-primary)">
                {leadCount}
              </span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleCreate} disabled={createSandbox.isPending}>
            {createSandbox.isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                Criando…
              </>
            ) : (
              "Criar teste"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
