"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import {
  ArrowRight,
  CheckSquare,
  Linkedin,
  MailSearch,
  MapPinned,
  RefreshCw,
  Sparkles,
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
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"

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
  const [source, setSource] = useState<LeadGeneratorSource>("google_maps")
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [existingListId, setExistingListId] = useState<string>("none")
  const [newListName, setNewListName] = useState("")
  const [mergeDuplicates, setMergeDuplicates] = useState(true)

  const [mapsSearchTerms, setMapsSearchTerms] = useState("clínicas odontológicas\ncontabilidades")
  const [mapsLocation, setMapsLocation] = useState("São Paulo, Brasil")
  const [mapsCategories, setMapsCategories] = useState("clínica odontológica\nconsultoria")
  const [mapsLimit, setMapsLimit] = useState("25")

  const [b2bTitles, setB2bTitles] = useState("Head de Marketing\nDiretor Comercial")
  const [b2bLocations, setB2bLocations] = useState("Brasil")
  const [b2bCities, setB2bCities] = useState("São Paulo\nCuritiba")
  const [b2bIndustries, setB2bIndustries] = useState("software\nmarketing & advertising")
  const [b2bKeywords, setB2bKeywords] = useState("B2B\nSaaS")
  const [b2bSizes, setB2bSizes] = useState("11-20\n21-50\n51-100")
  const [b2bLimit, setB2bLimit] = useState("50")

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-(--accent)">
            Prospecção assistida
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-(--text-primary)">Gerar leads</h1>
          <p className="mt-2 max-w-3xl text-sm text-(--text-secondary)">
            Rode captura, enriquecimento e revisão no mesmo fluxo antes de salvar em uma lista
            operacional.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
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

      <div className="grid gap-4 xl:grid-cols-4">
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
                <Field label="Termos de busca">
                  <Textarea
                    value={mapsSearchTerms}
                    onChange={(e) => setMapsSearchTerms(e.target.value)}
                  />
                </Field>
                <Field label="Localização">
                  <input
                    value={mapsLocation}
                    onChange={(e) => setMapsLocation(e.target.value)}
                    className={inputClassName}
                    placeholder="Cidade, estado ou país"
                    title="Localização"
                  />
                </Field>
                <Field label="Categorias">
                  <Textarea
                    value={mapsCategories}
                    onChange={(e) => setMapsCategories(e.target.value)}
                  />
                </Field>
                <Field label="Limite">
                  <input
                    value={mapsLimit}
                    onChange={(e) => setMapsLimit(e.target.value)}
                    className={inputClassName}
                    placeholder="25"
                    title="Limite"
                  />
                </Field>
              </>
            )}

            {source === "b2b_database" && (
              <>
                <Field label="Cargos alvo">
                  <Textarea value={b2bTitles} onChange={(e) => setB2bTitles(e.target.value)} />
                </Field>
                <Field label="Localizações">
                  <Textarea
                    value={b2bLocations}
                    onChange={(e) => setB2bLocations(e.target.value)}
                  />
                </Field>
                <Field label="Cidades">
                  <Textarea value={b2bCities} onChange={(e) => setB2bCities(e.target.value)} />
                </Field>
                <Field label="Indústrias">
                  <Textarea
                    value={b2bIndustries}
                    onChange={(e) => setB2bIndustries(e.target.value)}
                  />
                </Field>
                <Field label="Keywords de empresa">
                  <Textarea value={b2bKeywords} onChange={(e) => setB2bKeywords(e.target.value)} />
                </Field>
                <Field label="Faixas de tamanho">
                  <Textarea value={b2bSizes} onChange={(e) => setB2bSizes(e.target.value)} />
                </Field>
                <Field label="Limite">
                  <input
                    value={b2bLimit}
                    onChange={(e) => setB2bLimit(e.target.value)}
                    className={inputClassName}
                    placeholder="50"
                    title="Limite"
                  />
                </Field>
              </>
            )}

            {source === "linkedin_enrichment" && (
              <>
                <Field label="URLs do LinkedIn">
                  <Textarea
                    value={enrichmentUrls}
                    onChange={(e) => setEnrichmentUrls(e.target.value)}
                    placeholder="https://www.linkedin.com/in/..."
                  />
                </Field>
                <Field label="Limite">
                  <input
                    value={enrichmentLimit}
                    onChange={(e) => setEnrichmentLimit(e.target.value)}
                    className={inputClassName}
                    placeholder="25"
                    title="Limite"
                  />
                </Field>
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
                              <p className="mt-1 text-xs text-(--text-tertiary)">{row.jobTitle}</p>
                            )}
                            {row.location && (
                              <p className="mt-1 text-xs text-(--text-tertiary)">{row.location}</p>
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
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-(--text-primary)">{label}</span>
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
