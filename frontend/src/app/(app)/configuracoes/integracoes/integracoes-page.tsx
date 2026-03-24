"use client"

import { useState } from "react"
import { CheckCircle2, XCircle, ExternalLink, Info, Loader2, Save } from "lucide-react"
import { useTenant, useUpdateIntegrations } from "@/lib/api/hooks/use-tenant"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function StatusBadge({ connected }: { connected: boolean }) {
  return connected ? (
    <span className="flex items-center gap-1 rounded-full bg-(--success-subtle) px-2.5 py-1 text-xs font-medium text-(--success-subtle-fg)">
      <CheckCircle2 size={11} aria-hidden="true" />
      Conectado
    </span>
  ) : (
    <span className="flex items-center gap-1 rounded-full bg-(--bg-overlay) px-2.5 py-1 text-xs text-(--text-tertiary)">
      <XCircle size={11} aria-hidden="true" />
      Não conectado
    </span>
  )
}

export default function IntegracoesPage() {
  const { data: tenant, isLoading } = useTenant()
  const { mutate: updateIntegrations, isPending: saving } = useUpdateIntegrations()

  const integration = tenant?.integration

  // Pipedrive form state
  const [pdToken, setPdToken] = useState("")
  const [pdDomain, setPdDomain] = useState("")
  const [pdStageInterest, setPdStageInterest] = useState("")
  const [pdStageObjection, setPdStageObjection] = useState("")
  const [pdOwnerId, setPdOwnerId] = useState("")
  const [pdInitialized, setPdInitialized] = useState(false)

  // Sync form with loaded data (once)
  if (integration && !pdInitialized) {
    setPdToken("") // token not returned from API for security
    setPdDomain(integration.pipedrive_domain ?? "")
    setPdStageInterest(integration.pipedrive_stage_interest?.toString() ?? "")
    setPdStageObjection(integration.pipedrive_stage_objection?.toString() ?? "")
    setPdOwnerId(integration.pipedrive_owner_id?.toString() ?? "")
    setPdInitialized(true)
  }

  function handleSavePipedrive(e: React.FormEvent) {
    e.preventDefault()
    updateIntegrations({
      pipedrive_api_token: pdToken || null,
      pipedrive_domain: pdDomain || null,
      pipedrive_stage_interest: pdStageInterest ? Number(pdStageInterest) : null,
      pipedrive_stage_objection: pdStageObjection ? Number(pdStageObjection) : null,
      pipedrive_owner_id: pdOwnerId ? Number(pdOwnerId) : null,
    })
  }

  const linkedinConnected = !!integration?.unipile_linkedin_account_id
  const gmailConnected = !!integration?.unipile_gmail_account_id
  const pipedriveConnected = !!integration?.pipedrive_api_token

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-(--text-tertiary)" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-(--text-primary)">Integrações</h1>
        <p className="mt-1 text-sm text-(--text-secondary)">
          Canais de comunicação e serviços externos conectados ao Prospector.
        </p>
      </div>

      {/* Canais */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-(--text-primary)">Canais</h2>
        <div className="space-y-3">
          {/* LinkedIn */}
          <div className="flex items-start justify-between gap-4 rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-(--text-primary)">LinkedIn</p>
              <p className="mt-0.5 text-xs text-(--text-secondary)">
                Envio de convites e mensagens diretas via API Unipile.
              </p>
              {linkedinConnected && (
                <p className="mt-1 text-xs font-mono text-(--text-tertiary)">
                  {integration?.unipile_linkedin_account_id}
                </p>
              )}
            </div>
            <StatusBadge connected={linkedinConnected} />
          </div>

          {/* Gmail */}
          <div className="flex items-start justify-between gap-4 rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-(--text-primary)">E-mail (Google Workspace)</p>
              <p className="mt-0.5 text-xs text-(--text-secondary)">
                Envio de e-mails via Gmail API através da Unipile.
              </p>
              {gmailConnected && (
                <p className="mt-1 text-xs font-mono text-(--text-tertiary)">
                  {integration?.unipile_gmail_account_id}
                </p>
              )}
            </div>
            <StatusBadge connected={gmailConnected} />
          </div>
        </div>
      </section>

      {/* Pipedrive */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-(--text-primary)">CRM</h2>
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm">Pipedrive</CardTitle>
              <a
                href="https://developers.pipedrive.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-(--text-tertiary) hover:text-(--text-secondary)"
                aria-label="Documentação Pipedrive"
              >
                <ExternalLink size={12} aria-hidden="true" />
              </a>
            </div>
            <StatusBadge connected={pipedriveConnected} />
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSavePipedrive} className="space-y-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="pd-token">API Token</Label>
                  <Input
                    id="pd-token"
                    type="password"
                    value={pdToken}
                    onChange={(e) => setPdToken(e.target.value)}
                    placeholder="Token da API do Pipedrive"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pd-domain">Domínio</Label>
                  <Input
                    id="pd-domain"
                    value={pdDomain}
                    onChange={(e) => setPdDomain(e.target.value)}
                    placeholder="suaempresa"
                  />
                  <p className="text-[11px] text-(--text-tertiary)">
                    Ex: suaempresa (.pipedrive.com)
                  </p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pd-stage-interest">Stage ID (Interesse)</Label>
                  <Input
                    id="pd-stage-interest"
                    value={pdStageInterest}
                    onChange={(e) => setPdStageInterest(e.target.value)}
                    placeholder="ID do stage para leads com interesse"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pd-stage-objection">Stage ID (Objeção)</Label>
                  <Input
                    id="pd-stage-objection"
                    value={pdStageObjection}
                    onChange={(e) => setPdStageObjection(e.target.value)}
                    placeholder="ID do stage para leads com objeção"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pd-owner">Owner ID</Label>
                  <Input
                    id="pd-owner"
                    value={pdOwnerId}
                    onChange={(e) => setPdOwnerId(e.target.value)}
                    placeholder="ID do proprietário padrão dos deals"
                  />
                </div>
              </div>

              <Button type="submit" size="sm" disabled={saving}>
                {saving ? (
                  <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                ) : (
                  <Save size={14} aria-hidden="true" />
                )}
                Salvar Pipedrive
              </Button>
            </form>
          </CardContent>
        </Card>
      </section>

      <div className="flex items-start gap-2 rounded-md border border-(--border-default) bg-(--bg-overlay) px-4 py-3 text-xs text-(--text-secondary)">
        <Info size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span>
          Para conectar uma conta LinkedIn ou Gmail, configure as credenciais{" "}
          <code className="font-mono">UNIPILE_API_KEY</code> e{" "}
          <code className="font-mono">UNIPILE_BASE_URL</code> no servidor e utilize o fluxo de
          autenticação OAuth da Unipile.
        </span>
      </div>
    </div>
  )
}
