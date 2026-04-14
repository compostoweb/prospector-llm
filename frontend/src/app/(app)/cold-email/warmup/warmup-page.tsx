"use client"

import { useState } from "react"
import {
  Flame,
  Plus,
  Loader2,
  Pause,
  Play,
  Trash2,
  BarChart2,
  CheckCircle2,
  Clock,
} from "lucide-react"
import {
  useWarmupCampaigns,
  useWarmupStats,
  useCreateWarmupCampaign,
  useStartWarmup,
  usePauseWarmup,
  useDeleteWarmupCampaign,
  type WarmupCampaign,
} from "@/lib/api/hooks/use-warmup"
import { useEmailAccounts } from "@/lib/api/hooks/use-email-accounts"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// ── Helpers ───────────────────────────────────────────────────────────

const STATUS_STYLES = {
  active: "bg-(--success-subtle) text-(--success-subtle-fg)",
  paused: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
  completed: "bg-(--bg-overlay) text-(--text-tertiary)",
}

const STATUS_LABELS = {
  active: "Ativo",
  paused: "Pausado",
  completed: "Concluído",
}

// ── KPI card ──────────────────────────────────────────────────────────

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
      <p className="text-xs text-(--text-tertiary)">{label}</p>
      <p className="mt-1 text-2xl font-bold text-(--text-primary)">{value}</p>
    </div>
  )
}

// ── Stats panel ───────────────────────────────────────────────────────

function CampaignStats({ campaignId }: { campaignId: string }) {
  const { data: stats, isLoading } = useWarmupStats(campaignId)

  if (isLoading) {
    return (
      <div className="flex h-16 items-center justify-center">
        <Loader2 size={16} className="animate-spin text-(--text-tertiary)" />
      </div>
    )
  }
  if (!stats) return null

  // Gauge de progresso
  const progress = Math.min(stats.progress_pct, 100)

  return (
    <div className="mt-4 space-y-3">
      <div>
        <div className="mb-1 flex justify-between text-xs text-(--text-tertiary)">
          <span>Progresso do ramp-up</span>
          <span>
            Dia {stats.current_day} de {stats.ramp_days}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-(--bg-overlay)">
          <div
            className="h-full rounded-full bg-(--brand) transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2">
        <KpiCard label="Total enviados" value={stats.total_sent} />
        <KpiCard label="Respondidos" value={stats.total_replied} />
        <KpiCard label="Taxa de resposta" value={`${stats.reply_rate_pct}%`} />
        <KpiCard label="Taxa de spam" value={`${stats.spam_rate_pct}%`} />
      </div>
      <p className="text-xs text-(--text-tertiary)">
        Volume hoje: <strong>{stats.daily_volume_today}</strong> e-mails (meta:{" "}
        {stats.daily_volume_target})
      </p>
    </div>
  )
}

// ── Campaign card ─────────────────────────────────────────────────────

