"use client"

import { useState, useEffect, useMemo } from "react"
import { useTheme } from "next-themes"
import { createPortal } from "react-dom"
import dynamic from "next/dynamic"
import { format, parseISO } from "date-fns"
import {
  Sparkles,
  Save,
  Calendar,
  Send,
  Download,
  Upload,
  X,
  Wand2,
  Loader2,
  CheckCircle2,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  Moon,
  Sun,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

const NewsletterMarkdownEditor = dynamic(
  () =>
    import("@/components/content/newsletter-markdown-editor").then(
      (mod) => mod.NewsletterMarkdownEditor,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-120 items-center justify-center rounded-md border border-(--border-default) bg-(--bg-primary) text-sm text-(--text-tertiary)">
        Carregando editor...
      </div>
    ),
  },
)
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { useSession } from "next-auth/react"
import {
  useContentNewsletter,
  useUpdateNewsletter,
  useGenerateNewsletterDraft,
  useUploadNewsletterCover,
  useGenerateNewsletterCover,
  useScheduleNewsletter,
  useMarkNewsletterPublished,
  exportNewsletter,
} from "@/lib/api/hooks/use-content-newsletters"
import { useLLMModels } from "@/lib/api/hooks/use-llm-models"
import { useTenant, getTenantLLMConfig } from "@/lib/api/hooks/use-tenant"

interface Props {
  newsletterId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  gemini: "Gemini",
  anthropic: "Anthropic",
  openrouter: "OpenRouter",
}

