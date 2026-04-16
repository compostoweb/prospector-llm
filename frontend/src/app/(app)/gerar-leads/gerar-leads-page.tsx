"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import {
  ArrowRight,
  CalendarClock,
  CheckSquare,
  Clock,
  Download,
  FileSpreadsheet,
  Layers,
  Linkedin,
  MailSearch,
  MapPinned,
  Pause,
  Play,
  RefreshCw,
  Settings2,
  Sparkles,
  X,
} from "lucide-react"
import { toast } from "sonner"
import {
  type GeneratedLeadPreviewItem,
  type LinkedInProfile,
  useGenerateLeadsImport,
  useGenerateLeadsPreview,
  useImportLinkedInProfiles,
  useSearchLinkedIn,
} from "@/lib/api/hooks/use-leads"
import { useCreateLeadList, useLeadLists } from "@/lib/api/hooks/use-lead-lists"
import {
  useCaptureSchedules,
  useToggleCaptureSchedule,
  useUpsertCaptureSchedule,
  type CaptureScheduleConfig,
} from "@/lib/api/hooks/use-capture-schedule"
import {
  useEnrichmentJobs,
  useCreateEnrichmentJob,
  useDeleteEnrichmentJob,
  type EnrichmentJob,
} from "@/lib/api/hooks/use-enrichment-jobs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { CsvXlsImportDialog } from "@/components/leads/csv-xls-import-dialog"

type LeadGeneratorSource =
  | "google_maps"
  | "b2b_database"
  | "linkedin_enrichment"
  | "linkedin_search"

interface PreviewRow {
  id: string
  name: string
  jobTitle: string | null
  company: string | null
  location: string | null
  email: string | null
  phone: string | null
  linkedinUrl: string | null
  originLabel: string
  generatedItem?: GeneratedLeadPreviewItem
  linkedinProfile?: LinkedInProfile
}

const sourceOptions: Array<{
  id: LeadGeneratorSource
  title: string
  description: string
  icon: typeof MapPinned
}> = [
  {
    id: "google_maps",
    title: "Google Maps",
    description: "Capte empresas locais por busca, categoria e cidade.",
    icon: MapPinned,
  },
  {
    id: "b2b_database",
    title: "Base B2B",
    description: "Busque contatos com email, telefone e firmografia.",
    icon: MailSearch,
  },
  {
    id: "linkedin_enrichment",
    title: "Enriquecimento LinkedIn",
    description: "Complete dados a partir de URLs de perfis já capturados.",
    icon: Sparkles,
  },
  {
    id: "linkedin_search",
    title: "Busca LinkedIn",
    description: "Use a busca atual do sistema sem sair desta central.",
    icon: Linkedin,
  },
]

