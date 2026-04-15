"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import {
  Activity,
  ArrowRight,
  BarChart3,
  Copy,
  ExternalLink,
  FileDown,
  Gauge,
  Mail,
  Plus,
  Save,
  Settings,
  Sparkles,
  Upload,
  UserPlus,
  Wand2,
  Wifi,
  Zap,
} from "lucide-react"
import { toast } from "sonner"
import { env } from "@/env"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import {
  useContentLeadMagnets,
  useConvertLeadMagnetLead,
  useCreateContentLeadMagnet,
  useCreateExampleLeadMagnet,
  useLandingPage,
  useLeadMagnetLeads,
  useLeadMagnetMetrics,
  useTestSendPulseConnection,
  useTestSendPulseWebhook,
  useUpdateContentLeadMagnet,
  useUpdateLeadMagnetStatus,
  useUploadLeadMagnetPdf,
  useUpsertLandingPage,
  type SendPulseConnectionResult,
  type TestWebhookInput,
  type TestWebhookResult,
} from "@/lib/api/hooks/use-content-inbound"
import type {
  ContentLandingPageUpsertInput,
  ContentLeadMagnetCreateInput,
  ContentLeadMagnetUpdateInput,
  LeadMagnetStatus,
  LeadMagnetType,
} from "@/lib/content-inbound/types"
import { cn, formatRelativeTime, slugify } from "@/lib/utils"

const TYPE_OPTIONS: Array<{ value: LeadMagnetType; label: string }> = [
  { value: "pdf", label: "PDF" },
  { value: "calculator", label: "Calculadora" },
  { value: "email_sequence", label: "Sequencia de e-mail" },
  { value: "link", label: "Link externo" },
]

const STATUS_OPTIONS: Array<{ value: LeadMagnetStatus; label: string }> = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Ativo" },
  { value: "paused", label: "Pausado" },
  { value: "archived", label: "Arquivado" },
]

const EVENT_TYPE_OPTIONS: Array<{ value: TestWebhookInput["event_type"]; label: string }> = [
  { value: "subscribe", label: "subscribe" },
  { value: "open", label: "open" },
  { value: "click", label: "click" },
  { value: "unsubscribe", label: "unsubscribe" },
  { value: "sequence_completed", label: "sequence_completed" },
]

