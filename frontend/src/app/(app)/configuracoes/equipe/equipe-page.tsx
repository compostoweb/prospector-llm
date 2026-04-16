"use client"

import { useEffect, useState } from "react"
import { Loader2, MailPlus, Shield, Trash2, UserCog, Users } from "lucide-react"
import { toast } from "sonner"
import {
  useInviteTenantMember,
  useRemoveTenantMember,
  useTenantMembers,
  useUpdateTenantMember,
  type TenantMember,
  type TenantRole,
} from "@/lib/api/hooks/use-tenant-members"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { EmptyState } from "@/components/shared/empty-state"
import { SettingsPageShell, SettingsPanel } from "@/components/settings/settings-shell"

function roleLabel(role: TenantRole) {
  return role === "tenant_admin" ? "Admin do tenant" : "Usuário do tenant"
}

function MemberDialog({
  member,
  open,
  onClose,
}: {
  member: TenantMember | null
  open: boolean
  onClose: () => void
}) {
  const inviteMember = useInviteTenantMember()
  const updateMember = useUpdateTenantMember()
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [role, setRole] = useState<TenantRole>("tenant_user")

  useEffect(() => {
    if (!open) {
      return
    }
    setEmail(member?.email ?? "")
    setName(member?.name ?? "")
    setRole(member?.role ?? "tenant_user")
  }, [member, open])

  async function handleSubmit() {
    try {
      if (member) {
        await updateMember.mutateAsync({
          membershipId: member.membership_id,
          body: { role, is_active: true },
        })
        toast.success("Permissões atualizadas")
      } else {
        await inviteMember.mutateAsync({
          email: email.trim(),
          name: name.trim() || null,
          role,
        })
        toast.success("Membro vinculado ao tenant")
      }
      onClose()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao salvar membro")
    }
  }

  const isPending = inviteMember.isPending || updateMember.isPending

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{member ? "Editar acesso" : "Adicionar membro"}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="member-email">Email</Label>
            <Input
              id="member-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={!!member}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="member-name">Nome</Label>
            <Input id="member-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Papel</Label>
            <Select value={role} onValueChange={(value) => setRole(value as TenantRole)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tenant_admin">Admin do tenant</SelectItem>
                <SelectItem value="tenant_user">Usuário do tenant</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button onClick={() => void handleSubmit()} disabled={isPending || !email.trim()}>
            {isPending ? <Loader2 size={14} className="animate-spin" /> : null}
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function EquipePage() {
  const { data: members = [], isLoading } = useTenantMembers()
  const removeMember = useRemoveTenantMember()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedMember, setSelectedMember] = useState<TenantMember | null>(null)

  async function handleRemove(member: TenantMember) {
    try {
      await removeMember.mutateAsync(member.membership_id)
      toast.success("Acesso removido do tenant")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao remover membro")
    }
  }

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
      title="Equipe"
      description="Controle quem pode acessar este tenant e qual papel cada email terá no login com Google."
      actions={
        <Button
          onClick={() => {
            setSelectedMember(null)
            setDialogOpen(true)
          }}
        >
          <MailPlus size={14} />
          Adicionar membro
        </Button>
      }
    >
      {members.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Nenhum membro vinculado"
          description="Adicione os emails autorizados para este tenant. Somente emails cadastrados poderão entrar via Google."
          action={
            <Button
              onClick={() => {
                setSelectedMember(null)
                setDialogOpen(true)
              }}
            >
              Adicionar primeiro membro
            </Button>
          }
        />
      ) : (
        <SettingsPanel
          title="Acessos do tenant"
          description="Admins do tenant conseguem gerenciar equipe e configurações. Usuários do tenant têm acesso operacional normal."
          contentClassName="p-0"
        >
          <div className="divide-y divide-(--border-subtle)">
            {members.map((member) => (
              <div
                key={member.membership_id}
                className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-medium text-(--text-primary)">
                      {member.name || member.email}
                    </p>
                    <Badge variant={member.role === "tenant_admin" ? "default" : "outline"}>
                      {roleLabel(member.role)}
                    </Badge>
                    <Badge variant={member.is_active ? "success" : "outline"}>
                      {member.is_active ? "Ativo" : "Inativo"}
                    </Badge>
                    {member.is_superuser ? <Badge variant="info">Superuser</Badge> : null}
                  </div>
                  <p className="truncate text-sm text-(--text-secondary)">{member.email}</p>
                  <p className="text-xs text-(--text-tertiary)">
                    Vinculado em {new Date(member.joined_at).toLocaleDateString("pt-BR")}
                    {member.invited_by_email ? ` por ${member.invited_by_email}` : ""}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedMember(member)
                      setDialogOpen(true)
                    }}
                  >
                    <UserCog size={14} />
                    Editar
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => void handleRemove(member)}>
                    <Trash2 size={14} />
                    Remover
                  </Button>
                  {member.role === "tenant_admin" ? (
                    <Button variant="ghost" size="sm" disabled>
                      <Shield size={14} />
                      Admin
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </SettingsPanel>
      )}

      <MemberDialog
        member={selectedMember}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </SettingsPageShell>
  )
}