export default function GerarLeadsPage() {
  const [pageTab, setPageTab] = useState<"capturar" | "automacoes">("capturar")
  const [csvImportOpen, setCsvImportOpen] = useState(false)
  const [source, setSource] = useState<LeadGeneratorSource>("google_maps")
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [existingListId, setExistingListId] = useState<string>("none")
  const [newListName, setNewListName] = useState("")
  const [mergeDuplicates, setMergeDuplicates] = useState(true)

  const [mapsSearchTerms, setMapsSearchTerms] = useState("clínicas odontológicas\ncontabilidades")
  const [mapsLocation, setMapsLocation] = useState("São Paulo, Brasil")
  const [mapsLocations, setMapsLocations] = useState("")
  const [mapsCategories, setMapsCategories] = useState("clínica odontológica\nconsultoria")
  const [mapsLimit, setMapsLimit] = useState("25")

  const [b2bTitles, setB2bTitles] = useState("Head de Marketing\nDiretor Comercial")
  const [b2bLocations, setB2bLocations] = useState("Brasil")
  const [b2bCities, setB2bCities] = useState("São Paulo\nCuritiba")
  const [b2bIndustries, setB2bIndustries] = useState("software\nmarketing & advertising")
  const [b2bKeywords, setB2bKeywords] = useState("B2B\nSaaS")
  const [b2bSizes, setB2bSizes] = useState("11-20\n21-50\n51-100")
  const [b2bLimit, setB2bLimit] = useState("50")
  const [b2bNegativeTerms, setB2bNegativeTerms] = useState("")

  const [enrichmentUrls, setEnrichmentUrls] = useState("")
  const [enrichmentLimit, setEnrichmentLimit] = useState("25")

  const [linkedinKeywords, setLinkedinKeywords] = useState("marketing automation")
  const [linkedinTitles, setLinkedinTitles] = useState("Head de Marketing\nCMO")
  const [linkedinCompanies, setLinkedinCompanies] = useState("")
  const [linkedinLimit, setLinkedinLimit] = useState("25")

  const [generatedPreview, setGeneratedPreview] = useState<GeneratedLeadPreviewItem[]>([])
  const [linkedinPreview, setLinkedinPreview] = useState<LinkedInProfile[]>([])

  const { data: leadLists } = useLeadLists()
  const createLeadList = useCreateLeadList()
  const previewGeneratedLeads = useGenerateLeadsPreview()
  const importGeneratedLeads = useGenerateLeadsImport()
  const searchLinkedIn = useSearchLinkedIn()
  const importLinkedIn = useImportLinkedInProfiles()
  const saveMapsSchedule = useUpsertCaptureSchedule("google_maps")
  const saveB2BSchedule = useUpsertCaptureSchedule("b2b_database")
  const { data: schedules = [] } = useCaptureSchedules()
  const toggleMaps = useToggleCaptureSchedule("google_maps")
  const toggleB2B = useToggleCaptureSchedule("b2b_database")
  const { data: enrichmentJobs = [], isLoading: isLoadingJobs } = useEnrichmentJobs()
  const createEnrichmentJob = useCreateEnrichmentJob()
  const deleteEnrichmentJob = useDeleteEnrichmentJob()

  const previewRows = useMemo<PreviewRow[]>(() => {
    if (source === "linkedin_search") {
      return linkedinPreview.map((profile) => ({
        id: profile.provider_id,
        name: profile.name,
        jobTitle: profile.headline,
        company: profile.company,
        location: profile.location,
        email: null,
        phone: null,
        linkedinUrl: profile.profile_url,
        originLabel: "Busca LinkedIn",
        linkedinProfile: profile,
      }))
    }

    return generatedPreview.map((item) => ({
      id: item.preview_id,
      name: item.name,
      jobTitle: item.job_title,
      company: item.company,
      location: item.location ?? item.city,
      email: item.email_corporate ?? item.email_personal,
      phone: item.phone,
      linkedinUrl: item.linkedin_url,
      originLabel: item.origin_label,
      generatedItem: item,
    }))
  }, [generatedPreview, linkedinPreview, source])

  const selectedRows = previewRows.filter((row) => selectedIds.includes(row.id))
  const allSelected = previewRows.length > 0 && previewRows.length === selectedIds.length

  async function handlePreview() {
    try {
      if (source === "google_maps") {
        const result = await previewGeneratedLeads.mutateAsync({
          source,
          limit: Number(mapsLimit) || 25,
          search_terms: splitLines(mapsSearchTerms),
          location_query: mapsLocation.trim() || null,
          categories: splitLines(mapsCategories),
        })
        setGeneratedPreview(result.items)
        setLinkedinPreview([])
      } else if (source === "b2b_database") {
        const result = await previewGeneratedLeads.mutateAsync({
          source,
          limit: Number(b2bLimit) || 50,
          job_titles: splitLines(b2bTitles),
          locations: splitLines(b2bLocations),
          cities: splitLines(b2bCities),
          industries: splitLines(b2bIndustries),
          company_keywords: splitLines(b2bKeywords),
          company_sizes: splitLines(b2bSizes),
          email_status: ["validated"],
          negative_terms: splitLines(b2bNegativeTerms),
        })
        setGeneratedPreview(result.items)
        setLinkedinPreview([])
      } else if (source === "linkedin_enrichment") {
        const result = await previewGeneratedLeads.mutateAsync({
          source,
          limit: Number(enrichmentLimit) || 25,
          linkedin_urls: splitLines(enrichmentUrls),
        })
        setGeneratedPreview(result.items)
        setLinkedinPreview([])
      } else {
        const result = await searchLinkedIn.mutateAsync({
          keywords: linkedinKeywords.trim(),
          titles: splitLines(linkedinTitles),
          companies: splitLines(linkedinCompanies),
          limit: Number(linkedinLimit) || 25,
        })
        setLinkedinPreview(result.items)
        setGeneratedPreview([])
      }

      setSelectedIds([])
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao gerar preview")
    }
  }

  async function handleImport() {
    if (selectedRows.length === 0) {
      toast.error("Selecione pelo menos um lead para importar")
      return
    }

    try {
      let listId: string | undefined
      if (existingListId !== "none") {
        listId = existingListId
      } else if (newListName.trim()) {
        const createdList = await createLeadList.mutateAsync({ name: newListName.trim() })
        listId = createdList.id
      }

      if (source === "linkedin_search") {
        const profiles = selectedRows
          .map((row) => row.linkedinProfile)
          .filter((profile): profile is LinkedInProfile => Boolean(profile))
        const result = await importLinkedIn.mutateAsync({
          profiles,
          ...(listId ? { list_id: listId } : {}),
        })
        toast.success(`${result.created} leads importados do LinkedIn`)
      } else {
        const items = selectedRows
          .map((row) => row.generatedItem)
          .filter((item): item is GeneratedLeadPreviewItem => Boolean(item))
        const result = await importGeneratedLeads.mutateAsync({
          source,
          items,
          ...(listId ? { list_id: listId } : {}),
          merge_duplicates: mergeDuplicates,
        })
        toast.success(`${result.created} leads criados e ${result.updated} atualizados`)
      }

      setSelectedIds([])
      setNewListName("")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao importar leads")
    }
  }

  async function handleSaveSchedule() {
    try {
      if (source === "google_maps") {
        await saveMapsSchedule.mutateAsync({
          source: "google_maps",
          is_active: true,
          max_items: Number(mapsLimit) || 25,
          maps_search_terms: splitLines(mapsSearchTerms),
          maps_location: mapsLocation.trim() || null,
          maps_locations: splitLines(mapsLocations),
          maps_categories: splitLines(mapsCategories),
        })
        toast.success("Captura automática salva — será executada todos os dias às 08h")
      } else if (source === "b2b_database") {
        await saveB2BSchedule.mutateAsync({
          source: "b2b_database",
          is_active: true,
          max_items: Number(b2bLimit) || 50,
          b2b_job_titles: splitLines(b2bTitles),
          b2b_locations: splitLines(b2bLocations),
          b2b_cities: splitLines(b2bCities),
          b2b_industries: splitLines(b2bIndustries),
          b2b_company_keywords: splitLines(b2bKeywords),
          b2b_company_sizes: splitLines(b2bSizes),
        })
        toast.success("Captura automática salva — será executada todos os dias às 09h")
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao salvar configuração")
    }
  }

  function downloadEnrichmentTemplate() {
    const csv = "linkedin_url\nhttps://www.linkedin.com/in/exemplo"
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "prospector_enrichment_template.csv"
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleCreateEnrichmentQueue() {
    const urls = splitLines(enrichmentUrls)
    if (urls.length === 0) {
      toast.error("Adicione ao menos uma URL antes de criar a fila")
      return
    }
    const batchSize = Math.min(Number(enrichmentLimit) || 25, 100)
    const listName = newListName.trim() || null
    const listId = existingListId !== "none" ? existingListId : null
    try {
      const job = await createEnrichmentJob.mutateAsync({
        linkedin_urls: urls,
        batch_size: batchSize,
        target_list_id: listId,
        target_list_name: listName,
      })
      const batches = Math.ceil(urls.length / batchSize)
      toast.success(
        `Fila criada — ${urls.length} perfis divididos em ${batches} batch${batches > 1 ? "es" : ""} de ${batchSize}. O primeiro processa em até 1h.`,
      )
      setEnrichmentUrls("")
      // eslint-disable-next-line @typescript-eslint/no-unused-expressions
      job // keep TS happy
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Falha ao criar fila")
    }
  }

  async function handleToggleSchedule(cfg: CaptureScheduleConfig) {
    const toggle = cfg.source === "google_maps" ? toggleMaps : toggleB2B
    try {
      await toggle.mutateAsync({ config: cfg })
      toast.success(cfg.is_active ? "Captura pausada" : "Captura reativada")
    } catch {
      toast.error("Falha ao alterar estado da captura")
    }
  }

  function getNextCombo(cfg: CaptureScheduleConfig): string {
    if (cfg.source === "google_maps") {
      const terms = cfg.maps_search_terms ?? []
      const locs = cfg.maps_locations ?? (cfg.maps_location ? [cfg.maps_location] : [])
      if (!terms.length || !locs.length) return "—"
      const combos = terms.flatMap((t) => locs.map((l) => `${t} em ${l}`))
      return combos[cfg.maps_combo_index % combos.length] ?? "—"
    }
    const cities = cfg.b2b_cities ?? []
    const titles = cfg.b2b_job_titles ?? []
    if (!cities.length) return "—"
    const city = cities[cfg.b2b_rotation_index % cities.length]
    const titlesPreview = titles.slice(0, 2).join(", ") || "—"
    return `${titlesPreview} — ${city}`
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between mb-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-(--accent)">
            Prospecção assistida
          </p>
          <h1 className="mt-0 text-2xl font-semibold text-(--text-primary)">Gerar leads</h1>
          <p className="mt-1 max-w-3xl text-sm text-(--text-secondary)">
            Rode captura, enriquecimento e revisão no mesmo fluxo antes de salvar em uma lista
            operacional.
          </p>
        </div>

        <div className="flex flex-wrap gap-2 ">
          <Button asChild variant="outline">
            <Link href="/listas">Abrir listas</Link>
          </Button>
          <Button
            onClick={handlePreview}
            disabled={previewGeneratedLeads.isPending || searchLinkedIn.isPending}
          >
            <RefreshCw
              size={14}
              aria-hidden="true"
              className={
                previewGeneratedLeads.isPending || searchLinkedIn.isPending ? "animate-spin" : ""
              }
            />
            Gerar preview
          </Button>
        </div>
      </div>

      <Tabs value={pageTab} onValueChange={(v) => setPageTab(v as "capturar" | "automacoes")}>
        <nav className="flex gap-1 border-b border-(--border-default)">
          {(
            [
              { value: "capturar", label: "Capturar", icon: null },
              { value: "automacoes", label: "Automações", icon: Settings2 },
            ] as const
          ).map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => setPageTab(value)}
              className={`flex items-center gap-2 border-b-2 -mb-px px-4 py-2 text-sm transition-colors ${
                pageTab === value
                  ? "border-(--accent) text-(--accent) font-medium"
                  : "border-transparent text-(--text-secondary) hover:text-(--text-primary)"
              }`}
            >
              {Icon && <Icon className="h-4 w-4" />}
              {label}
              {value === "automacoes" && schedules.length > 0 && (
                <Badge variant="neutral" className="ml-0.5 h-4 px-1 text-[10px]">
                  {schedules.filter((s) => s.is_active).length}
                </Badge>
              )}
            </button>
          ))}
        </nav>

        <TabsContent value="capturar" className="mt-4">
          <div className="grid gap-4 xl:grid-cols-4 mb-4">
            {sourceOptions.map((option) => {
              const Icon = option.icon
              const isActive = option.id === source
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => {
                    setSource(option.id)
                    setSelectedIds([])
                  }}
                  className={`rounded-xl border p-4 text-left transition-colors ${
                    isActive
                      ? "border-(--accent) bg-(--accent-subtle)"
                      : "border-(--border-default) bg-(--bg-surface) hover:bg-(--bg-overlay)"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-(--bg-overlay) text-(--accent)">
                      <Icon size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-(--text-primary)">{option.title}</p>
                      <p className="text-xs text-(--text-secondary)">{option.description}</p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.05fr_1.45fr]">
            <Card>
              <CardHeader>
                <CardTitle>Filtros da fonte</CardTitle>
                <CardDescription>
                  Ajuste os parâmetros da captura antes de rodar o preview.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {source === "google_maps" && (
                  <>
                    <Field
                      label="Termos de busca"
                      hint="Um por linha. Ex.: clínicas odontológicas, escritórios de contabilidade. O Apify buscará cada termo no Google Maps."
                    >
                      <Textarea
                        value={mapsSearchTerms}
                        onChange={(e) => setMapsSearchTerms(e.target.value)}
                        placeholder={"clínicas odontológicas\nescritórios de contabilidade"}
                        rows={3}
                      />
                    </Field>
                    <Field
                      label="Localização para preview"
                      hint="Cidade, estado ou país onde o preview será rodado. Exemplos: São Paulo, Brasil / Rio de Janeiro, RJ."
                    >
                      <input
                        value={mapsLocation}
                        onChange={(e) => setMapsLocation(e.target.value)}
                        className={inputClassName}
                        placeholder="São Paulo, Brasil"
                        title="Localização"
                      />
                    </Field>
                    <Field
                      label="Localidades para rotação automática"
                      hint="Uma por linha — a captura diária vai ciclar uma combinação (termo × local) por dia. Deixe vazio para usar só a localização do preview acima."
                    >
                      <Textarea
                        value={mapsLocations}
                        onChange={(e) => setMapsLocations(e.target.value)}
                        placeholder={"São Paulo\nRio de Janeiro\nBelo Horizonte"}
                        rows={4}
                      />
                    </Field>
                    <Field
                      label="Categorias (opcional)"
                      hint="Filtre por categoria do Google Maps. Uma por linha. Ex.: restaurant, dentist. Deixe vazio para não filtrar."
                    >
                      <Textarea
                        value={mapsCategories}
                        onChange={(e) => setMapsCategories(e.target.value)}
                        placeholder={"restaurant\ndentist"}
                        rows={3}
                      />
                    </Field>
                    <Field
                      label="Limite de resultados"
                      hint="Recomendamos até 100 por execução. A API do Google Maps não tem limite diário fixo, mas volumes altos aumentam o custo do Apify."
                    >
                      <input
                        value={mapsLimit}
                        onChange={(e) => setMapsLimit(e.target.value)}
                        className={inputClassName}
                        placeholder="25"
                        title="Limite"
                        type="number"
                        min={1}
                        max={200}
                      />
                    </Field>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={handleSaveSchedule}
                      disabled={saveMapsSchedule.isPending}
                    >
                      <CalendarClock size={14} aria-hidden="true" />
                      Salvar como captura automática diária
                    </Button>
                  </>
                )}

                {source === "b2b_database" && (
                  <>
                    <Field
                      label="Cargos alvo"
                      hint="Um por linha. Serão buscados como OR. Ex.: Head de Marketing, CMO, Gerente de Vendas."
                    >
                      <Textarea
                        value={b2bTitles}
                        onChange={(e) => setB2bTitles(e.target.value)}
                        placeholder={"Head de Marketing\nCMO\nGerente de Vendas"}
                        rows={3}
                      />
                    </Field>
                    <Field
                      label="Localizações (país / estado)"
                      hint="Um por linha. Use nomes em inglês para melhor precisão. Ex.: Brazil, United States, São Paulo."
                    >
                      <Textarea
                        value={b2bLocations}
                        onChange={(e) => setB2bLocations(e.target.value)}
                        placeholder={"Brazil"}
                        rows={2}
                      />
                    </Field>
                    <Field
                      label="Cidades (para rotação automática)"
                      hint="Uma por linha. A captura diária cicla uma cidade por dia. Ex.: São Paulo, Curitiba, Belo Horizonte."
                    >
                      <Textarea
                        value={b2bCities}
                        onChange={(e) => setB2bCities(e.target.value)}
                        placeholder={"São Paulo\nCuritiba\nBelo Horizonte"}
                        rows={3}
                      />
                    </Field>
                    <Field
                      label="Indústrias"
                      hint="Um por linha. Filtra pelo setor da empresa. Ex.: Software, Marketing & Advertising, Financial Services."
                    >
                      <Textarea
                        value={b2bIndustries}
                        onChange={(e) => setB2bIndustries(e.target.value)}
                        placeholder={"Software\nMarketing & Advertising"}
                        rows={3}
                      />
                    </Field>
                    <Field
                      label="Keywords da empresa"
                      hint="Um por linha. Filtra empresas cujo nome ou descrição contém o termo. Ex.: SaaS, B2B, agência."
                    >
                      <Textarea
                        value={b2bKeywords}
                        onChange={(e) => setB2bKeywords(e.target.value)}
                        placeholder={"SaaS\nB2B"}
                        rows={2}
                      />
                    </Field>
                    <Field
                      label="Faixas de tamanho de empresa"
                      hint="Uma por linha. Opções: 1, 2-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5001-10000, 10001+."
                    >
                      <Textarea
                        value={b2bSizes}
                        onChange={(e) => setB2bSizes(e.target.value)}
                        placeholder={"11-50\n51-200"}
                        rows={2}
                      />
                    </Field>
                    <Field
                      label="Termos negativos (filtro de exclusão)"
                      hint="Um por linha. Leads com qualquer desses termos no cargo ou nome da empresa serão descartados automaticamente do preview. Ex.: estagiário, trainee, junior."
                    >
                      <Textarea
                        value={b2bNegativeTerms}
                        onChange={(e) => setB2bNegativeTerms(e.target.value)}
                        placeholder={"estagiário\ntrainee\njunior\nfreelancer"}
                        rows={3}
                      />
                    </Field>
                    <Field
                      label="Limite de resultados"
                      hint="Máximo de 200 por requisição na API Apify B2B. Recomendamos 50–100 para garantir qualidade e evitar leads repetidos."
                    >
                      <input
                        value={b2bLimit}
                        onChange={(e) => setB2bLimit(e.target.value)}
                        className={inputClassName}
                        placeholder="50"
                        title="Limite"
                        type="number"
                        min={1}
                        max={200}
                      />
                    </Field>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={handleSaveSchedule}
                      disabled={saveB2BSchedule.isPending}
                    >
                      <CalendarClock size={14} aria-hidden="true" />
                      Salvar como captura automática diária
                    </Button>
                  </>
                )}

                {source === "linkedin_enrichment" && (
                  <>
                    <Field
                      label="URLs de perfis do LinkedIn"
                      hint="Uma URL por linha (linkedin.com/in/…). Cole manualmente, importe via CSV/XLSX ou baixe a planilha modelo para preencher offline."
                    >
                      <Textarea
                        value={enrichmentUrls}
                        onChange={(e) => setEnrichmentUrls(e.target.value)}
                        placeholder={
                          "https://www.linkedin.com/in/joaosilva\nhttps://www.linkedin.com/in/mariaoliveira"
                        }
                        rows={5}
                      />
                    </Field>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => setCsvImportOpen(true)}
                      >
                        <FileSpreadsheet size={14} aria-hidden="true" />
                        Importar via CSV / XLSX
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={downloadEnrichmentTemplate}
                      >
                        <Download size={14} aria-hidden="true" />
                        Baixar planilha modelo
                      </Button>
                    </div>
                    <CsvXlsImportDialog
                      open={csvImportOpen}
                      onOpenChange={setCsvImportOpen}
                      onConfirm={(urls) =>
                        setEnrichmentUrls((prev) =>
                          [...new Set([...prev.split(/\n/).filter(Boolean), ...urls])].join("\n"),
                        )
                      }
                    />
                    <Field
                      label="Limite de resultados"
                      hint="Máximo de 100 por execução na API Unipile/LinkedIn. Acima disso aumenta o risco de rate-limit. Recomendamos até 50 por vez."
                    >
                      <input
                        value={enrichmentLimit}
                        onChange={(e) => setEnrichmentLimit(e.target.value)}
                        className={inputClassName}
                        placeholder="25"
                        title="Limite"
                        type="number"
                        min={1}
                        max={100}
                      />
                    </Field>

                    {/* Botão de fila automática — aparece quando há mais URLs que o limite */}
                    {splitLines(enrichmentUrls).length > Number(enrichmentLimit || 25) && (
                      <div className="rounded-md border border-blue-200 bg-blue-50 p-3 space-y-2">
                        <p className="text-xs text-blue-700 font-medium">
                          Você tem {splitLines(enrichmentUrls).length} URLs, mas o limite é{" "}
                          {enrichmentLimit}. Use a fila automática para processar tudo em batches.
                        </p>
                        <p className="text-xs text-blue-600">
                          Serão{" "}
                          {Math.ceil(
                            splitLines(enrichmentUrls).length / Number(enrichmentLimit || 25),
                          )}{" "}
                          batches processados automaticamente — um por hora — sem intervenção
                          manual.
                        </p>
                        <Button
                          type="button"
                          size="sm"
                          className="w-full"
                          onClick={handleCreateEnrichmentQueue}
                          disabled={createEnrichmentJob.isPending}
                        >
                          <Layers size={14} aria-hidden="true" />
                          Criar fila automática (
                          {Math.ceil(
                            splitLines(enrichmentUrls).length / Number(enrichmentLimit || 25),
                          )}{" "}
                          batches)
                        </Button>
                      </div>
                    )}

                    {/* Painel de jobs de enriquecimento existentes */}
                    {(enrichmentJobs.length > 0 || isLoadingJobs) && (
                      <div className="space-y-2 pt-1">
                        <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                          <Clock size={12} />
                          Filas de enriquecimento em andamento
                        </p>
                        {enrichmentJobs.map((job) => (
                          <EnrichmentJobCard
                            key={job.id}
                            job={job}
                            onDelete={(id) => deleteEnrichmentJob.mutate(id)}
                          />
                        ))}
                      </div>
                    )}
                  </>
                )}

                {source === "linkedin_search" && (
                  <>
                    <Field label="Keywords">
                      <input
                        value={linkedinKeywords}
                        onChange={(e) => setLinkedinKeywords(e.target.value)}
                        className={inputClassName}
                        placeholder="keyword principal"
                        title="Keywords"
                      />
                    </Field>
                    <Field label="Cargos">
                      <Textarea
                        value={linkedinTitles}
                        onChange={(e) => setLinkedinTitles(e.target.value)}
                      />
                    </Field>
                    <Field label="Empresas">
                      <Textarea
                        value={linkedinCompanies}
                        onChange={(e) => setLinkedinCompanies(e.target.value)}
                      />
                    </Field>
                    <Field label="Limite">
                      <input
                        value={linkedinLimit}
                        onChange={(e) => setLinkedinLimit(e.target.value)}
                        className={inputClassName}
                        placeholder="25"
                        title="Limite"
                      />
                    </Field>
                  </>
                )}
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <CardTitle>Preview</CardTitle>
                      <CardDescription>
                        {previewRows.length} resultados prontos para revisão e importação.
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="flex items-center gap-2 rounded-lg border border-(--border-default) bg-(--bg-overlay) px-3 py-2 text-xs text-(--text-secondary)">
                        <Checkbox
                          checked={mergeDuplicates}
                          onCheckedChange={(checked) => setMergeDuplicates(checked === true)}
                        />
                        Atualizar duplicados existentes
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 lg:grid-cols-[1fr_1fr_auto]">
                    <Field label="Lista existente">
                      <Select value={existingListId} onValueChange={setExistingListId}>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecionar lista" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Sem lista</SelectItem>
                          {(leadLists ?? []).map((list) => (
                            <SelectItem key={list.id} value={list.id}>
                              {list.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="Ou criar nova lista">
                      <input
                        value={newListName}
                        onChange={(e) => setNewListName(e.target.value)}
                        className={inputClassName}
                        placeholder="Ex.: SDRs SaaS Brasil"
                        title="Nova lista"
                      />
                    </Field>
                    <div className="flex items-end">
                      <Button
                        onClick={handleImport}
                        disabled={
                          selectedRows.length === 0 ||
                          importGeneratedLeads.isPending ||
                          importLinkedIn.isPending ||
                          createLeadList.isPending
                        }
                      >
                        <ArrowRight size={14} aria-hidden="true" />
                        Importar {selectedRows.length > 0 ? selectedRows.length : "selecionados"}
                      </Button>
                    </div>
                  </div>

                  {previewRows.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-(--border-default) bg-(--bg-overlay) p-8 text-center">
                      <p className="text-sm font-medium text-(--text-primary)">
                        Nenhum preview carregado
                      </p>
                      <p className="mt-2 text-sm text-(--text-secondary)">
                        Rode o preview da fonte selecionada para revisar os leads antes de salvar.
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto rounded-lg border border-(--border-default)">
                      <table className="w-full min-w-6xl text-sm">
                        <thead>
                          <tr className="border-b border-(--border-default) bg-(--bg-overlay)">
                            <th className="px-4 py-3 text-left">
                              <Checkbox
                                checked={allSelected}
                                onCheckedChange={(checked) =>
                                  setSelectedIds(
                                    checked === true ? previewRows.map((row) => row.id) : [],
                                  )
                                }
                              />
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                              Lead
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                              Empresa
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                              Contato
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                              Origem
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-(--border-subtle)">
                          {previewRows.map((row) => (
                            <tr key={row.id} className="hover:bg-(--bg-overlay)">
                              <td className="px-4 py-3 align-top">
                                <Checkbox
                                  checked={selectedIds.includes(row.id)}
                                  onCheckedChange={(checked) => {
                                    setSelectedIds((current) =>
                                      checked === true
                                        ? [...new Set([...current, row.id])]
                                        : current.filter((id) => id !== row.id),
                                    )
                                  }}
                                />
                              </td>
                              <td className="px-4 py-3">
                                <p className="font-medium text-(--text-primary)">{row.name}</p>
                                {row.linkedinUrl && (
                                  <a
                                    href={row.linkedinUrl}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="mt-1 inline-flex text-xs text-(--accent) hover:underline"
                                  >
                                    Abrir LinkedIn
                                  </a>
                                )}
                              </td>
                              <td className="px-4 py-3 text-(--text-secondary)">
                                <p>{row.company ?? "—"}</p>
                                {row.jobTitle && (
                                  <p className="mt-1 text-xs text-(--text-tertiary)">
                                    {row.jobTitle}
                                  </p>
                                )}
                                {row.location && (
                                  <p className="mt-1 text-xs text-(--text-tertiary)">
                                    {row.location}
                                  </p>
                                )}
                              </td>
                              <td className="px-4 py-3 text-(--text-secondary)">
                                <p>{row.email ?? "Sem email"}</p>
                                <p className="mt-1 text-xs text-(--text-tertiary)">
                                  {row.phone ?? "Sem telefone"}
                                </p>
                              </td>
                              <td className="px-4 py-3">
                                <span className="inline-flex rounded-(--radius-full) bg-(--bg-overlay) px-2 py-0.5 text-xs font-medium text-(--text-secondary)">
                                  {row.originLabel}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Fluxo sugerido</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 lg:grid-cols-3">
                  <FlowStep
                    icon={RefreshCw}
                    title="1. Rodar preview"
                    description="Teste a fonte com poucos resultados e ajuste os filtros."
                  />
                  <FlowStep
                    icon={CheckSquare}
                    title="2. Selecionar"
                    description="Revise só os leads que fazem sentido para a lista alvo."
                  />
                  <FlowStep
                    icon={ArrowRight}
                    title="3. Importar"
                    description="Salve em lista existente ou nova e siga para cadências."
                  />
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="automacoes" className="mt-4">
          {schedules.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CalendarClock className="mx-auto mb-3 opacity-40" size={32} />
                <p className="text-sm text-(--text-secondary)">
                  Nenhuma automação configurada ainda.
                </p>
                <p className="mt-1 text-xs text-(--text-tertiary)">
                  Vá para a aba &quot;Capturar&quot;, configure os filtros e clique em &quot;Salvar
                  como captura automática diária&quot;.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {schedules.map((cfg) => {
                const isGoogleMaps = cfg.source === "google_maps"
                const nextCombo = getNextCombo(cfg)
                return (
                  <Card key={cfg.id}>
                    <CardContent className="flex flex-wrap items-center gap-4 py-4">
                      <Badge variant={isGoogleMaps ? "default" : "neutral"}>
                        {isGoogleMaps ? "Google Maps" : "Base B2B"}
                      </Badge>
                      <Badge variant={cfg.is_active ? "default" : "outline"}>
                        {cfg.is_active ? "Ativa" : "Pausada"}
                      </Badge>
                      <div className="min-w-50 flex-1">
                        <p className="text-xs text-(--text-tertiary)">Próxima combo</p>
                        <p className="truncate text-sm font-medium">{nextCombo}</p>
                      </div>
                      <div className="min-w-35">
                        <p className="text-xs text-(--text-tertiary)">Última execução</p>
                        <p className="text-sm">
                          {cfg.last_run_at
                            ? new Date(cfg.last_run_at).toLocaleDateString("pt-BR")
                            : "Nunca"}
                        </p>
                      </div>
                      <div className="text-xs text-(--text-tertiary)">
                        {isGoogleMaps ? (
                          <span>
                            {cfg.maps_search_terms?.length ?? 0} termos ×{" "}
                            {(cfg.maps_locations?.length ?? 0) || 1} local(is)
                          </span>
                        ) : (
                          <span>
                            {cfg.b2b_cities?.length ?? 0} cidades ·{" "}
                            {cfg.b2b_job_titles?.length ?? 0} cargos
                          </span>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggleSchedule(cfg)}
                        disabled={toggleMaps.isPending || toggleB2B.isPending}
                      >
                        {cfg.is_active ? <Pause size={14} /> : <Play size={14} />}
                        {cfg.is_active ? "Pausar" : "Retomar"}
                      </Button>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-(--text-primary)">{label}</span>
      {hint && <p className="text-xs text-(--text-secondary)">{hint}</p>}
      {children}
    </label>
  )
}

function FlowStep({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof RefreshCw
  title: string
  description: string
}) {
  return (
    <div className="rounded-lg border border-(--border-default) bg-(--bg-overlay) p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-(--text-primary)">
        <Icon size={14} aria-hidden="true" className="text-(--accent)" />
        {title}
      </div>
      <p className="mt-2 text-sm text-(--text-secondary)">{description}</p>
    </div>
  )
}

function splitLines(value: string) {
  return value
    .split(/\r?\n|,|;/)
    .map((item) => item.trim())
    .filter(Boolean)
}

const inputClassName =
  "flex h-9 w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-2 text-sm text-(--text-primary) shadow-sm transition-colors placeholder:text-(--text-tertiary) focus:border-(--accent) focus:outline-none focus:ring-2 focus:ring-(--accent) focus:ring-offset-0"

// ── Componente de card de job ─────────────────────────────────────────

function EnrichmentJobCard({
  job,
  onDelete,
}: {
  job: EnrichmentJob
  onDelete: (id: string) => void
}) {
  const statusLabel: Record<EnrichmentJob["status"], string> = {
    pending: "Aguardando",
    running: "Processando...",
    done: "Concluído",
    failed: "Falhou",
  }
  const statusColor: Record<EnrichmentJob["status"], string> = {
    pending: "text-yellow-600 bg-yellow-50 border-yellow-200",
    running: "text-blue-600 bg-blue-50 border-blue-200",
    done: "text-green-600 bg-green-50 border-green-200",
    failed: "text-red-600 bg-red-50 border-red-200",
  }

  return (
    <div className="rounded-md border border-(--border-default) bg-(--bg-overlay) p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span
          className={`text-[11px] font-medium rounded px-1.5 py-0.5 border ${statusColor[job.status]}`}
        >
          {statusLabel[job.status]}
        </span>
        <span className="text-xs text-muted-foreground">
          {job.processed_count}/{job.total_count} perfis
        </span>
        {job.status !== "running" && (
          <button
            type="button"
            onClick={() => onDelete(job.id)}
            className="ml-auto text-muted-foreground hover:text-red-500 transition-colors"
            title="Remover job"
          >
            <X size={14} />
          </button>
        )}
      </div>
      {/* Barra de progresso */}
      <div className="h-1.5 rounded-full bg-(--border-default) overflow-hidden">
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{ width: `${job.progress_pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground">
        <span>{job.progress_pct}% concluído</span>
        {job.status !== "done" && (
          <span>
            {job.batches_remaining} batch{job.batches_remaining !== 1 ? "es" : ""} restante
            {job.batches_remaining !== 1 ? "s" : ""} (~{job.batches_remaining}h)
          </span>
        )}
        {job.target_list_id && <span className="truncate max-w-22.5">{job.target_list_id}</span>}
      </div>
      {job.error_message && (
        <p className="text-[11px] text-red-500 truncate" title={job.error_message}>
          {job.error_message}
        </p>
      )}
    </div>
  )
}
