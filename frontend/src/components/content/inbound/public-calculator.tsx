"use client"

import Image from "next/image"
import { useMutation, useQuery } from "@tanstack/react-query"
import {
  ArrowRight,
  Calculator,
  CheckCircle2,
  Clock3,
  FileText,
  Landmark,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  type LucideIcon,
} from "lucide-react"
import { useState, type FormEvent } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { env } from "@/env"
import type {
  CalculatorCalculateInput,
  CalculatorCalculateResult,
  CalculatorCompanySegment,
  CalculatorCompanySize,
  CalculatorConfig,
  CalculatorConvertInput,
  CalculatorConvertResult,
  CalculatorProcessAreaSpan,
  CalculatorProcessType,
  CalculatorRole,
} from "@/lib/content-inbound/types"
import { formatBRL } from "@/lib/utils"

interface Props {
  leadMagnetId?: string | undefined
}

const ROLE_OPTIONS: Array<{ value: CalculatorRole; label: string }> = [
  { value: "ceo", label: "CEO" },
  { value: "cfo", label: "CFO" },
  { value: "gerente", label: "Gerente" },
  { value: "analista", label: "Analista" },
  { value: "operacional", label: "Operacional" },
]

const PROCESS_OPTIONS: Array<{ value: CalculatorProcessType; label: string }> = [
  { value: "financeiro", label: "Financeiro" },
  { value: "juridico", label: "Jurídico" },
  { value: "operacional", label: "Operacional" },
  { value: "atendimento", label: "Atendimento" },
  { value: "rh", label: "RH" },
]

const SEGMENT_OPTIONS: Array<{ value: CalculatorCompanySegment; label: string }> = [
  { value: "clinicas", label: "Clínicas" },
  { value: "industria", label: "Indústria" },
  { value: "advocacia", label: "Advocacia" },
  { value: "contabilidade", label: "Contabilidade" },
  { value: "varejo", label: "Varejo" },
  { value: "servicos", label: "Serviços" },
]

const COMPANY_SIZE_OPTIONS: Array<{ value: CalculatorCompanySize; label: string }> = [
  { value: "pequena", label: "Pequena" },
  { value: "media", label: "Média" },
  { value: "grande", label: "Grande" },
]

const PROCESS_AREA_OPTIONS: Array<{ value: CalculatorProcessAreaSpan; label: string }> = [
  { value: "1", label: "1 área" },
  { value: "2-3", label: "2 a 3 áreas" },
  { value: "4+", label: "4 ou mais áreas" },
]

const SEGMENT_INSIGHTS: Record<CalculatorCompanySegment, string> = {
  clinicas:
    "Em clínicas, gargalos repetitivos costumam aparecer entre atendimento, agenda, faturamento e financeiro.",
  industria:
    "Na indústria, o ganho tende a aparecer quando o processo reduz repasses manuais entre operação, qualidade e administrativo.",
  advocacia:
    "Na advocacia, fluxos com alto volume de prazos, documentos e validações costumam acumular custo oculto com rapidez.",
  contabilidade:
    "Na contabilidade, rotinas com conferência, cobrança e fechamento mensal costumam concentrar retrabalho e urgência.",
  varejo:
    "No varejo, o maior impacto costuma vir de processos que envolvem equipe comercial, backoffice e atendimento ao mesmo tempo.",
  servicos:
    "Em empresas de serviços, os melhores ganhos aparecem quando o processo consome horas recorrentes de coordenação e execução.",
}

const SEGMENT_FOLLOW_UP: Record<CalculatorCompanySegment, string> = {
  clinicas:
    "Para clínicas, o próximo melhor passo costuma ser detalhar os pontos de repasse entre agenda, atendimento, faturamento e financeiro.",
  industria:
    "Para indústrias, o próximo melhor passo costuma ser atacar o repasse manual entre operação, qualidade e administrativo.",
  advocacia:
    "Para escritórios e operações jurídicas, o próximo melhor passo costuma ser organizar os fluxos com mais prazos, documentos e validações.",
  contabilidade:
    "Para contabilidade, o próximo melhor passo costuma ser priorizar o fluxo que mais pressiona conferência, cobrança e fechamento.",
  varejo:
    "Para varejo, o próximo melhor passo costuma ser alinhar o processo onde comercial, atendimento e backoffice mais se cruzam.",
  servicos:
    "Para empresas de serviços, o próximo melhor passo costuma ser cortar repasses nas etapas recorrentes de coordenação e execução.",
}

