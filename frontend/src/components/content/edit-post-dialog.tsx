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
  Maximize2,
} from "lucide-react"
import { format } from "date-fns"
import { toZonedTime } from "date-fns-tz"
import { localDateToUTC } from "@/lib/date"
import {
  useUpdatePost,
  useImprovePost,
  useDetectHookType,
  useApprovePost,
  useSchedulePost,
  useCancelSchedule,
  usePublishNow,
  useDeletePost,
  useGeneratePostImage,
  useDeletePostImage,
  useUploadPostImage,
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

const DAY_NAMES: Record<number, string> = {
  0: "Domingo", 1: "Segunda", 2: "Terça", 3: "Quarta", 4: "Quinta", 5: "Sexta", 6: "Sábado",
}
const DAY_COLORS: Record<number, string> = {
  0: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
  1: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  2: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  3: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  4: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  5: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
  6: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
}

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
  const [imageMode, setImageMode] = useState<"generate" | "upload">("generate")
  const [imageStyle, setImageStyle] = useState<ImageStyle>("clean")
  const [imageSubType, setImageSubType] = useState<ImageSubType>("metrics")
  const [imageAspect, setImageAspect] = useState<ImageAspectRatio>("4:5")
  const [customPrompt, setCustomPrompt] = useState("")
  const [localImage, setLocalImage] = useState<{ url: string; prompt: string } | null>(null)
  const [localUploadedImage, setLocalUploadedImage] = useState<{
    url: string
    name: string
    sizeMB: string
  } | null>(null)
  const [imageDeleted, setImageDeleted] = useState(false)
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const imageUploadInputRef = useRef<HTMLInputElement>(null)

  // Vídeo
  const [videoOpen, setVideoOpen] = useState(false)
  const videoInputRef = useRef<HTMLInputElement>(null)
  const [localVideoUrl, setLocalVideoUrl] = useState<string | null>(null)
  const [localVideoName, setLocalVideoName] = useState<string | null>(null)
  const [localVideoSizeMB, setLocalVideoSizeMB] = useState<string | null>(null)
  const [videoLightboxOpen, setVideoLightboxOpen] = useState(false)
  const [localVideoDeleted, setLocalVideoDeleted] = useState(false)

  const updatePost = useUpdatePost()
  const improvePost = useImprovePost()
  const detectHook = useDetectHookType()
  const approvePost = useApprovePost()
  const schedulePost = useSchedulePost()
  const cancelSchedulePost = useCancelSchedule()
  const publishNowPost = usePublishNow()
  const deletePostMut = useDeletePost()
  const generateImage = useGeneratePostImage()
  const deleteImage = useDeletePostImage()
  const uploadImage = useUploadPostImage()
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
    const result = await generateImage.mutateAsync({
      post_id: post.id,
      style: imageStyle,
      aspect_ratio: imageAspect,
      sub_type: imageStyle === "infographic" ? imageSubType : null,
      custom_prompt: customPrompt || null,
    })
    setImageDeleted(false)
    setLocalImage({
      url: `/api/backend/api/content/posts/${post.id}/image?t=${Date.now()}`,
      prompt: result.image_prompt,
    })
    setLocalUploadedImage(null)
    setCustomPrompt("")
  }

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!post || !e.target.files?.[0]) return
    const file = e.target.files[0]
    const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      alert("Formato inválido. Aceitos: JPG, PNG, WEBP, GIF.")
      if (imageUploadInputRef.current) imageUploadInputRef.current.value = ""
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      alert("A imagem excede o limite de 10 MB.")
      if (imageUploadInputRef.current) imageUploadInputRef.current.value = ""
      return
    }
    const objectUrl = URL.createObjectURL(file)
    try {
      await uploadImage.mutateAsync({ postId: post.id, file })
      setLocalUploadedImage({
        url: objectUrl,
        name: file.name,
        sizeMB: (file.size / 1024 / 1024).toFixed(1),
      })
      setLocalImage(null)
      setImageDeleted(false)
    } catch {
      URL.revokeObjectURL(objectUrl)
    }
    if (imageUploadInputRef.current) imageUploadInputRef.current.value = ""
  }

  async function handleVideoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!post || !e.target.files?.[0]) return
    const file = e.target.files[0]

    if (file.size > 150 * 1024 * 1024) {
      alert("O arquivo excede o limite de 150 MB.")
      if (videoInputRef.current) videoInputRef.current.value = ""
      return
    }

    const objectUrl = URL.createObjectURL(file)
    try {
      await uploadVideo.mutateAsync({ postId: post.id, file })
      setLocalVideoUrl(objectUrl)
      setLocalVideoName(file.name)
      setLocalVideoSizeMB((file.size / 1024 / 1024).toFixed(1))
    } catch {
      URL.revokeObjectURL(objectUrl)
    }
    if (videoInputRef.current) videoInputRef.current.value = ""
  }

  // Libera o blob URL do vídeo local quando trocar (evitar memory leak)
  useEffect(() => {
    return () => {
      if (localVideoUrl?.startsWith("blob:")) URL.revokeObjectURL(localVideoUrl)
    }
  }, [localVideoUrl])

  // Libera o blob URL da imagem local quando trocar (evitar memory leak)
  useEffect(() => {
    return () => {
      if (localUploadedImage?.url?.startsWith("blob:")) URL.revokeObjectURL(localUploadedImage.url)
    }
  }, [localUploadedImage])

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
    setLocalImage(null)
    setLocalUploadedImage(null)
    setImageDeleted(false)
    setLocalVideoDeleted(false)
  }, [post, defaultImproveOpen])

  // Auto-calcula semana do mês quando a data de publicação muda
  useEffect(() => {
    if (!publishDate) return
    try {
      const d = new Date(publishDate)
      // Semana do mês: ceil(dia / 7), máximo 5
      const weekOfMonth = Math.ceil(d.getDate() / 7)
      setWeekNumber(String(weekOfMonth))
    } catch {
      // data inválida, ignora
    }
  }, [publishDate])

  // Reseta estado local de vídeo apenas quando abre dialog para um post diferente (não em cada refetch)
  const prevPostIdRef = useRef<string | null>(null)
  useEffect(() => {
    if (!post) return
    if (prevPostIdRef.current !== post.id) {
      setLocalVideoUrl(null)
      setLocalVideoName(null)
      setLocalVideoSizeMB(null)
      setLocalVideoDeleted(false)
      prevPostIdRef.current = post.id
    }
  }, [post])

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
    <>
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
                <div className="flex items-center justify-between">
                  <Label>Tipo de gancho</Label>
                  <button
                    type="button"
                    onClick={async () => {
                      if (!body.trim()) return
                      const res = await detectHook.mutateAsync(body)
                      setHookType(res.hook_type as HookType)
                    }}
                    disabled={detectHook.isPending || !body.trim()}
                    className="flex items-center gap-1 text-xs text-(--accent) hover:text-(--accent)/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {detectHook.isPending ? (
                      <span className="animate-spin inline-block h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                    ) : (
                      <Sparkles className="h-3 w-3" />
                    )}
                    Detectar com IA
                  </button>
                </div>
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
                <div className="flex items-center gap-2">
                  <Label htmlFor="edit-publish-date">Data de publicação</Label>
                  {publishDate && (
                    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold leading-none ${DAY_COLORS[new Date(publishDate).getDay()]}`}>
                      {DAY_NAMES[new Date(publishDate).getDay()]}
                    </span>
                  )}
                </div>
                <Input
                  id="edit-publish-date"
                  type="datetime-local"
                  value={publishDate}
                  onChange={(e) => setPublishDate(e.target.value)}
                />
              </div>

              <div className="grid gap-1.5">
                <Label htmlFor="edit-week">Semana do mês</Label>
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
                  {!imageDeleted && (localImage || localUploadedImage || post?.image_url) && (
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
                  {!imageDeleted && (localImage || localUploadedImage || post?.image_url) ? (
                    /* Preview da imagem (gerada por IA ou upload) */
                    <div className="flex flex-col gap-2">
                      <button
                        type="button"
                        className="w-full cursor-zoom-in"
                        onClick={() => setLightboxOpen(true)}
                        title="Ampliar imagem"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={
                            localImage?.url ??
                            localUploadedImage?.url ??
                            (post?.image_s3_key
                              ? `/api/backend/api/content/posts/${post?.id}/image`
                              : undefined)
                          }
                          alt="Imagem do post"
                          className="w-full max-h-64 rounded object-contain bg-(--bg-subtle) hover:opacity-90 transition-opacity"
                        />
                      </button>

                      {/* Info: prompt (IA) ou nome/tamanho (upload) */}
                      {(localImage?.prompt ?? (post?.image_prompt && !post?.image_filename)) && (
                        <p
                          className="text-xs text-(--text-tertiary) truncate"
                          title={localImage?.prompt ?? post?.image_prompt ?? ""}
                        >
                          Prompt: {localImage?.prompt ?? post?.image_prompt}
                        </p>
                      )}
                      {(localUploadedImage || post?.image_filename) && (
                        <div className="flex items-center gap-1.5 text-xs text-(--text-tertiary)">
                          <ImageIcon className="h-3 w-3 shrink-0" />
                          <span className="truncate">
                            {localUploadedImage?.name ?? post?.image_filename ?? "imagem"}
                          </span>
                          {(localUploadedImage?.sizeMB ??
                            (post?.image_size_bytes
                              ? (post.image_size_bytes / 1024 / 1024).toFixed(1)
                              : null)) && (
                            <span className="text-(--text-quaternary) shrink-0">
                              {localUploadedImage?.sizeMB ??
                                (post?.image_size_bytes
                                  ? (post.image_size_bytes / 1024 / 1024).toFixed(1)
                                  : "")}
                              {" MB"}
                            </span>
                          )}
                        </div>
                      )}

                      <div className="flex gap-2">
                        {/* Regenerar — apenas para imagens geradas por IA */}
                        {(localImage || (!localUploadedImage && post?.image_prompt)) && (
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
                        )}
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs gap-1 text-(--danger) hover:text-(--danger)"
                          disabled={deleteImage.isPending}
                          onClick={() => {
                            if (post) {
                              deleteImage.mutate(post.id)
                              setLocalImage(null)
                              setLocalUploadedImage(null)
                              setImageDeleted(true)
                            }
                          }}
                        >
                          <X className="h-3 w-3" />
                          Excluir
                        </Button>
                      </div>
                    </div>
                  ) : (
                    /* Modo de adição: tabs Gerar com IA / Upload */
                    <div className="flex flex-col gap-3">
                      {/* Tabs de modo */}
                      <div className="flex gap-1 rounded-md border border-(--border-subtle) p-0.5 w-fit">
                        <button
                          type="button"
                          onClick={() => setImageMode("generate")}
                          className={`rounded px-3 py-1 text-xs transition-colors ${
                            imageMode === "generate"
                              ? "bg-(--accent) text-white"
                              : "text-(--text-secondary) hover:text-(--text-primary)"
                          }`}
                        >
                          <span className="flex items-center gap-1">
                            <Sparkles className="h-3 w-3" />
                            Gerar com IA
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setImageMode("upload")}
                          className={`rounded px-3 py-1 text-xs transition-colors ${
                            imageMode === "upload"
                              ? "bg-(--accent) text-white"
                              : "text-(--text-secondary) hover:text-(--text-primary)"
                          }`}
                        >
                          <span className="flex items-center gap-1">
                            <Upload className="h-3 w-3" />
                            Upload
                          </span>
                        </button>
                      </div>

                      {imageMode === "generate" ? (
                        /* Formulário de geração por IA */
                        <>
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
                        </>
                      ) : (
                        /* Upload manual */
                        <div className="flex flex-col gap-2">
                          <p className="text-xs text-(--text-secondary)">
                            Selecione um arquivo JPG, PNG, WEBP ou GIF (máx. 10 MB).
                          </p>
                          <div className="flex items-center gap-2">
                            <input
                              ref={imageUploadInputRef}
                              type="file"
                              accept="image/jpeg,image/png,image/webp,image/gif"
                              className="hidden"
                              aria-label="Selecionar imagem para upload"
                              onChange={handleImageUpload}
                            />
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="h-8 text-xs gap-1.5"
                              disabled={uploadImage.isPending}
                              onClick={() => imageUploadInputRef.current?.click()}
                            >
                              {uploadImage.isPending ? (
                                <>
                                  <span className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                                  Enviando…
                                </>
                              ) : (
                                <>
                                  <Upload className="h-3 w-3" />
                                  Selecionar arquivo
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      )}
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
                  {!localVideoDeleted && (localVideoUrl || post?.video_url) && (
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
                  {!localVideoDeleted && (localVideoUrl || post?.video_url) ? (
                    <div className="flex flex-col gap-2">
                      {/* Mini player 16:9 com botão ampliar */}
                      <div className="relative w-full aspect-video">
                        <video
                          src={
                            localVideoUrl ??
                            (post?.video_s3_key
                              ? `/api/backend/api/content/posts/${post.id}/video`
                              : undefined)
                          }
                          controls
                          preload="metadata"
                          className="absolute inset-0 w-full h-full rounded-md bg-black object-contain"
                        />
                        <button
                          type="button"
                          title="Ampliar vídeo"
                          className="absolute top-2 right-2 z-10 rounded-full bg-black/50 p-1.5 text-white hover:bg-black/75 transition-colors"
                          onClick={() => setVideoLightboxOpen(true)}
                        >
                          <Maximize2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      {/* Info row */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 text-sm text-(--text-secondary) min-w-0">
                          <VideoIcon className="h-4 w-4 shrink-0" />
                          <span className="truncate">
                            {localVideoName ?? post?.video_filename ?? "video.mp4"}
                          </span>
                          {(localVideoSizeMB ??
                            (post?.video_size_bytes
                              ? (post.video_size_bytes / 1024 / 1024).toFixed(1)
                              : null)) && (
                            <span className="shrink-0 text-xs text-(--text-tertiary)">
                              {localVideoSizeMB ??
                                (post?.video_size_bytes
                                  ? (post.video_size_bytes / 1024 / 1024).toFixed(1)
                                  : null)}{" "}
                              MB
                            </span>
                          )}
                          {post?.linkedin_video_urn && (
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
                          onClick={() => {
                            if (post) deleteVideo.mutate(post.id)
                            setLocalVideoDeleted(true)
                            setLocalVideoUrl(null)
                            setLocalVideoName(null)
                            setLocalVideoSizeMB(null)
                          }}
                        >
                          <X className="h-3 w-3" />
                          Remover
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2">
                      <p className="text-xs text-(--text-secondary)">
                        Selecione um arquivo MP4 (máx. 150 MB).
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

      {/* ── Lightbox de imagem ── */}
      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent className="max-w-4xl w-full p-2 bg-black/90 border-0 [&>button]:text-white [&>button]:opacity-100 [&>button]:bg-white/20 [&>button]:rounded-full [&>button]:p-1 [&>button]:hover:bg-white/40">
          <DialogHeader className="sr-only">
            <DialogTitle>Imagem do post</DialogTitle>
          </DialogHeader>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={
              localImage?.url ??
              localUploadedImage?.url ??
              (post?.image_s3_key ? `/api/backend/api/content/posts/${post?.id}/image` : undefined)
            }
            alt="Imagem do post"
            className="w-full max-h-[85vh] object-contain rounded"
          />
        </DialogContent>
      </Dialog>

      {/* ── Lightbox de vídeo ── */}
      <Dialog open={videoLightboxOpen} onOpenChange={setVideoLightboxOpen}>
        <DialogContent className="max-w-5xl w-full p-2 bg-black/90 border-0 [&>button]:text-white [&>button]:opacity-100 [&>button]:bg-white/20 [&>button]:rounded-full [&>button]:p-1 [&>button]:hover:bg-white/40">
          <DialogHeader className="sr-only">
            <DialogTitle>Vídeo do post</DialogTitle>
          </DialogHeader>
          <div className="w-full aspect-video">
            <video
              src={
                localVideoUrl ??
                (post?.video_s3_key
                  ? `/api/backend/api/content/posts/${post?.id}/video`
                  : undefined)
              }
              controls
              autoPlay
              className="w-full h-full rounded object-contain bg-black"
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
