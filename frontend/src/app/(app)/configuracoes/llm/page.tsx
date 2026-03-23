"use client"

import { useLLMModels, useLLMProviders, useTestModel } from "@/lib/api/hooks/use-llm-models"
import { useState } from "react"
import { CheckCircle2, XCircle, Loader2, Zap, Info } from "lucide-react"
import { cn } from "@/lib/utils"

export default function LLMPage() {
  const { data: providersData } = useLLMProviders()
  const { data: modelsData, isLoading: loadingModels } = useLLMModels()
  const testModel = useTestModel()
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
  const filteredModels = models.filter((m) => m.provider === testProvider)

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
      const msg = e instanceof Error ? e.message : "Erro desconhecido"
      setTestResult({ success: false, error: msg })
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Modelos LLM</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Provedores configurados e modelos disponíveis para composição de mensagens.
        </p>
      </div>

      {/* Provedores */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Provedores</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {providers.length === 0 ? (
            <p className="text-sm text-[var(--text-secondary)]">Nenhum provedor configurado.</p>
          ) : (
            providers.map((p) => (
              <ProviderCard
                key={p.provider}
                name={p.provider === "openai" ? "OpenAI" : "Google Gemini"}
                configured={p.configured}
                modelCount={p.models_count}
              />
            ))
          )}
        </div>
      </section>

      {/* Modelos */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
          Modelos disponíveis
        </h2>
        {loadingModels ? (
          <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <Loader2 size={14} className="animate-spin" />
            Carregando modelos…
          </div>
        ) : (
          <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--border-default)]">
            <table className="w-full text-sm">
              <thead className="border-b border-[var(--border-default)] bg-[var(--bg-overlay)]">
                <tr>
                  {["Provider", "Modelo", "Contexto", "Input ($/MTok)", "Output ($/MTok)"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-2.5 text-left text-xs font-semibold text-[var(--text-tertiary)]"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-default)] bg-[var(--bg-surface)]">
                {models.map((m) => (
                  <tr key={`${m.provider}-${m.id}`} className="hover:bg-[var(--bg-overlay)]">
                    <td className="px-4 py-2.5 font-medium text-[var(--text-primary)] capitalize">
                      {m.provider}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-[var(--text-secondary)]">
                      {m.id}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--text-secondary)]">
                      {m.context_window ? `${(m.context_window / 1000).toFixed(0)}k` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--text-secondary)]">
                      {m.input_cost_per_mtok !== undefined ? `$${m.input_cost_per_mtok}` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--text-secondary)]">
                      {m.output_cost_per_mtok !== undefined ? `$${m.output_cost_per_mtok}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Teste */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Testar modelo</h2>
        <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Provider
              </label>
              <select
                value={testProvider}
                onChange={(e) => {
                  setTestProvider(e.target.value)
                  setTestModelId("")
                }}
                className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-overlay)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              >
                {providers
                  .filter((p) => p.configured)
                  .map((p) => (
                    <option key={p.provider} value={p.provider}>
                      {p.provider === "openai" ? "OpenAI" : "Google Gemini"}
                    </option>
                  ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                Modelo
              </label>
              <select
                value={testModelId}
                onChange={(e) => setTestModelId(e.target.value)}
                className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-overlay)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
              >
                <option value="">Selecione…</option>
                {filteredModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Prompt
            </label>
            <textarea
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              rows={2}
              className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-overlay)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
          <button
            type="button"
            onClick={handleTest}
            disabled={!testModelId || testModel.isPending}
            className="flex items-center gap-1.5 rounded-[var(--radius-md)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-[var(--accent-fg)] hover:opacity-90 disabled:opacity-50"
          >
            {testModel.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Zap size={14} />
            )}
            {testModel.isPending ? "Testando…" : "Testar"}
          </button>

          {testResult && (
            <div
              className={cn(
                "rounded-[var(--radius-md)] border p-4 text-sm",
                testResult.success
                  ? "border-[var(--success-subtle)] bg-[var(--success-subtle)] text-[var(--success-subtle-fg)]"
                  : "border-[var(--danger-subtle)] bg-[var(--danger-subtle)] text-[var(--danger-subtle-fg)]",
              )}
            >
              <div className="flex items-center gap-2 mb-2 font-medium">
                {testResult.success ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                {testResult.success ? "Sucesso" : "Erro"}
              </div>
              <p className="font-mono text-xs whitespace-pre-wrap">
                {testResult.success ? testResult.response : testResult.error}
              </p>
            </div>
          )}
        </div>
      </section>

      <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-overlay)] px-4 py-3 text-xs text-[var(--text-secondary)]">
        <Info size={13} className="mt-0.5 shrink-0" />
        <span>
          Para adicionar ou trocar chaves de API configure as variáveis de ambiente{" "}
          <code className="font-mono">OPENAI_API_KEY</code> e{" "}
          <code className="font-mono">GEMINI_API_KEY</code> no servidor.
        </span>
      </div>
    </div>
  )
}

function ProviderCard({
  name,
  configured,
  modelCount,
}: {
  name: string
  configured: boolean
  modelCount: number
}) {
  return (
    <div className="flex items-center justify-between rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-3">
      <div>
        <span className="font-medium text-[var(--text-primary)]">{name}</span>
        {configured && (
          <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">{modelCount} modelos</p>
        )}
      </div>
      {configured ? (
        <span className="flex items-center gap-1 rounded-full bg-[var(--success-subtle)] px-2.5 py-1 text-xs font-medium text-[var(--success-subtle-fg)]">
          <CheckCircle2 size={11} />
          Configurado
        </span>
      ) : (
        <span className="flex items-center gap-1 rounded-full bg-[var(--bg-overlay)] px-2.5 py-1 text-xs text-[var(--text-tertiary)]">
          <XCircle size={11} />
          Não configurado
        </span>
      )}
    </div>
  )
}