const CALCULATOR_PROMISES: Array<{
  icon: LucideIcon
  title: string
  description: string
}> = [
  {
    icon: Sparkles,
    title: "Diagnóstico em poucos minutos",
    description: "Preencha o cenário atual e veja uma leitura executiva imediata.",
  },
  {
    icon: ShieldCheck,
    title: "Sem cadastro para estimar",
    description: "Seus dados de contato só entram quando você decide receber o diagnóstico.",
  },
  {
    icon: FileText,
    title: "PDF pronto para compartilhar",
    description:
      "Ao final, você pode receber o diagnóstico por e-mail com custo atual, payback e faixa de investimento.",
  },
]

const METHODOLOGY_ITEMS = [
  "Custo da operação atual com base no tempo das pessoas envolvidas.",
  "Peso do retrabalho sobre a rotina manual que existe hoje.",
  "Faixa de investimento esperada conforme o tipo de processo.",
  "Prazo estimado de retorno ao comparar custo anual versus automação.",
]

const NEXT_STEP_ITEMS = [
  "Priorizar o processo certo antes de investir em automação.",
  "Comparar o cenário atual com uma operação automatizada com mais clareza.",
  "Abrir a conversa comercial já com números organizados e contexto do caso.",
]

const COMPOSTO_WEB_ATTRIBUTION_URL =
  "https://compostoweb.com.br/?utm_source=prospector&utm_medium=calculator&utm_campaign=calculadora_roi"

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : "Falha ao processar calculadora",
    )
  }
  return payload as T
}

