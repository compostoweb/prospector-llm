"use client"

import { useEffect, useState } from "react"
import { Building2, Loader2, Pencil, Plus, Shield, Users } from "lucide-react"
import { toast } from "sonner"
import {
  useAdminTenants,
  useCreateTenant,
  useUpdateTenant,
  type AdminTenant,
} from "@/lib/api/hooks/use-admin-tenants"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { EmptyState } from "@/components/shared/empty-state"
import { SettingsPageShell, SettingsPanel } from "@/components/settings/settings-shell"

interface TenantDialogState {
  open: boolean
  tenant: AdminTenant | null
}

function TenantDialog({ state, onClose }: { state: TenantDialogState; onClose: () => void }) {
  const createTenant = useCreateTenant()
  const updateTenant = useUpdateTenant()
  const [name, setName] = useState("")
  const [slug, setSlug] = useState("")
  const [primaryAdminEmail, setPrimaryAdminEmail] = useState("")
  const [primaryAdminName, setPrimaryAdminName] = useState("")
  const [isActive, setIsActive] = useState(true)

  useEffect(() => {
    if (!state.open) {
      return
    }
    setName(state.tenant?.name ?? "")
    setSlug(state.tenant?.slug ?? "")
    setPrimaryAdminEmail(state.tenant?.primary_admin_email ?? "")
    setPrimaryAdminName("")
    setIsActive(state.tenant?.is_active ?? true)
  }, [state])

  async function handleSubmit() {
    try {
      if (state.tenant) {
        await updateTenant.mutateAsync({
          tenantId: state.tenant.id,
          body: {
            name: name.trim(),
            slug: slug.trim(),
            is_active: isActive,
          },
        })
        toast.success("Tenant atualizado")
      } else {
        await createTenant.mutateAsync({
          name: name.trim(),
          slug: slug.trim(),
          primary_admin_email: primaryAdminEmail.trim() || null,
          primary_admin_name: primaryAdminName.trim() || null,
        })
        toast.success("Tenant criado")
      }
      onClose()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao salvar tenant")
    }
  }

  const isPending = createTenant.isPending || updateTenant.isPending

  return (
    <Dialog open={state.open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{state.tenant ? "Editar tenant" : "Novo tenant"}</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="tenant-name">Nome</Label>
            <Input id="tenant-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tenant-slug">Slug</Label>
            <Input id="tenant-slug" value={slug} onChange={(e) => setSlug(e.target.value)} />
          </div>

          {!state.tenant ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="primary-admin-email">Email do admin inicial</Label>
                <Input
                  id="primary-admin-email"
                  type="email"
                  value={primaryAdminEmail}
                  onChange={(e) => setPrimaryAdminEmail(e.target.value)}
                  placeholder="admin@cliente.com"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="primary-admin-name">Nome do admin inicial</Label>
                <Input
                  id="primary-admin-name"
                  value={primaryAdminName}
                  onChange={(e) => setPrimaryAdminName(e.target.value)}
                  placeholder="Nome opcional"
                />
              </div>
            </>
          ) : (
            <label className="flex items-center gap-2 rounded-lg border border-(--border-default) px-3 py-2.5 text-sm text-(--text-secondary)">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4 rounded accent-(--accent)"
              />
              Tenant ativo
            </label>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button
            onClick={() => void handleSubmit()}
            disabled={isPending || !name.trim() || !slug.trim()}
          >
            {isPending ? <Loader2 className="animate-spin" size={14} /> : null}
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function ClientesPage() {
  const { data: tenants = [], isLoading } = useAdminTenants()
  const [dialogState, setDialogState] = useState<TenantDialogState>({ open: false, tenant: null })

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2
          size={18}
          className="animate-spin text-(--text-tertiary)"
          aria-label="Carregando"
        />
      </div>
    )
  }

  return (
    <SettingsPageShell
      title="Tenants"
      description="Gerencie os workspaces do sistema, acompanhe responsáveis e faça o bootstrap do admin inicial de cada cliente."
      actions={
        <Button onClick={() => setDialogState({ open: true, tenant: null })}>
          <Plus size={14} />
          Novo tenant
        </Button>
      }
    >
      {tenants.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="Nenhum tenant cadastrado"
          description="Crie o primeiro tenant para iniciar o provisionamento de clientes."
          action={
            <Button onClick={() => setDialogState({ open: true, tenant: null })}>
              Criar tenant
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {tenants.map((tenant) => (
            <SettingsPanel
              key={tenant.id}
              title={tenant.name}
              description={`/${tenant.slug}`}
              headerAside={
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setDialogState({ open: true, tenant })}
                >
                  <Pencil size={14} />
                  Editar
                </Button>
              }
            >
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={tenant.is_active ? "success" : "outline"}>
                    {tenant.is_active ? "Ativo" : "Inativo"}
                  </Badge>
                  <Badge variant="outline">{tenant.member_count} membros</Badge>
                  <Badge variant="outline">{tenant.admin_count} admins</Badge>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-3">
                    <div className="flex items-center gap-2 text-(--text-secondary)">
                      <Users size={14} />
                      <span className="text-xs uppercase tracking-wide">Equipe</span>
                    </div>
                    <p className="mt-2 text-lg font-semibold text-(--text-primary)">
                      {tenant.member_count}
                    </p>
                  </div>
                  <div className="rounded-lg border border-(--border-default) bg-(--bg-page) p-3">
                    <div className="flex items-center gap-2 text-(--text-secondary)">
                      <Shield size={14} />
                      <span className="text-xs uppercase tracking-wide">Admin principal</span>
                    </div>
                    <p className="mt-2 truncate text-sm font-medium text-(--text-primary)">
                      {tenant.primary_admin_email ?? "Não definido"}
                    </p>
                  </div>
                </div>
              </div>
            </SettingsPanel>
          ))}
        </div>
      )}

      <TenantDialog
        state={dialogState}
        onClose={() => setDialogState({ open: false, tenant: null })}
      />
    </SettingsPageShell>
  )
}
