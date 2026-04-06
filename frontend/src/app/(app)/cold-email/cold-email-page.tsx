"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Mail, Send, Eye, MessageSquare, UserMinus, Plus, FileText, Flame, Sparkles, Loader2 } from "lucide-react"
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
} from "@/lib/api/hooks/use-email-analytics"
import { useTenant, useUpdateIntegrations } from "@/lib/api/hooks/use-tenant"
import { LLMConfigForm, type LLMConfig } from "@/components/cadencias/llm-config-form"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

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
  highlight,
}: {
  icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: "true" }>
  label: string
  value: string | number
  sub?: string
  highlight?: boolean
}) {
  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
      <div className="flex items-center gap-2 text-(--text-secondary)">
        <Icon size={14} aria-hidden="true" />
        <span className="text-xs">{label}</span>
      </div>
      <p
        className={cn(
          "mt-2 text-2xl font-bold",
          highlight ? "text-(--accent)" : "text-(--text-primary)",
        )}
      >
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs text-(--text-tertiary)">{sub}</p>}
    </div>
  )
}

// ── Modal de configuração de IA ────────────────────────────────────────

function ColdEmailAIModal({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const { data: tenant } = useTenant()
  const updateIntegrations = useUpdateIntegrations()
  const integration = tenant?.integration

  const [llmConfig, setLlmConfig] = useState<LLMConfig>(DEFAULT_COLD_EMAIL_LLM)

  // Sincroniza quando os dados do tenant carregam
  useEffect(() => {
    if (integration) {
      setLlmConfig({
        llm_provider: (integration.cold_email_llm_provider ?? DEFAULT_COLD_EMAIL_LLM.llm_provider) as "openai" | "gemini",
        llm_model: integration.cold_email_llm_model ?? DEFAULT_COLD_EMAIL_LLM.llm_model,
        llm_temperature: integration.cold_email_llm_temperature ?? DEFAULT_COLD_EMAIL_LLM.llm_temperature,
        llm_max_tokens: integration.cold_email_llm_max_tokens ?? DEFAULT_COLD_EMAIL_LLM.llm_max_tokens,
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

// ── Página principal ──────────────────────────────────────────────────

export default function ColdEmailPage() {
  const [days, setDays] = useState<Days>(30)
  const [aiModalOpen, setAiModalOpen] = useState(false)
  const { data: stats, isLoading: loadingStats } = useEmailStats(days)
  const { data: cadences, isLoading: loadingCadences } = useEmailCadences(days)
  const { data: overTime } = useEmailOverTime(days)

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
            href="/cadencias/nova?preset=cold-email"
            className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-(--accent-hover)"
          >
            <Plus size={14} aria-hidden="true" />
            Nova cadência e-mail
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
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-(--bg-overlay)" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <KPICard icon={Send} label="Enviados" value={stats?.sent ?? 0} />
          <KPICard
            icon={Eye}
            label="Taxa de abertura"
            value={`${stats?.open_rate ?? 0}%`}
            sub={`${stats?.opened ?? 0} abertos`}
            highlight
          />
          <KPICard
            icon={MessageSquare}
            label="Taxa de resposta"
            value={`${stats?.reply_rate ?? 0}%`}
            sub={`${stats?.replied ?? 0} respostas`}
          />
          <KPICard icon={UserMinus} label="Descadastros" value={stats?.unsubscribed ?? 0} />
        </div>
      )}

      {/* Gráfico ao longo do tempo */}
      {overTime && overTime.length > 0 && (
        <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
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
      <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
        <div className="flex items-center justify-between border-b border-(--border-default) px-4 py-3">
          <h2 className="text-sm font-semibold text-(--text-primary)">Performance por cadência</h2>
          <Link
            href="/cadencias?cadence_type=email_only"
            className="text-xs text-(--accent) hover:underline"
          >
            Ver todas →
          </Link>
        </div>
        {loadingCadences ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded bg-(--bg-overlay)" />
            ))}
          </div>
        ) : cadences && cadences.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-(--border-subtle) text-left text-xs text-(--text-tertiary)">
                <th className="px-4 py-2">Cadência</th>
                <th className="px-4 py-2 text-right">Enviados</th>
                <th className="px-4 py-2 text-right">Abertos</th>
                <th className="px-4 py-2 text-right">T. Abertura</th>
                <th className="px-4 py-2 text-right">Respondidos</th>
                <th className="px-4 py-2 text-right">T. Resposta</th>
              </tr>
            </thead>
            <tbody>
              {cadences.map((c) => (
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
                  <td className="px-4 py-2.5 text-right text-(--text-secondary)">{c.sent}</td>
                  <td className="px-4 py-2.5 text-right text-(--text-secondary)">{c.opened}</td>
                  <td className="px-4 py-2.5 text-right font-medium text-(--accent)">
                    {c.open_rate}%
                  </td>
                  <td className="px-4 py-2.5 text-right text-(--text-secondary)">{c.replied}</td>
                  <td className="px-4 py-2.5 text-right font-medium text-(--success)">
                    {c.reply_rate}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-center">
            <Mail size={28} className="text-(--text-disabled)" aria-hidden="true" />
            <p className="text-sm text-(--text-secondary)">
              Nenhuma cadência de e-mail encontrada para este período.
            </p>
            <Link
              href="/cadencias/nova?preset=cold-email"
              className="text-sm text-(--accent) hover:underline"
            >
              Criar cadência de e-mail
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
