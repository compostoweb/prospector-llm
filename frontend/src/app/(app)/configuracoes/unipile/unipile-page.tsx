"use client"

import { useEffect, useState } from "react"
import {
  Loader2,
  Save,
  Info,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Globe,
} from "lucide-react"
import {
  useTenant,
  useRegisterUnipileWebhook,
  useUnipileWebhookStatus,
  useUpdateIntegrations,
  type UpdateIntegrationsBody,
  type UnipileWebhookRegistrationResult,
  type UnipileWebhookStatus,
} from "@/lib/api/hooks/use-tenant"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  SettingsCallout,
  SettingsPageShell,
  SettingsPanel,
} from "@/components/settings/settings-shell"

// ── Página ────────────────────────────────────────────────────────────

export default function UnipolePage() {
  const { data: tenant, isLoading, isError, error } = useTenant()
  const {
    data: webhookStatus,
    isLoading: webhookLoading,
    isError: webhookLoadFailed,
    error: webhookError,
  } = useUnipileWebhookStatus()
  const {
    mutate: saveIntegrations,
    isPending,
    isSuccess,
    isError: saveError,
    error: saveErrorDetails,
  } = useUpdateIntegrations()
  const {
    mutate: registerWebhook,
    isPending: registerPending,
    data: registerResult,
    error: registerErrorDetails,
  } = useRegisterUnipileWebhook()

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
        <Loader2
          size={20}
          className="animate-spin text-(--text-tertiary)"
          aria-label="Carregando"
        />
      </div>
    )
  }

  return (
    <SettingsPageShell
      title="Unipile"
      description="Conecte as contas usadas pelo LinkedIn e pelo Gmail e acompanhe a prontidão operacional do webhook do inbox na mesma tela."
      width="wide"
    >
      <SettingsCallout
        icon={<Info size={16} aria-hidden="true" />}
        title="Como encontrar os IDs de conta"
      >
        <p>
          No painel da Unipile, acesse <strong>Accounts</strong> e copie o{" "}
          <code className="rounded bg-(--accent-subtle) px-1 font-mono text-xs text-(--accent-subtle-fg)">
            account_id
          </code>{" "}
          de cada conta conectada.
        </p>
        <a
          href={webhookStatus?.docs_url ?? "https://developer.unipile.com/docs/webhooks-2"}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 font-medium underline-offset-2 hover:underline"
        >
          Documentação Unipile
          <ExternalLink size={12} aria-hidden="true" />
        </a>
      </SettingsCallout>

      {isError ? (
        <SettingsCallout
          icon={<AlertTriangle size={16} aria-hidden="true" />}
          title="Não foi possível carregar a configuração da Unipile"
          className="border-(--warning-subtle) bg-(--warning-subtle) text-(--warning-subtle-fg)"
        >
          <p>{error instanceof Error ? error.message : "Erro ao carregar dados do tenant."}</p>
          <p>Confirme se a API do backend está acessível antes de editar os Account IDs.</p>
        </SettingsCallout>
      ) : null}

      <div className="space-y-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <SettingsPanel
              title="LinkedIn"
              description="Conta Unipile usada para enviar convites e mensagens diretas."
            >
              <div className="space-y-1.5">
                <Label htmlFor="linkedin-account-id">Account ID</Label>
                <Input
                  id="linkedin-account-id"
                  placeholder="ex: abc12345-0000-0000-0000-000000000000"
                  value={linkedinAccountId}
                  onChange={(e) => setLinkedinAccountId(e.target.value)}
                />
              </div>
            </SettingsPanel>

            <SettingsPanel
              title="Gmail (Google Workspace)"
              description="Conta Unipile usada para enviar e-mails via Gmail API."
            >
              <div className="space-y-1.5">
                <Label htmlFor="gmail-account-id">Account ID</Label>
                <Input
                  id="gmail-account-id"
                  placeholder="ex: def67890-0000-0000-0000-000000000000"
                  value={gmailAccountId}
                  onChange={(e) => setGmailAccountId(e.target.value)}
                />
              </div>
            </SettingsPanel>
          </div>

          <SettingsPanel
            title="Salvar alterações"
            description="Os IDs informados passam a ser usados pelas integrações do tenant."
          >
            <div className="space-y-3">
              {saveError ? (
                <p
                  role="alert"
                  className="rounded-md bg-(--danger-subtle) px-3 py-2 text-sm text-(--danger-subtle-fg)"
                >
                  {saveErrorDetails instanceof Error
                    ? saveErrorDetails.message
                    : "Erro ao salvar configurações."}
                </p>
              ) : null}
              {isSuccess ? (
                <p
                  role="status"
                  className="rounded-md bg-(--success-subtle) px-3 py-2 text-sm text-(--success-subtle-fg)"
                >
                  Configurações salvas com sucesso.
                </p>
              ) : null}

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
            </div>
          </SettingsPanel>
        </form>

        <SettingsPanel
          title="Webhook do inbox"
          description="Mostra a URL pública e a prontidão operacional do recebimento em tempo real."
        >
          {webhookLoading ? (
            <div className="flex items-center gap-2 text-sm text-(--text-tertiary)">
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              Carregando status do webhook…
            </div>
          ) : webhookLoadFailed ? (
            <div className="space-y-1 rounded-md bg-(--warning-subtle) px-3 py-2 text-sm text-(--warning-subtle-fg)">
              <p className="font-medium">Não foi possível carregar o status do webhook.</p>
              <p>{webhookError instanceof Error ? webhookError.message : "Erro inesperado."}</p>
            </div>
          ) : webhookStatus ? (
            <WebhookStatusPanel
              status={webhookStatus}
              onRegister={() => registerWebhook()}
              isRegistering={registerPending}
              {...(registerResult ? { registerResult } : {})}
              registerError={
                registerErrorDetails instanceof Error ? registerErrorDetails.message : null
              }
            />
          ) : null}
        </SettingsPanel>
      </div>
    </SettingsPageShell>
  )
}

