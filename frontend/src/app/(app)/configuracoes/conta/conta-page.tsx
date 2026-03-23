"use client"

import { useEffect, useState } from "react"
import { Loader2, Save } from "lucide-react"
import {
  useTenant,
  useUpdateIntegrations,
  type UpdateIntegrationsBody,
} from "@/lib/api/hooks/use-tenant"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

// ── Tipos locais ──────────────────────────────────────────────────────

interface CheckboxRowProps {
  id: string
  label: string
  checked: boolean
  onChange: (value: boolean) => void
}

// ── Componente auxiliar ───────────────────────────────────────────────

function CheckboxRow({ id, label, checked, onChange }: CheckboxRowProps) {
  return (
    <div className="flex items-center gap-2.5">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 cursor-pointer rounded"
        style={{ accentColor: "var(--accent)" }}
      />
      <label htmlFor={id} className="cursor-pointer select-none text-sm text-(--text-secondary)">
        {label}
      </label>
    </div>
  )
}

// ── Página ────────────────────────────────────────────────────────────

export default function ContaPage() {
  const { data: tenant, isLoading } = useTenant()
  const { mutate: saveIntegrations, isPending, isSuccess, isError, error } = useUpdateIntegrations()

  const integration = tenant?.integration

  const [notifyEmail, setNotifyEmail] = useState("")
  const [notifyOnInterest, setNotifyOnInterest] = useState(true)
  const [notifyOnObjection, setNotifyOnObjection] = useState(true)
  const [allowPersonalEmail, setAllowPersonalEmail] = useState(false)
  const [limitLinkedinConnect, setLimitLinkedinConnect] = useState(20)
  const [limitLinkedinDm, setLimitLinkedinDm] = useState(40)
  const [limitEmail, setLimitEmail] = useState(300)

  // Sincroniza o formulário quando os dados carregam
  useEffect(() => {
    if (!integration) return
    setNotifyEmail(integration.notify_email ?? "")
    setNotifyOnInterest(integration.notify_on_interest)
    setNotifyOnObjection(integration.notify_on_objection)
    setAllowPersonalEmail(integration.allow_personal_email)
    setLimitLinkedinConnect(integration.limit_linkedin_connect)
    setLimitLinkedinDm(integration.limit_linkedin_dm)
    setLimitEmail(integration.limit_email)
  }, [integration])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const body: UpdateIntegrationsBody = {
      notify_email: notifyEmail.trim() || null,
      notify_on_interest: notifyOnInterest,
      notify_on_objection: notifyOnObjection,
      allow_personal_email: allowPersonalEmail,
      limit_linkedin_connect: limitLinkedinConnect,
      limit_linkedin_dm: limitLinkedinDm,
      limit_email: limitEmail,
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
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-(--text-primary)">Conta</h1>
        <p className="mt-1 text-sm text-(--text-secondary)">
          Configurações da conta e preferências do tenant.
        </p>
      </div>

      {/* Informações do tenant — somente leitura */}
      <Card>
        <CardHeader>
          <CardTitle>Informações</CardTitle>
          <CardDescription>Dados do workspace atual. Somente leitura.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="tenant-name">Nome</Label>
            <Input id="tenant-name" value={tenant?.name ?? ""} disabled />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tenant-slug">Slug</Label>
            <Input id="tenant-slug" value={tenant?.slug ?? ""} disabled />
          </div>
        </CardContent>
      </Card>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Notificações */}
        <Card>
          <CardHeader>
            <CardTitle>Notificações</CardTitle>
            <CardDescription>Configure o e-mail e os eventos que disparam alertas.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="notify-email">E-mail de notificação</Label>
              <Input
                id="notify-email"
                type="email"
                placeholder="voce@empresa.com"
                value={notifyEmail}
                onChange={(e) => setNotifyEmail(e.target.value)}
              />
            </div>
            <Separator />
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium text-(--text-primary)">Eventos</legend>
              <CheckboxRow
                id="notify-interest"
                label="Notificar quando lead demonstrar interesse"
                checked={notifyOnInterest}
                onChange={setNotifyOnInterest}
              />
              <CheckboxRow
                id="notify-objection"
                label="Notificar quando lead levantar objeção"
                checked={notifyOnObjection}
                onChange={setNotifyOnObjection}
              />
            </fieldset>
          </CardContent>
        </Card>

        {/* Preferências */}
        <Card>
          <CardHeader>
            <CardTitle>Preferências</CardTitle>
          </CardHeader>
          <CardContent>
            <CheckboxRow
              id="allow-personal-email"
              label="Permitir envio para e-mails pessoais (além dos corporativos)"
              checked={allowPersonalEmail}
              onChange={setAllowPersonalEmail}
            />
          </CardContent>
        </Card>

        {/* Limites diários */}
        <Card>
          <CardHeader>
            <CardTitle>Limites diários por canal</CardTitle>
            <CardDescription>
              Máximo de disparos por dia para proteger a reputação da conta.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="limit-connect">LinkedIn Connect</Label>
                <Input
                  id="limit-connect"
                  type="number"
                  min={1}
                  max={50}
                  value={limitLinkedinConnect}
                  onChange={(e) => setLimitLinkedinConnect(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="limit-dm">LinkedIn DM</Label>
                <Input
                  id="limit-dm"
                  type="number"
                  min={1}
                  max={100}
                  value={limitLinkedinDm}
                  onChange={(e) => setLimitLinkedinDm(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="limit-email">E-mail</Label>
                <Input
                  id="limit-email"
                  type="number"
                  min={1}
                  max={1000}
                  value={limitEmail}
                  onChange={(e) => setLimitEmail(Number(e.target.value))}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Feedback do save */}
        {isError && (
          <p
            role="alert"
            className="rounded-md bg-(--danger-subtle) px-3 py-2 text-sm text-(--danger-subtle-fg)"
          >
            {error instanceof Error ? error.message : "Erro ao salvar configurações."}
          </p>
        )}
        {isSuccess && (
          <p
            role="status"
            className="rounded-md bg-(--success-subtle) px-3 py-2 text-sm text-(--success-subtle-fg)"
          >
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
