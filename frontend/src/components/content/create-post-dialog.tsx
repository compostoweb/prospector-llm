"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import {
  Sparkles,
  Check,
  Wand2,
  RefreshCw,
  Download,
  ChevronDown,
  ChevronUp,
  ImageIcon,
  VideoIcon,
  Upload,
  Maximize2,
  X,
  Layers,
} from "lucide-react"
import { getDayOfMonthFromLocalDateTime, isFutureLocalDateTime, localDateToUTC } from "@/lib/date"
import {
  useCreateContentPost,
  useUpdatePost,
  useDeletePost,
  useImprovePost,
  useGeneratePost,
  useContentThemes,
  useMarkThemeUsed,
  useApprovePost,
  useSchedulePost,
  useDetectHookType,
  useGeneratePostImage,
  useDeletePostImage,
  useUploadPostImage,
  useUploadPostVideo,
  useDeletePostVideo,
  useContentPosts,
  type ContentPost,
  type CarouselImageItem,
  type HookType,
  type PostPillar,
  type ImageStyle,
  type ImageSubType,
  type ImageAspectRatio,
  type ImageVisualDirection,
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
import { CarouselEditor, CAROUSEL_MIN_IMAGES } from "@/components/content/carousel-editor"

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
  { value: "contrast_direct", label: "Contraste direto" },
  { value: "data_isolated", label: "Dado isolado" },
  { value: "short_reflection", label: "Reflexão curta" },
  { value: "personal_story", label: "História pessoal" },
  { value: "shortcut", label: "Atalho" },
  { value: "dm_offer", label: "Oferta DM" },
]

