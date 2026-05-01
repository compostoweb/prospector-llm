"use client"

import type { Route } from "next"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  Linkedin,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Zap,
  KeyRound,
  AlertTriangle,
} from "lucide-react"
import {
  useLinkedInAccounts,
  useCreateUnipileHostedAuthLink,
  useCreateUnipileReconnectLink,
  useCreateNativeLinkedInAccount,
  useUpdateLinkedInAccount,
  useDeleteLinkedInAccount,
  type LinkedInAccount,
  type CreateUnipileHostedAuthBody,
  type CreateNativeLinkedInAccountBody,
} from "@/lib/api/hooks/use-linkedin-accounts"
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
import { SettingsPageShell, SettingsPanel } from "@/components/settings/settings-shell"
import { SettingsCallout } from "@/components/settings/settings-shell"
import { Badge } from "@/components/ui/badge"

// ── Helpers ───────────────────────────────────────────────────────────

const PROVIDER_LABELS: Record<string, string> = {
  unipile: "Unipile",
  native: "Cookie Nativo",
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  unipile: <Zap size={14} />,
  native: <KeyRound size={14} />,
}

function ownerLabel(account: LinkedInAccount) {
  return account.owner_name || account.owner_email || "Sem dono"
}

function statusBadge(account: LinkedInAccount): {
  label: string
  variant: "outline" | "success" | "warning" | "danger"
} {
  if (!account.is_active) return { label: "Inativa", variant: "outline" }
  if (account.reconnect_required_at) return { label: "Reconectar", variant: "warning" }
  if (account.provider_status === "error") return { label: "Erro", variant: "danger" }
  if (account.provider_status === "ok" || account.provider_status === "connected") {
    return { label: "Conectada", variant: "success" }
  }
  return { label: "Status pendente", variant: "outline" }
}

function shouldOfferReconnect(account: LinkedInAccount) {
  return (
    account.provider_type === "unipile" &&
    Boolean(
      account.reconnect_required_at ||
      account.provider_status === "error" ||
      account.provider_status === "credentials" ||
      account.provider_status === "stopped",
    )
  )
}

// ── Account Card ──────────────────────────────────────────────────────