export function EditNewsletterDialog({ newsletterId, open, onOpenChange }: Props) {
  const { data: session } = useSession()
  const { data: nl, isLoading } = useContentNewsletter(newsletterId)
  const updateMutation = useUpdateNewsletter()
  const generateMutation = useGenerateNewsletterDraft()
  const uploadCoverMutation = useUploadNewsletterCover()
  const generateCoverMutation = useGenerateNewsletterCover()
  const scheduleMutation = useScheduleNewsletter()
  const markPublishedMutation = useMarkNewsletterPublished()

  const { data: llmModels } = useLLMModels()
  const { data: tenant } = useTenant()
  const tenantLLM = useMemo(
    () => getTenantLLMConfig(tenant?.integration ?? null, "system"),
    [tenant?.integration],
  )

  const [title, setTitle] = useState("")
  const [scheduledFor, setScheduledFor] = useState("")
  const [payloadJson, setPayloadJson] = useState("")
  const [bodyMarkdown, setBodyMarkdown] = useState("")
  const [bodyHtml, setBodyHtml] = useState("")
  const [htmlView, setHtmlView] = useState<"source" | "preview">("source")
  const [copiedMd, setCopiedMd] = useState(false)
  const [copiedHtml, setCopiedHtml] = useState(false)
  const [provider, setProvider] = useState<string>(tenantLLM.llm_provider)
  const [model, setModel] = useState<string>(tenantLLM.llm_model)
  const [coverPrompt, setCoverPrompt] = useState("")
  const [pulseViews, setPulseViews] = useState<string>("")
  const [pulseReactions, setPulseReactions] = useState<string>("")
  const [pulseComments, setPulseComments] = useState<string>("")
  const [pulseReposts, setPulseReposts] = useState<string>("")

  // Estado tela cheia do editor Markdown
  const [mdFullscreen, setMdFullscreen] = useState(false)
  const { resolvedTheme } = useTheme()
  const colorMode = resolvedTheme === "dark" ? "dark" : "light"
  const [fullscreenEditorTheme, setFullscreenEditorTheme] = useState<"dark" | "light">("dark")

  useEffect(() => {
    if (mdFullscreen) setFullscreenEditorTheme(colorMode)
  }, [mdFullscreen, colorMode])

  // Fechar tela cheia com ESC
  useEffect(() => {
    if (!mdFullscreen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation()
        setMdFullscreen(false)
      }
    }
    document.addEventListener("keydown", handler, { capture: true })
    return () => document.removeEventListener("keydown", handler, { capture: true })
  }, [mdFullscreen])

  // Estados do form "Marcar como publicada"
  const [showPublishForm, setShowPublishForm] = useState(false)
  const [publishUrl, setPublishUrl] = useState("")
  const [publishDate, setPublishDate] = useState("")
  const [createDerived, setCreateDerived] = useState(true)

  // Sync provider/model with tenant defaults once tenant loads
  useEffect(() => {
    setProvider((curr) => (curr ? curr : tenantLLM.llm_provider))
    setModel((curr) => (curr ? curr : tenantLLM.llm_model))
  }, [tenantLLM.llm_provider, tenantLLM.llm_model])

  useEffect(() => {
    if (nl) {
      setTitle(nl.title)
      setScheduledFor(
        nl.scheduled_for ? format(parseISO(nl.scheduled_for), "yyyy-MM-dd'T'HH:mm") : "",
      )
      setPayloadJson(nl.sections_payload ? JSON.stringify(nl.sections_payload, null, 2) : "")
      setBodyMarkdown(nl.body_markdown ?? "")
      setBodyHtml(nl.body_html ?? "")
      setPulseViews(nl.pulse_views_count != null ? String(nl.pulse_views_count) : "")
      setPulseReactions(nl.pulse_reactions_count != null ? String(nl.pulse_reactions_count) : "")
      setPulseComments(nl.pulse_comments_count != null ? String(nl.pulse_comments_count) : "")
      setPulseReposts(nl.pulse_reposts_count != null ? String(nl.pulse_reposts_count) : "")
    }
  }, [nl])

  const providers = llmModels?.providers ?? []
  const modelsForProvider = llmModels?.byProvider?.[provider] ?? []

  if (!nl && isLoading) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Carregando...</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
  }

  if (!nl) return null

  // Remove markdown syntax tokens before counting words
  const stripMarkdown = (md: string) =>
    md
      .replace(/```[\s\S]*?```/g, (m) => m.replace(/[^\s]/g, "x")) // keep whitespace structure
      .replace(/`[^`]+`/g, (m) => m.replace(/[^\s]/g, "x"))
      .replace(/^#{1,6}\s/gm, "")
      .replace(/^[-*_]{3,}\s*$/gm, "")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/~~([^~]+)~~/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/^[>\-+*]\s/gm, "")
      .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")

  // Decode HTML entities + strip tags
  const stripHtml = (html: string) =>
    html
      .replace(/<[^>]+>/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&nbsp;/g, " ")

  const countWords = (text: string) =>
    text.trim() ? text.trim().split(/\s+/).filter(Boolean).length : 0

  const mdWordCount = countWords(stripMarkdown(bodyMarkdown))
  const htmlWordCount = countWords(stripHtml(bodyHtml))

  const copyText = async (text: string, setCopied: (v: boolean) => void) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSave = async () => {
    let sections_payload: Record<string, unknown> | null = null
    if (payloadJson.trim()) {
      try {
        sections_payload = JSON.parse(payloadJson) as Record<string, unknown>
      } catch {
        toast.error("JSON do payload inválido")
        return
      }
    }
    const toInt = (s: string) => (s.trim() === "" ? null : parseInt(s, 10))
    await updateMutation.mutateAsync({
      id: nl.id,
      data: {
        title,
        sections_payload,
        body_markdown: bodyMarkdown || null,
        body_html: bodyHtml || null,
        pulse_views_count: toInt(pulseViews),
        pulse_reactions_count: toInt(pulseReactions),
        pulse_comments_count: toInt(pulseComments),
        pulse_reposts_count: toInt(pulseReposts),
      },
    })
    toast.success("Newsletter salva")
  }

  const handleGenerate = async () => {
    await generateMutation.mutateAsync({
      id: nl.id,
      input: {
        provider,
        model,
        edition_number: nl.edition_number,
      },
    })
  }

  const handleUploadCover = async (file: File) => {
    await uploadCoverMutation.mutateAsync({ id: nl.id, file })
  }

  const handleGenerateCover = async () => {
    await generateCoverMutation.mutateAsync({
      id: nl.id,
      input: {
        prompt: coverPrompt.trim() || null,
        style: "clean",
        aspect_ratio: "16:9",
        image_size: "1K",
      },
    })
    setCoverPrompt("")
  }

  const handleSchedule = async () => {
    if (!scheduledFor) return
    const iso = new Date(scheduledFor).toISOString()
    await scheduleMutation.mutateAsync({ id: nl.id, scheduled_for: iso })
  }

  const handleMarkPublished = async () => {
    if (!publishUrl.trim() || publishUrl.trim().length < 8) {
      toast.error("Informe a URL do LinkedIn Pulse")
      return
    }
    const isoDate = publishDate ? new Date(publishDate).toISOString() : undefined
    await markPublishedMutation.mutateAsync({
      id: nl.id,
      linkedin_pulse_url: publishUrl.trim(),
      create_derived_article: createDerived,
      ...(isoDate ? { published_at: isoDate } : {}),
    })
    setShowPublishForm(false)
    onOpenChange(false)
  }

  const handleExport = async (fmt: "markdown" | "html") => {
    if (!session?.accessToken) return
    try {
      const content = await exportNewsletter(nl.id, fmt, session.accessToken)
      const blob = new Blob([content], {
        type: fmt === "html" ? "text/html" : "text/markdown",
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `newsletter-edicao-${nl.edition_number}.${fmt === "html" ? "html" : "md"}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro ao exportar")
    }
  }

  return (
    <>
      {/* Dialog só permanece montado enquanto a tela cheia não está ativa.
          Radix define pointer-events:none no body quando o dialog está aberto,
          o que bloquearia o portal da tela cheia. */}
      {!mdFullscreen && (
      <Dialog
        open={open}
        onOpenChange={onOpenChange}
      >
        <DialogContent
          className="max-h-[90vh] sm:max-w-225 overflow-y-auto"
        >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 pr-8">
            Edição #{nl.edition_number}
            <Badge variant="outline">{nl.status}</Badge>
            {nl.status === "published" && (
              <Badge variant="success" className="gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Publicada
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        {nl.status !== "published" && (
          <div className="border border-(--border-default) rounded-md mt-2 mb-2 bg-(--bg-tertiary) overflow-hidden">
            {!showPublishForm ? (
              <div className="flex items-center gap-2 px-3 py-2">
                <Send className="h-4 w-4 shrink-0 text-(--accent)" />
                <span className="text-sm flex-1 text-(--text-secondary)">
                  Após publicar no LinkedIn Pulse, marque aqui para criar o artigo derivado.
                </span>
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => {
                    setPublishUrl(nl.linkedin_pulse_url ?? "")
                    setPublishDate(format(new Date(), "yyyy-MM-dd'T'HH:mm"))
                    setShowPublishForm(true)
                  }}
                  className="gap-2 shrink-0"
                >
                  Marcar publicada
                </Button>
              </div>
            ) : (
              <div className="px-3 py-3 space-y-3">
                <div className="flex items-center gap-2">
                  <Send className="h-4 w-4 shrink-0 text-(--accent)" />
                  <span className="text-sm font-medium">Confirmar publicação</span>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">URL do LinkedIn Pulse <span className="text-red-500">*</span></Label>
                  <Input
                    value={publishUrl}
                    onChange={(e) => setPublishUrl(e.target.value)}
                    placeholder="https://www.linkedin.com/pulse/..."
                    className="text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Data de publicação</Label>
                  <Input
                    type="datetime-local"
                    value={publishDate}
                    onChange={(e) => setPublishDate(e.target.value)}
                    className="text-xs"
                  />
                  <p className="text-xs text-(--text-tertiary)">
                    Padrão: agora. Altere para registrar uma data passada.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="create-derived"
                    checked={createDerived}
                    onChange={(e) => setCreateDerived(e.target.checked)}
                    className="h-4 w-4 rounded border border-(--border-default)"
                  />
                  <label htmlFor="create-derived" className="text-xs text-(--text-secondary) cursor-pointer">
                    Criar artigo derivado automaticamente
                  </label>
                </div>
                <div className="flex gap-2 pt-1">
                  <Button
                    size="sm"
                    onClick={handleMarkPublished}
                    disabled={markPublishedMutation.isPending || !publishUrl.trim()}
                    className="gap-2"
                  >
                    {markPublishedMutation.isPending ? "Salvando..." : "Confirmar publicação"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowPublishForm(false)}
                  >
                    Cancelar
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="space-y-4">
          {/* Cover */}
          <div className="space-y-2">
            <Label>Capa</Label>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
              {nl.cover_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={nl.cover_image_url}
                  alt="capa"
                  className="h-32 w-56 shrink-0 rounded object-cover"
                />
              ) : (
                <div className="flex h-32 w-56 shrink-0 items-center justify-center rounded border border-dashed border-(--border-default) text-xs text-(--text-tertiary)">
                  Sem capa
                </div>
              )}
              <div className="flex-1 space-y-2">
                <div className="flex flex-wrap gap-2">
                  <label className="cursor-pointer">
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) void handleUploadCover(f)
                      }}
                    />
                    <span className="inline-flex items-center gap-2 rounded-md border border-(--border-default) px-3 py-1.5 text-sm hover:bg-(--bg-tertiary) cursor-pointer">
                      <Upload className="h-4 w-4" />
                      Subir capa
                    </span>
                  </label>
                  <Button
                    variant="outline"
                    onClick={handleGenerateCover}
                    disabled={generateCoverMutation.isPending}
                    className="gap-2 h-auto px-3 py-1.5 text-sm font-normal bg-(--accent) text-white hover:bg-(--accent-hover) disabled:bg-(--accent) disabled:opacity-70 disabled:hover:bg-(--accent) disabled:hover:cursor-not-allowed"
                  >
                    {generateCoverMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Wand2 className="h-4 w-4" />
                    )}
                    {generateCoverMutation.isPending ? "Gerando..." : "Gerar capa com IA"}
                  </Button>
                </div>
                <Input
                  value={coverPrompt}
                  onChange={(e) => setCoverPrompt(e.target.value)}
                  placeholder="Prompt da capa (opcional — usa título + tema se vazio)"
                  className="text-xs"
                />
                <p className="text-xs text-(--text-tertiary)">
                  Aspect ratio 16:9 — Gemini Nano Banana 2.
                </p>
              </div>
            </div>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label>Título</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>

          {/* Generation panel */}
          <div className="rounded-md border border-(--border-default) bg-(--bg-tertiary) p-3 space-y-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-(--accent)" />
              <span className="text-sm font-medium">Gerar com IA</span>
              <span className="ml-auto text-xs text-(--text-tertiary)">
                Padrão do sistema: {PROVIDER_LABELS[tenantLLM.llm_provider] ?? tenantLLM.llm_provider}{" "}
                / {tenantLLM.llm_model}
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1">
                <Label className="text-xs">Provider</Label>
                <Select value={provider} onValueChange={setProvider}>
                  <SelectTrigger>
                    <SelectValue placeholder="Provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((p) => (
                      <SelectItem key={p} value={p}>
                        {PROVIDER_LABELS[p] ?? p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Modelo</Label>
                <Select
                  value={model}
                  onValueChange={setModel}
                  disabled={modelsForProvider.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Modelo" />
                  </SelectTrigger>
                  <SelectContent>
                    {modelsForProvider.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button
              onClick={handleGenerate}
              disabled={generateMutation.isPending || !provider || !model}
              size="sm"
              className="gap-2"
            >
              <Sparkles className="h-4 w-4" />
              {generateMutation.isPending ? "Gerando..." : "Gerar rascunho completo"}
            </Button>
          </div>

          {/* Abas de conteúdo */}
          <div className="space-y-2">
            <Tabs defaultValue={nl.sections_payload ? "json" : "markdown"}>
              <TabsList className="w-full bg-(--accent) bg-opacity-5 rounded-md p-3 pt-1 pb-1">
                <TabsTrigger value="json" className="flex-1 text-white  hover:text-amber-200">Payload (JSON)</TabsTrigger>
                <TabsTrigger value="markdown" className="flex-1 text-white  hover:text-amber-200">Markdown</TabsTrigger>
                <TabsTrigger value="html" className="flex-1 text-white hover:text-amber-200">HTML</TabsTrigger>
              </TabsList>

              <TabsContent value="json" className="mt-2 space-y-1">
                <Textarea
                  value={payloadJson}
                  onChange={(e) => setPayloadJson(e.target.value)}
                  rows={20}
                  className="font-mono text-xs"
                  placeholder='{"section_tema_quinzena": {...}, "section_visao_opiniao": {...}, ...}'
                />
                <p className="text-xs text-(--text-tertiary)">
                  5 seções: tema_quinzena (45%), visao_opiniao (15%), mini_tutorial (15%), radar (15%),
                  pergunta_quinzena (10%). Total: 1.000–1.400 palavras.
                </p>
              </TabsContent>

              <TabsContent value="markdown" className="mt-2 space-y-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-(--accent)">{mdWordCount.toLocaleString("pt-BR")} palavras</span>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => void copyText(bodyMarkdown, setCopiedMd)}
                      className="flex items-center gap-1 text-xs text-(--accent) hover:text-(--text-primary) transition-colors"
                      title="Copiar Markdown"
                    >
                      {copiedMd ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                      {copiedMd ? "Copiado!" : "Copiar"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setMdFullscreen(true)}
                      className="flex items-center gap-1 text-xs text-(--text-secondary) hover:text-(--text-primary) transition-colors"
                      title="Abrir em tela cheia"
                    >
                      <Maximize2 className="h-3.5 w-3.5" />
                      Tela cheia
                    </button>
                  </div>
                </div>
                <NewsletterMarkdownEditor
                  value={bodyMarkdown}
                  onChange={setBodyMarkdown}
                  height={520}
                />
              </TabsContent>

              <TabsContent value="html" className="mt-2 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1 border border-(--border-default) rounded-md p-0.5">
                    <button
                      type="button"
                      onClick={() => setHtmlView("source")}
                      className={`px-3 py-1 text-xs rounded transition-colors ${htmlView === "source" ? "bg-(--bg-secondary) font-medium" : "text-(--text-tertiary) hover:text-(--text-primary)"}`}
                    >
                      Texto
                    </button>
                    <button
                      type="button"
                      onClick={() => setHtmlView("preview")}
                      className={`px-3 py-1 text-xs rounded transition-colors ${htmlView === "preview" ? "bg-(--bg-secondary) font-medium" : "text-(--text-tertiary) hover:text-(--text-primary)"}`}
                    >
                      Visualizar
                    </button>
                  </div>
                  <span className="text-sm text-(--accent)">{htmlWordCount.toLocaleString("pt-BR")} palavras</span>
                  <button
                    type="button"
                    onClick={() => void copyText(bodyHtml, setCopiedHtml)}
                    className="flex items-center gap-1 pr-3 text-xs text-(--accent) hover:text-(--text-primary) transition-colors"
                    title="Copiar HTML"
                  >
                    {copiedHtml ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                    {copiedHtml ? "Copiado!" : "Copiar"}
                  </button>
                </div>
                {htmlView === "source" ? (
                  <Textarea
                    value={bodyHtml}
                    onChange={(e) => setBodyHtml(e.target.value)}
                    rows={20}
                    className="font-mono text-xs"
                    placeholder="Conteúdo em HTML..."
                  />
                ) : (
                  <div
                    className="min-h-120 rounded-md border border-(--border-default) bg-(--bg-primary) p-4 overflow-y-auto text-sm leading-relaxed [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mt-6 [&_h1]:mb-2 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mt-5 [&_h2]:mb-2 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-1 [&_p]:mb-3 [&_p]:leading-relaxed [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-3 [&_li]:mb-1.5 [&_strong]:font-semibold [&_em]:italic [&_a]:underline [&_a]:decoration-1 [&_hr]:my-4 [&_hr]:border-(--border-default) [&_blockquote]:border-l-4 [&_blockquote]:border-(--border-default) [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-(--text-secondary) [&_blockquote]:my-3 [&_code]:bg-(--bg-tertiary) [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_code]:font-mono [&_pre]:bg-(--bg-tertiary) [&_pre]:rounded [&_pre]:p-3 [&_pre]:overflow-x-auto [&_pre]:my-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0"
                    dangerouslySetInnerHTML={{ __html: bodyHtml || "<p><em>Nenhum conteúdo</em></p>" }}
                  />
                )}
              </TabsContent>
            </Tabs>
          </div>

          {/* Schedule */}
          <div className="space-y-2">
            <Label>Agendar publicação</Label>
            <div className="flex items-center gap-2">
              <Input
                type="datetime-local"
                value={scheduledFor}
                onChange={(e) => setScheduledFor(e.target.value)}
              />
              <Button
                onClick={handleSchedule}
                disabled={!scheduledFor || scheduleMutation.isPending}
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <Calendar className="h-4 w-4" />
                Agendar
              </Button>
            </div>
          </div>

          {/* Metrics */}
          <div className="rounded-md border border-(--border-default) bg-(--bg-tertiary) p-3 space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Métricas do Pulse</span>
              <span className="text-xs text-(--text-tertiary)">inserção manual — LinkedIn Analytics</span>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="space-y-1">
                <Label className="text-xs">Visualizações</Label>
                <Input
                  type="number"
                  min={0}
                  value={pulseViews}
                  onChange={(e) => setPulseViews(e.target.value)}
                  placeholder="—"
                  className="text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Reações</Label>
                <Input
                  type="number"
                  min={0}
                  value={pulseReactions}
                  onChange={(e) => setPulseReactions(e.target.value)}
                  placeholder="—"
                  className="text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Comentários</Label>
                <Input
                  type="number"
                  min={0}
                  value={pulseComments}
                  onChange={(e) => setPulseComments(e.target.value)}
                  placeholder="—"
                  className="text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Reshares</Label>
                <Input
                  type="number"
                  min={0}
                  value={pulseReposts}
                  onChange={(e) => setPulseReposts(e.target.value)}
                  placeholder="—"
                  className="text-xs"
                />
              </div>
            </div>
            <p className="text-xs text-(--text-tertiary)">
              Cole os números do painel Analytics do LinkedIn Campaign Manager após a publicação.
              Salvos junto com os demais campos ao clicar em &ldquo;Salvar&rdquo;.
            </p>
          </div>

          {/* Export row */}
          <div className="flex flex-wrap gap-2 border-t border-(--border-default) pt-3">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleExport("markdown")}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Markdown
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleExport("html")}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              HTML
            </Button>
          </div>
        </div>

        <DialogFooter className="mt-4 border-t border-(--border-default) pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="gap-2">
            <X className="h-4 w-4" />
            Fechar
          </Button>
          <Button onClick={handleSave} disabled={updateMutation.isPending} className="gap-2">
            <Save className="h-4 w-4" />
            {updateMutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    )}

    {/* Fullscreen editor — renderizado via portal fora do Dialog para escapar do transform */}
    {mdFullscreen && typeof document !== "undefined" && createPortal(
      <div
        className="newsletter-mdx-fullscreen fixed inset-0 flex flex-col"
        style={{ zIndex: 2147483647, pointerEvents: "auto" }}
        data-color-mode={fullscreenEditorTheme}
        data-editor-theme={fullscreenEditorTheme}
      >
        {/* Barra superior */}
        <div className="newsletter-mdx-fullscreen-toolbar flex items-center gap-3 px-4 py-2 shrink-0">
          <span className="text-sm font-medium">
            Edição #{nl.edition_number} — Editor Markdown
          </span>
          <span className="ml-auto text-sm text-(--accent)">
            {mdWordCount.toLocaleString("pt-BR")} palavras
          </span>
          <button
            type="button"
            onClick={() => void copyText(bodyMarkdown, setCopiedMd)}
            className="newsletter-mdx-fullscreen-action flex items-center gap-1 text-xs transition-colors"
            title="Copiar Markdown"
          >
            {copiedMd ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
            {copiedMd ? "Copiado!" : "Copiar"}
          </button>
          <button
            type="button"
            onClick={() => setFullscreenEditorTheme((theme) => (theme === "dark" ? "light" : "dark"))}
            className="newsletter-mdx-fullscreen-button flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            title="Alternar tema do editor em tela cheia"
          >
            {fullscreenEditorTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {fullscreenEditorTheme === "dark" ? "Tema claro" : "Tema escuro"}
          </button>
          <button
            type="button"
            onClick={() => setMdFullscreen(false)}
            className="newsletter-mdx-fullscreen-button flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
          >
            <Minimize2 className="h-4 w-4" />
            Fechar tela cheia
          </button>
        </div>
        {/* Editor ocupa o restante da tela */}
        <div className="flex-1 overflow-hidden">
          <NewsletterMarkdownEditor
            value={bodyMarkdown}
            onChange={setBodyMarkdown}
            height="100%"
            fullscreen
            editorTheme={fullscreenEditorTheme}
          />
        </div>
      </div>,
      document.body
    )}
    </>
  )
}
