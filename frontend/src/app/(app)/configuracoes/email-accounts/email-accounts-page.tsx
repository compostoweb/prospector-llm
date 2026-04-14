"use client"

import { useState } from "react"
import {
  Mail,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
  Server,
  Zap,
  Pencil,
  RefreshCw,
  AlertTriangle,
} from "lucide-react"
import {
  useEmailAccounts,
  useCreateUnipileAccount,
  useCreateSMTPAccount,
  useTestSMTP,
  useUpdateEmailAccount,
  useDeleteEmailAccount,
  useGoogleOAuthUrl,
  useFetchGmailSignature,
  type EmailAccount,
  type CreateUnipileAccountBody,
  type CreateSMTPAccountBody,
} from "@/lib/api/hooks/use-email-accounts"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { RichTextEditor } from "@/components/ui/rich-text-editor"
import {
  SettingsCallout,
  SettingsPageShell,
  SettingsPanel,
} from "@/components/settings/settings-shell"

// ── Helpers ───────────────────────────────────────────────────────────

const PROVIDER_LABELS: Record<string, string> = {
  unipile_gmail: "Unipile Gmail",
  google_oauth: "Gmail OAuth",
  smtp: "SMTP",
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  unipile_gmail: <Zap size={14} />,
  google_oauth: <Mail size={14} />,
  smtp: <Server size={14} />,
}

