"use client"

import { useEffect, useState } from "react"
import { Sparkles, Check, Wand2, RefreshCw, ChevronDown } from "lucide-react"
import { localDateToUTC } from "@/lib/date"
import {
  useCreateContentPost,
  useImprovePost,
  useGeneratePost,
  useContentThemes,
  useMarkThemeUsed,
  useApprovePost,
  useSchedulePost,
  type HookType,
  type PostPillar,
} from "@/lib/api/hooks/use-content"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const PILLAR_OPTIONS: { value: PostPillar; label: string }[] = [
  { value: "authority", label: "Autoridade" },
  { value: "case", label: "Caso" },
  { value: "vision", label: "Visão" },
]

const HOOK_OPTIONS: { value: HookType; label: string }[] = [
  { value: "loop_open", label: "Loop aberto" },
  { value: "contrarian", label: "Contrário" },
  { value: "identification", label: "Identificação" },
  { value: "shortcut", label: "Atalho" },
  { value: "benefit", label: "Benefício" },
  { value: "data", label: "Dado" },
]

interface CreatePostDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultPublishDate?: string | undefined
}

export function CreatePostDialog({
  open,
  onOpenChange,
  defaultPublishDate,
}: CreatePostDialogProps) {
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [pillar, setPillar] = useState<PostPillar>("authority")
  const [hookType, setHookType] = useState<HookType | "none">("none")
  const [hashtags, setHashtags] = useState("")
  const [publishDate, setPublishDate] = useState("")
  const [weekNumber, setWeekNumber] = useState("")
  const [improveOpen, setImproveOpen] = useState(false)
  const [instruction, setInstruction] = useState("")
  const [generateOpen, setGenerateOpen] = useState(false)
  const [selectedThemeId, setSelectedThemeId] = useState<string | null>(null)
  const [freeTheme, setFreeTheme] = useState("")
  const [themeSource, setThemeSource] = useState<"bank" | "free">("bank")

  useEffect(() => {
    if (defaultPublishDate) setPublishDate(defaultPublishDate)
  }, [defaultPublishDate])

  const createPost = useCreateContentPost()
  const improvePost = useImprovePost()
  const generatePost = useGeneratePost()
  const markThemeUsed = useMarkThemeUsed()
  const approvePost = useApprovePost()
  const schedulePost = useSchedulePost()
  const { data: availableThemes } = useContentThemes({ used: false })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const createdPost = await createPost.mutateAsync({
      title,
      body,
      pillar,
      hook_type: hookType === "none" ? null : hookType,
      hashtags: hashtags || null,
      character_count: body.length,
      publish_date: publishDate ? localDateToUTC(publishDate) : null,
      week_number: weekNumber ? parseInt(weekNumber, 10) : null,
    })
    // Auto-approve + schedule when date is provided
    if (publishDate) {
      try {
        await approvePost.mutateAsync(createdPost.id)
        await schedulePost.mutateAsync(createdPost.id)
      } catch {
        // post created as draft, user can schedule manually
      }
    }
    if (selectedThemeId) {
      try {
        await markThemeUsed.mutateAsync({ themeId: selectedThemeId, postId: createdPost.id })
      } catch {
        // tema não marcado como usado, não bloqueia criação
      }
    }
    onOpenChange(false)
    resetForm()
  }

  function resetForm() {
    setTitle("")
    setBody("")
    setPillar("authority")
    setHookType("none")
    setHashtags("")
    setPublishDate("")
    setWeekNumber("")
    setImproveOpen(false)
    setInstruction("")
    setGenerateOpen(false)
    setSelectedThemeId(null)
    setFreeTheme("")
    setThemeSource("bank")
  }

  async function handleGenerate() {
    const themeText =
      themeSource === "bank"
        ? (availableThemes?.find((t) => t.id === selectedThemeId)?.title ?? "")
        : freeTheme
    if (!themeText.trim()) return
    const selectedTheme =
      themeSource === "bank" ? availableThemes?.find((t) => t.id === selectedThemeId) : null
    const genPillar = selectedTheme ? selectedTheme.pillar : pillar
    const res = await generatePost.mutateAsync({
      theme: themeText,
      pillar: genPillar,
      variations: 1,
      temperature: 0.8,
    })
    const variation = res.variations[0]
    if (variation) {
      setBody(variation.text)
      if (variation.hook_type_used && variation.hook_type_used !== "auto") {
        setHookType(variation.hook_type_used as HookType)
      }
      if (selectedTheme) {
        setPillar(selectedTheme.pillar)
      }
      if (!title.trim()) {
        setTitle(themeText.slice(0, 80))
      }
    }
    setGenerateOpen(false)
  }

  async function handleImprove() {
    if (!instruction.trim()) return
    const result = await improvePost.mutateAsync({ body, instruction })
    setBody(result.text)
    setImproveOpen(false)
    setInstruction("")
  }

  const charCount = body.length
  const isOverLimit = charCount > 3000
  const isTooShort = charCount > 0 && charCount < 900

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Novo post</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="title">Título interno</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Semana 5 · Tema principal"
              required
            />
          </div>

          {/* Gerar com IA — seção colapsável */}
          <div className="grid gap-1.5">
            <button
              type="button"
              onClick={() => setGenerateOpen((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-medium text-(--accent) hover:text-(--accent)/80 transition-colors w-fit"
            >
              <Wand2 className="h-3.5 w-3.5" />
              Gerar texto com IA
              <ChevronDown
                className={`h-3 w-3 transition-transform ${generateOpen ? "rotate-180" : ""}`}
              />
            </button>

            {generateOpen && (
              <div className="flex flex-col gap-3 rounded-md border border-(--accent)/30 bg-(--accent)/5 p-3">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setThemeSource("bank")}
                    className={`text-xs px-2 py-1 rounded-md transition-colors ${themeSource === "bank" ? "bg-(--accent) text-white" : "text-(--text-secondary) hover:bg-(--bg-overlay)"}`}
                  >
                    Banco de temas
                  </button>
                  <button
                    type="button"
                    onClick={() => setThemeSource("free")}
                    className={`text-xs px-2 py-1 rounded-md transition-colors ${themeSource === "free" ? "bg-(--accent) text-white" : "text-(--text-secondary) hover:bg-(--bg-overlay)"}`}
                  >
                    Tema livre
                  </button>
                </div>

                {themeSource === "bank" ? (
                  <Select
                    value={selectedThemeId ?? ""}
                    onValueChange={(v) => setSelectedThemeId(v || null)}
                  >
                    <SelectTrigger className="text-xs">
                      <SelectValue placeholder="Selecione um tema do banco…" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableThemes?.map((t) => (
                        <SelectItem key={t.id} value={t.id} className="text-xs">
                          <span className="flex items-center gap-2">
                            <span
                              className={`inline-block h-2 w-2 rounded-full ${t.pillar === "authority" ? "bg-blue-500" : t.pillar === "case" ? "bg-emerald-500" : "bg-purple-500"}`}
                            />
                            {t.title}
                          </span>
                        </SelectItem>
                      ))}
                      {(!availableThemes || availableThemes.length === 0) && (
                        <SelectItem
                          value="_empty"
                          disabled
                          className="text-xs text-(--text-tertiary)"
                        >
                          Nenhum tema disponível
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                ) : (
                  <Textarea
                    value={freeTheme}
                    onChange={(e) => setFreeTheme(e.target.value)}
                    placeholder="Descreva o tema do post… Ex: Como reduzir tempo de onboarding sem contratar"
                    rows={2}
                    className="resize-none text-xs"
                  />
                )}

                <div className="flex items-center gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setGenerateOpen(false)
                      setSelectedThemeId(null)
                      setFreeTheme("")
                    }}
                    className="text-xs text-(--text-tertiary) hover:text-(--text-secondary)"
                  >
                    Cancelar
                  </button>
                  <Button
                    type="button"
                    size="sm"
                    className="h-7 text-xs gap-1"
                    onClick={handleGenerate}
                    disabled={
                      generatePost.isPending ||
                      (themeSource === "bank" ? !selectedThemeId : !freeTheme.trim())
                    }
                  >
                    {generatePost.isPending ? (
                      <>
                        <RefreshCw className="h-3 w-3 animate-spin" />
                        Gerando…
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3 w-3" />
                        Gerar
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="grid gap-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label htmlFor="body">Texto do post</Label>
                <button
                  type="button"
                  onClick={() => setImproveOpen((v) => !v)}
                  className="flex items-center gap-1 text-xs text-(--accent) hover:text-(--accent)/80 transition-colors"
                >
                  <Sparkles className="h-3 w-3" />
                  Melhorar com IA
                </button>
              </div>
              <span
                className={`text-xs ${
                  isOverLimit
                    ? "text-(--danger) font-medium"
                    : isTooShort
                      ? "text-amber-600 dark:text-amber-400"
                      : "text-(--text-tertiary)"
                }`}
              >
                {charCount} / 3.000
                {isTooShort && " · abaixo do ideal (900–1500)"}
              </span>
            </div>
            {improveOpen && (
              <div className="flex flex-col gap-2 rounded-md border border-(--accent)/30 bg-(--accent)/5 p-3">
                <p className="text-xs text-(--text-secondary)">Instrução para a IA:</p>
                <Textarea
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  placeholder="Ex: Reduza para 1000 caracteres mantendo o gancho"
                  rows={2}
                  className="resize-none text-xs"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                      void handleImprove()
                    }
                  }}
                />
                <div className="flex items-center gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setImproveOpen(false)
                      setInstruction("")
                    }}
                    className="text-xs text-(--text-tertiary) hover:text-(--text-secondary)"
                  >
                    Cancelar
                  </button>
                  <Button
                    type="button"
                    size="sm"
                    className="h-7 text-xs gap-1"
                    onClick={handleImprove}
                    disabled={!instruction.trim() || improvePost.isPending}
                  >
                    {improvePost.isPending ? (
                      <>
                        <span className="animate-spin inline-block h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                        Melhorando…
                      </>
                    ) : (
                      <>
                        <Check className="h-3 w-3" />
                        Aplicar
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
            <Textarea
              id="body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Escreva o conteúdo do post..."
              rows={8}
              required
              className="resize-none font-mono text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Pilar</Label>
              <Select value={pillar} onValueChange={(v) => setPillar(v as PostPillar)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PILLAR_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1.5">
              <Label>Tipo de gancho</Label>
              <Select value={hookType} onValueChange={(v) => setHookType(v as HookType | "none")}>
                <SelectTrigger>
                  <SelectValue placeholder="Nenhum" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Nenhum</SelectItem>
                  {HOOK_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="publish_date">Data de publicação</Label>
              <Input
                id="publish_date"
                type="datetime-local"
                value={publishDate}
                onChange={(e) => setPublishDate(e.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="week_number">Semana</Label>
              <Input
                id="week_number"
                type="number"
                min={1}
                max={54}
                value={weekNumber}
                onChange={(e) => setWeekNumber(e.target.value)}
                placeholder="1–54"
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="hashtags">Hashtags</Label>
            <Input
              id="hashtags"
              value={hashtags}
              onChange={(e) => setHashtags(e.target.value)}
              placeholder="#ia #processos #automacao"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createPost.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={createPost.isPending}>
              {createPost.isPending ? "Criando…" : "Criar post"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
