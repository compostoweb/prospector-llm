"use client"

import { useEffect, useRef, useState } from "react"
import {
  AlertTriangle,
  Sparkles,
  Check,
  Clock,
  Send,
  XCircle,
  Trash2,
  ImageIcon,
  VideoIcon,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  X,
  Upload,
} from "lucide-react"
import { format } from "date-fns"
import { toZonedTime } from "date-fns-tz"
import { localDateToUTC } from "@/lib/date"
import {
  useUpdatePost,
  useImprovePost,
  useApprovePost,
  useSchedulePost,
  useCancelSchedule,
  usePublishNow,
  useDeletePost,
  useGeneratePostImage,
  useDeletePostImage,
  useUploadPostVideo,
  useDeletePostVideo,
  type ContentPost,
  type PostPillar,
  type HookType,
  type ImageStyle,
  type ImageSubType,
  type ImageAspectRatio,
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

interface EditPostDialogProps {
  post: ContentPost | null
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultImproveOpen?: boolean
}

export function EditPostDialog({
  post,
  open,
  onOpenChange,
  defaultImproveOpen,
}: EditPostDialogProps) {
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [pillar, setPillar] = useState<PostPillar>("authority")
  const [hookType, setHookType] = useState<HookType | "none">("none")
  const [hashtags, setHashtags] = useState("")
  const [publishDate, setPublishDate] = useState("")
  const [weekNumber, setWeekNumber] = useState("")
  const [syncWarning, setSyncWarning] = useState<string | null>(null)
  const [improveOpen, setImproveOpen] = useState(false)
  const [instruction, setInstruction] = useState("")

  // Imagem
  const [imageOpen, setImageOpen] = useState(false)
  const [imageStyle, setImageStyle] = useState<ImageStyle>("clean")
  const [imageSubType, setImageSubType] = useState<ImageSubType>("metrics")
  const [imageAspect, setImageAspect] = useState<ImageAspectRatio>("4:5")
  const [customPrompt, setCustomPrompt] = useState("")

  // Vídeo
  const [videoOpen, setVideoOpen] = useState(false)
  const videoInputRef = useRef<HTMLInputElement>(null)

  const updatePost = useUpdatePost()
  const improvePost = useImprovePost()
  const approvePost = useApprovePost()
  const schedulePost = useSchedulePost()
  const cancelSchedulePost = useCancelSchedule()
  const publishNowPost = usePublishNow()
  const deletePostMut = useDeletePost()
  const generateImage = useGeneratePostImage()
  const deleteImage = useDeletePostImage()
  const uploadVideo = useUploadPostVideo()
  const deleteVideo = useDeletePostVideo()

  const isActionPending =
    approvePost.isPending ||
    schedulePost.isPending ||
    cancelSchedulePost.isPending ||
    publishNowPost.isPending ||
    deletePostMut.isPending

  async function handleGenerateImage() {
    if (!post) return
    await generateImage.mutateAsync({
      post_id: post.id,
      style: imageStyle,
      aspect_ratio: imageAspect,
      sub_type: imageStyle === "infographic" ? imageSubType : null,
      custom_prompt: customPrompt || null,
    })
    setCustomPrompt("")
  }

  async function handleVideoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!post || !e.target.files?.[0]) return
    await uploadVideo.mutateAsync({ postId: post.id, file: e.target.files[0] })
    if (videoInputRef.current) videoInputRef.current.value = ""
  }

  // Preencher form quando o post mudar
  useEffect(() => {
    if (!post) return
    setTitle(post.title)
    setBody(post.body)
    setPillar(post.pillar)
    setHookType(post.hook_type ?? "none")
    setHashtags(post.hashtags ?? "")
    setPublishDate(
      post.publish_date
        ? format(toZonedTime(post.publish_date, "America/Sao_Paulo"), "yyyy-MM-dd'T'HH:mm")
        : "",
    )
    setWeekNumber(post.week_number ? String(post.week_number) : "")
    setSyncWarning(null)
    setImproveOpen(defaultImproveOpen ?? false)
    setInstruction("")
  }, [post, defaultImproveOpen])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!post) return
    const result = await updatePost.mutateAsync({
      postId: post.id,
      data: {
        title,
        body,
        pillar,
        hook_type: hookType === "none" ? null : hookType,
        hashtags: hashtags || null,
        character_count: body.length,
        publish_date: publishDate ? localDateToUTC(publishDate) : null,
        week_number: weekNumber ? parseInt(weekNumber, 10) : null,
      },
    })
    if (result.linkedin_sync_warning) {
      setSyncWarning(result.linkedin_sync_warning)
    } else {
      onOpenChange(false)
    }
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
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar post</DialogTitle>
        </DialogHeader>

        {syncWarning && (
          <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{syncWarning}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-2">
          <div className="grid gap-1.5">
            <Label htmlFor="edit-title">Título</Label>
            <Input
              id="edit-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Título interno do post"
              required
            />
          </div>

          <div className="grid gap-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label htmlFor="edit-body">Conteúdo</Label>
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
                {charCount} / 3000
                {isTooShort && " · abaixo do ideal (900–1500)"}
              </span>
            </div>
            {improveOpen && (
              <div className="flex flex-col gap-2 rounded-md border border-(--accent)/30 bg-(--accent)/5 p-3">
                <p className="text-xs text-(--text-secondary)">
                  Instrução para a IA (ex: &quot;torne mais conciso&quot;, &quot;adicione um
                  dado&quot;):
                </p>
                <Textarea
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  placeholder="Ex: Reduza para 1000 caracteres mantendo o gancho"
                  rows={2}
                  className="resize-none text-xs"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleImprove()
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
              id="edit-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={10}
              className="resize-none text-sm"
              required
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
                  <SelectValue />
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
              <Label htmlFor="edit-publish-date">Data de publicação</Label>
              <Input
                id="edit-publish-date"
                type="datetime-local"
                value={publishDate}
                onChange={(e) => setPublishDate(e.target.value)}
              />
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="edit-week">Semana</Label>
              <Input
                id="edit-week"
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
            <Label htmlFor="edit-hashtags">Hashtags</Label>
            <Input
              id="edit-hashtags"
              value={hashtags}
              onChange={(e) => setHashtags(e.target.value)}
              placeholder="#marketing #automacao"
            />
          </div>

          {/* ── Seção de imagem ── */}
          <div className="rounded-md border border-(--border-subtle)">
            <button
              type="button"
              className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
              onClick={() => setImageOpen((v) => !v)}
            >
              <span className="flex items-center gap-2">
                <ImageIcon className="h-4 w-4 text-(--text-secondary)" />
                Imagem
                {post?.image_url && (
                  <span className="rounded-full bg-(--accent)/15 px-1.5 py-0.5 text-xs text-(--accent)">
                    Adicionada
                  </span>
                )}
              </span>
              {imageOpen ? (
                <ChevronUp className="h-4 w-4 text-(--text-tertiary)" />
              ) : (
                <ChevronDown className="h-4 w-4 text-(--text-tertiary)" />
              )}
            </button>

            {imageOpen && (
              <div className="border-t border-(--border-subtle) p-3 flex flex-col gap-3">
                {post?.image_url ? (
                  /* Preview da imagem gerada */
                  <div className="flex flex-col gap-2">
                    <img
                      src={post.image_url}
                      alt="Imagem do post"
                      className="w-full max-h-64 rounded object-contain bg-(--bg-subtle)"
                    />
                    {post.image_prompt && (
                      <p
                        className="text-xs text-(--text-tertiary) truncate"
                        title={post.image_prompt}
                      >
                        Prompt: {post.image_prompt}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        disabled={generateImage.isPending}
                        onClick={handleGenerateImage}
                      >
                        {generateImage.isPending ? (
                          <span className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                        ) : (
                          <RefreshCw className="h-3 w-3" />
                        )}
                        Regenerar
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs gap-1 text-(--danger) hover:text-(--danger)"
                        disabled={deleteImage.isPending}
                        onClick={() => post && deleteImage.mutate(post.id)}
                      >
                        <X className="h-3 w-3" />
                        Excluir
                      </Button>
                    </div>
                  </div>
                ) : (
                  /* Configuração para gerar nova imagem */
                  <div className="flex flex-col gap-3">
                    {/* Estilo */}
                    <div className="grid gap-1.5">
                      <Label className="text-xs">Estilo</Label>
                      <div className="flex gap-2 flex-wrap">
                        {(["clean", "with_text", "infographic"] as ImageStyle[]).map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => setImageStyle(s)}
                            className={`rounded px-2.5 py-1 text-xs border transition-colors ${
                              imageStyle === s
                                ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                                : "border-(--border-subtle) text-(--text-secondary) hover:border-(--accent)/50"
                            }`}
                          >
                            {s === "clean"
                              ? "Limpo"
                              : s === "with_text"
                                ? "Com texto"
                                : "Infográfico"}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Sub-tipo (apenas para infográfico) */}
                    {imageStyle === "infographic" && (
                      <div className="grid gap-1.5">
                        <Label className="text-xs">Tipo de infográfico</Label>
                        <div className="flex gap-2 flex-wrap">
                          {(["metrics", "steps", "comparison"] as ImageSubType[]).map((s) => (
                            <button
                              key={s}
                              type="button"
                              onClick={() => setImageSubType(s)}
                              className={`rounded px-2.5 py-1 text-xs border transition-colors ${
                                imageSubType === s
                                  ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                                  : "border-(--border-subtle) text-(--text-secondary) hover:border-(--accent)/50"
                              }`}
                            >
                              {s === "metrics"
                                ? "Métricas"
                                : s === "steps"
                                  ? "Passos"
                                  : "Comparativo"}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Proporção */}
                    <div className="grid gap-1.5">
                      <Label className="text-xs">Proporção</Label>
                      <div className="flex gap-2">
                        {(["4:5", "1:1", "16:9"] as ImageAspectRatio[]).map((r) => (
                          <button
                            key={r}
                            type="button"
                            onClick={() => setImageAspect(r)}
                            className={`rounded px-2.5 py-1 text-xs border transition-colors ${
                              imageAspect === r
                                ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                                : "border-(--border-subtle) text-(--text-secondary) hover:border-(--accent)/50"
                            }`}
                          >
                            {r}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Prompt personalizado (opcional) */}
                    <div className="grid gap-1.5">
                      <Label className="text-xs text-(--text-secondary)">
                        Instrução adicional{" "}
                        <span className="text-(--text-tertiary)">(opcional)</span>
                      </Label>
                      <Input
                        value={customPrompt}
                        onChange={(e) => setCustomPrompt(e.target.value)}
                        placeholder="Ex: use tons de verde e inclua gráfico de barras"
                        className="text-xs h-8"
                      />
                    </div>

                    <Button
                      type="button"
                      size="sm"
                      className="self-start h-8 text-xs gap-1.5"
                      disabled={generateImage.isPending}
                      onClick={handleGenerateImage}
                    >
                      {generateImage.isPending ? (
                        <>
                          <span className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                          Gerando…
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3 w-3" />
                          Gerar imagem
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ── Seção de vídeo ── */}
          <div className="rounded-md border border-(--border-subtle)">
            <button
              type="button"
              className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
              onClick={() => setVideoOpen((v) => !v)}
            >
              <span className="flex items-center gap-2">
                <VideoIcon className="h-4 w-4 text-(--text-secondary)" />
                Vídeo
                {post?.video_url && (
                  <span className="rounded-full bg-(--accent)/15 px-1.5 py-0.5 text-xs text-(--accent)">
                    Adicionado
                  </span>
                )}
              </span>
              {videoOpen ? (
                <ChevronUp className="h-4 w-4 text-(--text-tertiary)" />
              ) : (
                <ChevronDown className="h-4 w-4 text-(--text-tertiary)" />
              )}
            </button>

            {videoOpen && (
              <div className="border-t border-(--border-subtle) p-3 flex flex-col gap-3">
                {post?.video_url ? (
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm text-(--text-secondary) truncate">
                      <VideoIcon className="h-4 w-4 shrink-0" />
                      <span className="truncate">
                        {post.video_s3_key?.split("/").pop() ?? "video.mp4"}
                      </span>
                      {post.linkedin_video_urn && (
                        <span className="shrink-0 rounded-full bg-green-100 px-1.5 py-0.5 text-xs text-green-700 dark:bg-green-900 dark:text-green-300">
                          Processado
                        </span>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs gap-1 text-(--danger) hover:text-(--danger) shrink-0"
                      disabled={deleteVideo.isPending}
                      onClick={() => post && deleteVideo.mutate(post.id)}
                    >
                      <X className="h-3 w-3" />
                      Remover
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <p className="text-xs text-(--text-secondary)">
                      Selecione um arquivo MP4 (máx. 500 MB).
                    </p>
                    <div className="flex items-center gap-2">
                      <input
                        ref={videoInputRef}
                        type="file"
                        accept="video/mp4"
                        aria-label="Selecionar arquivo de vídeo MP4"
                        className="hidden"
                        id="video-upload-input"
                        onChange={handleVideoUpload}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs gap-1.5"
                        disabled={uploadVideo.isPending}
                        onClick={() => videoInputRef.current?.click()}
                      >
                        {uploadVideo.isPending ? (
                          <>
                            <span className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                            Enviando…
                          </>
                        ) : (
                          <>
                            <Upload className="h-3 w-3" />
                            Selecionar MP4
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter className="flex flex-col gap-3 sm:flex-col">
            {/* Status actions */}
            {post &&
              (post.status === "draft" ||
                post.status === "approved" ||
                post.status === "scheduled") && (
                <div className="flex items-center gap-2 flex-wrap border-b border-(--border-subtle) pb-3">
                  {post.status === "draft" && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1"
                      disabled={isActionPending}
                      onClick={async () => {
                        await approvePost.mutateAsync(post.id)
                        onOpenChange(false)
                      }}
                    >
                      <Check className="h-3 w-3" />
                      Aprovar
                    </Button>
                  )}
                  {post.status === "approved" && (
                    <>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        disabled={isActionPending || !publishDate}
                        title={
                          !publishDate ? "Defina uma data de publicação para agendar" : undefined
                        }
                        onClick={async () => {
                          // Salva data primeiro se mudou, depois agenda
                          if (publishDate !== (post.publish_date?.slice(0, 16) ?? "")) {
                            await updatePost.mutateAsync({
                              postId: post.id,
                              data: { publish_date: publishDate || null },
                            })
                          }
                          await schedulePost.mutateAsync(post.id)
                          onOpenChange(false)
                        }}
                      >
                        <Clock className="h-3 w-3" />
                        Agendar
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        disabled={isActionPending}
                        onClick={async () => {
                          await publishNowPost.mutateAsync(post.id)
                          onOpenChange(false)
                        }}
                      >
                        <Send className="h-3 w-3" />
                        Publicar agora
                      </Button>
                    </>
                  )}
                  {post.status === "scheduled" && (
                    <>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        disabled={isActionPending}
                        onClick={async () => {
                          await cancelSchedulePost.mutateAsync(post.id)
                          onOpenChange(false)
                        }}
                      >
                        <XCircle className="h-3 w-3" />
                        Cancelar agendamento
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        disabled={isActionPending}
                        onClick={async () => {
                          await publishNowPost.mutateAsync(post.id)
                          onOpenChange(false)
                        }}
                      >
                        <Send className="h-3 w-3" />
                        Publicar agora
                      </Button>
                    </>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs gap-1 text-(--danger) hover:text-(--danger) ml-auto"
                    disabled={isActionPending}
                    onClick={async () => {
                      await deletePostMut.mutateAsync(post.id)
                      onOpenChange(false)
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                    Excluir
                  </Button>
                </div>
              )}

            {/* Save / Cancel */}
            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSyncWarning(null)
                  onOpenChange(false)
                }}
              >
                {syncWarning ? "Fechar" : "Cancelar"}
              </Button>
              {!syncWarning && (
                <Button type="submit" disabled={updatePost.isPending || isOverLimit}>
                  {updatePost.isPending ? "Salvando…" : "Salvar alterações"}
                </Button>
              )}
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
