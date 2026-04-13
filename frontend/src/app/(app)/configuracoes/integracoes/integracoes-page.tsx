"use client"

import { useEffect, useState } from "react"
import { CheckCircle2, XCircle, ExternalLink, Info, Loader2, Save, AlertTriangle } from "lucide-react"
import { useTenant, useUpdateIntegrations } from "@/lib/api/hooks/use-tenant"
import {
  usePipedrivePipelines,
  usePipedriveStages,
  usePipedriveUsers,
} from "@/lib/api/hooks/use-pipedrive"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  SettingsCallout,
  SettingsPageShell,
  SettingsPanel,
} from "@/components/settings/settings-shell"

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
  const { data: tenant, isLoading, isError, error } = useTenant()
  const { mutate: updateIntegrations, isPending: saving } = useUpdateIntegrations()

  const integration = tenant?.integration

  // Pipedrive form state
  const [pdToken, setPdToken] = useState("")
  const [pdDomain, setPdDomain] = useState("")
  const [pdPipelineId, setPdPipelineId] = useState<number | null>(null)
  const [pdStageInterest, setPdStageInterest] = useState("")
  const [pdStageObjection, setPdStageObjection] = useState("")
  const [pdOwnerId, setPdOwnerId] = useState("")
  const [pdInitialized, setPdInitialized] = useState(false)

  const pipedriveConnected = !!integration?.pipedrive_api_token_set

  // Pipedrive metadata hooks — only fetch when connected
  const {
    data: pipelines,
    isLoading: loadingPipelines,
    isError: pipelinesError,
    error: pipelinesErrorDetails,
  } = usePipedrivePipelines(pipedriveConnected)
  const { data: stages, isLoading: loadingStages } = usePipedriveStages(
    pdPipelineId,
    pipedriveConnected,
  )
  const {
    data: users,
    isLoading: loadingUsers,
    isError: usersError,
    error: usersErrorDetails,
  } = usePipedriveUsers(pipedriveConnected)

  useEffect(() => {
    if (!integration || pdInitialized) return
    setPdToken("")
    setPdDomain(integration.pipedrive_domain ?? "")
    setPdStageInterest(integration.pipedrive_stage_interest?.toString() ?? "")
    setPdStageObjection(integration.pipedrive_stage_objection?.toString() ?? "")
    setPdOwnerId(integration.pipedrive_owner_id?.toString() ?? "")
    setPdInitialized(true)
  }, [integration, pdInitialized])

  useEffect(() => {
    if (!stages || stages.length === 0 || pdPipelineId !== null || !pdStageInterest) return
    const match = stages.find((s) => s.id === Number(pdStageInterest))
    if (match) setPdPipelineId(match.pipeline_id)
  }, [stages, pdPipelineId, pdStageInterest])

  function handleSavePipedrive(e: React.FormEvent) {
    e.preventDefault()
    const body: Record<string, unknown> = {
      pipedrive_domain: pdDomain || null,
      pipedrive_stage_interest: pdStageInterest ? Number(pdStageInterest) : null,
      pipedrive_stage_objection: pdStageObjection ? Number(pdStageObjection) : null,
      pipedrive_owner_id: pdOwnerId ? Number(pdOwnerId) : null,
    }
    // Only send token when user typed a new one (avoid clearing existing)
    if (pdToken) {
      body.pipedrive_api_token = pdToken
    }
    updateIntegrations(body)
  }

  const linkedinConnected = !!integration?.unipile_linkedin_account_id
  const gmailConnected = !!integration?.unipile_gmail_account_id

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-(--text-tertiary)" />
      </div>
    )
  }

  return (
    <SettingsPageShell
      title="Integrações"
      description="Centralize o status dos canais e do CRM em uma disposição mais compacta e útil no desktop."
      width="wide"
    >
      {isError || pipelinesError || usersError ? (
        <SettingsCallout
          icon={<AlertTriangle size={13} aria-hidden="true" />}
          title="Nem todas as integrações puderam ser carregadas"
          className="border-(--warning-subtle) bg-(--warning-subtle) text-(--warning-subtle-fg)"
        >
          {isError ? (
            <p>{error instanceof Error ? error.message : "Falha ao carregar dados do tenant."}</p>
          ) : null}
          {pipelinesError ? (
            <p>
              Pipelines do Pipedrive: {pipelinesErrorDetails instanceof Error ? pipelinesErrorDetails.message : "falha ao carregar pipelines."}
            </p>
          ) : null}
          {usersError ? (
            <p>
              Usuários do Pipedrive: {usersErrorDetails instanceof Error ? usersErrorDetails.message : "falha ao carregar usuários."}
            </p>
          ) : null}
          <p>Revise o backend e as credenciais do Pipedrive antes de salvar alterações operacionais.</p>
        </SettingsCallout>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_320px]">
        <SettingsPanel
          title="Pipedrive"
          description="Configure token, pipeline, stages e responsável pelos deals sincronizados."
          headerAside={
            <div className="flex items-center gap-2">
              <a
                href="https://developers.pipedrive.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-(--text-tertiary) hover:text-(--text-secondary)"
                aria-label="Documentação Pipedrive"
              >
                <ExternalLink size={12} aria-hidden="true" />
              </a>
              <StatusBadge connected={pipedriveConnected} />
            </div>
          }
        >
          <form onSubmit={handleSavePipedrive} className="space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="pd-token">API Token</Label>
                <div className="relative">
                  <Input
                    id="pd-token"
                    type="password"
                    value={pdToken}
                    onChange={(e) => setPdToken(e.target.value)}
                    placeholder={
                      pipedriveConnected ? "••••••••••••••••" : "Token da API do Pipedrive"
                    }
                  />
                  {pipedriveConnected && !pdToken && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[11px] text-emerald-600">
                      <CheckCircle2 size={12} />
                      Configurado
                    </span>
                  )}
                </div>
                {pipedriveConnected && (
                  <p className="text-[11px] text-(--text-tertiary)">
                    Deixe em branco para manter o token atual.
                  </p>
                )}
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

              {/* Pipeline selector — filtra os stages */}
              <div className="space-y-1.5">
                <Label>Pipeline</Label>
                <Select
                  value={pdPipelineId?.toString() ?? ""}
                  onValueChange={(v) => {
                    setPdPipelineId(Number(v))
                    setPdStageInterest("")
                    setPdStageObjection("")
                  }}
                  disabled={!pipedriveConnected}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={loadingPipelines ? "Carregando..." : "Selecione o pipeline"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {pipelines?.map((p) => (
                      <SelectItem key={p.id} value={p.id.toString()}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Stage — Interesse */}
              <div className="space-y-1.5">
                <Label>Stage (Interesse)</Label>
                <Select
                  value={pdStageInterest}
                  onValueChange={setPdStageInterest}
                  disabled={!pipedriveConnected || !pdPipelineId}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={loadingStages ? "Carregando..." : "Selecione o stage"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {stages?.map((s) => (
                      <SelectItem key={s.id} value={s.id.toString()}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Stage — Objeção */}
              <div className="space-y-1.5">
                <Label>Stage (Objeção)</Label>
                <Select
                  value={pdStageObjection}
                  onValueChange={setPdStageObjection}
                  disabled={!pipedriveConnected || !pdPipelineId}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={loadingStages ? "Carregando..." : "Selecione o stage"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {stages?.map((s) => (
                      <SelectItem key={s.id} value={s.id.toString()}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Owner (usuário) */}
              <div className="space-y-1.5">
                <Label>Proprietário dos Deals</Label>
                <Select
                  value={pdOwnerId}
                  onValueChange={setPdOwnerId}
                  disabled={!pipedriveConnected}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={loadingUsers ? "Carregando..." : "Selecione o proprietário"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {users?.map((u) => (
                      <SelectItem key={u.id} value={u.id.toString()}>
                        {u.name} ({u.email})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
        </SettingsPanel>

        <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <SettingsPanel
            title="Canais conectados"
            description="Resumo rápido das integrações usadas no dispatch."
          >
            <div className="grid gap-3">
              <div className="flex items-start justify-between gap-4 rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-3.5">
                <div className="flex-1">
                  <p className="text-sm font-medium text-(--text-primary)">LinkedIn</p>
                  <p className="mt-0.5 text-xs text-(--text-secondary)">
                    Envio de convites e mensagens diretas via API Unipile.
                  </p>
                  {linkedinConnected ? (
                    <p className="mt-1 text-xs font-mono text-(--text-tertiary)">
                      {integration?.unipile_linkedin_account_id}
                    </p>
                  ) : null}
                </div>
                <StatusBadge connected={linkedinConnected} />
              </div>

              <div className="flex items-start justify-between gap-4 rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-3.5">
                <div className="flex-1">
                  <p className="text-sm font-medium text-(--text-primary)">
                    E-mail (Google Workspace)
                  </p>
                  <p className="mt-0.5 text-xs text-(--text-secondary)">
                    Envio de e-mails via Gmail API através da Unipile.
                  </p>
                  {gmailConnected ? (
                    <p className="mt-1 text-xs font-mono text-(--text-tertiary)">
                      {integration?.unipile_gmail_account_id}
                    </p>
                  ) : null}
                </div>
                <StatusBadge connected={gmailConnected} />
              </div>
            </div>
          </SettingsPanel>

          <SettingsCallout
            icon={<Info size={13} aria-hidden="true" />}
            title="Dependências de conexão"
          >
            <span>
              Para conectar LinkedIn ou Gmail, configure as credenciais{" "}
              <code className="font-mono">UNIPILE_API_KEY</code> e{" "}
              <code className="font-mono">UNIPILE_BASE_URL</code> no servidor e utilize o fluxo de
              autenticação OAuth da Unipile.
            </span>
          </SettingsCallout>
        </div>
      </div>
    </SettingsPageShell>
  )
}
