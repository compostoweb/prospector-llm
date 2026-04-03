"use client"

import { useState } from "react"
import { Linkedin, Plus, Trash2, CheckCircle2, XCircle, Loader2, Zap, KeyRound } from "lucide-react"
import {
  useLinkedInAccounts,
  useCreateUnipileLinkedInAccount,
  useCreateNativeLinkedInAccount,
  useUpdateLinkedInAccount,
  useDeleteLinkedInAccount,
  type LinkedInAccount,
  type CreateUnipileLinkedInAccountBody,
  type CreateNativeLinkedInAccountBody,
} from "@/lib/api/hooks/use-linkedin-accounts"
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

// ── Helpers ───────────────────────────────────────────────────────────

const PROVIDER_LABELS: Record<string, string> = {
  unipile: "Unipile",
  native: "Cookie Nativo",
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  unipile: <Zap size={14} />,
  native: <KeyRound size={14} />,
}

// ── Account Card ──────────────────────────────────────────────────────

function AccountCard({
  account,
  onDelete,
  onToggleActive,
}: {
  account: LinkedInAccount
  onDelete: (id: string) => void
  onToggleActive: (id: string, active: boolean) => void
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
          {PROVIDER_ICONS[account.provider_type] ?? <Linkedin size={14} />}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-(--text-primary)">
            {account.display_name}
          </p>
          {account.linkedin_username && (
            <p className="truncate text-xs text-(--text-secondary)">
              linkedin.com/in/{account.linkedin_username}
            </p>
          )}
          <span className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-(--bg-overlay) px-2 py-0.5 text-xs text-(--text-tertiary)">
            {PROVIDER_LABELS[account.provider_type] ?? account.provider_type}
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

// ── Modal Unipile ─────────────────────────────────────────────────────

function UnipileModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form, setForm] = useState<CreateUnipileLinkedInAccountBody>({
    display_name: "",
    linkedin_username: "",
    unipile_account_id: "",
  })
  const [error, setError] = useState<string | null>(null)
  const create = useCreateUnipileLinkedInAccount()

  async function handleSubmit() {
    setError(null)
    try {
      await create.mutateAsync(form)
      onClose()
      setForm({ display_name: "", linkedin_username: "", unipile_account_id: "" })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro desconhecido")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Conectar via Unipile</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div>
            <Label htmlFor="ul-display_name">Nome de exibição</Label>
            <Input
              id="ul-display_name"
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
              placeholder="Ex: LinkedIn Vendas"
            />
          </div>
          <div>
            <Label htmlFor="ul-username">Username LinkedIn (opcional)</Label>
            <Input
              id="ul-username"
              value={form.linkedin_username ?? ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, linkedin_username: e.target.value || null }))
              }
              placeholder="joao-silva-123"
            />
          </div>
          <div>
            <Label htmlFor="ul-account_id">Account ID (Unipile)</Label>
            <Input
              id="ul-account_id"
              value={form.unipile_account_id}
              onChange={(e) => setForm((f) => ({ ...f, unipile_account_id: e.target.value }))}
              placeholder="ID da conta no painel Unipile"
            />
          </div>

          {error && <p className="text-sm text-(--danger)">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              create.isPending || !form.display_name.trim() || !form.unipile_account_id.trim()
            }
          >
            {create.isPending && <Loader2 size={14} className="mr-2 animate-spin" />}
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Modal Nativo (cookie li_at) ───────────────────────────────────────

function NativeModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form, setForm] = useState<CreateNativeLinkedInAccountBody>({
    display_name: "",
    linkedin_username: "",
    li_at_cookie: "",
  })
  const [error, setError] = useState<string | null>(null)
  const create = useCreateNativeLinkedInAccount()

  async function handleSubmit() {
    setError(null)
    try {
      await create.mutateAsync(form)
      onClose()
      setForm({ display_name: "", linkedin_username: "", li_at_cookie: "" })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro desconhecido")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Conectar via Cookie Nativo</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-lg border border-(--warning-subtle) bg-(--warning-subtle)/20 p-3">
            <p className="text-xs text-(--text-secondary)">
              O cookie <strong>li_at</strong> é extraído do seu browser após fazer login no
              LinkedIn. No Chrome: DevTools → Application → Cookies → linkedin.com → li_at. Ele é
              armazenado criptografado e nunca exposto via API.
            </p>
          </div>

          <div>
            <Label htmlFor="nat-display_name">Nome de exibição</Label>
            <Input
              id="nat-display_name"
              value={form.display_name}
              onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
              placeholder="Ex: LinkedIn CEO"
            />
          </div>
          <div>
            <Label htmlFor="nat-username">Username LinkedIn</Label>
            <Input
              id="nat-username"
              value={form.linkedin_username}
              onChange={(e) => setForm((f) => ({ ...f, linkedin_username: e.target.value }))}
              placeholder="joao-silva-123"
            />
          </div>
          <div>
            <Label htmlFor="nat-cookie">Cookie li_at</Label>
            <Input
              id="nat-cookie"
              type="password"
              value={form.li_at_cookie}
              onChange={(e) => setForm((f) => ({ ...f, li_at_cookie: e.target.value }))}
              placeholder="Cole o valor do cookie li_at aqui"
            />
          </div>

          {error && <p className="text-sm text-(--danger)">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              create.isPending ||
              !form.display_name.trim() ||
              !form.linkedin_username.trim() ||
              !form.li_at_cookie.trim()
            }
          >
            {create.isPending && <Loader2 size={14} className="mr-2 animate-spin" />}
            Validar e Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Página principal ──────────────────────────────────────────────────

export default function LinkedInAccountsPage() {
  const [showUnipileModal, setShowUnipileModal] = useState(false)
  const [showNativeModal, setShowNativeModal] = useState(false)

  const { data, isLoading } = useLinkedInAccounts()
  const updateAccount = useUpdateLinkedInAccount()
  const deleteAccount = useDeleteLinkedInAccount()

  const accounts = data?.accounts ?? []

  async function handleDelete(id: string) {
    if (
      !confirm(
        "Remover esta conta LinkedIn? As cadências que usam esta conta passarão a usar o Unipile global.",
      )
    )
      return
    await deleteAccount.mutateAsync(id)
  }

  async function handleToggleActive(id: string, active: boolean) {
    await updateAccount.mutateAsync({ id, body: { is_active: active } })
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-(--text-primary)">Contas LinkedIn</h1>
          <p className="mt-1 text-sm text-(--text-secondary)">
            Conecte contas LinkedIn para prospecção. Cada cadência pode usar uma conta diferente.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => setShowUnipileModal(true)}
          >
            <Zap size={14} />
            Via Unipile
          </Button>
          <Button size="sm" className="gap-2" onClick={() => setShowNativeModal(true)}>
            <Plus size={14} />
            Via Cookie
          </Button>
        </div>
      </div>

      {/* Lista de contas */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">
            Contas configuradas ({accounts.length})
          </CardTitle>
          <CardDescription className="text-xs">
            Contas Unipile usam webhook para inbox. Contas nativas usam polling a cada minuto.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={20} className="animate-spin text-(--text-tertiary)" />
            </div>
          ) : accounts.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <Linkedin size={32} className="text-(--text-tertiary)" />
              <p className="text-sm text-(--text-secondary)">Nenhuma conta conectada.</p>
              <p className="text-xs text-(--text-tertiary)">
                Adicione uma conta Unipile ou via cookie nativo para começar.
              </p>
            </div>
          ) : (
            accounts.map((account) => (
              <AccountCard
                key={account.id}
                account={account}
                onDelete={handleDelete}
                onToggleActive={handleToggleActive}
              />
            ))
          )}
        </CardContent>
      </Card>

      {/* Modals */}
      <UnipileModal open={showUnipileModal} onClose={() => setShowUnipileModal(false)} />
      <NativeModal open={showNativeModal} onClose={() => setShowNativeModal(false)} />
    </div>
  )
}
