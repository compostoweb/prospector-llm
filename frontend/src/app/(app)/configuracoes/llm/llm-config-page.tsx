"use client"

import {
  useLLMModels,
  useLLMProviders,
  useTestModel,
  useSyncLLMModels,
} from "@/lib/api/hooks/use-llm-models"
import { useTenant, useUpdateIntegrations } from "@/lib/api/hooks/use-tenant"
import { LLMConfigForm, type LLMConfig } from "@/components/cadencias/llm-config-form"
import { LLMConsumptionPanel } from "@/components/settings/llm-consumption-panel"
import { useState, useEffect } from "react"
import {
  BarChart3,
  CheckCircle2,
  XCircle,
  Loader2,
  Zap,
  Save,
  SlidersHorizontal,
  LayoutList,
  FlaskConical,
  RefreshCw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type Tab = "padrao" | "modelos" | "consumo" | "testar"
type ModelFilter = "all" | "openai" | "gemini" | "anthropic"

const DEFAULT_LLM = {
  llm_provider: "openai" as const,
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 1024,
}

const DEFAULT_COLD_EMAIL_LLM = {
  llm_provider: "openai" as const,
  llm_model: "gpt-4o-mini",
  llm_temperature: 0.7,
  llm_max_tokens: 512,
}

export default function LLMConfigPage() {
  const [activeTab, setActiveTab] = useState<Tab>("padrao")
  const [modelFilter, setModelFilter] = useState<ModelFilter>("all")

  const { data: providersData } = useLLMProviders()
  const { data: modelsData, isLoading: loadingModels } = useLLMModels()
  const syncModels = useSyncLLMModels()
  const { data: tenant } = useTenant()
  const updateIntegrations = useUpdateIntegrations()
  const testModel = useTestModel()

  const integration = tenant?.integration

  const [systemLLM, setSystemLLM] = useState<LLMConfig>(DEFAULT_LLM)
  const [coldEmailLLM, setColdEmailLLM] = useState<LLMConfig>(DEFAULT_COLD_EMAIL_LLM)

  // Sincroniza quando os dados do tenant chegam pela API
  useEffect(() => {
    if (!integration) return
    setSystemLLM({
      llm_provider: (integration.llm_default_provider ?? DEFAULT_LLM.llm_provider) as
        | "openai"
        | "gemini",
      llm_model: integration.llm_default_model ?? DEFAULT_LLM.llm_model,
      llm_temperature: integration.llm_default_temperature ?? DEFAULT_LLM.llm_temperature,
      llm_max_tokens: integration.llm_default_max_tokens ?? DEFAULT_LLM.llm_max_tokens,
    })
    setColdEmailLLM({
      llm_provider: (integration.cold_email_llm_provider ?? DEFAULT_COLD_EMAIL_LLM.llm_provider) as
        | "openai"
        | "gemini",
      llm_model: integration.cold_email_llm_model ?? DEFAULT_COLD_EMAIL_LLM.llm_model,
      llm_temperature:
        integration.cold_email_llm_temperature ?? DEFAULT_COLD_EMAIL_LLM.llm_temperature,
      llm_max_tokens:
        integration.cold_email_llm_max_tokens ?? DEFAULT_COLD_EMAIL_LLM.llm_max_tokens,
    })
  }, [integration])

  const [testProvider, setTestProvider] = useState("openai")
  const [testModelId, setTestModelId] = useState("")
  const [testPrompt, setTestPrompt] = useState("Olá! Responda com uma frase curta em português.")
  const [testResult, setTestResult] = useState<{
    success: boolean
    response?: string
    error?: string
  } | null>(null)

  const providers = providersData?.details ?? []
  const models = modelsData?.models ?? []
  const filteredModels =
    modelFilter === "all" ? models : models.filter((m) => m.provider === modelFilter)
  const testableModels = models.filter((m) => m.provider === testProvider)

  async function handleSaveSystem() {
    try {
      await updateIntegrations.mutateAsync({
        llm_default_provider: systemLLM.llm_provider,
        llm_default_model: systemLLM.llm_model,
        llm_default_temperature: systemLLM.llm_temperature,
        llm_default_max_tokens: systemLLM.llm_max_tokens,
      })
      toast.success("Modelo padrão do sistema salvo.")
    } catch {
      toast.error("Erro ao salvar configuração.")
    }
  }

  async function handleSaveColdEmail() {
    try {
      await updateIntegrations.mutateAsync({
        cold_email_llm_provider: coldEmailLLM.llm_provider,
        cold_email_llm_model: coldEmailLLM.llm_model,
        cold_email_llm_temperature: coldEmailLLM.llm_temperature,
        cold_email_llm_max_tokens: coldEmailLLM.llm_max_tokens,
      })
      toast.success("Modelo padrão de Cold Email salvo.")
    } catch {
      toast.error("Erro ao salvar configuração.")
    }
  }

  async function handleTest() {
    setTestResult(null)
    try {
      const res = await testModel.mutateAsync({
        provider: testProvider,
        model: testModelId,
        prompt: testPrompt,
      })
      setTestResult({ success: true, response: res.response })
    } catch (e: unknown) {
      setTestResult({ success: false, error: e instanceof Error ? e.message : "Erro desconhecido" })
    }
  }

  const TABS: { id: Tab; label: string; icon: React.ComponentType<{ size?: number }> }[] = [
    { id: "padrao", label: "Padrões", icon: SlidersHorizontal },
    { id: "modelos", label: "Modelos", icon: LayoutList },
    { id: "consumo", label: "Consumo", icon: BarChart3 },
    { id: "testar", label: "Testar", icon: FlaskConical },
  ]

  return (
    <div className="space-y-6">
      {/* ── Cabeçalho ──────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-(--text-primary)">Modelos LLM</h1>
          <p className="mt-1 text-sm text-(--text-secondary)">
            Configure provedores e modelos padrão para o sistema.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={async () => {
              try {
                await syncModels.mutateAsync()
                toast.success("Modelos sincronizados com sucesso.")
              } catch {
                toast.error("Erro ao sincronizar modelos.")
              }
            }}
            disabled={syncModels.isPending}
            className="flex items-center gap-1.5 rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-1.5 text-xs font-medium text-(--text-secondary) hover:bg-(--bg-overlay) disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={12} className={syncModels.isPending ? "animate-spin" : ""} />
            {syncModels.isPending ? "Sincronizando…" : "Sincronizar modelos"}
          </button>
          {providers.map((p) => (
            <span
              key={p.provider}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
                p.configured
                  ? "bg-(--success-subtle) text-(--success-subtle-fg)"
                  : "bg-(--bg-overlay) text-(--text-tertiary)",
              )}
            >
              {p.configured ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
              {p.provider === "openai"
                ? "OpenAI"
                : p.provider === "gemini"
                  ? "Gemini"
                  : "Anthropic"}
              {p.configured && <span className="opacity-60">· {p.models_count}</span>}
            </span>
          ))}
        </div>
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────────── */}
      <div className="border-b border-(--border-default)">
        <nav className="flex gap-1" aria-label="Seções LLM">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={cn(
                "flex items-center gap-1.5 border-b-2 px-3 pb-2.5 pt-1 text-sm font-medium transition-colors",
                activeTab === id
                  ? "border-(--accent) text-(--accent)"
                  : "border-transparent text-(--text-secondary) hover:text-(--text-primary)",
              )}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab: Padrões ───────────────────────────────────────────────── */}
      {activeTab === "padrao" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Sistema */}
          <div className="flex flex-col gap-4 rounded-lg border border-(--border-default) bg-(--bg-surface) p-5">
            <div>
              <h2 className="text-sm font-semibold text-(--text-primary)">Sistema</h2>
              <p className="mt-0.5 text-xs text-(--text-secondary)">
                Pré-selecionado ao criar novas cadências.
              </p>
            </div>
            <LLMConfigForm value={systemLLM} onChange={setSystemLLM} />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSaveSystem}
                disabled={updateIntegrations.isPending}
                className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {updateIntegrations.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Save size={14} />
                )}
                Salvar padrão
              </button>
            </div>
          </div>

          {/* Cold Email */}
          <div className="flex flex-col gap-4 rounded-lg border border-(--border-default) bg-(--bg-surface) p-5">
            <div>
              <h2 className="text-sm font-semibold text-(--text-primary)">Cold Email</h2>
              <p className="mt-0.5 text-xs text-(--text-secondary)">
                Usado ao criar campanhas de e-mail. Otimize para volume e custo.
              </p>
            </div>
            <LLMConfigForm value={coldEmailLLM} onChange={setColdEmailLLM} />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSaveColdEmail}
                disabled={updateIntegrations.isPending}
                className="flex items-center gap-1.5 rounded-md bg-(--accent) px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {updateIntegrations.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Save size={14} />
                )}
                Salvar padrão
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Modelos ───────────────────────────────────────────────── */}
      {activeTab === "modelos" && (
        <div className="space-y-4">
          {/* Filtro */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-(--text-secondary)">Filtrar:</span>
            <div className="flex gap-1 rounded-md border border-(--border-default) bg-(--bg-overlay) p-0.5">
              {(["all", "openai", "gemini", "anthropic"] as ModelFilter[]).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setModelFilter(f)}
                  className={cn(
                    "rounded px-2.5 py-1 text-xs font-medium transition-colors",
                    modelFilter === f
                      ? "bg-(--bg-surface) text-(--text-primary) shadow-sm"
                      : "text-(--text-secondary) hover:text-(--text-primary)",
                  )}
                >
                  {f === "all"
                    ? "Todos"
                    : f === "openai"
                      ? "OpenAI"
                      : f === "gemini"
                        ? "Gemini"
                        : "Anthropic"}
                  <span className="ml-1.5 tabular-nums opacity-50">
                    {f === "all" ? models.length : models.filter((m) => m.provider === f).length}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Tabela */}
          {loadingModels ? (
            <div className="flex items-center gap-2 text-sm text-(--text-secondary)">
              <Loader2 size={14} className="animate-spin" />
              Carregando modelos…
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-(--border-default)">
              <div className="max-h-105 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 border-b border-(--border-default) bg-(--bg-overlay)">
                    <tr>
                      {["Provider", "Modelo", "Contexto", "Input ($/MTok)", "Output ($/MTok)"].map(
                        (h) => (
                          <th
                            key={h}
                            className="px-4 py-2.5 text-left text-xs font-semibold text-(--text-tertiary)"
                          >
                            {h}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-(--border-default) bg-(--bg-surface)">
                    {filteredModels.map((m) => (
                      <tr key={`${m.provider}-${m.id}`} className="hover:bg-(--bg-overlay)">
                        <td className="px-4 py-2.5">
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-[10px] font-medium",
                              m.provider === "openai"
                                ? "bg-(--accent-subtle) text-(--accent-subtle-fg)"
                                : "bg-(--info-subtle) text-(--info-subtle-fg)",
                            )}
                          >
                            {m.provider === "openai" ? "OpenAI" : "Gemini"}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 font-mono text-xs text-(--text-secondary)">
                          {m.id}
                        </td>
                        <td className="px-4 py-2.5 text-(--text-secondary)">
                          {m.context_window ? `${(m.context_window / 1000).toFixed(0)}k` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-(--text-secondary)">
                          {m.input_cost_per_mtok !== undefined ? `$${m.input_cost_per_mtok}` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-(--text-secondary)">
                          {m.output_cost_per_mtok !== undefined
                            ? `$${m.output_cost_per_mtok}`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "consumo" && <LLMConsumptionPanel />}

      {/* ── Tab: Testar ────────────────────────────────────────────────── */}
      {activeTab === "testar" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Coluna esquerda — controles */}
          <div className="flex flex-col gap-4 rounded-lg border border-(--border-default) bg-(--bg-surface) p-5">
            <div>
              <h2 className="text-sm font-semibold text-(--text-primary)">Configuração do teste</h2>
              <p className="mt-0.5 text-xs text-(--text-secondary)">
                Selecione o provider e modelo, escreva um prompt e envie.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-(--text-secondary)">
                  Provider
                </label>
                <select
                  title="Provider"
                  value={testProvider}
                  onChange={(e) => {
                    setTestProvider(e.target.value)
                    setTestModelId("")
                  }}
                  className="w-full rounded-md border border-(--border-default) bg-(--bg-overlay) px-3 py-2 text-sm text-(--text-primary) focus:outline-none focus:ring-2 focus:ring-(--accent)"
                >
                  {providers
                    .filter((p) => p.configured)
                    .map((p) => (
                      <option key={p.provider} value={p.provider}>
                        {p.provider === "openai"
                          ? "OpenAI"
                          : p.provider === "gemini"
                            ? "Google Gemini"
                            : "Anthropic"}
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-(--text-secondary)">
                  Modelo
                </label>
                <select
                  title="Modelo"
                  value={testModelId}
                  onChange={(e) => setTestModelId(e.target.value)}
                  className="w-full rounded-md border border-(--border-default) bg-(--bg-overlay) px-3 py-2 text-sm text-(--text-primary) focus:outline-none focus:ring-2 focus:ring-(--accent)"
                >
                  <option value="">Selecione…</option>
                  {testableModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-1 flex-col">
              <label className="mb-1.5 block text-xs font-medium text-(--text-secondary)">
                Prompt
              </label>
              <textarea
                title="Prompt"
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                rows={8}
                placeholder="Digite o prompt de teste aqui…"
                className="w-full flex-1 resize-none rounded-md border border-(--border-default) bg-(--bg-overlay) px-3 py-2.5 text-sm text-(--text-primary) placeholder:text-(--text-tertiary) focus:outline-none focus:ring-2 focus:ring-(--accent)"
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs text-(--text-tertiary)">
                {testModelId ? (
                  <span className="font-mono">{testModelId}</span>
                ) : (
                  "Nenhum modelo selecionado"
                )}
              </span>
              <button
                type="button"
                onClick={handleTest}
                disabled={!testModelId || testModel.isPending}
                className="flex items-center gap-1.5 rounded-md bg-(--accent) px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {testModel.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Zap size={14} />
                )}
                {testModel.isPending ? "Testando…" : "Testar"}
              </button>
            </div>
          </div>

          {/* Coluna direita — resultado */}
          <div className="flex flex-col rounded-lg border border-(--border-default) bg-(--bg-surface) p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-(--text-primary)">Resposta</h2>
              {testResult && (
                <span
                  className={cn(
                    "flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
                    testResult.success
                      ? "bg-(--success-subtle) text-(--success-subtle-fg)"
                      : "bg-(--danger-subtle) text-(--danger-subtle-fg)",
                  )}
                >
                  {testResult.success ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
                  {testResult.success ? "Sucesso" : "Erro"}
                </span>
              )}
            </div>

            {testModel.isPending ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 py-12 text-(--text-tertiary)">
                <Loader2 size={24} className="animate-spin" />
                <span className="text-sm">Aguardando resposta do modelo…</span>
              </div>
            ) : testResult ? (
              <div
                className={cn(
                  "flex-1 rounded-md border p-4",
                  testResult.success
                    ? "border-(--border-default) bg-(--bg-overlay)"
                    : "border-(--danger-subtle) bg-(--danger-subtle)",
                )}
              >
                <p
                  className={cn(
                    "whitespace-pre-wrap text-sm leading-relaxed",
                    testResult.success
                      ? "text-(--text-primary)"
                      : "text-(--danger-subtle-fg) font-mono text-xs",
                  )}
                >
                  {testResult.success ? testResult.response : testResult.error}
                </p>
              </div>
            ) : (
              <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-md border border-dashed border-(--border-default) py-16 text-(--text-tertiary)">
                <Zap size={28} className="opacity-30" />
                <span className="text-sm">A resposta aparecerá aqui</span>
                <span className="text-xs opacity-60">Selecione um modelo e clique em Testar</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