interface CreatePostDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultPublishDate?: string
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
  const [showCloseConfirm, setShowCloseConfirm] = useState(false)
  const [validationMessage, setValidationMessage] = useState<string | null>(null)

  const [draftPost, setDraftPost] = useState<ContentPost | null>(null)
  const draftPostIdRef = useRef<string | null>(null)

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

  const [videoOpen, setVideoOpen] = useState(false)
  const videoInputRef = useRef<HTMLInputElement>(null)
  const [localVideoUrl, setLocalVideoUrl] = useState<string | null>(null)
  const [localVideoName, setLocalVideoName] = useState<string | null>(null)
  const [localVideoSizeMB, setLocalVideoSizeMB] = useState<string | null>(null)
  const [videoLightboxOpen, setVideoLightboxOpen] = useState(false)
  const [localVideoDeleted, setLocalVideoDeleted] = useState(false)

  const [carouselOpen, setCarouselOpen] = useState(false)
  const [isCreatingDraftForCarousel, setIsCreatingDraftForCarousel] = useState(false)

  const createPost = useCreateContentPost()
  const updatePost = useUpdatePost()
  const deletePostMut = useDeletePost()
  const improvePost = useImprovePost()
  const generatePost = useGeneratePost()
  const markThemeUsed = useMarkThemeUsed()
  const approvePost = useApprovePost()
  const schedulePost = useSchedulePost()
  const detectHook = useDetectHookType()
  const generateImage = useGeneratePostImage()
  const deleteImage = useDeletePostImage()
  const uploadImage = useUploadPostImage()
  const uploadVideo = useUploadPostVideo()
  const deleteVideo = useDeletePostVideo()
  const { data: availableThemes } = useContentThemes({ used: false })

  // Lê dados frescos do post-rascunho via cache da listagem (atualiza após mutações de carrossel).
  const { data: allPostsForDraft } = useContentPosts()
  const liveDraftPost = useMemo(() => {
    if (!draftPost) return null
    return allPostsForDraft?.find((p) => p.id === draftPost.id) ?? draftPost
  }, [allPostsForDraft, draftPost])
  const carouselImages = (liveDraftPost?.carousel_images ?? []) as CarouselImageItem[]

  useEffect(() => {
    if (open) return
    createPost.reset()
    updatePost.reset()
  }, [open, createPost, updatePost])

  useEffect(() => {
    if (defaultPublishDate) setPublishDate(defaultPublishDate)
  }, [defaultPublishDate])

  useEffect(() => {
    if (!publishDate) return
    const dayOfMonth = getDayOfMonthFromLocalDateTime(publishDate)
    if (dayOfMonth == null) return
    const weekOfMonth = Math.ceil(dayOfMonth / 7)
    setWeekNumber(String(weekOfMonth))
  }, [publishDate])

  useEffect(() => {
    return () => {
      if (localVideoUrl?.startsWith("blob:")) URL.revokeObjectURL(localVideoUrl)
    }
  }, [localVideoUrl])

  useEffect(() => {
    return () => {
      if (localUploadedImage?.url?.startsWith("blob:")) {
        URL.revokeObjectURL(localUploadedImage.url)
      }
    }
  }, [localUploadedImage])

  function setDraft(post: ContentPost | null) {
    setDraftPost(post)
    draftPostIdRef.current = post?.id ?? null
  }

  function buildPostPayload() {
    return {
      title,
      body,
      pillar,
      hook_type: hookType === "none" ? null : hookType,
      hashtags: hashtags || null,
      character_count: body.length,
      publish_date: publishDate ? localDateToUTC(publishDate) : null,
      week_number: weekNumber ? parseInt(weekNumber, 10) : null,
    }
  }

  const canAutoScheduleAtSelectedTime = isFutureLocalDateTime(publishDate)
  const hasPastPublishDateSelection = !!publishDate && !canAutoScheduleAtSelectedTime

  async function ensureDraftPost() {
    const existingDraftId = draftPostIdRef.current
    if (existingDraftId) {
      const updated = await updatePost.mutateAsync({
        postId: existingDraftId,
        data: buildPostPayload(),
      })
      setDraft(updated)
      return updated
    }

    if (!title.trim() || !body.trim()) {
      alert("Preencha o título interno e o texto do post antes de adicionar mídia.")
      return null
    }

    const created = await createPost.mutateAsync(buildPostPayload())
    setDraft(created)
    return created
  }

  function resetForm() {
    createPost.reset()
    updatePost.reset()
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
    setValidationMessage(null)
    setShowCloseConfirm(false)
    setDraft(null)

    setImageOpen(false)
    setImageMode("generate")
    setImageStyle("clean")
    setImageSubType("metrics")
    setImageAspect("4:5")
    setCustomPrompt("")
    setLocalImage(null)
    setLocalUploadedImage(null)
    setImageDeleted(false)
    setLightboxOpen(false)
    setDownloadImageDialogOpen(false)
    setDownloadImageName("")
    setIsDownloadingImage(false)

    setVideoOpen(false)
    setLocalVideoUrl(null)
    setLocalVideoName(null)
    setLocalVideoSizeMB(null)
    setVideoLightboxOpen(false)
    setLocalVideoDeleted(false)

    setCarouselOpen(false)
    setIsCreatingDraftForCarousel(false)
  }

  function handleClose(keepDraft: boolean) {
    const draftId = draftPostIdRef.current
    const shouldDeleteImage =
      !keepDraft &&
      !!draftId &&
      !imageDeleted &&
      (Boolean(localImage) || Boolean(localUploadedImage) || Boolean(draftPost?.image_s3_key))
    const shouldDeleteVideo =
      !keepDraft &&
      !!draftId &&
      !localVideoDeleted &&
      (Boolean(localVideoUrl) || Boolean(draftPost?.video_s3_key))

    onOpenChange(false)
    resetForm()

    if (!keepDraft && draftId) {
      void (async () => {
        if (shouldDeleteImage) {
          try {
            await deleteImage.mutateAsync(draftId)
          } catch {
            // melhor esforço
          }
        }

        if (shouldDeleteVideo) {
          try {
            await deleteVideo.mutateAsync(draftId)
          } catch {
            // melhor esforço
          }
        }

        try {
          await deletePostMut.mutateAsync(draftId)
        } catch {
          // melhor esforço
        }
      })()
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (publishDate && !canAutoScheduleAtSelectedTime) {
      setValidationMessage(
        "A data de publicação está no passado. Ajuste também o dia para agendar.",
      )
      return
    }

    let savedPost: ContentPost
    const payload = buildPostPayload()
    if (draftPostIdRef.current) {
      savedPost = await updatePost.mutateAsync({
        postId: draftPostIdRef.current,
        data: payload,
      })
      setDraft(savedPost)
    } else {
      savedPost = await createPost.mutateAsync(payload)
      setDraft(savedPost)
    }

    if (publishDate) {
      try {
        await approvePost.mutateAsync(savedPost.id)
        await schedulePost.mutateAsync(savedPost.id)
      } catch {
        // post fica draft se o agendamento falhar
      }
    }

    if (selectedThemeId) {
      try {
        await markThemeUsed.mutateAsync({ themeId: selectedThemeId, postId: savedPost.id })
      } catch {
        // não bloqueia criação
      }
    }

    handleClose(true)
  }

  async function handleGenerate() {
    const themeText =
      themeSource === "bank"
        ? (availableThemes?.find((theme) => theme.id === selectedThemeId)?.title ?? "")
        : freeTheme
    if (!themeText.trim()) return

    const selectedTheme =
      themeSource === "bank" ? availableThemes?.find((theme) => theme.id === selectedThemeId) : null
    const generatedPillar = selectedTheme ? selectedTheme.pillar : pillar

    const result = await generatePost.mutateAsync({
      theme: themeText,
      pillar: generatedPillar,
      variations: 1,
      temperature: 0.8,
    })

    const variation = result.variations[0]
    if (variation) {
      const generatedParts = extractGeneratedPostParts(variation.text)
      setBody(generatedParts.body || variation.text)
      setHashtags(generatedParts.hashtags)
      if (variation.hook_type_used && variation.hook_type_used !== "auto") {
        setHookType(variation.hook_type_used as HookType)
      }
      if (selectedTheme) {
        setPillar(selectedTheme.pillar)
      }
      setTitle(buildGeneratedTitle(generatedParts.body || variation.text, themeText))
    }

    setGenerateOpen(false)
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

  async function handleDetectHook() {
    if (!body.trim()) return
    const result = await detectHook.mutateAsync(body)
    setHookType(result.hook_type as HookType)
  }

  async function handleGenerateImage() {
    if (!body.trim()) {
      alert("Preencha o texto do post antes de gerar a imagem com IA.")
      return
    }

    const ensuredPost = await ensureDraftPost()
    if (!ensuredPost) return

    const result = await generateImage.mutateAsync({
      post_id: ensuredPost.id,
      style: imageStyle,
      aspect_ratio: imageAspect,
      sub_type: imageStyle === "infographic" ? imageSubType : null,
      visual_direction: imageVisualDirection,
      custom_prompt: customPrompt || null,
    })

    setDraft({
      ...ensuredPost,
      image_url: result.image_url,
      image_s3_key: "__generated__",
      image_prompt: result.image_prompt,
      image_style: imageStyle,
      image_aspect_ratio: imageAspect,
      image_filename: null,
      image_size_bytes: null,
    })
    setImageDeleted(false)
    setLocalImage({
      url: getPostImageProxyUrl(ensuredPost.id, { cacheBuster: Date.now() }),
      prompt: result.image_prompt,
    })
    setLocalUploadedImage(null)
    setCustomPrompt("")
  }

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.[0]) return

    const ensuredPost = await ensureDraftPost()
    if (!ensuredPost) {
      if (imageUploadInputRef.current) imageUploadInputRef.current.value = ""
      return
    }

    const file = e.target.files[0]
    const allowedImageTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if (!allowedImageTypes.includes(file.type)) {
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
      const updatedPost = await uploadImage.mutateAsync({ postId: ensuredPost.id, file })
      setDraft(updatedPost)
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

  async function handleDeleteImage() {
    const draftId = draftPostIdRef.current
    if (!draftId) return

    await deleteImage.mutateAsync(draftId)
    setLocalImage(null)
    setLocalUploadedImage(null)
    setImageDeleted(true)
    setDraft(
      draftPost
        ? {
            ...draftPost,
            image_url: null,
            image_s3_key: null,
            image_style: null,
            image_prompt: null,
            image_aspect_ratio: null,
            image_filename: null,
            image_size_bytes: null,
            linkedin_image_urn: null,
          }
        : draftPost,
    )
  }

  async function handleVideoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.[0]) return

    const ensuredPost = await ensureDraftPost()
    if (!ensuredPost) {
      if (videoInputRef.current) videoInputRef.current.value = ""
      return
    }

    const file = e.target.files[0]
    if (file.size > 150 * 1024 * 1024) {
      alert("O arquivo excede o limite de 150 MB.")
      if (videoInputRef.current) videoInputRef.current.value = ""
      return
    }

    const objectUrl = URL.createObjectURL(file)
    try {
      const updatedPost = await uploadVideo.mutateAsync({ postId: ensuredPost.id, file })
      setDraft(updatedPost)
      setLocalVideoUrl(objectUrl)
      setLocalVideoName(file.name)
      setLocalVideoSizeMB((file.size / 1024 / 1024).toFixed(1))
      setLocalVideoDeleted(false)
    } catch {
      URL.revokeObjectURL(objectUrl)
    }

    if (videoInputRef.current) videoInputRef.current.value = ""
  }

  async function handleDeleteVideo() {
    const draftId = draftPostIdRef.current
    if (!draftId) return

    await deleteVideo.mutateAsync(draftId)
    setLocalVideoDeleted(true)
    setLocalVideoUrl(null)
    setLocalVideoName(null)
    setLocalVideoSizeMB(null)
    setDraft(
      draftPost
        ? {
            ...draftPost,
            video_url: null,
            video_s3_key: null,
            video_filename: null,
            video_size_bytes: null,
            linkedin_video_urn: null,
          }
        : draftPost,
    )
  }

  function getCurrentImageUrl() {
    return localImage?.url ?? localUploadedImage?.url ?? persistedImageUrl ?? null
  }

  function getCurrentImageSuggestedName() {
    return getDownloadBaseName(localUploadedImage?.name ?? draftPost?.image_filename, title)
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

  const charCount = body.length
  const isOverLimit = charCount > 3000
  const isTooShort = charCount > 0 && charCount < 900
  const persistedImageUrl = resolvePostImageUrl(draftPost)
  const persistedVideoUrl = resolvePostVideoUrl(draftPost)
  const isMediaPreviewOpen = lightboxOpen || videoLightboxOpen
  const isSaving = createPost.isPending || updatePost.isPending
  const isMediaPending =
    detectHook.isPending ||
    generateImage.isPending ||
    uploadImage.isPending ||
    deleteImage.isPending ||
    uploadVideo.isPending ||
    deleteVideo.isPending
  const hasUnsavedChanges =
    title.trim().length > 0 ||
    body.trim().length > 0 ||
    pillar !== "authority" ||
    hookType !== "none" ||
    hashtags.trim().length > 0 ||
    publishDate.length > 0 ||
    weekNumber.length > 0 ||
    instruction.trim().length > 0 ||
    selectedThemeId !== null ||
    freeTheme.trim().length > 0 ||
    customPrompt.trim().length > 0 ||
    draftPostIdRef.current !== null ||
    localImage !== null ||
    localUploadedImage !== null ||
    localVideoUrl !== null ||
    Boolean(draftPost?.image_s3_key) ||
    Boolean(draftPost?.video_s3_key)

  function handleDialogInteractOutside(event: {
    preventDefault: () => void
    target: EventTarget | null
  }) {
    if (validationMessage || showCloseConfirm) {
      event.preventDefault()
      return
    }

    if (!hasUnsavedChanges) return
    if (isMediaPreviewOpen) {
      event.preventDefault()
      return
    }

    const target = event.target
    if (
      target instanceof HTMLElement &&
      (target.closest('[role="dialog"]') || target.closest('[role="alertdialog"]'))
    ) {
      event.preventDefault()
      return
    }

    event.preventDefault()
    setShowCloseConfirm(true)
  }

  function requestClose() {
    if (!hasUnsavedChanges) {
      handleClose(false)
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
            if (validationMessage || showCloseConfirm) {
              event.preventDefault()
              return
            }
            if (!hasUnsavedChanges) return
            event.preventDefault()
            setShowCloseConfirm(true)
          }}
        >
          <DialogHeader>
            <DialogTitle>Novo post</DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid gap-1.5 pt-2">
              <Label htmlFor="title">Título interno</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex: Semana 5 · Tema principal"
                required
              />
            </div>

            <div className="grid gap-1.5">
              <button
                type="button"
                onClick={() => setGenerateOpen((value) => !value)}
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
                      onValueChange={(value) => setSelectedThemeId(value || null)}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="Selecione um tema do banco…" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableThemes?.map((theme) => (
                          <SelectItem key={theme.id} value={theme.id} className="text-xs">
                            <span className="flex items-center gap-2">
                              <span
                                className={`inline-block h-2 w-2 rounded-full ${theme.pillar === "authority" ? "bg-blue-500" : theme.pillar === "case" ? "bg-emerald-500" : "bg-purple-500"}`}
                              />
                              {theme.title}
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
                    onClick={() => setImproveOpen((value) => !value)}
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
                <Select value={pillar} onValueChange={(value) => setPillar(value as PostPillar)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PILLAR_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
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
                    onClick={() => void handleDetectHook()}
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
                <Select
                  value={hookType}
                  onValueChange={(value) => setHookType(value as HookType | "none")}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Nenhum" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nenhum</SelectItem>
                    {HOOK_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-1.5">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="publish_date">Data de publicação</Label>
                    {publishDate && (
                      <span
                        className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold leading-none ${DAY_COLORS[new Date(publishDate).getDay()]}`}
                      >
                        {DAY_NAMES[new Date(publishDate).getDay()]}
                      </span>
                    )}
                  </div>
                  <Input
                    id="publish_date"
                    type="datetime-local"
                    value={publishDate}
                    onChange={(e) => setPublishDate(e.target.value)}
                  />
                </div>

                <div className="grid gap-1.5">
                  <Label htmlFor="week_number">Semana do mês</Label>
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
              {hasPastPublishDateSelection && (
                <p className="pl-2 text-base text-(--warning-subtle-fg)">
                  A data escolhida já passou. Para agendar, ajuste também o dia, não só a hora.
                </p>
              )}
            </>

            <div className="grid gap-1.5">
              <Label htmlFor="hashtags">Hashtags</Label>
              <Input
                id="hashtags"
                value={hashtags}
                onChange={(e) => setHashtags(e.target.value)}
                placeholder="#ia #processos #automacao"
              />
            </div>

            <div className="rounded-md border border-(--border-subtle)">
              <button
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
                onClick={() => setImageOpen((value) => !value)}
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

                      {(localImage?.prompt ??
                        (draftPost?.image_prompt && !draftPost?.image_filename)) && (
                        <p
                          className="text-xs text-(--text-tertiary) truncate"
                          title={localImage?.prompt ?? draftPost?.image_prompt ?? ""}
                        >
                          Prompt: {localImage?.prompt ?? draftPost?.image_prompt}
                        </p>
                      )}

                      {(localUploadedImage || draftPost?.image_filename) && (
                        <div className="flex items-center gap-1.5 text-xs text-(--text-tertiary)">
                          <ImageIcon className="h-3 w-3 shrink-0" />
                          <span className="truncate">
                            {localUploadedImage?.name ?? draftPost?.image_filename ?? "imagem"}
                          </span>
                          {(localUploadedImage?.sizeMB ??
                            (draftPost?.image_size_bytes
                              ? (draftPost.image_size_bytes / 1024 / 1024).toFixed(1)
                              : null)) && (
                            <span className="text-(--text-quaternary) shrink-0">
                              {localUploadedImage?.sizeMB ??
                                (draftPost?.image_size_bytes
                                  ? (draftPost.image_size_bytes / 1024 / 1024).toFixed(1)
                                  : "")}
                              {" MB"}
                            </span>
                          )}
                        </div>
                      )}

                      <div className="flex gap-2">
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
                        {(localImage || (!localUploadedImage && draftPost?.image_prompt)) && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs gap-1"
                            disabled={generateImage.isPending}
                            onClick={() => void handleGenerateImage()}
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
                          onClick={() => void handleDeleteImage()}
                        >
                          <X className="h-3 w-3" />
                          Excluir
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
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
                        <>
                          <div className="grid gap-1.5">
                            <Label className="text-xs">Estilo</Label>
                            <div className="flex gap-2 flex-wrap">
                              {(["clean", "with_text", "infographic"] as ImageStyle[]).map(
                                (style) => (
                                  <button
                                    key={style}
                                    type="button"
                                    onClick={() => setImageStyle(style)}
                                    className={`rounded px-2.5 py-1 text-xs border transition-colors ${
                                      imageStyle === style
                                        ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                                        : "border-(--border-subtle) text-(--text-secondary) hover:border-(--accent)/50"
                                    }`}
                                  >
                                    {style === "clean"
                                      ? "Limpo"
                                      : style === "with_text"
                                        ? "Com texto"
                                        : "Infográfico"}
                                  </button>
                                ),
                              )}
                            </div>
                            {imageStyle === "with_text" && (
                              <p className="text-[11px] text-(--text-tertiary)">
                                Referência deste modo: capa editorial limpa, texto como foco
                                principal, fundo azul escuro #051932 e poucos elementos de apoio.
                              </p>
                            )}
                          </div>

                          {imageStyle === "infographic" && (
                            <div className="grid gap-1.5">
                              <Label className="text-xs">Tipo de infográfico</Label>
                              <div className="flex gap-2 flex-wrap">
                                {(["metrics", "steps", "comparison"] as ImageSubType[]).map(
                                  (subType) => (
                                    <button
                                      key={subType}
                                      type="button"
                                      onClick={() => setImageSubType(subType)}
                                      className={`rounded px-2.5 py-1 text-xs border transition-colors ${
                                        imageSubType === subType
                                          ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                                          : "border-(--border-subtle) text-(--text-secondary) hover:border-(--accent)/50"
                                      }`}
                                    >
                                      {subType === "metrics"
                                        ? "Métricas"
                                        : subType === "steps"
                                          ? "Passos"
                                          : "Comparativo"}
                                    </button>
                                  ),
                                )}
                              </div>
                            </div>
                          )}

                          <div className="grid gap-1.5">
                            <Label className="text-xs">Proporção</Label>
                            <div className="flex gap-2">
                              {(["4:5", "1:1", "16:9"] as ImageAspectRatio[]).map((ratio) => (
                                <button
                                  key={ratio}
                                  type="button"
                                  onClick={() => setImageAspect(ratio)}
                                  className={`rounded px-2.5 py-1 text-xs border transition-colors ${
                                    imageAspect === ratio
                                      ? "border-(--accent) bg-(--accent)/10 text-(--accent)"
                                      : "border-(--border-subtle) text-(--text-secondary) hover:border-(--accent)/50"
                                  }`}
                                >
                                  {ratio}
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
                            onClick={() => void handleGenerateImage()}
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

            <div className="rounded-md border border-(--border-subtle)">
              <button
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
                onClick={() => setVideoOpen((value) => !value)}
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

                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 text-sm text-(--text-secondary) min-w-0">
                          <VideoIcon className="h-4 w-4 shrink-0" />
                          <span className="truncate">
                            {localVideoName ?? draftPost?.video_filename ?? "video.mp4"}
                          </span>
                          {(localVideoSizeMB ??
                            (draftPost?.video_size_bytes
                              ? (draftPost.video_size_bytes / 1024 / 1024).toFixed(1)
                              : null)) && (
                            <span className="shrink-0 text-xs text-(--text-tertiary)">
                              {localVideoSizeMB ??
                                (draftPost?.video_size_bytes
                                  ? (draftPost.video_size_bytes / 1024 / 1024).toFixed(1)
                                  : null)}{" "}
                              MB
                            </span>
                          )}
                          {draftPost?.linkedin_video_urn && (
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
                          onClick={() => void handleDeleteVideo()}
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
                  {carouselImages.length > 0 && (
                    <span className="rounded-full bg-(--accent)/15 px-1.5 py-0.5 text-xs text-(--accent)">
                      {carouselImages.length} imagens
                    </span>
                  )}
                  {liveDraftPost?.media_kind === "carousel" &&
                    carouselImages.length < CAROUSEL_MIN_IMAGES && (
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

              {carouselOpen && (
                <div className="border-t border-(--border-subtle) p-3">
                  <p className="mb-3 text-xs text-(--text-tertiary)">
                    Carrossel multi-imagem (até 9). Mutualmente exclusivo com imagem única ou vídeo.
                    Ao adicionar a primeira imagem, o tipo do post muda automaticamente para
                    &quot;carrossel&quot;.
                  </p>
                  {liveDraftPost ? (
                    <CarouselEditor postId={liveDraftPost.id} images={carouselImages} />
                  ) : (
                    <div className="flex flex-col items-start gap-2 rounded-md bg-(--bg-subtle) p-3 text-xs text-(--text-secondary)">
                      <p>
                        Para anexar imagens ao carrossel, primeiro salvamos um rascunho do post com
                        título e texto.
                      </p>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={isCreatingDraftForCarousel || !title.trim() || !body.trim()}
                        onClick={async () => {
                          setIsCreatingDraftForCarousel(true)
                          try {
                            await ensureDraftPost()
                          } finally {
                            setIsCreatingDraftForCarousel(false)
                          }
                        }}
                      >
                        {isCreatingDraftForCarousel ? "Criando rascunho…" : "Iniciar carrossel"}
                      </Button>
                      {(!title.trim() || !body.trim()) && (
                        <p className="text-(--text-tertiary)">
                          Preencha o título interno e o texto do post primeiro.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={requestClose} disabled={isSaving}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSaving || isMediaPending || isOverLimit}>
                {isSaving ? "Criando…" : "Criar post"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Fechar sem salvar?</AlertDialogTitle>
            <AlertDialogDescription>
              Você tem alterações não salvas neste post. Se fechar agora, tudo o que foi escrito ou
              anexado será perdido.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continuar editando</AlertDialogCancel>
            <AlertDialogAction
              className="bg-(--danger) text-white hover:opacity-90 focus-visible:ring-(--danger)"
              onClick={() => {
                setShowCloseConfirm(false)
                handleClose(false)
              }}
            >
              Fechar sem salvar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={validationMessage !== null}
        onOpenChange={(open) => {
          if (!open) setValidationMessage(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Data de publicação inválida</AlertDialogTitle>
            <AlertDialogDescription>{validationMessage}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setValidationMessage(null)}>OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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

      <Dialog open={downloadImageDialogOpen} onOpenChange={setDownloadImageDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Nome do arquivo para download</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4 pt-2">
            <div className="grid gap-2">
              <Label htmlFor="create-post-image-download-name">Nome da imagem</Label>
              <Input
                id="create-post-image-download-name"
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