function WebhookStatusPanel({
  status,
  onRegister,
  isRegistering,
  registerResult,
  registerError,
}: {
  status: UnipileWebhookStatus
  onRegister: () => void
  isRegistering: boolean
  registerResult?: UnipileWebhookRegistrationResult
  registerError: string | null
}) {
  const sourceAlignment =
    status.expected_sources.length > 0 &&
    status.expected_sources.every(
      (sourceStatus) =>
        sourceStatus.registered &&
        sourceStatus.enabled !== false &&
        sourceStatus.missing_events.length === 0 &&
        sourceStatus.extra_events.length === 0,
    )

  return (
    <div className="space-y-4 xl:space-y-5">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(280px,0.75fr)] xl:items-start">
        <div className="space-y-4 rounded-xl border border-(--border-default) bg-(--bg-page) p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className={status.ready ? statusPillClass.ready : statusPillClass.pending}>
              {status.ready ? "Pronto para receber eventos" : "Configuração pendente"}
            </span>
            <span className="text-xs text-(--text-tertiary)">
              HTTP {status.public_endpoint_status_code ?? "—"}
            </span>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="unipile-webhook-url">URL do webhook</Label>
            <Input id="unipile-webhook-url" value={status.url} readOnly />
            <p className="text-xs leading-5 text-(--text-tertiary)">
              Um POST sem autenticação retornar 401 é esperado e indica que o endpoint público está
              protegido.
            </p>
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-(--border-default) bg-(--bg-page) p-4 text-sm text-(--text-secondary)">
          <p className="font-medium text-(--text-primary)">Registro do webhook</p>
          <p>
            Você pode registrar o webhook pelo dashboard da Unipile ou pela API, desde que use a URL
            acima.
          </p>
          {status.registration_lookup_error ? (
            <div className="rounded-lg bg-(--warning-subtle) px-3 py-2 text-sm text-(--warning-subtle-fg)">
              {status.registration_lookup_error}
            </div>
          ) : null}
          {status.registered_in_unipile ? (
            <div className="rounded-lg bg-(--success-subtle) px-3 py-2 text-sm text-(--success-subtle-fg)">
              <p className="font-medium">Webhook já cadastrado na Unipile.</p>
              <p>
                {status.registered_webhooks.length === 1
                  ? "Cadastro detectado para a URL atual."
                  : `${status.registered_webhooks.length} webhooks detectados para a URL atual.`}
              </p>
            </div>
          ) : null}
          {registerError ? (
            <div className="rounded-lg bg-(--danger-subtle) px-3 py-2 text-sm text-(--danger-subtle-fg)">
              {registerError}
            </div>
          ) : null}
          {registerResult ? (
            <div className="rounded-lg bg-(--success-subtle) px-3 py-2 text-sm text-(--success-subtle-fg)">
              <p>{registerResult.message}</p>
              <div className="mt-2 space-y-1">
                {registerResult.webhooks.map((webhook) => (
                  <p key={`${webhook.source}-${webhook.webhook_id ?? "none"}`}>
                    {formatSourceLabel(webhook.source)}: {webhook.created ? "criado" : "já existia"}
                    {webhook.webhook_id ? ` (${webhook.webhook_id})` : ""}
                  </p>
                ))}
              </div>
            </div>
          ) : null}
          {status.api_registration_blockers.length > 0 ? (
            <div className="rounded-lg bg-(--warning-subtle) px-3 py-2 text-sm text-(--warning-subtle-fg)">
              {status.api_registration_blockers.map((blocker) => (
                <p key={blocker}>{blocker}</p>
              ))}
            </div>
          ) : null}
          <Button onClick={onRegister} disabled={!status.api_registration_ready || isRegistering}>
            {isRegistering ? (
              <>
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                Registrando…
              </>
            ) : (
              <>
                <ShieldCheck size={14} aria-hidden="true" />
                {status.registered_in_unipile
                  ? "Registrar novamente via API"
                  : "Registrar via API da Unipile"}
              </>
            )}
          </Button>
          <div className="flex flex-wrap gap-3 text-sm">
            <a
              href={status.dashboard_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-medium underline-offset-2 hover:underline"
            >
              Abrir dashboard
              <ExternalLink size={12} aria-hidden="true" />
            </a>
            <a
              href={status.docs_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-medium underline-offset-2 hover:underline"
            >
              Ver docs do webhook
              <ExternalLink size={12} aria-hidden="true" />
            </a>
          </div>
        </div>
      </div>

      <div className="grid gap-2 xl:grid-cols-2">
        <StatusRow
          icon={Globe}
          label="Endpoint público"
          ok={status.public_endpoint_healthy}
          detail={
            status.public_endpoint_status_code != null
              ? `HTTP ${status.public_endpoint_status_code}`
              : "Não foi possível validar o endpoint agora"
          }
        />
        <StatusRow
          icon={ShieldCheck}
          label="Secret configurado"
          ok={status.secret_configured}
          detail={
            status.secret_configured
              ? "Backend pronto para validar autenticação"
              : "Preencha UNIPILE_WEBHOOK_SECRET no ambiente"
          }
        />
        <StatusRow
          label="Conta LinkedIn vinculada"
          ok={status.linkedin_account_configured}
          detail={status.linkedin_account_configured ? "OK" : "Account ID ainda não definido"}
        />
        <StatusRow
          label="Conta Gmail vinculada"
          ok={status.gmail_account_configured}
          detail={status.gmail_account_configured ? "OK" : "Account ID ainda não definido"}
        />
        <StatusRow
          label="Registro via API pronto"
          ok={status.api_registration_ready}
          detail={
            status.api_registration_ready
              ? "Pode registrar automaticamente sem sair desta tela"
              : (status.api_registration_blockers[0] ??
                (status.api_registration_supported
                  ? "Finalize a configuração do webhook"
                  : "Sem API key/base URL para registro automático"))
          }
        />
        <StatusRow
          label="Cadastrado na Unipile"
          ok={status.registered_in_unipile}
          detail={
            status.registered_in_unipile
              ? `${status.registered_webhooks.length} webhook(s) encontrados para a URL atual`
              : (status.registration_lookup_error ?? "Nenhum webhook encontrado para esta URL")
          }
        />
        <StatusRow
          label="Sources alinhados"
          ok={sourceAlignment}
          detail={
            sourceAlignment
              ? "Todos os sources esperados pelo sistema estão ativos e com eventos compatíveis"
              : summarizeSourceAlignment(status.expected_sources)
          }
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-2 rounded-xl border border-(--border-default) bg-(--bg-page) p-4 xl:col-span-2">
          <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
            Sources esperados
          </p>
          <div className="grid gap-3 xl:grid-cols-3">
            {status.expected_sources.map((sourceStatus) => (
              <div key={sourceStatus.source} className="space-y-3 rounded-lg bg-(--bg-overlay) p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-(--text-primary)">
                      {sourceStatus.label}
                    </p>
                    <p className="text-xs text-(--text-tertiary)">{sourceStatus.source}</p>
                  </div>
                  <span
                    className={
                      sourceStatus.registered && sourceStatus.enabled !== false
                        ? statusPillClass.ready
                        : statusPillClass.pending
                    }
                  >
                    {sourceStatus.registered
                      ? sourceStatus.enabled === false
                        ? "desativado"
                        : "detectado"
                      : "faltando"}
                  </span>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
                    Eventos esperados
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {sourceStatus.expected_events.map((eventName) => (
                      <span
                        key={eventName}
                        className="rounded-full bg-(--bg-page) px-2.5 py-1 text-xs font-medium text-(--text-secondary)"
                      >
                        {eventName}
                      </span>
                    ))}
                  </div>
                </div>

                {sourceStatus.registered ? (
                  <div className="space-y-2 text-xs text-(--text-secondary)">
                    {sourceStatus.webhook_id ? <p>ID {sourceStatus.webhook_id}</p> : null}
                    <div className="flex flex-wrap gap-2">
                      {sourceStatus.registered_events.map((eventName) => (
                        <span
                          key={eventName}
                          className="rounded-full bg-(--accent-subtle) px-2.5 py-1 font-medium text-(--accent-subtle-fg)"
                        >
                          {eventName}
                        </span>
                      ))}
                    </div>
                    {sourceStatus.missing_events.length > 0 ? (
                      <p>Faltando: {sourceStatus.missing_events.join(", ")}</p>
                    ) : null}
                    {sourceStatus.extra_events.length > 0 ? (
                      <p>Extras: {sourceStatus.extra_events.join(", ")}</p>
                    ) : null}
                  </div>
                ) : (
                  <p className="text-xs text-(--text-secondary)">
                    Nenhum webhook deste source foi encontrado para a URL atual.
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-(--border-default) bg-(--bg-page) p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
            Headers aceitos
          </p>
          <div className="flex flex-wrap gap-2">
            {status.auth_headers.map((header) => (
              <span
                key={header}
                className="rounded-full bg-(--accent-subtle) px-2.5 py-1 text-xs font-medium text-(--accent-subtle-fg)"
              >
                {header}
              </span>
            ))}
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-(--border-default) bg-(--bg-page) p-4 xl:col-span-2">
          <p className="text-xs font-medium uppercase tracking-wider text-(--text-tertiary)">
            Cadastros detectados na Unipile
          </p>
          {status.registered_webhooks.length > 0 ? (
            <div className="space-y-3">
              <div className="grid gap-3 xl:grid-cols-2">
                {status.registered_webhooks.map((webhook, index) => (
                  <div
                    key={`${webhook.source ?? "unknown"}-${webhook.webhook_id ?? index}`}
                    className="space-y-3 rounded-lg bg-(--bg-overlay) p-3"
                  >
                    <div className="flex flex-wrap gap-2">
                      {webhook.webhook_id ? (
                        <span className="rounded-full bg-(--success-subtle) px-2.5 py-1 text-xs font-medium text-(--success-subtle-fg)">
                          ID {webhook.webhook_id}
                        </span>
                      ) : null}
                      <span className="rounded-full bg-(--bg-page) px-2.5 py-1 text-xs font-medium text-(--text-secondary)">
                        source {formatSourceLabel(webhook.source)}
                      </span>
                      <span
                        className={
                          webhook.enabled === false
                            ? "rounded-full bg-(--warning-subtle) px-2.5 py-1 text-xs font-medium text-(--warning-subtle-fg)"
                            : "rounded-full bg-(--success-subtle) px-2.5 py-1 text-xs font-medium text-(--success-subtle-fg)"
                        }
                      >
                        {webhook.enabled === false ? "desativado" : "ativo"}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {webhook.events.map((eventName) => (
                        <span
                          key={eventName}
                          className="rounded-full bg-(--accent-subtle) px-2.5 py-1 text-xs font-medium text-(--accent-subtle-fg)"
                        >
                          {eventName}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-(--text-secondary)">
              Nenhum cadastro persistente foi encontrado na Unipile para a URL atual.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusRow({
  label,
  ok,
  detail,
  icon: Icon,
}: {
  label: string
  ok: boolean
  detail: string
  icon?: typeof CheckCircle2
}) {
  const StatusIcon = ok ? CheckCircle2 : XCircle
  return (
    <div className="flex items-start gap-3 rounded-lg border border-(--border-default) bg-(--bg-page) px-3 py-3">
      {Icon ? (
        <Icon size={16} className="mt-0.5 shrink-0 text-(--text-tertiary)" aria-hidden="true" />
      ) : null}
      <div className="min-w-0 flex-1 space-y-0.5">
        <p className="text-sm font-medium text-(--text-primary)">{label}</p>
        <p className="text-xs leading-5 text-(--text-secondary)">{detail}</p>
      </div>
      <StatusIcon
        size={16}
        className={ok ? "mt-0.5 shrink-0 text-(--success)" : "mt-0.5 shrink-0 text-(--danger)"}
        aria-hidden="true"
      />
    </div>
  )
}

const statusPillClass = {
  ready:
    "inline-flex items-center rounded-full bg-(--success-subtle) px-3 py-1 text-xs font-semibold text-(--success-subtle-fg)",
  pending:
    "inline-flex items-center rounded-full bg-(--warning-subtle) px-3 py-1 text-xs font-semibold text-(--warning-subtle-fg)",
}

function summarizeSourceAlignment(statuses: UnipileWebhookStatus["expected_sources"]) {
  const pending = statuses
    .filter(
      (sourceStatus) =>
        !sourceStatus.registered ||
        sourceStatus.enabled === false ||
        sourceStatus.missing_events.length > 0 ||
        sourceStatus.extra_events.length > 0,
    )
    .map((sourceStatus) => {
      if (!sourceStatus.registered) {
        return `${sourceStatus.label}: não cadastrado`
      }
      if (sourceStatus.enabled === false) {
        return `${sourceStatus.label}: desativado`
      }
      if (sourceStatus.missing_events.length > 0) {
        return `${sourceStatus.label}: faltando ${sourceStatus.missing_events.join(", ")}`
      }
      if (sourceStatus.extra_events.length > 0) {
        return `${sourceStatus.label}: extras ${sourceStatus.extra_events.join(", ")}`
      }
      return `${sourceStatus.label}: revisar`
    })

  return pending.join(" | ") || "Cadastre ou detecte os sources esperados para comparar"
}

function formatSourceLabel(source: string | null) {
  switch (source) {
    case "messaging":
      return "messaging"
    case "users":
      return "users"
    case "mailing":
      return "mailing"
    case "account_status":
      return "account_status"
    default:
      return source ?? "desconhecido"
  }
}