export default function InboundHubPage() {
  const leadMagnetsQuery = useContentLeadMagnets()
  const createLeadMagnet = useCreateContentLeadMagnet()
  const createExampleLM = useCreateExampleLeadMagnet()
  const updateLeadMagnet = useUpdateContentLeadMagnet()
  const updateLeadMagnetStatus = useUpdateLeadMagnetStatus()
  const upsertLandingPage = useUpsertLandingPage()
  const convertLead = useConvertLeadMagnetLead()
  const uploadPdf = useUploadLeadMagnetPdf()
  const testConnection = useTestSendPulseConnection()
  const testWebhook = useTestSendPulseWebhook()
  const pdfInputRef = useRef<HTMLInputElement>(null)
  const [selectedLeadMagnetId, setSelectedLeadMagnetId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("metricas")
  const [connectionResult, setConnectionResult] = useState<SendPulseConnectionResult | null>(null)
  const [webhookTestResult, setWebhookTestResult] = useState<TestWebhookResult | null>(null)
  const [webhookTestForm, setWebhookTestForm] = useState<TestWebhookInput>({
    event_type: "open",
    email: "",
    list_id: "",
  })
  const [leadMagnetForm, setLeadMagnetForm] = useState<ContentLeadMagnetUpdateInput>({})
  const [landingPageForm, setLandingPageForm] = useState<ContentLandingPageUpsertInput>({
    slug: "",
    title: "",
    subtitle: "",
    hero_image_url: "",
    benefits: [],
    social_proof_count: 0,
    author_bio: "",
    author_photo_url: "",
    meta_title: "",
    meta_description: "",
    published: false,
  })

  const leadMagnets = useMemo(() => leadMagnetsQuery.data ?? [], [leadMagnetsQuery.data])
  const selectedLeadMagnet = leadMagnets.find((item) => item.id === selectedLeadMagnetId) ?? null
  const landingPageQuery = useLandingPage(selectedLeadMagnetId)
  const metricsQuery = useLeadMagnetMetrics(selectedLeadMagnetId)
  const leadsQuery = useLeadMagnetLeads(selectedLeadMagnetId)

  useEffect(() => {
    if (leadMagnets.length === 0) {
      setSelectedLeadMagnetId(null)
      return
    }

    const selectionStillExists = leadMagnets.some((item) => item.id === selectedLeadMagnetId)
    if (!selectedLeadMagnetId || !selectionStillExists) {
      setSelectedLeadMagnetId(leadMagnets[0]?.id ?? null)
    }
  }, [leadMagnets, selectedLeadMagnetId])

  useEffect(() => {
    if (!selectedLeadMagnet) {
      setLeadMagnetForm({})
      return
    }

    setLeadMagnetForm({
      type: selectedLeadMagnet.type,
      title: selectedLeadMagnet.title,
      description: selectedLeadMagnet.description,
      file_url: selectedLeadMagnet.file_url,
      cta_text: selectedLeadMagnet.cta_text,
      sendpulse_list_id: selectedLeadMagnet.sendpulse_list_id,
    })
  }, [selectedLeadMagnet])

  useEffect(() => {
    if (!selectedLeadMagnet) {
      return
    }

    const landingPage = landingPageQuery.data
    if (landingPage) {
      setLandingPageForm({
        slug: landingPage.slug,
        title: landingPage.title,
        subtitle: landingPage.subtitle,
        hero_image_url: landingPage.hero_image_url,
        benefits: landingPage.benefits,
        social_proof_count: landingPage.social_proof_count,
        author_bio: landingPage.author_bio,
        author_photo_url: landingPage.author_photo_url,
        meta_title: landingPage.meta_title,
        meta_description: landingPage.meta_description,
        published: landingPage.published,
      })
      return
    }

    setLandingPageForm({
      slug: slugify(selectedLeadMagnet.title),
      title: selectedLeadMagnet.title,
      subtitle: selectedLeadMagnet.description,
      hero_image_url: "",
      benefits: [],
      social_proof_count: 0,
      author_bio: "",
      author_photo_url: "",
      meta_title: selectedLeadMagnet.title,
      meta_description: selectedLeadMagnet.description,
      published: false,
    })
  }, [landingPageQuery.data, selectedLeadMagnet])

  const totals = useMemo(() => {
    const activeCount = leadMagnets.filter((item) => item.status === "active").length
    const totalCaptured = leadMagnets.reduce((sum, item) => sum + item.total_leads_captured, 0)
    return {
      totalLeadMagnets: leadMagnets.length,
      activeCount,
      totalCaptured,
    }
  }, [leadMagnets])

  const publicUrl = landingPageQuery.data?.slug
    ? `${env.NEXT_PUBLIC_APP_URL}/lm/${landingPageQuery.data.slug}`
    : null
  const calculatorUrl = selectedLeadMagnetId
    ? `${env.NEXT_PUBLIC_APP_URL}/lm/calculadora?lead_magnet_id=${selectedLeadMagnetId}`
    : null
  const launchHref = selectedLeadMagnet
    ? `/content/gerar?${new URLSearchParams({
        contentGoal: "lead_magnet_launch",
        leadMagnetId: selectedLeadMagnet.id,
        theme: selectedLeadMagnet.title,
      }).toString()}`
    : "/content/gerar"

  async function handleCreateExample() {
    try {
      const result = await createExampleLM.mutateAsync()
      setSelectedLeadMagnetId(result.id)
      toast.success(
        <span>
          LP de exemplo criada!{" "}
          <a href={result.public_url} target="_blank" rel="noreferrer" className="underline">
            Abrir
          </a>
        </span>,
      )
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao criar LP de exemplo")
    }
  }

  async function handleTestConnection() {
    setConnectionResult(null)
    try {
      const result = await testConnection.mutateAsync()
      setConnectionResult(result)
      if (result.status === "ok") {
        toast.success(result.message)
      } else {
        toast.error(result.message)
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao testar conexão SendPulse")
    }
  }

  async function handleTestWebhook() {
    setWebhookTestResult(null)
    try {
      const result = await testWebhook.mutateAsync({
        ...webhookTestForm,
        list_id: webhookTestForm.list_id?.trim() || undefined,
      })
      setWebhookTestResult(result)
      toast.success(result.message)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao simular webhook")
    }
  }

  async function handleSaveLeadMagnet() {
    if (!selectedLeadMagnetId) {
      return
    }

    try {
      await updateLeadMagnet.mutateAsync({
        leadMagnetId: selectedLeadMagnetId,
        body: {
          ...leadMagnetForm,
          title: (leadMagnetForm.title || "").trim(),
          description: normalizeNullableText(leadMagnetForm.description),
          file_url: normalizeNullableText(leadMagnetForm.file_url),
          cta_text: normalizeNullableText(leadMagnetForm.cta_text),
          sendpulse_list_id: normalizeNullableText(leadMagnetForm.sendpulse_list_id),
        },
      })
      toast.success("Lead magnet salvo")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao salvar lead magnet")
    }
  }

  async function handleChangeStatus(status: LeadMagnetStatus) {
    if (!selectedLeadMagnetId) {
      return
    }

    try {
      await updateLeadMagnetStatus.mutateAsync({ leadMagnetId: selectedLeadMagnetId, status })
      toast.success(`Status atualizado para ${statusLabel(status)}`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao atualizar status")
    }
  }

  async function handleSaveLandingPage() {
    if (!selectedLeadMagnetId) {
      return
    }

    try {
      await upsertLandingPage.mutateAsync({
        leadMagnetId: selectedLeadMagnetId,
        body: {
          ...landingPageForm,
          slug: slugify(landingPageForm.slug || selectedLeadMagnet?.title || "lead-magnet"),
          title: (landingPageForm.title || selectedLeadMagnet?.title || "").trim(),
          subtitle: normalizeNullableText(landingPageForm.subtitle),
          hero_image_url: normalizeNullableText(landingPageForm.hero_image_url),
          benefits: landingPageForm.benefits?.filter(Boolean) ?? [],
          author_bio: normalizeNullableText(landingPageForm.author_bio),
          author_photo_url: normalizeNullableText(landingPageForm.author_photo_url),
          meta_title: normalizeNullableText(landingPageForm.meta_title),
          meta_description: normalizeNullableText(landingPageForm.meta_description),
          published: Boolean(landingPageForm.published),
          social_proof_count: Number(landingPageForm.social_proof_count || 0),
        },
      })
      toast.success("Landing page salva")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao salvar landing page")
    }
  }

  async function handleCopyPublicUrl() {
    if (!publicUrl) {
      return
    }
    await navigator.clipboard.writeText(publicUrl)
    toast.success("Link publico copiado")
  }

  async function handleConvertLead(lmLeadId: string) {
    if (!selectedLeadMagnetId) {
      return
    }

    try {
      await convertLead.mutateAsync({ leadMagnetId: selectedLeadMagnetId, lmLeadId })
      toast.success("Lead convertido para prospeccao")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao converter lead")
    }
  }

  async function handleUploadPdf(file: File) {
    if (!selectedLeadMagnetId) {
      return
    }

    try {
      await uploadPdf.mutateAsync({ leadMagnetId: selectedLeadMagnetId, file })
      toast.success("PDF enviado com sucesso")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao enviar PDF")
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* ─── Cabeçalho ─── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-(--text-primary)">Inbound e Lead Magnets</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-(--text-secondary)">
            Gerencie materiais, landing pages e capturas sem misturar com o outbound.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void handleCreateExample()}
            disabled={createExampleLM.isPending}
          >
            <Wand2 className="h-4 w-4" />
            {createExampleLM.isPending ? "Criando..." : "Criar LP de exemplo"}
          </Button>
          <Button asChild variant="outline" size="sm">
            <a href="/lm/calculadora" target="_blank" rel="noreferrer">
              <Gauge className="h-4 w-4" />
              Ver calculadora
            </a>
          </Button>
          <CreateLeadMagnetDialog
            isPending={createLeadMagnet.isPending}
            onCreate={async (payload) => {
              const created = await createLeadMagnet.mutateAsync(payload)
              setSelectedLeadMagnetId(created.id)
            }}
          />
        </div>
      </div>

      {/* ─── Cards de resumo ─── */}
      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard icon={FileDown} label="Lead magnets" value={String(totals.totalLeadMagnets)} />
        <SummaryCard icon={Sparkles} label="Ativos" value={String(totals.activeCount)} />
        <SummaryCard icon={UserPlus} label="Capturados" value={String(totals.totalCaptured)} />
      </div>

      {/* ─── Seletor de lead magnet ─── */}
      <div className="flex flex-col gap-3 rounded-2xl border border-(--border-default) bg-(--bg-surface) p-4 sm:flex-row sm:items-center">
        <div className="flex-1">
          {leadMagnetsQuery.isLoading ? (
            <p className="text-sm text-(--text-secondary)">Carregando lead magnets...</p>
          ) : leadMagnets.length === 0 ? (
            <p className="text-sm text-(--text-secondary)">
              Nenhum lead magnet criado. Clique em{" "}
              <span className="font-medium text-(--text-primary)">Novo lead magnet</span> para
              começar.
            </p>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-(--text-tertiary)">Selecionado:</span>
              <Select
                value={selectedLeadMagnetId ?? ""}
                onValueChange={(value) => {
                  setSelectedLeadMagnetId(value)
                  setActiveTab("metricas")
                }}
              >
                <SelectTrigger className="h-9 w-full max-w-[600px] text-sm">
                  <SelectValue placeholder="Escolher lead magnet..." />
                </SelectTrigger>
                <SelectContent>
                  {leadMagnets.map((item) => (
                    <SelectItem key={item.id} value={item.id}>
                      <span className="flex items-center gap-2">
                        <span>{item.title}</span>
                        <span className="text-xs text-(--text-tertiary)">
                          · {typeLabel(item.type)} · {item.total_leads_captured} leads
                        </span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedLeadMagnet && (
                <Badge variant={statusVariant(selectedLeadMagnet.status)}>
                  {statusLabel(selectedLeadMagnet.status)}
                </Badge>
              )}
              {selectedLeadMagnet && (
                <Badge variant="outline">{typeLabel(selectedLeadMagnet.type)}</Badge>
              )}
            </div>
          )}
        </div>
        {selectedLeadMagnet && publicUrl && (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void handleCopyPublicUrl()}>
              <Copy className="h-4 w-4" />
              Copiar link
            </Button>
            <Button asChild variant="outline" size="sm">
              <a href={publicUrl} target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" />
                Abrir LP
              </a>
            </Button>
          </div>
        )}
      </div>

      {/* ─── Painel principal ─── */}
      {!selectedLeadMagnet ? (
        <Card>
          <CardContent className="flex min-h-60 items-center justify-center text-sm text-(--text-secondary)">
            {leadMagnets.length === 0
              ? "Crie seu primeiro lead magnet para começar."
              : "Selecione um lead magnet acima para continuar."}
          </CardContent>
        </Card>
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="metricas">
              <BarChart3 className="h-4 w-4" />
              Métricas
            </TabsTrigger>
            <TabsTrigger value="configuracao">
              <Settings className="h-4 w-4" />
              Configuração
            </TabsTrigger>
            <TabsTrigger value="leads">
              <UserPlus className="h-4 w-4" />
              Leads
            </TabsTrigger>
            <TabsTrigger value="integracoes">
              <Activity className="h-4 w-4" />
              Integrações
            </TabsTrigger>
          </TabsList>

          {/* ─────────────── ABA: MÉTRICAS ─────────────── */}
          <TabsContent value="metricas">
            <div className="flex flex-col gap-6">
              {!metricsQuery.data ? (
                <Card>
                  <CardContent className="p-6 text-sm text-(--text-secondary)">
                    Carregando métricas...
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Métricas do funil</CardTitle>
                    <CardDescription>
                      Visibilidade de captura, nutrição e qualificação.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <MetricCard
                        label="Capturados"
                        value={String(metricsQuery.data.total_leads_captured)}
                      />
                      <MetricCard
                        label="Sincronizados"
                        value={String(metricsQuery.data.total_synced_to_sendpulse)}
                      />
                      <MetricCard
                        label="Views LP"
                        value={String(metricsQuery.data.landing_page_views)}
                      />
                      <MetricCard
                        label="Submissões LP"
                        value={String(metricsQuery.data.landing_page_submissions)}
                      />
                      <MetricCard label="Opens" value={String(metricsQuery.data.total_opens)} />
                      <MetricCard label="Clicks" value={String(metricsQuery.data.total_clicks)} />
                      <MetricCard
                        label="Seq. concluída"
                        value={String(metricsQuery.data.total_sequence_completed)}
                      />
                      <MetricCard
                        label="Conv. qualificada"
                        value={
                          metricsQuery.data.qualified_conversion_rate != null
                            ? `${metricsQuery.data.qualified_conversion_rate.toFixed(1)}%`
                            : "-"
                        }
                      />
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader>
                  <CardTitle>Fluxos disponíveis</CardTitle>
                  <CardDescription>
                    Atalhos para lançar, distribuir e medir o ativo.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-3">
                  <QuickLinkCard
                    icon={Sparkles}
                    title="Launch post com IA"
                    description="Abre o gerador no modo lead magnet launch para criar o post nativo de divulgação."
                    href={launchHref}
                    cta="Abrir gerador"
                  />
                  <QuickLinkCard
                    icon={Mail}
                    title="LP pública"
                    description="Use a landing page para captura e envio automático para a lista do SendPulse."
                    href={publicUrl || "#"}
                    cta={publicUrl ? "Abrir LP" : "Configure a LP"}
                    disabled={!publicUrl}
                  />
                  <QuickLinkCard
                    icon={BarChart3}
                    title="Calculadora pública"
                    description="Fluxo alternativo para diagnóstico de ROI e qualificação antes do handoff comercial."
                    href={calculatorUrl || "/lm/calculadora"}
                    cta="Abrir calculadora"
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* ─────────────── ABA: CONFIGURAÇÃO ─────────────── */}
          <TabsContent value="configuracao">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Configuração do lead magnet</CardTitle>
                  <CardDescription>
                    Arquivo, CTA, lista do SendPulse e tipo do ativo.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Tipo">
                      <Select
                        value={leadMagnetForm.type ?? selectedLeadMagnet.type}
                        onValueChange={(value) =>
                          setLeadMagnetForm((current) => ({
                            ...current,
                            type: value as LeadMagnetType,
                          }))
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {TYPE_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>

                    <Field label="Status">
                      <Select
                        value={selectedLeadMagnet.status}
                        onValueChange={(value) =>
                          void handleChangeStatus(value as LeadMagnetStatus)
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {STATUS_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>
                  </div>

                  <Field label="Título">
                    <Input
                      value={leadMagnetForm.title ?? ""}
                      onChange={(event) =>
                        setLeadMagnetForm((current) => ({
                          ...current,
                          title: event.target.value,
                        }))
                      }
                    />
                  </Field>

                  <Field label="Descrição">
                    <Textarea
                      value={leadMagnetForm.description ?? ""}
                      onChange={(event) =>
                        setLeadMagnetForm((current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                      rows={4}
                    />
                  </Field>

                  <Field label="CTA principal">
                    <Input
                      value={leadMagnetForm.cta_text ?? ""}
                      onChange={(event) =>
                        setLeadMagnetForm((current) => ({
                          ...current,
                          cta_text: event.target.value,
                        }))
                      }
                      placeholder="Ex: Receber checklist"
                    />
                  </Field>

                  <Field label="URL do arquivo / Link externo">
                    <div className="flex gap-2">
                      <Input
                        value={leadMagnetForm.file_url ?? ""}
                        onChange={(event) =>
                          setLeadMagnetForm((current) => ({
                            ...current,
                            file_url: event.target.value,
                          }))
                        }
                        placeholder="https://..."
                      />
                      <input
                        ref={pdfInputRef}
                        type="file"
                        accept="application/pdf"
                        aria-label="Selecionar PDF para upload"
                        className="hidden"
                        onChange={(event) => {
                          const file = event.target.files?.[0]
                          if (file) void handleUploadPdf(file)
                          event.target.value = ""
                        }}
                      />
                      <Button
                        variant="outline"
                        size="icon"
                        title="Enviar PDF para MinIO"
                        disabled={uploadPdf.isPending}
                        onClick={() => pdfInputRef.current?.click()}
                      >
                        <Upload className="h-4 w-4" />
                      </Button>
                    </div>
                    {selectedLeadMagnet.file_url && (
                      <p className="mt-1 truncate text-xs text-(--text-secondary)">
                        Atual:{" "}
                        <a
                          href={selectedLeadMagnet.file_url}
                          target="_blank"
                          rel="noreferrer"
                          className="underline"
                        >
                          {selectedLeadMagnet.file_url}
                        </a>
                      </p>
                    )}
                  </Field>

                  <Field label="ID da lista no SendPulse">
                    <Input
                      value={leadMagnetForm.sendpulse_list_id ?? ""}
                      onChange={(event) =>
                        setLeadMagnetForm((current) => ({
                          ...current,
                          sendpulse_list_id: event.target.value,
                        }))
                      }
                      placeholder="addressbook_id"
                    />
                  </Field>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={() => void handleSaveLeadMagnet()}
                      disabled={updateLeadMagnet.isPending}
                    >
                      <Save className="h-4 w-4" />
                      Salvar configuração
                    </Button>
                    <Button asChild variant="outline">
                      <a href={launchHref}>
                        <Sparkles className="h-4 w-4" />
                        Gerar launch com IA
                      </a>
                    </Button>
                    {selectedLeadMagnet.type === "calculator" && calculatorUrl && (
                      <Button asChild variant="outline">
                        <a href={calculatorUrl} target="_blank" rel="noreferrer">
                          <ExternalLink className="h-4 w-4" />
                          Abrir calculadora
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Landing page pública</CardTitle>
                  <CardDescription>
                    Slug, copy, prova social e publicação do material.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Slug">
                      <Input
                        value={landingPageForm.slug}
                        onChange={(event) =>
                          setLandingPageForm((current) => ({
                            ...current,
                            slug: slugify(event.target.value),
                          }))
                        }
                      />
                    </Field>
                    <Field label="Título da página">
                      <Input
                        value={landingPageForm.title}
                        onChange={(event) =>
                          setLandingPageForm((current) => ({
                            ...current,
                            title: event.target.value,
                          }))
                        }
                      />
                    </Field>
                  </div>

                  <Field label="Subtítulo">
                    <Textarea
                      value={landingPageForm.subtitle ?? ""}
                      onChange={(event) =>
                        setLandingPageForm((current) => ({
                          ...current,
                          subtitle: event.target.value,
                        }))
                      }
                      rows={3}
                    />
                  </Field>

                  <Field label="Benefícios (1 por linha)">
                    <Textarea
                      value={(landingPageForm.benefits ?? []).join("\n")}
                      onChange={(event) =>
                        setLandingPageForm((current) => ({
                          ...current,
                          benefits: event.target.value.split("\n"),
                        }))
                      }
                      rows={4}
                    />
                  </Field>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Hero image URL">
                      <Input
                        value={landingPageForm.hero_image_url ?? ""}
                        onChange={(event) =>
                          setLandingPageForm((current) => ({
                            ...current,
                            hero_image_url: event.target.value,
                          }))
                        }
                      />
                    </Field>
                    <Field label="Foto autor URL">
                      <Input
                        value={landingPageForm.author_photo_url ?? ""}
                        onChange={(event) =>
                          setLandingPageForm((current) => ({
                            ...current,
                            author_photo_url: event.target.value,
                          }))
                        }
                      />
                    </Field>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Meta title">
                      <Input
                        value={landingPageForm.meta_title ?? ""}
                        onChange={(event) =>
                          setLandingPageForm((current) => ({
                            ...current,
                            meta_title: event.target.value,
                          }))
                        }
                      />
                    </Field>
                    <Field label="Prova social (quantidade)">
                      <Input
                        type="number"
                        min={0}
                        value={landingPageForm.social_proof_count ?? 0}
                        onChange={(event) =>
                          setLandingPageForm((current) => ({
                            ...current,
                            social_proof_count: Number(event.target.value || 0),
                          }))
                        }
                      />
                    </Field>
                  </div>

                  <Field label="Bio do autor">
                    <Textarea
                      value={landingPageForm.author_bio ?? ""}
                      onChange={(event) =>
                        setLandingPageForm((current) => ({
                          ...current,
                          author_bio: event.target.value,
                        }))
                      }
                      rows={3}
                    />
                  </Field>

                  <Field label="Meta description">
                    <Textarea
                      value={landingPageForm.meta_description ?? ""}
                      onChange={(event) =>
                        setLandingPageForm((current) => ({
                          ...current,
                          meta_description: event.target.value,
                        }))
                      }
                      rows={3}
                    />
                  </Field>

                  <div className="flex items-center justify-between rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-(--text-primary)">
                        Publicar landing page
                      </p>
                      <p className="text-xs text-(--text-tertiary)">
                        A rota pública só responde quando a LP estiver publicada.
                      </p>
                    </div>
                    <Switch
                      checked={Boolean(landingPageForm.published)}
                      onCheckedChange={(checked) =>
                        setLandingPageForm((current) => ({ ...current, published: checked }))
                      }
                    />
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={() => void handleSaveLandingPage()}
                      disabled={upsertLandingPage.isPending}
                    >
                      <Save className="h-4 w-4" />
                      Salvar landing page
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => void handleCopyPublicUrl()}
                      disabled={!publicUrl}
                    >
                      <Copy className="h-4 w-4" />
                      Copiar link público
                    </Button>
                    {publicUrl && (
                      <Button asChild variant="outline">
                        <a href={publicUrl} target="_blank" rel="noreferrer">
                          <ExternalLink className="h-4 w-4" />
                          Abrir página
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* ─────────────── ABA: LEADS ─────────────── */}
          <TabsContent value="leads">
            <Card>
              <CardHeader>
                <CardTitle>Leads capturados</CardTitle>
                <CardDescription>
                  Contatos vindos da LP, calculadora, comments e direct.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {(leadsQuery.data ?? []).length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-(--border-default) bg-(--bg-overlay) p-6 text-center text-sm text-(--text-secondary)">
                    Nenhuma captura registrada ainda para este lead magnet.
                  </div>
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-sm)">
                    <table className="min-w-full divide-y divide-(--border-subtle)">
                      <thead>
                        <tr className="border-b border-(--accent) bg-(--accent)">
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-invert)">
                            Nome / E-mail
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-invert)">
                            Empresa / Cargo
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-invert)">
                            Origem
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-invert)">
                            SP / Seq.
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-invert)">
                            Captado
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-invert)">
                            Ações
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-(--border-subtle) bg-(--bg-surface)">
                        {(leadsQuery.data ?? []).map((lead) => (
                          <tr key={lead.id} className="hover:bg-(--bg-overlay) transition-colors">
                            <td className="px-4 py-3">
                              <p className="text-sm font-medium text-(--text-primary)">
                                {lead.name}
                              </p>
                              <p className="text-xs text-(--text-secondary)">{lead.email}</p>
                              {lead.phone && (
                                <p className="text-xs text-(--text-tertiary)">{lead.phone}</p>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <p className="text-sm text-(--text-primary)">{lead.company || "—"}</p>
                              <p className="text-xs text-(--text-tertiary)">{lead.role || "—"}</p>
                            </td>
                            <td className="px-4 py-3">
                              <Badge variant="outline">{originLabel(lead.origin)}</Badge>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-col gap-1">
                                <Badge variant={syncVariant(lead.sendpulse_sync_status)}>
                                  {lead.sendpulse_sync_status}
                                </Badge>
                                <span className="text-xs text-(--text-tertiary)">
                                  {lead.sequence_status}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-xs text-(--text-tertiary)">
                              {formatRelativeTime(lead.created_at)}
                            </td>
                            <td className="px-4 py-3">
                              {!lead.converted_to_lead ? (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => void handleConvertLead(lead.id)}
                                  disabled={convertLead.isPending}
                                >
                                  <UserPlus className="h-4 w-4" />
                                  Converter
                                </Button>
                              ) : (
                                <span className="text-xs text-(--success)">Convertido</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ─────────────── ABA: CONFIGURAÇÕES (INTEGRAÇÕES) ─────────────── */}
          <TabsContent value="integracoes">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-(--accent)" />
                  Integração SendPulse
                </CardTitle>
                <CardDescription>
                  Teste as credenciais e simule eventos de webhook sem precisar de uma requisição
                  externa.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <p className="text-sm font-medium text-(--text-primary)">Testar credenciais</p>
                  <Button
                    variant="outline"
                    onClick={() => void handleTestConnection()}
                    disabled={testConnection.isPending}
                  >
                    <Wifi className="h-4 w-4" />
                    {testConnection.isPending ? "Verificando..." : "Testar conexão SendPulse"}
                  </Button>
                  {connectionResult && (
                    <div
                      className={cn(
                        "rounded-2xl border p-4 text-sm",
                        connectionResult.status === "ok"
                          ? "border-(--success)/30 bg-(--success-subtle) text-(--success-subtle-fg)"
                          : "border-(--danger)/30 bg-(--danger-subtle) text-(--danger-subtle-fg)",
                      )}
                    >
                      <p className="font-medium">{connectionResult.message}</p>
                      {connectionResult.lists && connectionResult.lists.length > 0 && (
                        <ul className="mt-2 space-y-1 text-xs">
                          {connectionResult.lists.slice(0, 6).map((list) => (
                            <li key={list.id}>
                              {list.name} — {list.all_email_qty} contatos
                              <span className="ml-2 font-mono opacity-60">(ID: {list.id})</span>
                            </li>
                          ))}
                          {connectionResult.lists.length > 6 && (
                            <li className="opacity-60">
                              ...e mais {connectionResult.lists.length - 6} lista(s)
                            </li>
                          )}
                        </ul>
                      )}
                    </div>
                  )}
                </div>

                <div className="space-y-3">
                  <p className="text-sm font-medium text-(--text-primary)">
                    Simular evento de webhook
                  </p>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Field label="Tipo de evento">
                      <Select
                        value={webhookTestForm.event_type}
                        onValueChange={(value) =>
                          setWebhookTestForm((current) => ({
                            ...current,
                            event_type: value as TestWebhookInput["event_type"],
                          }))
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {EVENT_TYPE_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="E-mail do lead">
                      <Input
                        type="email"
                        value={webhookTestForm.email}
                        onChange={(event) =>
                          setWebhookTestForm((current) => ({
                            ...current,
                            email: event.target.value,
                          }))
                        }
                        placeholder="lead@exemplo.com.br"
                      />
                    </Field>
                    <Field label="ID da lista (opcional)">
                      <Input
                        value={webhookTestForm.list_id ?? ""}
                        onChange={(event) =>
                          setWebhookTestForm((current) => ({
                            ...current,
                            list_id: event.target.value,
                          }))
                        }
                        placeholder="addressbook_id"
                      />
                    </Field>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => void handleTestWebhook()}
                    disabled={testWebhook.isPending || !webhookTestForm.email.trim()}
                  >
                    <Zap className="h-4 w-4" />
                    {testWebhook.isPending ? "Simulando..." : "Disparar webhook de teste"}
                  </Button>
                  {webhookTestResult && (
                    <div
                      className={cn(
                        "rounded-2xl border p-4 text-sm",
                        webhookTestResult.status === "ok"
                          ? "border-(--success)/30 bg-(--success-subtle) text-(--success-subtle-fg)"
                          : "border-(--border-default) bg-(--bg-overlay) text-(--text-secondary)",
                      )}
                    >
                      <p className="font-medium">{webhookTestResult.message}</p>
                      <p className="mt-1 text-xs">
                        Lead atualizado:{" "}
                        <strong>{webhookTestResult.lm_lead_updated ? "sim" : "não"}</strong>
                        {" · "}Evento gravado:{" "}
                        <strong>{webhookTestResult.event_stored ? "sim" : "não"}</strong>
                        {webhookTestResult.event_id && (
                          <>
                            {" · "}ID:{" "}
                            <span className="font-mono">{webhookTestResult.event_id}</span>
                          </>
                        )}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
interface CreateLeadMagnetDialogProps {
  isPending: boolean
  onCreate: (payload: ContentLeadMagnetCreateInput) => Promise<void>
}

function CreateLeadMagnetDialog({ isPending, onCreate }: CreateLeadMagnetDialogProps) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<ContentLeadMagnetCreateInput>({
    type: "pdf",
    title: "",
    description: "",
    status: "draft",
    file_url: "",
    cta_text: "",
    sendpulse_list_id: "",
  })

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    try {
      await onCreate({
        ...form,
        title: form.title.trim(),
        description: normalizeNullableText(form.description),
        file_url: normalizeNullableText(form.file_url),
        cta_text: normalizeNullableText(form.cta_text),
        sendpulse_list_id: normalizeNullableText(form.sendpulse_list_id),
      })
      setOpen(false)
      setForm({
        type: "pdf",
        title: "",
        description: "",
        status: "draft",
        file_url: "",
        cta_text: "",
        sendpulse_list_id: "",
      })
      toast.success("Lead magnet criado")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao criar lead magnet")
    }
  }

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <Plus className="h-4 w-4" />
        Novo lead magnet
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo lead magnet</DialogTitle>
            <DialogDescription>
              Crie o ativo base que sera conectado a LP, SendPulse e launches no LinkedIn.
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <Field label="Tipo">
              <Select
                value={form.type}
                onValueChange={(value) =>
                  setForm((current) => ({ ...current, type: value as LeadMagnetType }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Titulo">
              <Input
                value={form.title}
                onChange={(event) =>
                  setForm((current) => ({ ...current, title: event.target.value }))
                }
                required
              />
            </Field>

            <Field label="Descricao">
              <Textarea
                value={form.description ?? ""}
                onChange={(event) =>
                  setForm((current) => ({ ...current, description: event.target.value }))
                }
                rows={3}
              />
            </Field>

            <Field label="CTA principal">
              <Input
                value={form.cta_text ?? ""}
                onChange={(event) =>
                  setForm((current) => ({ ...current, cta_text: event.target.value }))
                }
              />
            </Field>

            <Field label="ID da lista no SendPulse">
              <Input
                value={form.sendpulse_list_id ?? ""}
                onChange={(event) =>
                  setForm((current) => ({ ...current, sendpulse_list_id: event.target.value }))
                }
              />
            </Field>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isPending || !form.title.trim()}>
                Criar lead magnet
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

interface SummaryCardProps {
  icon: typeof FileDown
  label: string
  value: string
}

function SummaryCard({ icon: Icon, label, value }: SummaryCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
            {label}
          </p>
          <p className="mt-1 text-2xl font-semibold text-(--text-primary)">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}

interface MetricCardProps {
  label: string
  value: string
}

function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">{label}</p>
      <p className="mt-2 text-lg font-semibold text-(--text-primary)">{value}</p>
    </div>
  )
}

interface QuickLinkCardProps {
  icon: typeof Sparkles
  title: string
  description: string
  href: string
  cta: string
  disabled?: boolean
}

function QuickLinkCard({
  icon: Icon,
  title,
  description,
  href,
  cta,
  disabled,
}: QuickLinkCardProps) {
  return (
    <div className="rounded-3xl border border-(--border-default) bg-(--bg-overlay) p-5">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-(--accent-subtle) text-(--accent-subtle-fg)">
        <Icon className="h-5 w-5" />
      </div>
      <p className="mt-4 text-base font-semibold text-(--text-primary)">{title}</p>
      <p className="mt-2 text-sm leading-6 text-(--text-secondary)">{description}</p>

      <Button asChild variant="outline" className="mt-4 w-full justify-between" disabled={disabled}>
        <a href={href} target={href.startsWith("http") ? "_blank" : undefined} rel="noreferrer">
          {cta}
          <ArrowRight className="h-4 w-4" />
        </a>
      </Button>
    </div>
  )
}

interface FieldProps {
  label: string
  children: React.ReactNode
}

function Field({ label, children }: FieldProps) {
  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      {children}
    </div>
  )
}

function normalizeNullableText(value: string | null | undefined): string | null {
  const normalized = value?.trim()
  return normalized ? normalized : null
}

function typeLabel(type: LeadMagnetType): string {
  switch (type) {
    case "pdf":
      return "PDF"
    case "calculator":
      return "Calculadora"
    default:
      return "Sequencia"
  }
}

function statusLabel(status: LeadMagnetStatus): string {
  switch (status) {
    case "active":
      return "Ativo"
    case "paused":
      return "Pausado"
    case "archived":
      return "Arquivado"
    default:
      return "Draft"
  }
}

function statusVariant(status: LeadMagnetStatus): "default" | "warning" | "neutral" | "success" {
  switch (status) {
    case "active":
      return "success"
    case "paused":
      return "warning"
    case "archived":
      return "neutral"
    default:
      return "default"
  }
}

function syncVariant(status: string): "default" | "warning" | "danger" | "success" | "outline" {
  switch (status) {
    case "synced":
      return "success"
    case "failed":
      return "danger"
    case "processing":
      return "warning"
    case "skipped":
      return "outline"
    default:
      return "default"
  }
}

function originLabel(origin: string): string {
  switch (origin) {
    case "landing_page":
      return "LP"
    case "linkedin_comment":
      return "Comentario"
    case "linkedin_dm":
      return "DM"
    case "calculator":
      return "Calculadora"
    default:
      return "Direto"
  }
}
