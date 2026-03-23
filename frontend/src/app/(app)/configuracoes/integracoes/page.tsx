"use client"

import { useState } from "react"
import { CheckCircle2, XCircle, ExternalLink, RefreshCw, Info } from "lucide-react"
import { useSession } from "next-auth/react"

interface IntegrationStatus {
  id: string
  name: string
  description: string
  connected: boolean
  accountLabel?: string
  docsUrl?: string
}

const INTEGRATIONS: IntegrationStatus[] = [
  {
    id: "linkedin",
    name: "LinkedIn",
    description: "Envio de convites e mensagens diretas via API Unipile.",
    connected: false,
  },
  {
    id: "email",
    name: "E-mail (Google Workspace)",
    description: "Envio de e-mails via Gmail API através da Unipile.",
    connected: false,
  },
  {
    id: "unipile",
    name: "Unipile",
    description: "Hub de conectores para LinkedIn e Gmail.",
    connected: false,
    docsUrl: "https://docs.unipile.com",
  },
]

export default function IntegracoesPage() {
  const { data: session } = useSession()
  const [refreshing, setRefreshing] = useState<string | null>(null)

  async function handleRefresh(id: string) {
    setRefreshing(id)
    await new Promise((resolve) => setTimeout(resolve, 800))
    setRefreshing(null)
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Integrações</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Canais de comunicação e serviços externos conectados ao Prospector.
        </p>
      </div>

      {/* Tenant */}
      {session?.user && (
        <div className="flex items-center gap-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent-subtle)] text-sm font-semibold text-[var(--accent-subtle-fg)]">
            {(session.user.name ?? session.user.email ?? "U")[0]?.toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">
              {session.user.name ?? session.user.email}
            </p>
            <p className="text-xs text-[var(--text-tertiary)]">Conta ativa</p>
          </div>
        </div>
      )}

      {/* Integrações */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Canais</h2>
        <div className="space-y-3">
          {INTEGRATIONS.map((integration) => (
            <div
              key={integration.id}
              className="flex items-start justify-between gap-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-[var(--text-primary)]">
                    {integration.name}
                  </p>
                  {integration.docsUrl && (
                    <a
                      href={integration.docsUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
                      aria-label={`Documentação ${integration.name}`}
                    >
                      <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                  {integration.description}
                </p>
                {integration.accountLabel && (
                  <p className="mt-1 text-xs font-mono text-[var(--text-tertiary)]">
                    {integration.accountLabel}
                  </p>
                )}
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={() => void handleRefresh(integration.id)}
                  disabled={refreshing === integration.id}
                  aria-label={`Atualizar status ${integration.name}`}
                  className="rounded-[var(--radius-md)] p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-overlay)] hover:text-[var(--text-secondary)] disabled:opacity-50"
                >
                  <RefreshCw
                    size={13}
                    className={refreshing === integration.id ? "animate-spin" : ""}
                    aria-hidden="true"
                  />
                </button>

                {integration.connected ? (
                  <span className="flex items-center gap-1 rounded-full bg-[var(--success-subtle)] px-2.5 py-1 text-xs font-medium text-[var(--success-subtle-fg)]">
                    <CheckCircle2 size={11} aria-hidden="true" />
                    Conectado
                  </span>
                ) : (
                  <span className="flex items-center gap-1 rounded-full bg-[var(--bg-overlay)] px-2.5 py-1 text-xs text-[var(--text-tertiary)]">
                    <XCircle size={11} aria-hidden="true" />
                    Não conectado
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-overlay)] px-4 py-3 text-xs text-[var(--text-secondary)]">
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