function AccountCard({
  account,
  onDelete,
  onReconnect,
  onToggleActive,
  onToggleInmail,
  isReconnecting,
}: {
  account: LinkedInAccount
  onDelete: (id: string) => void
  onReconnect: (id: string) => void
  onToggleActive: (id: string, active: boolean) => void
  onToggleInmail: (id: string, enabled: boolean) => void
  isReconnecting: boolean
}) {
  const status = statusBadge(account)
  const canReconnect = shouldOfferReconnect(account)

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs ${
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
          <div className="mt-1 flex flex-wrap gap-1.5">
            <Badge variant="outline">
              {PROVIDER_LABELS[account.provider_type] ?? account.provider_type}
            </Badge>
            <Badge variant={status.variant}>{status.label}</Badge>
            <Badge variant="neutral">Dono: {ownerLabel(account)}</Badge>
            <Badge variant={account.supports_inmail ? "success" : "outline"}>
              {account.supports_inmail ? "InMail habilitado" : "Sem InMail"}
            </Badge>
          </div>
          {account.health_error ? (
            <p className="mt-1 truncate text-xs text-(--danger)">{account.health_error}</p>
          ) : null}
        </div>
      </div>
      <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch lg:justify-end">
        <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) px-4 py-3 lg:w-80 xl:w-88">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-(--text-tertiary)">
                InMail Premium
              </p>
              <p className="text-xs text-(--text-secondary)">
                Habilite apenas se essa conta realmente puder enviar InMail.
              </p>
            </div>
            <Switch
              checked={account.supports_inmail}
              onCheckedChange={(value) => onToggleInmail(account.id, value)}
              aria-label={account.supports_inmail ? "Desativar InMail" : "Ativar InMail"}
            />
          </div>
        </div>

        <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) px-4 py-3 lg:w-80 xl:w-88">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-(--text-tertiary)">
                Conta ativa
              </p>
              <p className="text-xs text-(--text-secondary)">
                Desative para pausar uso operacional sem remover a conta.
              </p>
            </div>
            <div className="flex items-center gap-2.5">
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
            </div>
          </div>
        </div>

        {canReconnect ? (
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-2 self-end lg:self-center"
            disabled={isReconnecting}
            onClick={() => onReconnect(account.id)}
          >
            {isReconnecting ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <RefreshCw size={14} />
            )}
            Reconectar
          </Button>
        ) : null}

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 self-end text-(--text-tertiary) hover:text-(--danger) lg:self-center"
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
  const [form, setForm] = useState<CreateUnipileHostedAuthBody>({
    display_name: "",
    linkedin_username: "",
    supports_inmail: false,
  })
  const [error, setError] = useState<string | null>(null)
  const createHostedAuth = useCreateUnipileHostedAuthLink()

  async function handleSubmit() {
    setError(null)
    try {
      const result = await createHostedAuth.mutateAsync(form)
      window.location.assign(result.auth_url)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro desconhecido")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Conectar LinkedIn via Unipile</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) px-3 py-3 text-xs leading-5 text-(--text-secondary)">
            O Prospector vai abrir o Hosted Auth da Unipile em uma nova etapa segura. Depois da
            confirmação, a conta volta associada ao usuário atual e aparece nesta tela.
          </div>
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
          <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) px-3 py-3">
            <div className="mb-3">
              <p className="text-sm font-medium text-(--text-primary)">Capacidades operacionais</p>
              <p className="text-xs text-(--text-secondary)">
                Marque o que essa conta realmente suporta no runtime.
              </p>
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-(--text-primary)">InMail Premium</p>
                <p className="text-xs text-(--text-secondary)">
                  Ative quando a conta tiver Premium ou capability operacional para InMail.
                </p>
              </div>
              <Switch
                checked={form.supports_inmail ?? false}
                onCheckedChange={(value) => setForm((f) => ({ ...f, supports_inmail: value }))}
                aria-label="Conta com capability de InMail"
              />
            </div>
          </div>

          {error && <p className="text-sm text-(--danger)">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createHostedAuth.isPending || !form.display_name.trim()}
          >
            {createHostedAuth.isPending && <Loader2 size={14} className="mr-2 animate-spin" />}
            Abrir Unipile
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
    supports_inmail: false,
    li_at_cookie: "",
  })
  const [error, setError] = useState<string | null>(null)
  const create = useCreateNativeLinkedInAccount()

  async function handleSubmit() {
    setError(null)
    try {
      await create.mutateAsync(form)
      onClose()
      setForm({
        display_name: "",
        linkedin_username: "",
        supports_inmail: false,
        li_at_cookie: "",
      })
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
          <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) px-3 py-3">
            <div className="mb-3">
              <p className="text-sm font-medium text-(--text-primary)">Capacidades operacionais</p>
              <p className="text-xs text-(--text-secondary)">
                Marque o que essa sessão nativa realmente suporta em produção.
              </p>
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-(--text-primary)">InMail Premium</p>
                <p className="text-xs text-(--text-secondary)">
                  Use quando essa sessão realmente puder enviar InMail no runtime.
                </p>
              </div>
              <Switch
                checked={form.supports_inmail ?? false}
                onCheckedChange={(value) => setForm((f) => ({ ...f, supports_inmail: value }))}
                aria-label="Conta com capability de InMail"
              />
            </div>
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
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const handledUnipileStatusRef = useRef<string | null>(null)
  const [showUnipileModal, setShowUnipileModal] = useState(false)
  const [showNativeModal, setShowNativeModal] = useState(false)

  const { data, isLoading, isError, error } = useLinkedInAccounts()
  const updateAccount = useUpdateLinkedInAccount()
  const deleteAccount = useDeleteLinkedInAccount()
  const reconnectAccount = useCreateUnipileReconnectLink()

  const accounts = data?.accounts ?? []

  useEffect(() => {
    const unipileStatus = searchParams.get("unipile")
    if (!unipileStatus || handledUnipileStatusRef.current === unipileStatus) return

    handledUnipileStatusRef.current = unipileStatus
    if (unipileStatus === "success") {
      toast.success("Conta LinkedIn conectada com sucesso")
      queryClient.invalidateQueries({ queryKey: ["linkedin-accounts"] })
    } else if (unipileStatus === "reconnected") {
      toast.success("Conta LinkedIn reconectada com sucesso")
      queryClient.invalidateQueries({ queryKey: ["linkedin-accounts"] })
    } else if (unipileStatus === "error") {
      toast.error("Não foi possível concluir a conexão LinkedIn")
    }

    const nextParams = new URLSearchParams(searchParams.toString())
    nextParams.delete("unipile")
    const nextQuery = nextParams.toString()
    const nextUrl = `/configuracoes/linkedin-accounts${nextQuery ? `?${nextQuery}` : ""}`
    router.replace(nextUrl as Route, { scroll: false })
  }, [queryClient, router, searchParams])

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

  async function handleToggleInmail(id: string, enabled: boolean) {
    await updateAccount.mutateAsync({ id, body: { supports_inmail: enabled } })
  }

  async function handleReconnect(id: string) {
    const result = await reconnectAccount.mutateAsync(id)
    window.location.assign(result.auth_url)
  }

  return (
    <SettingsPageShell
      title="Contas LinkedIn"
      description="Conecte perfis usados na prospecção e distribua melhor lista, ações e contexto operacional no desktop."
      width="wide"
      actions={
        <>
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
        </>
      }
    >
      {isError ? (
        <SettingsCallout
          icon={<AlertTriangle size={16} aria-hidden="true" />}
          title="Não foi possível carregar as contas LinkedIn"
          className="border-(--warning-subtle) bg-(--warning-subtle) text-(--warning-subtle-fg)"
        >
          <p>{error instanceof Error ? error.message : "Erro ao buscar contas LinkedIn."}</p>
          <p>
            Se a API estiver fora do ar, a lista de contas e os modais não vão refletir o estado
            real.
          </p>
        </SettingsCallout>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.45fr)_320px]">
        <SettingsPanel
          title="Contas configuradas"
          description="Contas Unipile usam webhook para inbox. Contas nativas usam polling a cada minuto."
          headerAside={
            <span className="rounded-full bg-(--bg-overlay) px-2.5 py-1 text-xs font-medium text-(--text-secondary)">
              {accounts.length} conta(s)
            </span>
          }
        >
          <div className="mb-4 rounded-xl border border-(--border-subtle) bg-(--bg-overlay) px-4 py-3 text-sm text-(--text-secondary)">
            A opção de InMail fica no bloco InMail Premium de cada conta e também aparece nos modais
            Via Unipile e Via Cookie ao cadastrar uma nova conta.
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={20} className="animate-spin text-(--text-tertiary)" />
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <AlertTriangle size={28} className="text-(--warning)" />
              <p className="text-sm text-(--text-secondary)">
                Não foi possível consultar as contas.
              </p>
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
            <div className="grid gap-2.5">
              {accounts.map((account) => (
                <AccountCard
                  key={account.id}
                  account={account}
                  onDelete={handleDelete}
                  onReconnect={handleReconnect}
                  onToggleActive={handleToggleActive}
                  onToggleInmail={handleToggleInmail}
                  isReconnecting={reconnectAccount.isPending}
                />
              ))}
            </div>
          )}
        </SettingsPanel>

        <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <SettingsPanel
            title="Métodos de conexão"
            description="Escolha o modo com base no nível de controle e no setup disponível."
          >
            <div className="space-y-3 text-sm text-(--text-secondary)">
              <div className="flex gap-2.5">
                <Zap size={15} className="mt-0.5 shrink-0 text-(--brand)" />
                <p>
                  <strong className="text-(--text-primary)">Via Unipile:</strong> configuração mais
                  simples para abrir o Hosted Auth da Unipile e conectar LinkedIn sem copiar IDs
                  manualmente.
                </p>
              </div>
              <div className="flex gap-2.5">
                <KeyRound size={15} className="mt-0.5 shrink-0 text-(--brand)" />
                <p>
                  <strong className="text-(--text-primary)">Via Cookie:</strong> oferece um caminho
                  nativo quando você precisa operar com cookie li_at e controle mais direto da
                  sessão.
                </p>
              </div>
            </div>
          </SettingsPanel>

          <SettingsPanel
            title="Boas práticas"
            description="Evite instabilidade operacional entre contas concorrentes."
          >
            <p className="text-sm leading-6 text-(--text-secondary)">
              Mantenha somente uma conta ativa por perfil operacional, remova conexões obsoletas e
              prefira nomes de exibição claros para cada uso de cadência.
            </p>
          </SettingsPanel>
        </div>
      </div>

      <UnipileModal open={showUnipileModal} onClose={() => setShowUnipileModal(false)} />
      <NativeModal open={showNativeModal} onClose={() => setShowNativeModal(false)} />
    </SettingsPageShell>
  )
}
