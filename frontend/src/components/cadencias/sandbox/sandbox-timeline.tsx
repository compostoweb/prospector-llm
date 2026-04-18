"use client"

import { useMemo } from "react"
import type { SandboxRun } from "@/lib/api/hooks/use-sandbox"
import type { TestEmailTransportSummary } from "@/lib/cadences/test-email-transport"
import { SandboxStepCard } from "./sandbox-step-card"
import { Users } from "lucide-react"

interface SandboxTimelineProps {
  run: SandboxRun
  emailTransportSummary: TestEmailTransportSummary
}

interface LeadGroup {
  leadId: string | null
  leadName: string
  leadCompany: string
  steps: SandboxRun["steps"]
}

export function SandboxTimeline({ run, emailTransportSummary }: SandboxTimelineProps) {
  const grouped = useMemo(() => {
    const map = new Map<string, LeadGroup>()

    for (const step of run.steps) {
      const key = step.lead_id ?? step.lead_name ?? step.fictitious_lead_data?.name ?? `fict-${step.id}`
      if (!map.has(key)) {
        map.set(key, {
          leadId: step.lead_id,
          leadName: step.lead_name ?? step.fictitious_lead_data?.name ?? "Lead",
          leadCompany: step.lead_company ?? step.fictitious_lead_data?.company ?? "",
          steps: [],
        })
      }
      const group = map.get(key)
      if (group) group.steps.push(step)
    }

    // Sort steps within each group by step_number
    for (const group of map.values()) {
      group.steps.sort((a, b) => a.step_number - b.step_number)
    }

    return Array.from(map.values())
  }, [run.steps])

  if (run.steps.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-(--border-default) bg-(--bg-surface) px-6 py-8 text-center">
        <p className="text-sm text-(--text-secondary)">
          Nenhum passo gerado ainda. Clique em &quot;Gerar todas&quot; para começar.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {grouped.map((group, gi) => (
        <div key={group.leadId ?? gi}>
          {/* Lead header */}
          <div className="mb-3 flex items-center gap-2">
            <Users size={14} className="text-(--text-tertiary)" aria-hidden="true" />
            <span className="text-sm font-semibold text-(--text-primary)">{group.leadName}</span>
            {group.leadCompany && (
              <span className="text-xs text-(--text-tertiary)">· {group.leadCompany}</span>
            )}
          </div>

          {/* Steps timeline */}
          <div className="relative ml-2 space-y-3 border-l-2 border-(--border-subtle) pl-5">
            {group.steps.map((step) => (
              <div key={step.id} className="relative">
                {/* Timeline dot */}
                <div
                  className={`absolute -left-6 top-4 h-2.5 w-2.5 rounded-full border-2 border-(--bg-surface) ${
                    step.status === "approved"
                      ? "bg-(--success)"
                      : step.status === "rejected"
                        ? "bg-(--danger)"
                        : step.status === "generated"
                          ? "bg-(--accent)"
                          : "bg-(--text-disabled)"
                  }`}
                />
                <SandboxStepCard step={step} emailTransportSummary={emailTransportSummary} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
