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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
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
    <div className="flex items-center justify-between rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
      <div className="flex min-w-0 items-center gap-3">
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs ${
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
          <span className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-(--bg-overlay) px-2 py-0.5 text-xs text-(--text-tertiary)">
            {PROVIDER_LABELS[account.provider_type]}
          </span>
        </div>
      </div>
      <div className="ml-4 flex shrink-0 items-center gap-3">
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
  const { data, isLoading } = useEmailAccounts()
  const { data: oauthUrl } = useGoogleOAuthUrl()
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
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold text-(--text-primary)">E-mail Accounts</h1>
        <p className="mt-1 text-sm text-(--text-secondary)">
          Conecte contas de e-mail para envio de cold emails. Cada cadência pode usar uma conta
          diferente.
        </p>
      </div>

      {/* Contas */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base">Contas conectadas</CardTitle>
            <CardDescription>{accounts.length} conta(s)</CardDescription>
          </div>
          <div className="flex gap-2">
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
              <Button variant="outline" size="sm" disabled>
                <Mail size={13} className="mr-1" />
                Gmail OAuth
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-20 items-center justify-center">
              <Loader2 size={18} className="animate-spin text-(--text-tertiary)" />
            </div>
          ) : accounts.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-(--text-tertiary)">
              <Mail size={28} />
              <p className="text-sm">Nenhuma conta conectada ainda.</p>
              <p className="text-xs">
                Use os botões acima para conectar via SMTP, Gmail OAuth ou Unipile.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
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
        </CardContent>
      </Card>

      {/* Orientações */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Qual método usar?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-(--text-secondary)">
          <div className="flex gap-2">
            <Zap size={15} className="mt-0.5 shrink-0 text-(--brand)" />
            <p>
              <strong className="text-(--text-primary)">Unipile:</strong> Melhor opção se você já
              usa Unipile para LinkedIn. Conecta a mesma conta Gmail sem configuração extra.
            </p>
          </div>
          <div className="flex gap-2">
            <Mail size={15} className="mt-0.5 shrink-0 text-(--brand)" />
            <p>
              <strong className="text-(--text-primary)">Gmail OAuth:</strong> Conecta diretamente
              via OAuth do Google, sem intermediários. Ideal para múltiplas contas Gmail.
            </p>
          </div>
          <div className="flex gap-2">
            <Server size={15} className="mt-0.5 shrink-0 text-(--brand)" />
            <p>
              <strong className="text-(--text-primary)">SMTP:</strong> Para qualquer provedor de
              e-mail (Outlook, Yahoo, Zoho, Proton, etc.). Insira os dados do servidor SMTP.
            </p>
          </div>
        </CardContent>
      </Card>

      <SMTPModal open={smtpOpen} onClose={() => setSmtpOpen(false)} />
      <UnipileModal open={unipileOpen} onClose={() => setUnipileOpen(false)} />
      <AccountSettingsModal account={editingAccount} onClose={() => setEditingAccount(null)} />
    </div>
  )
}
