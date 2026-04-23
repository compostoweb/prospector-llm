"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Plus, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { LLMConfigForm, type LLMConfig } from "@/components/cadencias/llm-config-form"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useTenant, useUpdateIntegrations } from "@/lib/api/hooks/use-tenant"

const DEFAULT_COLD_EMAIL_LLM = {
  llm_provider: "openai" as const,
  llm_model: "gpt-5.4-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

function ColdEmailAIModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data: tenant } = useTenant()
  const updateIntegrations = useUpdateIntegrations()
  const integration = tenant?.integration

  const [llmConfig, setLlmConfig] = useState<LLMConfig>(DEFAULT_COLD_EMAIL_LLM)

  useEffect(() => {
    if (integration) {
      setLlmConfig({
        llm_provider: (integration.cold_email_llm_provider ??
          DEFAULT_COLD_EMAIL_LLM.llm_provider) as LLMConfig["llm_provider"],
        llm_model: integration.cold_email_llm_model ?? DEFAULT_COLD_EMAIL_LLM.llm_model,
        llm_temperature:
          integration.cold_email_llm_temperature ?? DEFAULT_COLD_EMAIL_LLM.llm_temperature,
        llm_max_tokens:
          integration.cold_email_llm_max_tokens ?? DEFAULT_COLD_EMAIL_LLM.llm_max_tokens,
      })
    }
  }, [integration])

  async function handleSave() {
    try {
      await updateIntegrations.mutateAsync({
        cold_email_llm_provider: llmConfig.llm_provider,
        cold_email_llm_model: llmConfig.llm_model,
        cold_email_llm_temperature: llmConfig.llm_temperature,
        cold_email_llm_max_tokens: llmConfig.llm_max_tokens,
      })
      toast.success("Configuração de IA para Cold Email salva.")
      onClose()
    } catch {
      toast.error("Erro ao salvar configuração.")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl p-5 sm:p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles size={16} className="text-(--accent)" />
            IA — Cold Email
          </DialogTitle>
          <DialogDescription className="text-sm leading-6">
            Modelo padrão usado ao criar novas campanhas de e-mail.
          </DialogDescription>
        </DialogHeader>
        <div className="py-1">
          <LLMConfigForm value={llmConfig} onChange={setLlmConfig} variant="dialog" />
        </div>
        <DialogFooter className="pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-(--border-default) px-4 py-2 text-sm text-(--text-secondary) hover:bg-(--bg-overlay)"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={updateIntegrations.isPending}
            className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            Salvar configuração
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function ColdEmailOverviewActions() {
  const [aiModalOpen, setAiModalOpen] = useState(false)

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setAiModalOpen(true)}
          className="flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--bg-overlay)"
        >
          <Sparkles size={14} aria-hidden="true" />
          IA
        </button>
        <Link
          href="/cold-email/nova-campanha"
          className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <Plus size={14} aria-hidden="true" />
          Nova campanha e-mail
        </Link>
      </div>

      <ColdEmailAIModal open={aiModalOpen} onClose={() => setAiModalOpen(false)} />
    </>
  )
}