export default function PublicCalculator({ leadMagnetId }: Props) {
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [result, setResult] = useState<CalculatorCalculateResult | null>(null)
  const [submissionResult, setSubmissionResult] = useState<CalculatorConvertResult | null>(null)
  const [calculationForm, setCalculationForm] = useState<CalculatorCalculateInput>({
    lead_magnet_id: leadMagnetId ?? null,
    pessoas: 3,
    horas_semana: 12,
    custo_hora: null,
    cargo: "gerente",
    retrabalho_pct: 15,
    tipo_processo: "operacional",
    company_segment: "servicos",
    company_size: "media",
    process_area_span: "2-3",
    session_id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`,
  })
  const [captureForm, setCaptureForm] = useState<Omit<CalculatorConvertInput, "result_id">>({
    name: "",
    email: "",
    company: "",
    role: "",
    phone: "",
    create_prospect: true,
  })
  const configQuery = useQuery({
    queryKey: ["content", "calculator", "config"],
    queryFn: async () => {
      const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/api/content/calculator/config`)
      return parseResponse<CalculatorConfig>(response)
    },
  })

  const calculateMutation = useMutation({
    mutationFn: async (body: CalculatorCalculateInput) => {
      const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/api/content/calculator/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      return parseResponse<CalculatorCalculateResult>(response)
    },
    onSuccess: (payload) => {
      setError(null)
      setSuccessMessage(null)
      setSubmissionResult(null)
      setResult(payload)
    },
    onError: (mutationError) => {
      setSubmissionResult(null)
      setError(mutationError instanceof Error ? mutationError.message : "Falha ao calcular")
    },
  })

  const convertMutation = useMutation({
    mutationFn: async (body: CalculatorConvertInput) => {
      const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/api/content/calculator/convert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      return parseResponse<CalculatorConvertResult>(response)
    },
    onSuccess: (payload) => {
      setError(null)
      setSubmissionResult(payload)
      setSuccessMessage(
        payload.diagnosis_email_sent
          ? `O PDF do diagnóstico foi enviado para ${captureForm.email.trim().toLowerCase()}.`
          : "Recebemos sua simulação, mas o PDF não pôde ser disparado automaticamente agora.",
      )
    },
    onError: (mutationError) => {
      setSubmissionResult(null)
      setError(
        mutationError instanceof Error ? mutationError.message : "Falha ao enviar diagnóstico",
      )
    },
  })

  function handleCalculateSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSuccessMessage(null)
    setSubmissionResult(null)
    void calculateMutation.mutateAsync(calculationForm)
  }

  function handleConvertSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!result) {
      return
    }
    setError(null)
    void convertMutation.mutateAsync({
      result_id: result.result_id,
      ...captureForm,
    })
  }

  function formatWhatsapp(value: string) {
    const digits = value.replace(/\D/g, "").slice(0, 11)

    if (digits.length === 0) {
      return ""
    }
    if (digits.length < 3) {
      return `(${digits}`
    }
    if (digits.length < 7) {
      return `(${digits.slice(0, 2)}) ${digits.slice(2)}`
    }
    if (digits.length < 11) {
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`
    }
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
  }

  const numberFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 })
  const suggestedHourlyCost = configQuery.data?.role_hourly_costs[calculationForm.cargo]
  const selectedProcessLabel =
    PROCESS_OPTIONS.find((option) => option.value === calculationForm.tipo_processo)?.label ??
    "Processo"
  const selectedSegmentLabel =
    SEGMENT_OPTIONS.find((option) => option.value === calculationForm.company_segment)?.label ??
    "Serviços"
  const selectedCompanySizeLabel =
    COMPANY_SIZE_OPTIONS.find((option) => option.value === calculationForm.company_size)?.label ??
    "Média"
  const selectedAreaLabel =
    PROCESS_AREA_OPTIONS.find((option) => option.value === calculationForm.process_area_span)
      ?.label ?? "2 a 3 áreas"
  const methodologyItems = [
    ...METHODOLOGY_ITEMS,
    `Contexto informado: empresa de ${selectedSegmentLabel.toLowerCase()}, porte ${selectedCompanySizeLabel.toLowerCase()} e processo envolvendo ${selectedAreaLabel.toLowerCase()}.`,
  ]
  const nextStepItems = [
    ...NEXT_STEP_ITEMS,
    `No seu cenário, vale começar pelo processo com maior impacto entre ${selectedAreaLabel.toLowerCase()} para validar prioridade e retorno.`,
  ]
  const resultDrivers = result
    ? [
        `${calculationForm.pessoas} pessoa(s) dedicam ${numberFormatter.format(calculationForm.horas_semana)} hora(s) por semana ao processo ${selectedProcessLabel.toLowerCase()}.`,
        `O cálculo considera custo-hora de ${formatBRL(result.custo_hora_sugerido)} e ${numberFormatter.format(calculationForm.retrabalho_pct)}% de retrabalho sobre a operação atual.`,
        `Nesse cenário, o custo anual estimado chega a ${formatBRL(result.custo_anual)} e a faixa de investimento analisada vai de ${formatBRL(result.investimento_estimado_min)} a ${formatBRL(result.investimento_estimado_max)}.`,
        `Com esse recorte, o retorno estimado é de ${numberFormatter.format(result.roi_estimado)}% e o payback previsto fica em ${numberFormatter.format(result.payback_meses)} meses.`,
        `${SEGMENT_INSIGHTS[calculationForm.company_segment ?? "servicos"]} Neste diagnóstico, o caso foi lido como uma operação de porte ${selectedCompanySizeLabel.toLowerCase()}, com ${selectedAreaLabel.toLowerCase()} participando do fluxo.`,
      ]
    : []
  const successHighlights = submissionResult
    ? [
        submissionResult.diagnosis_email_sent
          ? `O PDF com o resumo financeiro foi enviado para ${captureForm.email.trim().toLowerCase()}.`
          : "Sua simulação foi registrada, mas o envio automático do PDF não foi concluído nesta tentativa.",
        submissionResult.internal_notification_sent
          ? "Nossa equipe também recebeu o mesmo contexto da simulação para continuar a conversa com base nesses números."
          : "Mesmo sem aviso interno automático, a sua simulação ficou registrada para continuidade manual do atendimento.",
        `${SEGMENT_FOLLOW_UP[calculationForm.company_segment ?? "servicos"]} No seu caso, o recorte foi salvo como ${selectedSegmentLabel.toLowerCase()}, porte ${selectedCompanySizeLabel.toLowerCase()}, com ${selectedAreaLabel.toLowerCase()} no fluxo.`,
      ]
    : []

  return (
    <div className="min-h-screen bg-(--bg-page) bg-[radial-gradient(circle_at_top_right,color-mix(in_srgb,var(--accent)_14%,transparent),transparent_38%),radial-gradient(circle_at_top_left,color-mix(in_srgb,var(--info)_12%,transparent),transparent_34%),linear-gradient(180deg,var(--bg-page)_0%,var(--bg-surface)_100%)] text-(--text-primary)">
      <div className="mx-auto flex w-full max-w-380 flex-col gap-8 px-6 py-10 lg:px-8 lg:py-14 2xl:max-w-420 2xl:px-10">
        <header className="flex flex-col gap-5">
          <Image
            src={`${env.NEXT_PUBLIC_API_URL}/assets/branding/compostoweb-logo-primary-transparent.webp`}
            alt="Composto Web"
            width={192}
            height={44}
            unoptimized
            className="h-auto w-48 object-contain"
          />
          <Badge className="w-fit px-3 py-1 text-[11px] uppercase tracking-[0.18em]">
            Calculadora de ROI
          </Badge>

          <div className="grid gap-3 lg:grid-cols-3 xl:gap-4">
            <div className="col-span-full flex flex-col gap-3">
              <h1 className="text-4xl font-semibold leading-tight tracking-tight lg:text-5xl">
                Descubra quanto o seu processo manual custa por ano
              </h1>
              <p className="text-base leading-7 text-(--text-secondary)">
                Preencha os dados do processo atual para estimar custo anual, faixa de investimento,
                payback e potencial de retorno antes de priorizar a automação.
              </p>
            </div>
            {CALCULATOR_PROMISES.map(({ icon: Icon, title, description }) => (
              <PromiseCard key={title} icon={Icon} title={title} description={description} />
            ))}
          </div>
        </header>

        <div className="grid gap-8 lg:grid-cols-[0.92fr_1.08fr] lg:items-start xl:gap-10 2xl:grid-cols-[0.9fr_1.1fr] 2xl:gap-12">
          <div className="grid gap-5">
            <section className="rounded-[28px] border border-(--border-default) bg-(--bg-surface) p-6 shadow-(--shadow-lg)">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
                  <Calculator className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-medium text-(--text-primary)">Simulação guiada</p>
                  <p className="text-sm text-(--text-secondary)">
                    Diagnóstico rápido para priorizar automação
                  </p>
                </div>
              </div>

              <form className="mt-6 space-y-4" onSubmit={handleCalculateSubmit}>
                <div className="grid gap-2">
                  <Label htmlFor="cargo">Cargo predominante no processo</Label>
                  <Select
                    value={calculationForm.cargo}
                    onValueChange={(value) =>
                      setCalculationForm((current) => ({
                        ...current,
                        cargo: value as CalculatorRole,
                      }))
                    }
                  >
                    <SelectTrigger id="cargo">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLE_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {suggestedHourlyCost !== undefined && (
                    <p className="text-xs text-(--text-tertiary)">
                      Custo/h sugerido para este perfil: {formatBRL(suggestedHourlyCost)}
                    </p>
                  )}
                  {configQuery.isError && (
                    <p className="text-xs text-(--text-tertiary)">
                      Não foi possível carregar a referência de custo. Você ainda pode usar um valor
                      customizado.
                    </p>
                  )}
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="grid gap-2">
                    <Label htmlFor="pessoas">Pessoas envolvidas</Label>
                    <Input
                      id="pessoas"
                      type="number"
                      min={1}
                      max={1000}
                      value={calculationForm.pessoas}
                      onChange={(event) =>
                        setCalculationForm((current) => ({
                          ...current,
                          pessoas: Number(event.target.value || 0),
                        }))
                      }
                      required
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="horas_semana">Horas por semana</Label>
                    <Input
                      id="horas_semana"
                      type="number"
                      min={1}
                      max={168}
                      step="0.5"
                      value={calculationForm.horas_semana}
                      onChange={(event) =>
                        setCalculationForm((current) => ({
                          ...current,
                          horas_semana: Number(event.target.value || 0),
                        }))
                      }
                      required
                    />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="grid gap-2">
                    <Label htmlFor="retrabalho_pct">Retrabalho (%)</Label>
                    <Input
                      id="retrabalho_pct"
                      type="number"
                      min={0}
                      max={50}
                      step="1"
                      value={calculationForm.retrabalho_pct}
                      onChange={(event) =>
                        setCalculationForm((current) => ({
                          ...current,
                          retrabalho_pct: Number(event.target.value || 0),
                        }))
                      }
                      required
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="custo_hora">Custo/h customizado (opcional)</Label>
                    <Input
                      id="custo_hora"
                      type="number"
                      min={1}
                      step="0.01"
                      value={calculationForm.custo_hora ?? ""}
                      onChange={(event) =>
                        setCalculationForm((current) => ({
                          ...current,
                          custo_hora: event.target.value ? Number(event.target.value) : null,
                        }))
                      }
                      placeholder="Deixe em branco para usar o sugerido"
                    />
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="tipo_processo">Tipo de processo</Label>
                  <Select
                    value={calculationForm.tipo_processo}
                    onValueChange={(value) =>
                      setCalculationForm((current) => ({
                        ...current,
                        tipo_processo: value as CalculatorProcessType,
                      }))
                    }
                  >
                    <SelectTrigger id="tipo_processo">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PROCESS_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
                  <p className="text-sm font-medium text-(--text-primary)">Contexto da operação</p>
                  <p className="mt-1 text-xs leading-5 text-(--text-secondary)">
                    Esses dados ajudam a personalizar a leitura do diagnóstico para o seu tipo de
                    empresa, sem mudar ainda a lógica central do cálculo.
                  </p>

                  <div className="mt-4 grid gap-4 lg:grid-cols-3">
                    <div className="grid gap-2">
                      <Label htmlFor="segmento_empresa">Segmento da empresa</Label>
                      <Select
                        value={calculationForm.company_segment ?? "servicos"}
                        onValueChange={(value) =>
                          setCalculationForm((current) => ({
                            ...current,
                            company_segment: value as CalculatorCompanySegment,
                          }))
                        }
                      >
                        <SelectTrigger id="segmento_empresa">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {SEGMENT_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="porte_empresa">Porte da empresa</Label>
                      <Select
                        value={calculationForm.company_size ?? "media"}
                        onValueChange={(value) =>
                          setCalculationForm((current) => ({
                            ...current,
                            company_size: value as CalculatorCompanySize,
                          }))
                        }
                      >
                        <SelectTrigger id="porte_empresa">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {COMPANY_SIZE_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid gap-2">
                      <Label htmlFor="areas_processo">Áreas no processo</Label>
                      <Select
                        value={calculationForm.process_area_span ?? "2-3"}
                        onValueChange={(value) =>
                          setCalculationForm((current) => ({
                            ...current,
                            process_area_span: value as CalculatorProcessAreaSpan,
                          }))
                        }
                      >
                        <SelectTrigger id="areas_processo">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {PROCESS_AREA_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full justify-between"
                  disabled={calculateMutation.isPending}
                >
                  {calculateMutation.isPending ? "Calculando..." : "Calcular ROI"}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </form>
            </section>

            <div className="grid gap-5 xl:grid-cols-2">
              <InfoListCard
                eyebrow="O que entra no cálculo"
                title="Premissas que moldam a estimativa"
                items={methodologyItems}
                tone="neutral"
              />
              <InfoListCard
                eyebrow="Depois da simulação"
                title="Como usar esse diagnóstico"
                items={nextStepItems}
                tone="accent"
                footer="Você já sai com uma visão inicial para priorizar o caso certo e levar a conversa adiante com mais contexto."
              />
            </div>
          </div>

          <aside className="flex flex-col gap-5 lg:sticky lg:top-8">
            <section className="overflow-hidden rounded-[28px] border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-lg)">
              <div className="border-b border-(--border-subtle) bg-[linear-gradient(135deg,color-mix(in_srgb,var(--accent)_10%,transparent),transparent_65%),linear-gradient(180deg,var(--bg-surface),var(--bg-overlay))] px-6 py-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
                      Resultado
                    </p>
                    <h2 className="mt-2 text-2xl font-semibold">
                      Visão financeira do processo atual
                    </h2>
                  </div>
                  {result && <Badge variant="success">Simulação concluída</Badge>}
                </div>
                <p className="mt-4 max-w-2xl text-sm leading-6 text-(--text-secondary)">
                  Veja o impacto anual do processo manual, compare com a faixa de investimento e
                  entenda em quanto tempo a automação tende a se pagar.
                </p>
              </div>

              <div className="p-6">
                {!result ? (
                  <div className="space-y-5">
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <PreviewMetricCard label="Custo anual" />
                      <PreviewMetricCard label="ROI estimado" />
                      <PreviewMetricCard label="Payback" />
                      <PreviewMetricCard label="Investimento" />
                    </div>

                    <div className="rounded-2xl border border-dashed border-(--border-default) bg-(--bg-overlay) p-6 text-sm leading-6 text-(--text-secondary)">
                      Preencha o formulário para estimar custo anual, faixa de investimento e
                      payback da automação.
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <MetricCard
                        icon={Landmark}
                        label="Custo anual"
                        value={formatBRL(result.custo_anual)}
                      />
                      <MetricCard
                        icon={TrendingUp}
                        label="ROI estimado"
                        value={`${result.roi_estimado.toFixed(1)}%`}
                      />
                      <MetricCard
                        icon={Clock3}
                        label="Payback"
                        value={`${result.payback_meses.toFixed(1)} meses`}
                      />
                      <MetricCard
                        icon={CheckCircle2}
                        label="Investimento base"
                        value={`${formatBRL(result.investimento_estimado_min)} a ${formatBRL(result.investimento_estimado_max)}`}
                      />
                    </div>

                    <div className="rounded-2xl bg-(--accent-subtle) p-5 text-(--accent-subtle-fg)">
                      <p className="text-sm font-medium">Leitura executiva</p>
                      <p className="mt-2 text-sm leading-6">{result.mensagem_resultado}</p>
                    </div>

                    <div className="rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-5">
                      <p className="text-sm font-medium text-(--text-primary)">
                        Como chegamos nisso
                      </p>
                      <div className="mt-3 grid gap-3">
                        {resultDrivers.map((item) => (
                          <div
                            key={item}
                            className="flex gap-3 rounded-2xl bg-(--bg-surface) px-4 py-3"
                          >
                            <span className="mt-1 h-2 w-2 rounded-full bg-(--accent)" />
                            <p className="text-sm leading-6 text-(--text-secondary)">{item}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <form
                      className="grid gap-3 rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-5"
                      onSubmit={handleConvertSubmit}
                    >
                      <div>
                        <p className="text-sm font-medium text-(--text-primary)">
                          Receber PDF do diagnóstico e próximo passo
                        </p>
                        <p className="mt-1 text-sm leading-6 text-(--text-secondary)">
                          Envie seus dados para receber o PDF desta simulação por e-mail, registrar
                          o diagnóstico e abrir uma conversa comercial com contexto completo para
                          uma empresa de {selectedSegmentLabel.toLowerCase()}.
                        </p>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <Input
                          value={captureForm.name}
                          onChange={(event) =>
                            setCaptureForm((current) => ({ ...current, name: event.target.value }))
                          }
                          placeholder="Seu nome"
                          required
                        />
                        <Input
                          type="email"
                          value={captureForm.email}
                          onChange={(event) =>
                            setCaptureForm((current) => ({ ...current, email: event.target.value }))
                          }
                          placeholder="Seu e-mail"
                          required
                        />
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <Input
                          value={captureForm.company || ""}
                          onChange={(event) =>
                            setCaptureForm((current) => ({
                              ...current,
                              company: event.target.value,
                            }))
                          }
                          placeholder="Empresa"
                          required
                        />
                        <Input
                          value={captureForm.role || ""}
                          onChange={(event) =>
                            setCaptureForm((current) => ({ ...current, role: event.target.value }))
                          }
                          placeholder="Cargo"
                          required
                        />
                      </div>
                      <Input
                        value={captureForm.phone || ""}
                        onChange={(event) =>
                          setCaptureForm((current) => ({
                            ...current,
                            phone: formatWhatsapp(event.target.value),
                          }))
                        }
                        placeholder="Seu WhatsApp > (ddd) + número"
                        inputMode="numeric"
                        maxLength={15}
                        required
                      />

                      <Button
                        type="submit"
                        className="justify-between"
                        disabled={convertMutation.isPending}
                      >
                        {convertMutation.isPending
                          ? "Enviando PDF..."
                          : "Receber PDF do diagnóstico"}
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </form>
                  </div>
                )}

                {error && (
                  <div className="mt-4 rounded-2xl border border-(--danger)/30 bg-(--danger-subtle) px-4 py-3 text-sm text-(--danger-subtle-fg)">
                    {error}
                  </div>
                )}

                {successMessage && submissionResult && (
                  <div className="mt-4 rounded-2xl border border-(--success)/30 bg-(--success-subtle) p-4 text-(--success-subtle-fg)">
                    <p className="text-sm font-medium">Diagnóstico encaminhado</p>
                    <p className="mt-1 text-sm leading-6">{successMessage}</p>
                    <div className="mt-4 grid gap-3">
                      {successHighlights.map((item) => (
                        <div
                          key={item}
                          className="flex gap-3 rounded-2xl bg-(--bg-surface)/70 px-4 py-3"
                        >
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                          <p className="text-sm leading-6 text-inherit">{item}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          </aside>
        </div>

        <footer className="pt-2 text-center text-sm text-(--text-tertiary)">
          Desenvolvido por{" "}
          <a
            href={COMPOSTO_WEB_ATTRIBUTION_URL}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-(--accent) underline decoration-(--accent)/40 underline-offset-4 transition-opacity hover:opacity-80"
          >
            Composto Web
          </a>
        </footer>
      </div>
    </div>
  )
}

interface PromiseCardProps {
  icon: LucideIcon
  title: string
  description: string
}

function PromiseCard({ icon: Icon, title, description }: PromiseCardProps) {
  return (
    <div className="rounded-2xl border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-medium text-(--text-primary)">{title}</p>
          <p className="mt-1 text-sm leading-6 text-(--text-secondary)">{description}</p>
        </div>
      </div>
    </div>
  )
}

interface InfoListCardProps {
  eyebrow: string
  title: string
  items: string[]
  tone: "neutral" | "accent"
  footer?: string
}

function InfoListCard({ eyebrow, title, items, tone, footer }: InfoListCardProps) {
  const itemClassName =
    tone === "accent"
      ? "flex gap-3 rounded-2xl bg-(--accent-subtle) px-4 py-3 text-(--accent-subtle-fg)"
      : "flex gap-3 rounded-2xl bg-(--bg-overlay) px-4 py-3"

  return (
    <section className="rounded-3xl border border-(--border-default) bg-(--bg-surface) p-5 shadow-(--shadow-sm)">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
        {eyebrow}
      </p>
      <h3 className="mt-3 text-lg font-semibold text-(--text-primary)">{title}</h3>
      <div className="mt-4 grid gap-3">
        {items.map((item) => (
          <div key={item} className={itemClassName}>
            {tone === "accent" ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            ) : (
              <span className="mt-1 h-2 w-2 rounded-full bg-(--accent)" />
            )}
            <p className="text-sm leading-6 text-inherit">{item}</p>
          </div>
        ))}
      </div>
      {footer && <p className="mt-4 text-sm leading-6 text-(--text-secondary)">{footer}</p>}
    </section>
  )
}

interface PreviewMetricCardProps {
  label: string
}

function PreviewMetricCard({ label }: PreviewMetricCardProps) {
  return (
    <div className="rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">{label}</p>
      <div className="mt-4 h-6 w-24 rounded-full bg-(--bg-sunken)" />
      <div className="mt-3 h-3 w-20 rounded-full bg-(--bg-sunken)" />
    </div>
  )
}

interface MetricCardProps {
  icon: LucideIcon
  label: string
  value: string
}

function MetricCard({ icon: Icon, label, value }: MetricCardProps) {
  return (
    <div className="rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
      <div className="flex items-center gap-2 text-(--text-tertiary)">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-3 text-lg font-semibold leading-tight text-(--text-primary)">{value}</p>
    </div>
  )
}