function AccountCard({
  account,
  onDelete,
  onToggleActive,
  onEdit,
}: {
  account: EmailAccount
  onDelete: (id: string) => void
  onToggleActive: (id: string, active: boolean) => void
  onEdit: (account: EmailAccount) => void
}) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-(--border-default) bg-(--bg-surface) px-3.5 py-3.5">
      <div className="flex min-w-0 items-center gap-3">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs ${
            account.is_active
              ? "bg-(--brand-subtle) text-(--brand)"
              : "bg-(--bg-overlay) text-(--text-tertiary)"
          }`}
        >
          {PROVIDER_ICONS[account.provider_type] ?? <Mail size={14} />}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-(--text-primary)">
            {account.display_name}
          </p>
          <p className="truncate text-xs text-(--text-secondary)">{account.email_address}</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <span className="inline-flex items-center gap-1 rounded-full bg-(--bg-overlay) px-2 py-0.5 text-[11px] text-(--text-tertiary)">
              {PROVIDER_LABELS[account.provider_type]}
            </span>
            {account.outbound_uses_fallback ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-(--info-subtle) px-2 py-0.5 text-[11px] text-(--info-subtle-fg)">
                envia via {PROVIDER_LABELS[account.effective_provider_type]}
              </span>
            ) : null}
          </div>
        </div>
      </div>
      <div className="ml-4 flex shrink-0 items-center gap-2.5">
        {account.is_active ? (
          <CheckCircle2 size={15} className="text-(--success)" />
        ) : (
          <XCircle size={15} className="text-(--text-tertiary)" />
        )}
        <Switch
          checked={account.is_active}
          onCheckedChange={(v) => onToggleActive(account.id, v)}
          aria-label={account.is_active ? "Desativar conta" : "Ativar conta"}
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-(--text-tertiary) hover:text-(--text-primary)"
          onClick={() => onEdit(account)}
          aria-label="Editar configurações"
        >
          <Pencil size={14} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-(--text-tertiary) hover:text-(--danger)"
          onClick={() => onDelete(account.id)}
          aria-label="Remover conta"
        >
          <Trash2 size={14} />
        </Button>
      </div>
    </div>
  )
}

// ── Modal de configurações da conta ───────────────────────────────────

function AccountSettingsModal({
  account,
  onClose,
}: {
  account: EmailAccount | null
  onClose: () => void
}) {
  const [dailyLimit, setDailyLimit] = useState<number>(account?.daily_send_limit ?? 50)
  const [signature, setSignature] = useState<string>(account?.email_signature ?? "")
  const [fetchMsg, setFetchMsg] = useState<string | null>(null)
  const [showHtml, setShowHtml] = useState(false)

  const { mutate: update, isPending: saving } = useUpdateEmailAccount()
  const { mutate: fetchSig, isPending: fetchingSignature } = useFetchGmailSignature()

  if (!account) return null

  const currentAccount = account

  function handleSyncSignature() {
    setFetchMsg(null)
    fetchSig(
      { accountId: currentAccount.id, save: false },
      {
        onSuccess: (r) => {
          setSignature(r.signature ?? "")
          setFetchMsg(
            r.signature
              ? "✓ Assinatura importada com sucesso!"
              : "Gmail não tem assinatura configurada.",
          )
        },
        onError: (e) => setFetchMsg(`✗ ${e.message}`),
      },
    )
  }

  function handleSave() {
    update(
      {
        id: currentAccount.id,
        body: {
          daily_send_limit: dailyLimit,
          email_signature: signature || null,
        },
      },
      { onSuccess: onClose },
    )
  }

  return (
    <Dialog open={!!account} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Configurar conta</DialogTitle>
          <p className="text-sm text-(--text-secondary)">{currentAccount.email_address}</p>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          {/* Limite diário */}
          <div className="space-y-1">
            <Label>Limite diário de envios</Label>
            <Input
              type="number"
              min={1}
              max={1000}
              value={dailyLimit}
              onChange={(e) => setDailyLimit(parseInt(e.target.value) || 50)}
            />
            <p className="text-xs text-(--text-tertiary)">
              Máximo de e-mails enviados por dia por esta conta.
            </p>
          </div>

          {/* Assinatura */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <Label>Assinatura de e-mail</Label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowHtml((v) => !v)}
                  className="text-xs text-(--text-tertiary) hover:text-(--text-secondary) underline underline-offset-2"
                >
                  {showHtml ? "Editar visual" : "HTML bruto"}
                </button>
                {currentAccount.provider_type === "google_oauth" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSyncSignature}
                    disabled={fetchingSignature}
                    className="h-7 gap-1 text-xs"
                  >
                    {fetchingSignature ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <RefreshCw size={12} />
                    )}
                    Sincronizar do Gmail
                  </Button>
                )}
              </div>
            </div>
            {showHtml ? (
              <Textarea
                value={signature}
                onChange={(e) => setSignature(e.target.value)}
                rows={8}
                className="font-mono text-xs"
                placeholder="<div>Minha assinatura...</div>"
              />
            ) : (
              <RichTextEditor
                value={signature}
                onChange={setSignature}
                placeholder="Crie sua assinatura — use a barra de ferramentas para formatar e inserir imagens..."
                minHeight={160}
              />
            )}
            {fetchMsg && (
              <p
                className={`text-xs ${
                  fetchMsg.startsWith("✓")
                    ? "text-(--success)"
                    : fetchMsg.startsWith("✗")
                      ? "text-(--danger)"
                      : "text-(--text-secondary)"
                }`}
              >
                {fetchMsg}
              </p>
            )}
            <p className="text-xs text-(--text-tertiary)">
              Será anexada ao final de cada e-mail enviado por esta conta.
              {currentAccount.provider_type === "google_oauth" &&
                ' Use "Sincronizar do Gmail" para importar a assinatura existente.'}
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 size={14} className="animate-spin" /> : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Modal SMTP ────────────────────────────────────────────────────────

function SMTPModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form, setForm] = useState<CreateSMTPAccountBody>({
    display_name: "",
    email_address: "",
    smtp_host: "",
    smtp_port: 587,
    smtp_username: "",
    smtp_password: "",
    smtp_use_tls: true,
    daily_send_limit: 50,
  })
  const [testResult, setTestResult] = useState<string | null>(null)
  const [showImap, setShowImap] = useState(false)

  const { mutate: createSMTP, isPending: creating } = useCreateSMTPAccount()
  const { mutate: testSMTP, isPending: testing } = useTestSMTP()

  function handleTest() {
    setTestResult(null)
    testSMTP(
      {
        smtp_host: form.smtp_host,
        smtp_port: form.smtp_port ?? 587,
        smtp_username: form.smtp_username,
        smtp_password: form.smtp_password,
        smtp_use_tls: form.smtp_use_tls ?? true,
      },
      {
        onSuccess: (r) => setTestResult(r.ok ? "✓ Conexão OK!" : `✗ ${r.error}`),
        onError: () => setTestResult("✗ Erro ao testar conexão"),
      },
    )
  }

  function handleCreate() {
    createSMTP(form, {
      onSuccess: () => {
        onClose()
        setForm({
          display_name: "",
          email_address: "",
          smtp_host: "",
          smtp_port: 587,
          smtp_username: "",
          smtp_password: "",
          smtp_use_tls: true,
          daily_send_limit: 50,
        })
        setTestResult(null)
        setShowImap(false)
      },
      onError: (e) => setTestResult(`✗ ${e.message}`),
    })
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Conectar via SMTP</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Nome da conta</Label>
              <Input
                placeholder="Ex: Gmail empresarial"
                value={form.display_name}
                onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <Label>E-mail do remetente</Label>
              <Input
                type="email"
                placeholder="voce@empresa.com"
                value={form.email_address}
                onChange={(e) => setForm((p) => ({ ...p, email_address: e.target.value }))}
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 space-y-1">
              <Label>Servidor SMTP</Label>
              <Input
                placeholder="smtp.gmail.com"
                value={form.smtp_host}
                onChange={(e) => setForm((p) => ({ ...p, smtp_host: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <Label>Porta</Label>
              <Input
                type="number"
                value={form.smtp_port}
                onChange={(e) =>
                  setForm((p) => ({ ...p, smtp_port: parseInt(e.target.value) || 587 }))
                }
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Usuário</Label>
              <Input
                value={form.smtp_username}
                onChange={(e) => setForm((p) => ({ ...p, smtp_username: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <Label>Senha</Label>
              <Input
                type="password"
                value={form.smtp_password}
                onChange={(e) => setForm((p) => ({ ...p, smtp_password: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Switch
                checked={form.smtp_use_tls ?? true}
                onCheckedChange={(v) => setForm((p) => ({ ...p, smtp_use_tls: v }))}
              />
              <Label>Usar TLS/STARTTLS</Label>
            </div>
            <Button variant="outline" size="sm" onClick={handleTest} disabled={testing}>
              {testing ? <Loader2 size={13} className="animate-spin" /> : "Testar conexão"}
            </Button>
          </div>
          {testResult && (
            <p
              className={`text-sm ${testResult.startsWith("✓") ? "text-(--success)" : "text-(--danger)"}`}
            >
              {testResult}
            </p>
          )}
          <div className="space-y-1">
            <Label>Limite diário de envios</Label>
            <Input
              type="number"
              value={form.daily_send_limit}
              onChange={(e) =>
                setForm((p) => ({ ...p, daily_send_limit: parseInt(e.target.value) || 50 }))
              }
            />
          </div>

          {/* IMAP — opcional */}
          <div className="rounded-lg border border-(--border-default) p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Detectar replies (IMAP)</p>
                <p className="text-xs text-(--text-tertiary)">
                  Conecte ao IMAP para pausar a cadência quando o lead responder.
                </p>
              </div>
              <Switch
                checked={showImap}
                onCheckedChange={(v) => {
                  setShowImap(v)
                  if (!v) setForm((p) => ({ ...p, imap_host: "", imap_password: "" }))
                }}
              />
            </div>
            {showImap && (
              <div className="grid gap-3 pt-1">
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2 space-y-1">
                    <Label>Servidor IMAP</Label>
                    <Input
                      placeholder="imap.gmail.com"
                      value={form.imap_host ?? ""}
                      onChange={(e) => setForm((p) => ({ ...p, imap_host: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label>Porta</Label>
                    <Input
                      type="number"
                      placeholder="993"
                      value={form.imap_port ?? ""}
                      onChange={(e) =>
                        setForm((p) => ({ ...p, imap_port: parseInt(e.target.value) || 993 }))
                      }
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label>
                    Senha IMAP{" "}
                    <span className="text-(--text-tertiary) font-normal">
                      (deixe em branco para usar a mesma do SMTP)
                    </span>
                  </Label>
                  <Input
                    type="password"
                    placeholder="Mesma senha SMTP"
                    value={form.imap_password ?? ""}
                    onChange={(e) =>
                      setForm(
                        (p) => ({ ...p, imap_password: e.target.value }) as CreateSMTPAccountBody,
                      )
                    }
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={form.imap_use_ssl ?? true}
                    onCheckedChange={(v) => setForm((p) => ({ ...p, imap_use_ssl: v }))}
                  />
                  <Label>Usar SSL (porta 993)</Label>
                </div>
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? <Loader2 size={14} className="animate-spin" /> : "Conectar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Modal Unipile ─────────────────────────────────────────────────────

function UnipileModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form, setForm] = useState<CreateUnipileAccountBody>({
    display_name: "",
    email_address: "",
    unipile_account_id: "",
    daily_send_limit: 100,
  })
  const [error, setError] = useState<string | null>(null)
  const { mutate: create, isPending } = useCreateUnipileAccount()

  function handleCreate() {
    setError(null)
    create(form, {
      onSuccess: () => {
        onClose()
        setForm({
          display_name: "",
          email_address: "",
          unipile_account_id: "",
          daily_send_limit: 100,
        })
      },
      onError: (e) => setError(e.message),
    })
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Conectar via Unipile</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3 py-2">
          <div className="space-y-1">
            <Label>Nome da conta</Label>
            <Input
              placeholder="Gmail via Unipile"
              value={form.display_name}
              onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label>E-mail do remetente</Label>
            <Input
              type="email"
              placeholder="voce@empresa.com"
              value={form.email_address}
              onChange={(e) => setForm((p) => ({ ...p, email_address: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label>Unipile Account ID</Label>
            <Input
              placeholder="acc_..."
              value={form.unipile_account_id}
              onChange={(e) => setForm((p) => ({ ...p, unipile_account_id: e.target.value }))}
            />
            <p className="text-xs text-(--text-tertiary)">
              O account_id da conta Gmail conectada no Unipile.
            </p>
          </div>
          {error && <p className="text-sm text-(--danger)">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleCreate} disabled={isPending}>
            {isPending ? <Loader2 size={14} className="animate-spin" /> : "Conectar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Página principal ──────────────────────────────────────────────────

export default function EmailAccountsPage() {
  const { data, isLoading, isError, error } = useEmailAccounts()
  const { data: oauthUrl, isError: oauthError, error: oauthErrorDetails } = useGoogleOAuthUrl()
  const { mutate: deleteAccount } = useDeleteEmailAccount()
  const { mutate: updateAccount } = useUpdateEmailAccount()

  const [smtpOpen, setSmtpOpen] = useState(false)
  const [unipileOpen, setUnipileOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<EmailAccount | null>(null)

  const accounts = data?.accounts ?? []

  function handleDelete(id: string) {
    if (!confirm("Remover esta conta de e-mail?")) return
    deleteAccount(id)
  }

  function handleToggleActive(id: string, active: boolean) {
    updateAccount({ id, body: { is_active: active } })
  }

  return (
    <SettingsPageShell
      title="Contas de E-mail"
      description="Conecte remetentes para cold email e distribua melhor o espaço entre lista, ações e orientação operacional."
      width="wide"
      actions={
        <>
          <Button variant="outline" size="sm" onClick={() => setUnipileOpen(true)}>
            <Zap size={13} className="mr-1" />
            Unipile
          </Button>
          <Button variant="outline" size="sm" onClick={() => setSmtpOpen(true)}>
            <Server size={13} className="mr-1" />
            SMTP
          </Button>
          {oauthUrl ? (
            <Button variant="outline" size="sm" asChild>
              <a href={oauthUrl} target="_blank" rel="noreferrer">
                <Mail size={13} className="mr-1" />
                Gmail OAuth
                <ExternalLink size={11} className="ml-1" />
              </a>
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              disabled
              title={oauthError ? "Falha ao obter URL OAuth" : undefined}
            >
              <Mail size={13} className="mr-1" />
              Gmail OAuth
            </Button>
          )}
        </>
      }
    >
      {isError || oauthError ? (
        <SettingsCallout
          icon={<AlertTriangle size={16} aria-hidden="true" />}
          title="Nem todas as configurações de e-mail puderam ser carregadas"
          className="border-(--warning-subtle) bg-(--warning-subtle) text-(--warning-subtle-fg)"
        >
          {isError ? (
            <p>{error instanceof Error ? error.message : "Falha ao carregar contas de e-mail."}</p>
          ) : null}
          {oauthError ? (
            <p>
              Gmail OAuth:{" "}
              {oauthErrorDetails instanceof Error
                ? oauthErrorDetails.message
                : "falha ao obter URL de autorização."}
            </p>
          ) : null}
          <p>
            Confirme se a API do backend e as credenciais do Google estão acessíveis no ambiente
            atual.
          </p>
        </SettingsCallout>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.45fr)_320px]">
        <SettingsPanel
          title="Contas conectadas"
          description="Ative, desative ou edite cada remetente sem precisar abrir outra área."
          headerAside={
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-xs font-medium text-(--text-secondary)">
              {accounts.length} conta(s)
            </span>
          }
        >
          {isLoading ? (
            <div className="flex h-20 items-center justify-center">
              <Loader2 size={18} className="animate-spin text-(--text-tertiary)" />
            </div>
          ) : accounts.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center text-(--text-tertiary)">
              <Mail size={28} />
              <p className="text-sm">Nenhuma conta conectada ainda.</p>
              <p className="text-xs">
                Use os botões do topo para conectar via SMTP, Gmail OAuth ou Unipile.
              </p>
            </div>
          ) : (
            <div className="grid gap-2.5">
              {accounts.map((acc) => (
                <AccountCard
                  key={acc.id}
                  account={acc}
                  onDelete={handleDelete}
                  onToggleActive={handleToggleActive}
                  onEdit={setEditingAccount}
                />
              ))}
            </div>
          )}
        </SettingsPanel>

        <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <SettingsPanel
            title="Qual método usar?"
            description="Escolha o tipo de conexão com base no seu fluxo atual."
          >
            <div className="space-y-3 text-sm text-(--text-secondary)">
              <div className="flex gap-2.5">
                <Zap size={15} className="mt-0.5 shrink-0 text-(--brand)" />
                <p>
                  <strong className="text-(--text-primary)">Unipile:</strong> melhor opção se você
                  já usa Unipile para LinkedIn e quer reaproveitar a conta Gmail sem configuração
                  extra.
                </p>
              </div>
              <div className="flex gap-2.5">
                <Mail size={15} className="mt-0.5 shrink-0 text-(--brand)" />
                <p>
                  <strong className="text-(--text-primary)">Gmail OAuth:</strong> conecta direto com
                  o Google e tende a ser a rota mais simples para múltiplas contas Gmail.
                </p>
              </div>
              <div className="flex gap-2.5">
                <Server size={15} className="mt-0.5 shrink-0 text-(--brand)" />
                <p>
                  <strong className="text-(--text-primary)">SMTP:</strong> cobre Outlook, Yahoo,
                  Zoho, Proton e outros provedores que exigem host, porta e credenciais próprias.
                </p>
              </div>
            </div>
          </SettingsPanel>

          <SettingsPanel
            title="Operação"
            description="Mantenha apenas contas ativas e com limite coerente para evitar gargalos de entrega."
          >
            <p className="text-sm leading-6 text-(--text-secondary)">
              Cada cadência pode selecionar uma conta diferente. Ative apenas os remetentes que de
              fato estão prontos para envio e use a edição da conta para revisar assinatura e limite
              diário.
            </p>
            <p className="mt-3 text-sm leading-6 text-(--text-secondary)">
              Quando uma conta Unipile tiver uma conta Gmail OAuth ativa com o mesmo endereço, o
              sistema envia pelo OAuth para preservar nome do remetente e assinatura.
            </p>
          </SettingsPanel>
        </div>
      </div>

      <SMTPModal open={smtpOpen} onClose={() => setSmtpOpen(false)} />
      <UnipileModal open={unipileOpen} onClose={() => setUnipileOpen(false)} />
      <AccountSettingsModal account={editingAccount} onClose={() => setEditingAccount(null)} />
    </SettingsPageShell>
  )
}
