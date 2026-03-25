"use client"

import {
  usePipedriveDryRun,
  type SandboxRun,
  type PipedriveDryRunResult,
} from "@/lib/api/hooks/use-sandbox"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, ExternalLink, User, Briefcase, StickyNote } from "lucide-react"
import { useState } from "react"
import { intentConfig } from "@/lib/utils"

interface SandboxPipedrivePreviewProps {
  run: SandboxRun
}

export function SandboxPipedrivePreview({ run }: SandboxPipedrivePreviewProps) {
  const pipedriveDryRun = usePipedriveDryRun()
  const [result, setResult] = useState<PipedriveDryRunResult | null>(null)

  // Only show when run has generated/approved steps
  const hasContent = run.steps.some((s) => s.status === "generated" || s.status === "approved")
  if (!hasContent && !result) return null

  async function handleDryRun() {
    try {
      const data = await pipedriveDryRun.mutateAsync(run.id)
      setResult(data)
    } catch {
      // handled by React Query
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-(--text-primary)">Pipedrive — Dry Run</h3>
        {!result && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleDryRun}
            disabled={pipedriveDryRun.isPending}
          >
            {pipedriveDryRun.isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                Simulando…
              </>
            ) : (
              <>
                <ExternalLink size={14} aria-hidden="true" />
                Simular Pipedrive
              </>
            )}
          </Button>
        )}
      </div>

      {result && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {result.leads.map((lead, i) => (
            <div
              key={i}
              className="rounded-md border border-(--border-default) bg-(--bg-surface) p-4 space-y-3"
            >
              {/* Lead header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <User size={14} className="text-(--text-tertiary)" aria-hidden="true" />
                  <span className="text-sm font-medium text-(--text-primary)">
                    {lead.lead_name}
                  </span>
                </div>
                {lead.intent && (
                  <Badge variant={intentConfig(lead.intent).variant}>
                    {intentConfig(lead.intent).label}
                  </Badge>
                )}
              </div>

              {lead.lead_company && (
                <p className="text-xs text-(--text-tertiary)">{lead.lead_company}</p>
              )}

              {/* Person info */}
              <div className="rounded-md bg-(--bg-overlay) p-2 text-xs space-y-1">
                <div className="flex items-center gap-1.5">
                  <User size={11} className="text-(--text-disabled)" aria-hidden="true" />
                  <span className="text-(--text-secondary)">
                    {lead.person.name}
                    {lead.person.email && ` · ${lead.person.email}`}
                  </span>
                </div>
                <Badge variant={lead.person.person_exists ? "success" : "info"}>
                  {lead.person.person_exists ? "Pessoa existente" : "Será criada"}
                </Badge>
              </div>

              {/* Deal info */}
              <div className="rounded-md bg-(--bg-overlay) p-2 text-xs space-y-1">
                <div className="flex items-center gap-1.5">
                  <Briefcase size={11} className="text-(--text-disabled)" aria-hidden="true" />
                  <span className="font-medium text-(--text-primary)">{lead.deal.title}</span>
                </div>
                <p className="text-(--text-secondary)">
                  Estágio: {lead.deal.stage} · Valor: R$ {lead.deal.value}
                </p>
              </div>

              {/* Note preview */}
              {lead.note_preview && (
                <div className="rounded-md bg-(--bg-overlay) p-2 text-xs">
                  <div className="mb-1 flex items-center gap-1.5">
                    <StickyNote size={11} className="text-(--text-disabled)" aria-hidden="true" />
                    <span className="font-medium text-(--text-secondary)">Nota</span>
                  </div>
                  <p className="line-clamp-3 text-(--text-tertiary)">{lead.note_preview}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
