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
  Layers,
  MessageSquare,
  VideoIcon,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  X,
  Upload,
  Maximize2,
  Download,
  History,
  RotateCcw,
} from "lucide-react"
import {
  getDayOfMonthFromLocalDateTime,
  isFutureLocalDateTime,
  localDateToUTC,
  utcToLocalDateTimeInputValue,
} from "@/lib/date"
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
  useRetryFirstComment,
  usePostRevisions,
  useRestoreRevision,
  type ContentPost,
  type PostPillar,
  type HookType,
  type ImageStyle,
  type ImageSubType,
  type ImageAspectRatio,
  type ImageVisualDirection,
  type CarouselImageItem,
} from "@/lib/api/hooks/use-content"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { CarouselEditor, CAROUSEL_MIN_IMAGES } from "@/components/content/carousel-editor"
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
import {
  getPostImageProxyUrl,
  resolvePostImageUrl,
  resolvePostVideoUrl,
} from "@/lib/content/post-media"
import { downloadMediaFile, getDownloadBaseName } from "@/lib/content/media-download"
import { buildGeneratedTitle, extractGeneratedPostParts } from "@/lib/content/generated-post"

const DAY_NAMES: Record<number, string> = {
  0: "Domingo",
  1: "Segunda",
  2: "Terça",
  3: "Quarta",
  4: "Quinta",
  5: "Sexta",
  6: "Sábado",
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
  const [firstCommentText, setFirstCommentText] = useState("")
  const [firstCommentOpen, setFirstCommentOpen] = useState(false)
  const [revisionsOpen, setRevisionsOpen] = useState(false)
  const [syncWarning, setSyncWarning] = useState<string | null>(null)
  const [improveOpen, setImproveOpen] = useState(false)
  const [instruction, setInstruction] = useState("")
  const [showCloseConfirm, setShowCloseConfirm] = useState(false)

  // Imagem
  const [imageOpen, setImageOpen] = useState(false)
  const [imageMode, setImageMode] = useState<"generate" | "upload">("generate")
  const [imageStyle, setImageStyle] = useState<ImageStyle>("clean")
  const [imageSubType, setImageSubType] = useState<ImageSubType>("metrics")
  const [imageAspect, setImageAspect] = useState<ImageAspectRatio>("4:5")
  const [imageVisualDirection, setImageVisualDirection] = useState<ImageVisualDirection>("auto")
  const [customPrompt, setCustomPrompt] = useState("")
  const [localImage, setLocalImage] = useState<{ url: string; prompt: string } | null>(null)
  const [localUploadedImage, setLocalUploadedImage] = useState<{
    url: string
    name: string
    sizeMB: string
  } | null>(null)
  const [imageDeleted, setImageDeleted] = useState(false)
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [downloadImageDialogOpen, setDownloadImageDialogOpen] = useState(false)
  const [downloadImageName, setDownloadImageName] = useState("")
  const [isDownloadingImage, setIsDownloadingImage] = useState(false)
  const imageUploadInputRef = useRef<HTMLInputElement>(null)

  // Carrossel
  const [carouselOpen, setCarouselOpen] = useState(false)

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
  const retryFirstComment = useRetryFirstComment()
  const revisionsQuery = usePostRevisions(revisionsOpen && post ? post.id : null)
  const restoreRevision = useRestoreRevision()

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
      visual_direction: imageVisualDirection,
      custom_prompt: customPrompt || null,
    })
    setImageDeleted(false)
    setLocalImage({
      url: getPostImageProxyUrl(post.id, { cacheBuster: Date.now() }),
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
    setPublishDate(utcToLocalDateTimeInputValue(post.publish_date))
    setWeekNumber(post.week_number ? String(post.week_number) : "")
    setFirstCommentText(post.first_comment_text ?? "")
    setSyncWarning(null)
    setImproveOpen(defaultImproveOpen ?? false)
    setInstruction("")
    setLocalImage(null)
    setLocalUploadedImage(null)
    setImageDeleted(false)
    setDownloadImageDialogOpen(false)
    setDownloadImageName("")
    setIsDownloadingImage(false)
    setLocalVideoDeleted(false)
  }, [post, defaultImproveOpen])

  // Auto-calcula semana do mês quando a data de publicação muda
  useEffect(() => {
    if (!publishDate) return
    const dayOfMonth = getDayOfMonthFromLocalDateTime(publishDate)
    if (dayOfMonth == null) return
    const weekOfMonth = Math.ceil(dayOfMonth / 7)
    setWeekNumber(String(weekOfMonth))
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

  function getCurrentImageUrl() {
    return localImage?.url ?? localUploadedImage?.url ?? persistedImageUrl ?? null
  }

  function getCurrentImageSuggestedName() {
    return getDownloadBaseName(localUploadedImage?.name ?? post?.image_filename, title)
  }

  function openImageDownloadDialog() {
    if (!getCurrentImageUrl()) return
    setDownloadImageName(getCurrentImageSuggestedName())
    setDownloadImageDialogOpen(true)
  }

  async function handleDownloadImage() {
    const imageUrl = getCurrentImageUrl()
    if (!imageUrl) return

    try {
      setIsDownloadingImage(true)
      await downloadMediaFile(imageUrl, downloadImageName || getCurrentImageSuggestedName())
      setDownloadImageDialogOpen(false)
    } catch (error) {
      alert(error instanceof Error ? error.message : "Falha ao baixar imagem")
    } finally {
      setIsDownloadingImage(false)
    }
  }

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
        first_comment_text: firstCommentText.trim() ? firstCommentText : null,
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
    const improvedParts = extractGeneratedPostParts(result.text)
    const improvedBody = improvedParts.body || result.text
    setBody(improvedBody)
    if (improvedParts.hashtags) {
      setHashtags(improvedParts.hashtags)
    }
    setTitle(buildGeneratedTitle(improvedBody, title))
    setImproveOpen(false)
    setInstruction("")
  }

  const charCount = body.length
  const isOverLimit = charCount > 3000
  const isTooShort = charCount > 0 && charCount < 900
  const persistedImageUrl = resolvePostImageUrl(post)
  const persistedVideoUrl = resolvePostVideoUrl(post)
  const isMediaPreviewOpen = lightboxOpen || videoLightboxOpen
  const initialPublishDate = utcToLocalDateTimeInputValue(post?.publish_date)
  const canScheduleAtSelectedTime = isFutureLocalDateTime(publishDate)
  const hasPastPublishDateSelection = !!publishDate && !canScheduleAtSelectedTime
  const initialWeekNumber = post?.week_number ? String(post.week_number) : ""
  const hasUnsavedChanges =
    !syncWarning &&
    !!post &&
    (title !== post.title ||
      body !== post.body ||
      pillar !== post.pillar ||
      hookType !== (post.hook_type ?? "none") ||
      hashtags !== (post.hashtags ?? "") ||
      publishDate !== initialPublishDate ||
      weekNumber !== initialWeekNumber ||
      instruction.trim().length > 0 ||
      customPrompt.trim().length > 0 ||
      imageDeleted ||
      localVideoDeleted ||
      localImage !== null ||
      localUploadedImage !== null ||
      localVideoUrl !== null)

  function handleDialogInteractOutside(event: {
    preventDefault: () => void
    target: EventTarget | null
  }) {
    if (!hasUnsavedChanges) return
    if (isMediaPreviewOpen) {
      event.preventDefault()
      return
    }

    const target = event.target
    if (target instanceof HTMLElement && target.closest('[role="dialog"]')) {
      event.preventDefault()
      return
    }

    event.preventDefault()
    setShowCloseConfirm(true)
  }

  function requestClose() {
    if (!hasUnsavedChanges) {
      setSyncWarning(null)
      onOpenChange(false)
      return
    }
    setShowCloseConfirm(true)
  }

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : requestClose())}
      >
        <DialogContent
          className="max-w-2xl max-h-[90vh] overflow-y-auto"
          onInteractOutside={handleDialogInteractOutside}
          onEscapeKeyDown={(event) => {
            if (!hasUnsavedChanges) return
            event.preventDefault()
            setShowCloseConfirm(true)
          }}
        >
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
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold leading-none ${DAY_COLORS[new Date(publishDate).getDay()]}`}
                    >
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
            {hasPastPublishDateSelection && (
              <p className="text-base flex pl-2 text-(--warning-subtle-fg)">
                A data escolhida já passou. Para agendar, ajuste também o dia, não só a hora.
              </p>
            )}

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
                  {!imageDeleted && (localImage || localUploadedImage || persistedImageUrl) && (
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
                  {!imageDeleted && (localImage || localUploadedImage || persistedImageUrl) ? (
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
                            persistedImageUrl ??
                            undefined
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
                        {/* Baixar imagem */}
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs gap-1"
                          onClick={openImageDownloadDialog}
                        >
                          <Download className="h-3 w-3" />
                          Baixar
                        </Button>

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
                            {imageStyle === "with_text" && (
                              <p className="text-[11px] text-(--text-tertiary)">
                                Referência deste modo: capa editorial limpa, texto como foco
                                principal, fundo azul escuro #051932 e poucos elementos de apoio.
                              </p>
                            )}
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

                          <div className="grid gap-1.5">
                            <Label className="text-xs">Direção visual</Label>
                            <div className="flex gap-2 flex-wrap">
                              {(
                                [
                                  ["auto", "Auto"],
                                  ["editorial", "Editorial"],
                                  ["minimal", "Minimalista"],
                                  ["bold", "Impactante"],
                                  ["organic", "Orgânica"],
                                ] as const
                              ).map(([value, label]) => (
                                <button
                                  key={value}
                                  type="button"
                                  onClick={() => setImageVisualDirection(value)}
                                  className={`rounded px-2.5 py-1 text-xs border transition-colors ${
                                    imageVisualDirection === value
                                      ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                                      : "border-(--border-subtle) text-(--text-secondary) hover:border-(--accent)/50"
                                  }`}
                                >
                                  {label}
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
                              placeholder={
                                imageStyle === "with_text"
                                  ? "Ex: fundo #051932, tipografia branca de alto contraste, uma faixa de destaque, sem elementos extras"
                                  : "Ex: fundo claro, sem amarelo, mais cara de revista executiva"
                              }
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

            {/* ── Seção de carrossel ── */}
            <div className="rounded-md border border-(--border-subtle)">
              <button
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
                onClick={() => setCarouselOpen((v) => !v)}
              >
                <span className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-(--text-secondary)" />
                  Carrossel
                  {(post?.carousel_images?.length ?? 0) > 0 && (
                    <span className="rounded-full bg-(--accent)/15 px-1.5 py-0.5 text-xs text-(--accent)">
                      {post?.carousel_images?.length ?? 0} imagens
                    </span>
                  )}
                  {post?.media_kind === "carousel" &&
                    (post?.carousel_images?.length ?? 0) < CAROUSEL_MIN_IMAGES && (
                      <span className="rounded-full bg-red-500/15 px-1.5 py-0.5 text-xs text-red-600">
                        Mínimo {CAROUSEL_MIN_IMAGES}
                      </span>
                    )}
                </span>
                {carouselOpen ? (
                  <ChevronUp className="h-4 w-4 text-(--text-tertiary)" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-(--text-tertiary)" />
                )}
              </button>

              {carouselOpen && post && (
                <div className="border-t border-(--border-subtle) p-3">
                  <p className="mb-3 text-xs text-(--text-tertiary)">
                    Carrossel multi-imagem (até 9). Mutualmente exclusivo com imagem única ou vídeo.
                    Ao adicionar a primeira imagem, o tipo do post muda automaticamente para
                    &quot;carrossel&quot;.
                  </p>
                  <CarouselEditor
                    postId={post.id}
                    images={(post.carousel_images ?? []) as CarouselImageItem[]}
                  />
                </div>
              )}
            </div>

            {/* ── Seção de first comment ── */}
            <div className="rounded-md border border-(--border-subtle)">
              <button
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
                onClick={() => setFirstCommentOpen((v) => !v)}
              >
                <span className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-(--text-secondary)" />
                  Primeiro comentário
                  {firstCommentText.trim() && (
                    <span className="rounded-full bg-(--accent)/15 px-1.5 py-0.5 text-xs text-(--accent)">
                      Configurado
                    </span>
                  )}
                  {post?.first_comment_status === "posted" && (
                    <span className="rounded-full bg-green-500/15 px-1.5 py-0.5 text-xs text-green-600">
                      Publicado
                    </span>
                  )}
                  {post?.first_comment_status === "failed" && (
                    <span className="rounded-full bg-red-500/15 px-1.5 py-0.5 text-xs text-red-600">
                      Falhou
                    </span>
                  )}
                </span>
                {firstCommentOpen ? (
                  <ChevronUp className="h-4 w-4 text-(--text-tertiary)" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-(--text-tertiary)" />
                )}
              </button>
              {firstCommentOpen && (
                <div className="border-t border-(--border-subtle) p-3 flex flex-col gap-2">
                  <p className="text-xs text-(--text-tertiary)">
                    Será publicado ~30s após o post ir ao ar. Pin não é suportado oficialmente pela
                    API do LinkedIn — a feature ficará marcada como &quot;not_supported&quot;.
                  </p>
                  <Textarea
                    value={firstCommentText}
                    onChange={(e) => setFirstCommentText(e.target.value.slice(0, 1250))}
                    placeholder="Ex.: Curtiu? Salva esse post! Quer mais conteúdo assim? Comenta aí 👇"
                    rows={4}
                    maxLength={1250}
                  />
                  <div className="flex items-center justify-between text-xs text-(--text-tertiary)">
                    <span>{firstCommentText.length}/1250</span>
                    {post?.first_comment_status === "failed" && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => post && retryFirstComment.mutate({ postId: post.id })}
                        disabled={retryFirstComment.isPending}
                      >
                        {retryFirstComment.isPending ? "Re-tentando…" : "Re-tentar"}
                      </Button>
                    )}
                  </div>
                  {post?.first_comment_error && (
                    <p className="text-xs text-red-600" title={post.first_comment_error}>
                      Erro: {post.first_comment_error.slice(0, 200)}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* ── Seção de Histórico (revisões) ── */}
            {post && (
              <div className="rounded-md border border-(--border-subtle)">
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
                  onClick={() => setRevisionsOpen((v) => !v)}
                >
                  <span className="flex items-center gap-2">
                    <History className="h-4 w-4 text-(--text-secondary)" />
                    Histórico de revisões
                    {revisionsQuery.data && revisionsQuery.data.length > 0 && (
                      <span className="rounded-full bg-(--accent)/15 px-1.5 py-0.5 text-xs text-(--accent)">
                        {revisionsQuery.data.length}
                      </span>
                    )}
                  </span>
                  {revisionsOpen ? (
                    <ChevronUp className="h-4 w-4 text-(--text-tertiary)" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-(--text-tertiary)" />
                  )}
                </button>
                {revisionsOpen && (
                  <div className="border-t border-(--border-subtle) p-3 flex flex-col gap-2">
                    {revisionsQuery.isLoading && (
                      <p className="text-xs text-(--text-tertiary)">Carregando…</p>
                    )}
                    {revisionsQuery.data && revisionsQuery.data.length === 0 && (
                      <p className="text-xs text-(--text-tertiary)">
                        Nenhuma revisão registrada ainda. Edições e publicações geram snapshots
                        automáticos.
                      </p>
                    )}
                    {revisionsQuery.data?.map((rev) => {
                      const reasonLabel: Record<string, string> = {
                        manual_edit: "Edição manual",
                        pre_publish: "Pré-publicação",
                        restore: "Restauração",
                        system: "Sistema",
                      }
                      const canRestore =
                        post.status === "draft" ||
                        post.status === "approved" ||
                        post.status === "failed"
                      return (
                        <div
                          key={rev.id}
                          className="flex items-start justify-between gap-2 rounded-md border border-(--border-subtle) p-2 text-xs"
                        >
                          <div className="flex flex-col gap-1">
                            <span className="font-medium text-(--text-primary)">
                              {reasonLabel[rev.reason] ?? rev.reason}
                            </span>
                            <span className="text-(--text-tertiary)">
                              {new Date(rev.created_at).toLocaleString("pt-BR")}
                            </span>
                            {rev.snapshot.title && (
                              <span className="text-(--text-secondary) line-clamp-1">
                                {rev.snapshot.title}
                              </span>
                            )}
                          </div>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={!canRestore || restoreRevision.isPending}
                            onClick={() =>
                              restoreRevision.mutate({ postId: post.id, revisionId: rev.id })
                            }
                            title={
                              !canRestore
                                ? "Só é possível restaurar em rascunho/aprovado/falhou"
                                : "Restaurar este snapshot"
                            }
                          >
                            <RotateCcw className="h-3 w-3" />
                          </Button>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

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
                  {!localVideoDeleted && (localVideoUrl || persistedVideoUrl) && (
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
                  {!localVideoDeleted && (localVideoUrl || persistedVideoUrl) ? (
                    <div className="flex flex-col gap-2">
                      {/* Mini player 16:9 com botão ampliar */}
                      <div className="relative w-full aspect-video">
                        <video
                          src={localVideoUrl ?? persistedVideoUrl ?? undefined}
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
                          disabled={isActionPending || !publishDate || !canScheduleAtSelectedTime}
                          title={
                            !publishDate
                              ? "Defina uma data de publicação para agendar"
                              : !canScheduleAtSelectedTime
                                ? "A data de publicação está no passado. Ajuste também o dia para agendar"
                                : undefined
                          }
                          onClick={async () => {
                            // Salva data primeiro se mudou, depois agenda
                            if (publishDate !== initialPublishDate) {
                              await updatePost.mutateAsync({
                                postId: post.id,
                                data: {
                                  publish_date: publishDate ? localDateToUTC(publishDate) : null,
                                },
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
                <Button type="button" variant="outline" onClick={requestClose}>
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

      <AlertDialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Fechar sem salvar?</AlertDialogTitle>
            <AlertDialogDescription>
              Existem alterações não salvas neste post. Se fechar agora, suas edições serão
              descartadas.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continuar editando</AlertDialogCancel>
            <AlertDialogAction
              className="bg-(--danger) text-white hover:opacity-90 focus-visible:ring-(--danger)"
              onClick={() => {
                setShowCloseConfirm(false)
                setSyncWarning(null)
                onOpenChange(false)
              }}
            >
              Fechar sem salvar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={downloadImageDialogOpen} onOpenChange={setDownloadImageDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Nome do arquivo para download</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4 pt-2">
            <div className="grid gap-2">
              <Label htmlFor="edit-post-image-download-name">Nome da imagem</Label>
              <Input
                id="edit-post-image-download-name"
                value={downloadImageName}
                onChange={(e) => setDownloadImageName(e.target.value)}
                placeholder="Digite o nome do arquivo"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    void handleDownloadImage()
                  }
                }}
                autoFocus
              />
              <p className="text-xs text-(--text-secondary)">
                A extensão será mantida automaticamente no download.
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDownloadImageDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={() => void handleDownloadImage()} disabled={isDownloadingImage}>
                {isDownloadingImage ? (
                  <span className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                {isDownloadingImage ? "Baixando..." : "Baixar imagem"}
              </Button>
            </DialogFooter>
          </div>
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
            src={localImage?.url ?? localUploadedImage?.url ?? persistedImageUrl ?? undefined}
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
              src={localVideoUrl ?? persistedVideoUrl ?? undefined}
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