function CampaignCard({
  campaign,
  accountEmail,
}: {
  campaign: WarmupCampaign
  accountEmail: string
}) {
  const [expanded, setExpanded] = useState(false)
  const { mutate: start, isPending: starting } = useStartWarmup()
  const { mutate: pause, isPending: pausing } = usePauseWarmup()
  const { mutate: del, isPending: deleting } = useDeleteWarmupCampaign()

  function handleDelete() {
    if (!confirm("Remover esta campanha de warmup?")) return
    del(campaign.id)
  }

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[campaign.status]}`}
            >
              {STATUS_LABELS[campaign.status]}
            </span>
            <p className="truncate text-sm font-medium text-(--text-primary)">{accountEmail}</p>
          </div>
          <p className="mt-1 text-xs text-(--text-tertiary)">
            {campaign.daily_volume_start} → {campaign.daily_volume_target} e-mails/dia em{" "}
            {campaign.ramp_days} dias
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {campaign.status === "active" ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => pause(campaign.id)}
              disabled={pausing}
              title="Pausar"
            >
              {pausing ? <Loader2 size={13} className="animate-spin" /> : <Pause size={13} />}
            </Button>
          ) : campaign.status === "paused" ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => start(campaign.id)}
              disabled={starting}
              title="Retomar"
            >
              {starting ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setExpanded((e) => !e)}
            title="Ver estatísticas"
          >
            <BarChart2 size={13} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-(--text-tertiary) hover:text-(--danger)"
            onClick={handleDelete}
            disabled={deleting}
            title="Remover"
          >
            {deleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
          </Button>
        </div>
      </div>
      {expanded && <CampaignStats campaignId={campaign.id} />}
    </div>
  )
}

// ── Modal de criação ──────────────────────────────────────────────────

function CreateModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data: accountsData } = useEmailAccounts()
  const { mutate: create, isPending, error } = useCreateWarmupCampaign()

  const [accountId, setAccountId] = useState("")
  const [volStart, setVolStart] = useState(5)
  const [volTarget, setVolTarget] = useState(80)
  const [rampDays, setRampDays] = useState(30)

  const accounts = accountsData?.accounts ?? []

  function handleCreate() {
    if (!accountId) return
    create(
      {
        email_account_id: accountId,
        daily_volume_start: volStart,
        daily_volume_target: volTarget,
        ramp_days: rampDays,
      },
      {
        onSuccess: () => {
          onClose()
          setAccountId("")
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nova campanha de warmup</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3 py-2">
          <div className="space-y-1">
            <Label>Conta de e-mail</Label>
            <Select value={accountId} onValueChange={setAccountId}>
              <SelectTrigger>
                <SelectValue placeholder="Selecione uma conta" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((acc) => (
                  <SelectItem key={acc.id} value={acc.id}>
                    {acc.display_name} ({acc.email_address})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label>Vol. inicial</Label>
              <Input
                type="number"
                value={volStart}
                min={1}
                max={100}
                onChange={(e) => setVolStart(parseInt(e.target.value) || 5)}
              />
            </div>
            <div className="space-y-1">
              <Label>Vol. alvo</Label>
              <Input
                type="number"
                value={volTarget}
                min={5}
                max={500}
                onChange={(e) => setVolTarget(parseInt(e.target.value) || 80)}
              />
            </div>
            <div className="space-y-1">
              <Label>Dias</Label>
              <Input
                type="number"
                value={rampDays}
                min={7}
                max={90}
                onChange={(e) => setRampDays(parseInt(e.target.value) || 30)}
              />
            </div>
          </div>
          <p className="text-xs text-(--text-tertiary)">
            O volume crescerá de {volStart} para {volTarget} e-mails/dia ao longo de {rampDays}{" "}
            dias.
          </p>
          {error && <p className="text-sm text-(--danger)">{error.message}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleCreate} disabled={isPending || !accountId}>
            {isPending ? <Loader2 size={14} className="animate-spin" /> : "Criar campanha"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Página principal ──────────────────────────────────────────────────

export default function WarmupPage() {
  const { data: campaigns, isLoading } = useWarmupCampaigns()
  const { data: accountsData } = useEmailAccounts()
  const [createOpen, setCreateOpen] = useState(false)

  const accounts = accountsData?.accounts ?? []

  function getAccountEmail(accountId: string) {
    return accounts.find((a) => a.id === accountId)?.email_address ?? accountId
  }

  const active = campaigns?.filter((c) => c.status === "active") ?? []
  const paused = campaigns?.filter((c) => c.status === "paused") ?? []
  const completed = campaigns?.filter((c) => c.status === "completed") ?? []

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-(--text-primary)">Warmup de E-mail</h1>
          <p className="mt-1 text-sm text-(--text-secondary)">
            Aquece contas de e-mail gradualmente para melhorar a entregabilidade e evitar spam.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={14} className="mr-1" />
          Nova campanha
        </Button>
      </div>

      {/* Resumo */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="flex items-center gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
          <Flame size={20} className="text-(--brand)" />
          <div>
            <p className="text-xs text-(--text-tertiary)">Ativas</p>
            <p className="text-xl font-bold text-(--text-primary)">{active.length}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
          <Clock size={20} className="text-(--warning)" />
          <div>
            <p className="text-xs text-(--text-tertiary)">Pausadas</p>
            <p className="text-xl font-bold text-(--text-primary)">{paused.length}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
          <CheckCircle2 size={20} className="text-(--success)" />
          <div>
            <p className="text-xs text-(--text-tertiary)">Concluídas</p>
            <p className="text-xl font-bold text-(--text-primary)">{completed.length}</p>
          </div>
        </div>
      </div>

      {/* Lista de campanhas */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Campanhas</CardTitle>
          <CardDescription>
            Cada campanha aquece uma conta de e-mail ao longo de X dias.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-24 items-center justify-center">
              <Loader2 size={18} className="animate-spin text-(--text-tertiary)" />
            </div>
          ) : !campaigns || campaigns.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-10 text-(--text-tertiary)">
              <Flame size={28} />
              <p className="text-sm">Nenhuma campanha de warmup ainda.</p>
              <Button size="sm" variant="outline" onClick={() => setCreateOpen(true)}>
                <Plus size={13} className="mr-1" />
                Criar primeira campanha
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {campaigns.map((c) => (
                <CampaignCard
                  key={c.id}
                  campaign={c}
                  accountEmail={getAccountEmail(c.email_account_id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
