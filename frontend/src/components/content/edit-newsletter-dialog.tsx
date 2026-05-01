"use client"

import { useState, useEffect } from "react"
import { format, parseISO } from "date-fns"
import { Sparkles, Save, Calendar, Send, Download, Upload, X } from "lucide-react"
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
import { toast } from "sonner"
import { useSession } from "next-auth/react"
import {
  useContentNewsletter,
  useUpdateNewsletter,
  useGenerateNewsletterDraft,
  useUploadNewsletterCover,
  useScheduleNewsletter,
  useMarkNewsletterPublished,
  exportNewsletter,
  type NewsletterFullPayload,
} from "@/lib/api/hooks/use-content-newsletters"

interface Props {
  newsletterId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EditNewsletterDialog({ newsletterId, open, onOpenChange }: Props) {
  const { data: session } = useSession()
  const { data: nl, isLoading } = useContentNewsletter(newsletterId)
  const updateMutation = useUpdateNewsletter()
  const generateMutation = useGenerateNewsletterDraft()
  const uploadCoverMutation = useUploadNewsletterCover()
  const scheduleMutation = useScheduleNewsletter()
  const markPublishedMutation = useMarkNewsletterPublished()

  const [title, setTitle] = useState("")
  const [centralTheme, setCentralTheme] = useState("")
  const [scheduledFor, setScheduledFor] = useState("")
  const [payloadJson, setPayloadJson] = useState("")
  const [provider, setProvider] = useState("gemini")
  const [model, setModel] = useState("gemini-2.5-pro")

  useEffect(() => {
    if (nl) {
      setTitle(nl.title)
      setCentralTheme(nl.central_theme ?? "")
      setScheduledFor(
        nl.scheduled_for ? format(parseISO(nl.scheduled_for), "yyyy-MM-dd'T'HH:mm") : "",
      )
      setPayloadJson(nl.payload ? JSON.stringify(nl.payload, null, 2) : "")
    }
  }, [nl])

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

  const handleSave = async () => {
    let payload: NewsletterFullPayload | null = null
    if (payloadJson.trim()) {
      try {
        payload = JSON.parse(payloadJson) as NewsletterFullPayload
      } catch {
        toast.error("JSON do payload inválido")
        return
      }
    }
    await updateMutation.mutateAsync({
      id: nl.id,
      data: {
        title,
        central_theme: centralTheme || null,
        payload,
      },
    })
    toast.success("Newsletter salva")
  }

  const handleGenerate = async () => {
    await generateMutation.mutateAsync({
      id: nl.id,
      input: {
        central_theme: centralTheme || null,
        provider,
        model,
        edition_number: nl.edition_number,
      },
    })
  }

  const handleUploadCover = async (file: File) => {
    await uploadCoverMutation.mutateAsync({ id: nl.id, file })
  }

  const handleSchedule = async () => {
    if (!scheduledFor) return
    const iso = new Date(scheduledFor).toISOString()
    await scheduleMutation.mutateAsync({ id: nl.id, scheduled_for: iso })
  }

  const handleMarkPublished = async () => {
    if (!confirm("Marcar como publicada e criar artigo derivado?")) return
    await markPublishedMutation.mutateAsync({
      id: nl.id,
      create_article: true,
    })
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] sm:max-w-225 overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Edição #{nl.edition_number}
            <Badge variant="outline">{nl.status}</Badge>
            {nl.word_count != null && <Badge variant="neutral">{nl.word_count} palavras</Badge>}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Cover */}
          <div className="space-y-2">
            <Label>Capa</Label>
            <div className="flex items-center gap-3">
              {nl.cover_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={nl.cover_url} alt="capa" className="h-24 w-40 rounded object-cover" />
              ) : (
                <div className="flex h-24 w-40 items-center justify-center rounded border border-dashed border-(--border-default) text-xs text-(--text-tertiary)">
                  Sem capa
                </div>
              )}
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
                <span className="inline-flex items-center gap-2 rounded-md border border-(--border-default) px-3 py-1.5 text-sm hover:bg-(--bg-tertiary)">
                  <Upload className="h-4 w-4" />
                  Subir capa
                </span>
              </label>
            </div>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label>Título</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>

          {/* Central theme */}
          <div className="space-y-2">
            <Label>Tema central</Label>
            <Textarea
              value={centralTheme}
              onChange={(e) => setCentralTheme(e.target.value)}
              rows={2}
            />
          </div>

          {/* Generation panel */}
          <div className="rounded-md border border-(--border-default) bg-(--bg-tertiary) p-3 space-y-2">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-(--accent)" />
              <span className="text-sm font-medium">Gerar com IA</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="Provider (gemini/openai)"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              />
              <Input
                placeholder="Model (gemini-2.5-pro)"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              />
            </div>
            <Button
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
              size="sm"
              className="gap-2"
            >
              <Sparkles className="h-4 w-4" />
              {generateMutation.isPending ? "Gerando..." : "Gerar rascunho completo"}
            </Button>
            {nl.generation_violations && nl.generation_violations.length > 0 && (
              <div className="text-xs text-(--destructive)">
                <p className="font-medium">Violações detectadas:</p>
                <ul className="ml-4 list-disc">
                  {nl.generation_violations.map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Payload editor (JSON) */}
          <div className="space-y-2">
            <Label>Payload completo (JSON)</Label>
            <Textarea
              value={payloadJson}
              onChange={(e) => setPayloadJson(e.target.value)}
              rows={20}
              className="font-mono text-xs"
              placeholder='{"tema_quinzena": {...}, "visao_opiniao": {...}, ...}'
            />
            <p className="text-xs text-(--text-tertiary)">
              5 seções: tema_quinzena (45%), visao_opiniao (15%), mini_tutorial (15%), radar (15%),
              pergunta_quinzena (10%). Total: 1.000–1.400 palavras.
            </p>
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

          {/* Actions row */}
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
            <div className="flex-1" />
            {nl.status !== "published" && (
              <Button size="sm" variant="default" onClick={handleMarkPublished} className="gap-2">
                <Send className="h-4 w-4" />
                Marcar publicada + criar artigo
              </Button>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            <X className="h-4 w-4" />
            Fechar
          </Button>
          <Button onClick={handleSave} disabled={updateMutation.isPending} className="gap-2">
            <Save className="h-4 w-4" />
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
