"use client"

import { useEffect, useState } from "react"
import { Loader2, Save, Info, ExternalLink } from "lucide-react"
import {
  useTenant,
  useUpdateIntegrations,
  type UpdateIntegrationsBody,
} from "@/lib/api/hooks/use-tenant"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

// ── Página ────────────────────────────────────────────────────────────

export default function UnipolePage() {
  const { data: tenant, isLoading } = useTenant()
  const {
    mutate: saveIntegrations,
    isPending,
    isSuccess,
    isError,
    error,
  } = useUpdateIntegrations()

  const integration = tenant?.integration

  const [linkedinAccountId, setLinkedinAccountId] = useState("")
  const [gmailAccountId, setGmailAccountId] = useState("")

  // Sincroniza o formulário quando os dados carregam
  useEffect(() => {
    if (!integration) return
    setLinkedinAccountId(integration.unipile_linkedin_account_id ?? "")
    setGmailAccountId(integration.unipile_gmail_account_id ?? "")
  }, [integration])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const body: UpdateIntegrationsBody = {
      unipile_linkedin_account_id: linkedinAccountId.trim() || null,
      unipile_gmail_account_id: gmailAccountId.trim() || null,
    }
    saveIntegrations(body)
  }

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-(--text-tertiary)" aria-label="Carregando" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-(--text-primary)">Unipile</h1>
        <p className="mt-1 text-sm text-(--text-secondary)">
          Configure os IDs de conta Unipile para LinkedIn e Gmail.
        </p>
      </div>

      {/* Guia de como encontrar os IDs */}
      <div className="flex gap-3 rounded-lg border border-(--info-subtle) bg-(--info-subtle) px-4 py-3">
        <Info size={16} className="mt-0.5 shrink-0 text-(--info)" aria-hidden="true" />
        <div className="space-y-1 text-sm text-(--info-subtle-fg)">
          <p className="font-medium">Como encontrar os IDs de conta</p>
          <p>
            No painel da Unipile, acesse{" "}
            <strong>Accounts</strong> e copie o{" "}
            <code className="rounded bg-(--accent-subtle) px-1 font-mono text-xs text-(--accent-subtle-fg)">
              account_id
            </code>{" "}
            de cada conta conectada.
          </p>
          <a
            href="https://docs.unipile.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-medium underline-offset-2 hover:underline"
          >
            Documentação Unipile
            <ExternalLink size={12} aria-hidden="true" />
          </a>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* LinkedIn */}
        <Card>
          <CardHeader>
            <CardTitle>LinkedIn</CardTitle>
            <CardDescription>
              Conta Unipile usada para enviar convites e mensagens diretas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              <Label htmlFor="linkedin-account-id">Account ID</Label>
              <Input
                id="linkedin-account-id"
                placeholder="ex: abc12345-0000-0000-0000-000000000000"
                value={linkedinAccountId}
                onChange={(e) => setLinkedinAccountId(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Gmail */}
        <Card>
          <CardHeader>
            <CardTitle>Gmail (Google Workspace)</CardTitle>
            <CardDescription>
              Conta Unipile usada para enviar e-mails via Gmail API.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              <Label htmlFor="gmail-account-id">Account ID</Label>
              <Input
                id="gmail-account-id"
                placeholder="ex: def67890-0000-0000-0000-000000000000"
                value={gmailAccountId}
                onChange={(e) => setGmailAccountId(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Feedback do save */}
        {isError && (
          <p role="alert" className="rounded-md bg-(--danger-subtle) px-3 py-2 text-sm text-(--danger-subtle-fg)">
            {error instanceof Error ? error.message : "Erro ao salvar configurações."}
          </p>
        )}
        {isSuccess && (
          <p role="status" className="rounded-md bg-(--success-subtle) px-3 py-2 text-sm text-(--success-subtle-fg)">
            Configurações salvas com sucesso.
          </p>
        )}

        <div className="flex justify-end">
          <Button type="submit" disabled={isPending}>
            {isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                Salvando…
              </>
            ) : (
              <>
                <Save size={14} aria-hidden="true" />
                Salvar alterações
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
