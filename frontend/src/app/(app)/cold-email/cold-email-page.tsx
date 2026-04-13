"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import {
  Mail,
  Send,
  Eye,
  MessageSquare,
  UserMinus,
  AlertCircle,
  Plus,
  FileText,
  Flame,
  Sparkles,
  Loader2,
  Pause,
  Play,
  ExternalLink,
  FlaskConical,
  ChevronDown,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import {
  useEmailStats,
  useEmailCadences,
  useEmailOverTime,
  useEmailABResults,
} from "@/lib/api/hooks/use-email-analytics"
import { useCadences } from "@/lib/api/hooks/use-cadences"
import { useTenant, useUpdateIntegrations } from "@/lib/api/hooks/use-tenant"
import { LLMConfigForm, type LLMConfig } from "@/components/cadencias/llm-config-form"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"
import { useQueryClient } from "@tanstack/react-query"

type Days = 7 | 30 | 90

const DEFAULT_COLD_EMAIL_LLM = {
  llm_provider: "openai" as const,
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

function KPICard({
  icon: Icon,
  label,
  value,
  sub,
  variant = "default",
}: {
  icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: "true" }>
  label: string
  value: string | number
  sub?: string | undefined
  variant?: "default" | "accent" | "danger"
}) {
  const valueClass =
    variant === "accent"
      ? "text-(--accent)"
      : variant === "danger"
        ? "text-red-500"
        : "text-(--text-primary)"

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
      <div className="flex items-center gap-2 text-(--text-secondary)">
        <Icon size={14} aria-hidden="true" />
        <span className="text-xs">{label}</span>
      </div>
      <p className={cn("mt-2 text-2xl font-bold", valueClass)}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-(--text-tertiary)">{sub}</p>}
    </div>
  )
}

// ── Modal de configuração de IA ────────────────────────────────────────

function ColdEmailAIModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data: tenant } = useTenant()
  const updateIntegrations = useUpdateIntegrations()
  const integration = tenant?.integration

  const [llmConfig, setLlmConfig] = useState<LLMConfig>(DEFAULT_COLD_EMAIL_LLM)

  // Sincroniza quando os dados do tenant carregam
  useEffect(() => {
    if (integration) {
      setLlmConfig({
        llm_provider: (integration.cold_email_llm_provider ??
          DEFAULT_COLD_EMAIL_LLM.llm_provider) as LLMConfig["llm_provider"],
        llm_model: integration.cold_email_llm_model ?? DEFAULT_COLD_EMAIL_LLM.llm_model,
        llm_temperature:
          integration.cold_email_llm_temperature ?? DEFAULT_COLD_EMAIL_LLM.llm_temperature,
        llm_max_tokens:
          integration.cold_email_llm_max_tokens ?? DEFAULT_COLD_EMAIL_LLM.llm_max_tokens,
      })
    }
  }, [integration])

  async function handleSave() {
    try {
      await updateIntegrations.mutateAsync({
        cold_email_llm_provider: llmConfig.llm_provider,
        cold_email_llm_model: llmConfig.llm_model,
        cold_email_llm_temperature: llmConfig.llm_temperature,
        cold_email_llm_max_tokens: llmConfig.llm_max_tokens,
      })
      toast.success("Configuração de IA para Cold Email salva.")
      onClose()
    } catch {
      toast.error("Erro ao salvar configuração.")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles size={16} className="text-(--accent)" />
            IA — Cold Email
          </DialogTitle>
          <p className="text-xs text-(--text-secondary)">
            Modelo padrão usado ao criar novas campanhas de e-mail.
          </p>
        </DialogHeader>
        <div className="py-2">
          <LLMConfigForm value={llmConfig} onChange={setLlmConfig} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-(--border-default) px-4 py-2 text-sm text-(--text-secondary) hover:bg-(--bg-overlay)"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={updateIntegrations.isPending}
            className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-(--accent-fg) hover:opacity-90 disabled:opacity-50"
          >
            {updateIntegrations.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
            Salvar configuração
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── Botão inline pause / activate ────────────────────────────────────

function CadenceToggleButton({ cadenceId, isActive }: { cadenceId: string; isActive: boolean }) {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  const [loading, setLoading] = useState(false)
  const [active, setActive] = useState(isActive)

  async function handleToggle() {
    setLoading(true)
    try {
      const client = createBrowserClient(session?.accessToken)
      await client.PATCH(`/cadences/${cadenceId}` as never, {
        body: { is_active: !active } as never,
      })
      setActive((prev) => !prev)
      toast.success(active ? "Cadência pausada." : "Cadência ativada.")
      await queryClient.invalidateQueries({ queryKey: ["email-analytics"] })
    } catch {
      toast.error("Erro ao alterar status da cadência.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleToggle}
      disabled={loading}
      title={active ? "Pausar campanha" : "Ativar campanha"}
      className={cn(
        "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors disabled:opacity-50",
        active
          ? "bg-green-100 text-green-700 hover:opacity-75 dark:bg-green-900/30 dark:text-green-400"
          : "bg-yellow-100 text-yellow-700 hover:opacity-75 dark:bg-yellow-900/30 dark:text-yellow-400",
      )}
    >
      {loading ? (
        <Loader2 size={9} className="animate-spin" />
      ) : active ? (
        <Pause size={9} />
      ) : (
        <Play size={9} />
      )}
      {active ? "Ativa" : "Pausada"}
    </button>
  )
}

// ── Seção A/B ─────────────────────────────────────────────────────────

function ABResultsSection({
  cadences,
}: {
  cadences: { cadence_id: string; cadence_name: string }[]
}) {
  const [selectedCadenceId, setSelectedCadenceId] = useState("")
  const [stepNumber, setStepNumber] = useState(1)
  const { data: abResults, isLoading } = useEmailABResults(selectedCadenceId, stepNumber)

  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface)">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-(--border-default) px-4 py-3">
        <div className="flex items-center gap-2">
          <FlaskConical size={14} className="text-(--text-secondary)" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-(--text-primary)">Resultados A/B de assunto</h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <select
              value={selectedCadenceId}
              onChange={(e) => setSelectedCadenceId(e.target.value)}
              aria-label="Selecione a cadência"
              className="appearance-none rounded-md border border-(--border-default) bg-(--bg-overlay) pl-3 pr-7 py-1.5 text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
            >
              <option value="">Selecione a cadência…</option>
              {cadences.map((c) => (
                <option key={c.cadence_id} value={c.cadence_id}>
                  {c.cadence_name}
                </option>
              ))}
            </select>
            <ChevronDown
              size={11}
              className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            />
          </div>
          <div className="relative">
            <select
              value={stepNumber}
              onChange={(e) => setStepNumber(Number(e.target.value))}
              aria-label="Número do step"
              className="appearance-none rounded-md border border-(--border-default) bg-(--bg-overlay) pl-3 pr-7 py-1.5 text-xs text-(--text-primary) focus:outline-none focus:ring-1 focus:ring-(--accent)"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  Step {n}
                </option>
              ))}
            </select>
            <ChevronDown
              size={11}
              className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-(--text-tertiary)"
            />
          </div>
        </div>
      </div>

      {!selectedCadenceId ? (
        <p className="px-4 py-8 text-center text-sm text-(--text-tertiary)">
          Selecione uma cadência para ver os resultados A/B dos assuntos.
        </p>
      ) : isLoading ? (
        <div className="flex items-center justify-center gap-2 px-4 py-8 text-sm text-(--text-secondary)">
          <Loader2 size={14} className="animate-spin" />
          Carregando…
        </div>
      ) : !abResults || abResults.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-(--text-tertiary)">
          Sem dados A/B para este step. Configure variantes de assunto na cadência.
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-(--border-subtle) text-left text-xs text-(--text-tertiary)">
              <th className="px-4 py-2">Assunto</th>
              <th className="px-4 py-2 text-right">Enviados</th>
              <th className="px-4 py-2 text-right">Abertos</th>
              <th className="px-4 py-2 text-right">Taxa abertura</th>
            </tr>
          </thead>
          <tbody>
            {abResults.map((r, i) => (
              <tr
                key={i}
                className="border-b border-(--border-subtle) last:border-0 hover:bg-(--bg-overlay)"
              >
                <td className="px-4 py-2.5 text-(--text-primary)">{r.subject || "—"}</td>
                <td className="px-4 py-2.5 text-right text-(--text-secondary)">{r.sent}</td>
                <td className="px-4 py-2.5 text-right text-(--text-secondary)">{r.opened}</td>
                <td className="px-4 py-2.5 text-right">
                  <span
                    className={cn(
                      "font-semibold",
                      r.open_rate >= 40
                        ? "text-green-600 dark:text-green-400"
                        : r.open_rate >= 20
                          ? "text-(--accent)"
                          : "text-(--text-secondary)",
                    )}
                  >
                    {r.open_rate}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────

export default function ColdEmailPage() {
  const [days, setDays] = useState<Days>(30)
  const [aiModalOpen, setAiModalOpen] = useState(false)
  const { data: stats, isLoading: loadingStats } = useEmailStats(days)
  const { data: analyticsData, isLoading: loadingCadences } = useEmailCadences(days)
  const { data: allEmailCadences, isLoading: loadingAllCadences } = useCadences("email_only")
  const { data: overTime } = useEmailOverTime(days)

  // Merge: show all email_only cadences, with analytics when available
  const analyticsMap = new Map((analyticsData ?? []).map((c) => [c.cadence_id, c]))
  const mergedCadences = (allEmailCadences ?? []).map((c) => ({
    cadence_id: c.id,
    cadence_name: c.name,
    sent: analyticsMap.get(c.id)?.sent ?? 0,
    opened: analyticsMap.get(c.id)?.opened ?? 0,
    replied: analyticsMap.get(c.id)?.replied ?? 0,
    bounced: analyticsMap.get(c.id)?.bounced ?? 0,
    open_rate: analyticsMap.get(c.id)?.open_rate ?? 0,
    reply_rate: analyticsMap.get(c.id)?.reply_rate ?? 0,
    is_active: c.is_active,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Cold Email</h1>
          <p className="text-sm text-(--text-secondary)">Cadências de prospecção por e-mail</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/cold-email/warmup"
            className="flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--bg-overlay)"
          >
            <Flame size={14} aria-hidden="true" />
            Warmup
          </Link>
          <Link
            href="/cold-email/templates"
            className="flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--bg-overlay)"
          >
            <FileText size={14} aria-hidden="true" />
            Templates
          </Link>
          <button
            type="button"
            onClick={() => setAiModalOpen(true)}
            className="flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition-colors hover:bg-(--bg-overlay)"
          >
            <Sparkles size={14} aria-hidden="true" />
            IA
          </button>
          <Link
            href="/cold-email/nova-campanha"
            className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
          >
            <Plus size={14} aria-hidden="true" />
            Nova campanha e-mail
          </Link>
        </div>
      </div>

      <ColdEmailAIModal open={aiModalOpen} onClose={() => setAiModalOpen(false)} />

      <div className="flex gap-1 rounded-md border border-(--border-default) bg-(--bg-overlay) p-1 w-fit">
        {([7, 30, 90] as Days[]).map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDays(d)}
            className={cn(
              "rounded px-3 py-1 text-xs font-medium transition-colors",
              days === d
                ? "bg-(--bg-surface) text-(--text-primary) shadow-sm"
                : "text-(--text-secondary) hover:text-(--text-primary)",
            )}
          >
            {d} dias
          </button>
        ))}
      </div>

      {/* KPIs */}
      {loadingStats ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-(--bg-overlay)" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <KPICard icon={Send} label="Enviados" value={stats?.sent ?? 0} />
          <KPICard
            icon={Eye}
            label="Taxa de abertura"
            value={`${stats?.open_rate ?? 0}%`}
            sub={`${stats?.opened ?? 0} abertos`}
            variant="accent"
          />
          <KPICard
            icon={MessageSquare}
            label="Taxa de resposta"
            value={`${stats?.reply_rate ?? 0}%`}
            sub={`${stats?.replied ?? 0} respostas`}
          />
          <KPICard
            icon={UserMinus}
            label="Descadastros"
            value={stats?.unsubscribed ?? 0}
            sub={stats?.unsubscribe_rate != null ? `${stats.unsubscribe_rate}%` : undefined}
          />
          <KPICard
            icon={AlertCircle}
            label="Bounce rate"
            value={`${stats?.bounce_rate ?? 0}%`}
            sub={`${stats?.bounced ?? 0} bounces`}
            variant={(stats?.bounce_rate ?? 0) > 2 ? "danger" : "default"}
          />
        </div>
      )}

      {/* Gráfico ao longo do tempo */}
      {overTime && overTime.length > 0 && (
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4">
          <h2 className="mb-4 text-sm font-semibold text-(--text-primary)">
            Evolução nos últimos {days} dias
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={overTime} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line
                type="monotone"
                dataKey="sent"
                name="Enviados"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="opened"
                name="Abertos"
                stroke="var(--success)"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="replied"
                name="Respondidos"
                stroke="var(--info)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tabela de cadências */}
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface)">
        <div className="flex items-center justify-between border-b border-(--border-default) px-4 py-3">
          <h2 className="text-sm font-semibold text-(--text-primary)">Performance por cadência</h2>
          <Link
            href="/cadencias?cadence_type=email_only"
            className="text-xs text-(--accent) hover:underline"
          >
            Ver todas →
          </Link>
        </div>
        {loadingCadences || loadingAllCadences ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-(--bg-overlay)" />
            ))}
          </div>
        ) : mergedCadences.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-(--border-subtle) text-left text-xs text-(--text-tertiary)">
                  <th className="px-4 py-2">Cadência</th>
                  <th className="px-4 py-2 text-right">Enviados</th>
                  <th className="px-4 py-2 text-right">T. Abertura</th>
                  <th className="px-4 py-2 text-right">T. Resposta</th>
                  <th className="px-4 py-2 text-right">Bounce</th>
                  <th className="px-4 py-2 text-center">Status</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {mergedCadences.map((c) => (
                  <tr
                    key={c.cadence_id}
                    className="border-b border-(--border-subtle) last:border-0 hover:bg-(--bg-overlay)"
                  >
                    <td className="px-4 py-2.5">
                      <Link
                        href={`/cadencias/${c.cadence_id}`}
                        className="font-medium text-(--text-primary) hover:underline"
                      >
                        {c.cadence_name}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-right text-(--text-secondary)">
                      {c.sent > 0 ? c.sent : <span className="text-(--text-disabled)">—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium text-(--accent)">
                      {c.sent > 0 ? (
                        `${c.open_rate}%`
                      ) : (
                        <span className="text-(--text-disabled)">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium text-green-600 dark:text-green-400">
                      {c.sent > 0 ? (
                        `${c.reply_rate}%`
                      ) : (
                        <span className="text-(--text-disabled)">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          c.bounced > 0 ? "text-red-500" : "text-(--text-tertiary)",
                        )}
                      >
                        {c.bounced > 0 ? c.bounced : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <CadenceToggleButton cadenceId={c.cadence_id} isActive={c.is_active} />
                    </td>
                    <td className="px-4 py-2.5">
                      <Link
                        href={`/cadencias/${c.cadence_id}`}
                        title="Ver cadência"
                        className="flex justify-end text-(--text-tertiary) hover:text-(--text-primary)"
                      >
                        <ExternalLink size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-center">
            <Mail size={28} className="text-(--text-disabled)" aria-hidden="true" />
            <p className="text-sm text-(--text-secondary)">
              Nenhuma cadência de e-mail criada ainda.
            </p>
            <Link
              href="/cold-email/nova-campanha"
              className="text-sm text-(--accent) hover:underline"
            >
              Criar campanha de e-mail
            </Link>
          </div>
        )}
      </div>

      {/* A/B Results */}
      {mergedCadences.length > 0 && <ABResultsSection cadences={mergedCadences} />}
    </div>
  )
}
