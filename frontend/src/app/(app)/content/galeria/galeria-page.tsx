/* eslint-disable @next/next/no-img-element */
"use client"

import { useCallback, useState } from "react"
import Link from "next/link"
import type { Route } from "next"
import {
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  Eye,
  ImageIcon,
  Loader2,
  Search,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react"
import { toast } from "sonner"
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
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { resolvePostImageUrl } from "@/lib/content/post-media"
import {
  type GalleryImage,
  ImageAspectRatio,
  ImageStyle,
  ImageSubType,
  ImageVisualDirection,
  useContentImages,
  useDeleteGalleryImage,
  useGenerateStandaloneImage,
  useUploadStandaloneImage,
} from "@/lib/api/hooks/use-content"

const PAGE_SIZE = 24
const GALLERY_GRID_CLASS =
  "grid grid-cols-[repeat(auto-fit,minmax(168px,220px))] justify-start gap-4"

function getImageSrc(image: GalleryImage): string {
  return (
    resolvePostImageUrl({
      id: image.post_id,
      image_url: image.image_url,
      image_s3_key: image.image_s3_key,
    }) ?? ""
  )
}

export default function GaleriaPage() {
  const [page, setPage] = useState(1)
  const [source, setSource] = useState<string>("")
  const [style, setStyle] = useState<string>("")
  const [pillar, setPillar] = useState<string>("")
  const [status, setStatus] = useState<string>("")
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [generateOpen, setGenerateOpen] = useState(false)
  const [lightboxImage, setLightboxImage] = useState<GalleryImage | null>(null)
  const [downloadDialogOpen, setDownloadDialogOpen] = useState(false)
  const [downloadName, setDownloadName] = useState("")
  const [isDownloadingImage, setIsDownloadingImage] = useState(false)
  const [imagePendingDelete, setImagePendingDelete] = useState<GalleryImage | null>(null)

  const uploadMutation = useUploadStandaloneImage()
  const generateMutation = useGenerateStandaloneImage()
  const deleteMutation = useDeleteGalleryImage()

  const { data, isLoading, error } = useContentImages({
    page,
    page_size: PAGE_SIZE,
    source: source ? (source as "generated" | "uploaded") : undefined,
    style: style ? (style as ImageStyle) : undefined,
    pillar: pillar ? (pillar as "authority" | "case" | "vision") : undefined,
    status: status
      ? (status as "draft" | "approved" | "scheduled" | "published" | "failed")
      : undefined,
    search: debouncedSearch || undefined,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const totalImagesLabel = data?.total === 1 ? "imagem" : "imagens"
  const hasActiveSearch = debouncedSearch.trim().length > 0
  const hasActiveFilters = Boolean(source || style || pillar || status)

  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        setDebouncedSearch(search)
        setPage(1)
      }
    },
    [search],
  )

  const handleDelete = (image: GalleryImage, e: React.MouseEvent) => {
    e.stopPropagation()
    setImagePendingDelete(image)
  }

  const confirmDeleteImage = useCallback(() => {
    if (!imagePendingDelete) return

    deleteMutation.mutate(imagePendingDelete.post_id, {
      onSuccess: () => {
        toast.success("Imagem excluída")
        setLightboxImage((current) =>
          current?.post_id === imagePendingDelete.post_id ? null : current,
        )
        setDownloadDialogOpen(false)
      },
      onError: (err) => toast.error(err instanceof Error ? err.message : "Erro ao excluir"),
      onSettled: () => setImagePendingDelete(null),
    })
  }, [deleteMutation, imagePendingDelete])

  const handleUpload = useCallback(
    (file: File) => {
      uploadMutation.mutate(file, {
        onSuccess: () => {
          toast.success("Imagem enviada com sucesso!")
          setPage(1)
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : "Erro no upload"),
      })
    },
    [uploadMutation],
  )

  const openDownloadDialog = useCallback(() => {
    if (!lightboxImage) return
    setDownloadName(getDownloadBaseName(lightboxImage))
    setDownloadDialogOpen(true)
  }, [lightboxImage])

  const handleDownloadImage = useCallback(async () => {
    if (!lightboxImage) return

    const src = getImageSrc(lightboxImage)
    if (!src) {
      toast.error("Imagem indisponível para download")
      return
    }

    try {
      setIsDownloadingImage(true)

      const response = await fetch(src, {
        credentials: "include",
      })

      if (!response.ok) {
        throw new Error("Nao foi possivel preparar o download da imagem")
      }

      const blob = await response.blob()
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement("a")

      link.href = objectUrl
      link.download = buildDownloadFilename(lightboxImage, downloadName, blob.type)
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(objectUrl)

      setDownloadDialogOpen(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao baixar imagem")
    } finally {
      setIsDownloadingImage(false)
    }
  }, [downloadName, lightboxImage])

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-50 flex-1 flex-col gap-2">
            <span className="text-sm text-(--text-secondary)">
              {data ? (
                hasActiveSearch && hasActiveFilters ? (
                  <>
                    <strong className="font-semibold text-(--text-primary)">{data.total}</strong>{" "}
                    {data.total === 1
                      ? "resultado para a busca e filtros aplicados"
                      : "resultados para a busca e filtros aplicados"}
                  </>
                ) : hasActiveSearch ? (
                  <>
                    <strong className="font-semibold text-(--text-primary)">{data.total}</strong>{" "}
                    {data.total === 1 ? "resultado para a busca" : "resultados para a busca"}
                  </>
                ) : hasActiveFilters ? (
                  <>
                    <strong className="font-semibold text-(--text-primary)">{data.total}</strong>{" "}
                    {totalImagesLabel} com os filtros aplicados
                  </>
                ) : (
                  <>
                    Total de{" "}
                    <strong className="font-semibold text-(--text-primary)">{data.total}</strong>{" "}
                    {totalImagesLabel} na galeria
                  </>
                )
              ) : (
                "Carregando imagens..."
              )}
            </span>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-(--text-tertiary)" />
              <Input
                placeholder="Buscar por título, prompt ou arquivo..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                onBlur={() => {
                  setDebouncedSearch(search)
                  setPage(1)
                }}
                className="pl-9"
              />
              {search && (
                <button
                  onClick={() => {
                    setSearch("")
                    setDebouncedSearch("")
                    setPage(1)
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                >
                  <X className="h-4 w-4 text-(--text-tertiary)" />
                </button>
              )}
            </div>
          </div>

          <div className="flex min-w-33 flex-col gap-1">
            <label className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--text-tertiary)">
              Origem
            </label>
            <Select
              value={source || "all"}
              onValueChange={(v) => {
                setSource(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-35">
                <SelectValue placeholder="Origem" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="generated">IA Gerada</SelectItem>
                <SelectItem value="uploaded">Upload</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex min-w-33 flex-col gap-1">
            <label className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--text-tertiary)">
              Estilo
            </label>
            <Select
              value={style || "all"}
              onValueChange={(v) => {
                setStyle(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-35">
                <SelectValue placeholder="Estilo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="clean">Clean</SelectItem>
                <SelectItem value="with_text">Com Texto</SelectItem>
                <SelectItem value="infographic">Infográfico</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex min-w-30.5 flex-col gap-1">
            <label className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--text-tertiary)">
              Pilar
            </label>
            <Select
              value={pillar || "all"}
              onValueChange={(v) => {
                setPillar(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-32.5">
                <SelectValue placeholder="Pilar" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="authority">Autoridade</SelectItem>
                <SelectItem value="case">Case</SelectItem>
                <SelectItem value="vision">Visão</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex min-w-33 flex-col gap-1">
            <label className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--text-tertiary)">
              Status
            </label>
            <Select
              value={status || "all"}
              onValueChange={(v) => {
                setStatus(v === "all" ? "" : v)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-35">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="draft">Rascunho</SelectItem>
                <SelectItem value="approved">Aprovado</SelectItem>
                <SelectItem value="scheduled">Agendado</SelectItem>
                <SelectItem value="published">Publicado</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="ml-auto flex flex-wrap gap-2">
            <Button onClick={() => setGenerateOpen(true)}>
              <Sparkles className="mr-2 h-4 w-4" />
              Gerar com IA
            </Button>
            <label className="cursor-pointer">
              <Button asChild>
                <span>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload
                </span>
              </Button>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleUpload(file)
                }}
              />
            </label>
          </div>
        </div>
      </div>

      {error ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="mb-2 text-red-500">Erro ao carregar galeria</p>
          <p className="mb-4 text-sm text-(--text-secondary)">
            {error instanceof Error ? error.message : "Erro desconhecido"}
          </p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Tentar novamente
          </Button>
        </div>
      ) : isLoading ? (
        <div className={GALLERY_GRID_CLASS}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="aspect-4/5 animate-pulse rounded-lg bg-(--bg-secondary)" />
          ))}
        </div>
      ) : data && data.images.length > 0 ? (
        <>
          <div className={GALLERY_GRID_CLASS}>
            {data.images.map((image) => (
              <GalleryCard
                key={image.post_id}
                image={image}
                onView={() => setLightboxImage(image)}
                onDelete={(e) => handleDelete(image, e)}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 pt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                Anterior
              </Button>
              <span className="text-sm text-(--text-secondary)">
                {page} de {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <ImageIcon className="mb-4 h-16 w-16 text-(--text-tertiary)" />
          <h3 className="mb-1 text-lg font-medium text-(--text-primary)">
            Nenhuma imagem encontrada
          </h3>
          <p className="mb-6 max-w-md text-sm text-(--text-secondary)">
            Gere imagens com IA ou faça upload de arquivos para começar sua galeria.
          </p>
          <div className="flex gap-2">
            <Button onClick={() => setGenerateOpen(true)}>
              <Sparkles className="mr-2 h-4 w-4" />
              Gerar com IA
            </Button>
            <label className="cursor-pointer">
              <Button variant="outline" asChild>
                <span>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload
                </span>
              </Button>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleUpload(file)
                }}
              />
            </label>
          </div>
        </div>
      )}

      <GenerateImageDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        generateMutation={generateMutation}
        onGenerated={() => {
          setPage(1)
          setGenerateOpen(false)
        }}
      />

      <Dialog
        open={!!lightboxImage}
        onOpenChange={() => {
          setLightboxImage(null)
          setDownloadDialogOpen(false)
        }}
      >
        <DialogContent
          className="w-full max-w-4xl gap-0 overflow-y-hidden! border-0 bg-black/95 p-0 [&>button]:hidden"
          aria-describedby="lightbox-desc"
        >
          {lightboxImage && (
            <div className="flex flex-col" style={{ maxHeight: "85vh" }}>
              <div className="flex shrink-0 items-center justify-between gap-3 border-b border-white/10 px-3 py-2">
                <span className="max-w-[60%] truncate text-xs font-medium text-white">
                  {lightboxImage.post_title}
                </span>
                <div className="flex shrink-0 items-center gap-1">
                  <Link
                    href={`/content/posts?edit=${lightboxImage.post_id}` as Route}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/12 text-white/70 transition-colors hover:bg-white/22 hover:text-white"
                    title="Editar post"
                  >
                    <ExternalLink className="h-4.5 w-4.5" />
                  </Link>
                  <button
                    type="button"
                    onClick={openDownloadDialog}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/12 text-white/70 transition-colors hover:bg-white/22 hover:text-white"
                    title="Download"
                  >
                    <Download className="h-4.5 w-4.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setImagePendingDelete(lightboxImage)}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-red-500/18 text-red-100 transition-colors hover:bg-red-500/32 hover:text-white"
                    title="Excluir imagem"
                  >
                    <Trash2 className="h-4.5 w-4.5" />
                  </button>
                  <DialogClose className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/16 text-white/80 transition-colors hover:bg-white/28 hover:text-white focus:outline-none focus:ring-2 focus:ring-white/40 focus:ring-offset-0">
                    <X className="h-4.5 w-4.5" />
                    <span className="sr-only">Fechar</span>
                  </DialogClose>
                </div>
              </div>

              <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden">
                <img
                  src={getImageSrc(lightboxImage)}
                  alt={lightboxImage.post_title}
                  className="object-contain"
                  style={{ maxWidth: "100%", maxHeight: "calc(85vh - 70px)" }}
                />
              </div>

              <div
                id="lightbox-desc"
                className="flex shrink-0 flex-col gap-2 border-t border-white/10 bg-black/60 px-3 py-2.5"
              >
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-medium text-white/85">
                  <span className="rounded-full bg-white/10 px-2 py-1">
                    {lightboxImage.source === "generated" ? "IA Gerada" : "Upload"}
                  </span>
                  {lightboxImage.image_style && (
                    <span className="rounded-full bg-white/10 px-2 py-1">
                      {lightboxImage.image_style}
                    </span>
                  )}
                  {lightboxImage.image_aspect_ratio && (
                    <span className="rounded-full bg-white/10 px-2 py-1">
                      {lightboxImage.image_aspect_ratio}
                    </span>
                  )}
                  {lightboxImage.image_size_bytes && (
                    <span className="rounded-full bg-white/10 px-2 py-1">
                      {formatBytes(lightboxImage.image_size_bytes)}
                    </span>
                  )}
                </div>
                {lightboxImage.image_prompt && (
                  <p className="line-clamp-2 text-xs leading-relaxed text-white/72">
                    {lightboxImage.image_prompt}
                  </p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={downloadDialogOpen} onOpenChange={setDownloadDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Nome do arquivo para download</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-4 pt-2">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-(--text-primary)">Nome da imagem</label>
              <Input
                value={downloadName}
                onChange={(e) => setDownloadName(e.target.value)}
                placeholder="Digite o nome do arquivo"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleDownloadImage()
                  }
                }}
                autoFocus
              />
              <p className="text-xs text-(--text-secondary)">
                A extensão será mantida automaticamente no download.
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDownloadDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleDownloadImage} disabled={isDownloadingImage}>
                {isDownloadingImage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Baixando...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Baixar imagem
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={!!imagePendingDelete}
        onOpenChange={(open) => {
          if (!open && !deleteMutation.isPending) {
            setImagePendingDelete(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {imagePendingDelete && isDeleteBlockedForImage(imagePendingDelete)
                ? "Imagem vinculada a post ativo"
                : imagePendingDelete && hasLinkedPostWarning(imagePendingDelete)
                  ? "Excluir imagem vinculada"
                  : "Excluir imagem da galeria"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {imagePendingDelete ? getDeleteDialogDescription(imagePendingDelete) : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              {imagePendingDelete && isDeleteBlockedForImage(imagePendingDelete)
                ? "Fechar"
                : "Cancelar"}
            </AlertDialogCancel>
            {imagePendingDelete && !isDeleteBlockedForImage(imagePendingDelete) && (
              <AlertDialogAction
                onClick={(e) => {
                  e.preventDefault()
                  confirmDeleteImage()
                }}
                disabled={deleteMutation.isPending}
                className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"
              >
                {deleteMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Excluindo...
                  </>
                ) : (
                  "Excluir imagem"
                )}
              </AlertDialogAction>
            )}
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function GalleryCard({
  image,
  onView,
  onDelete,
}: {
  image: GalleryImage
  onView: () => void
  onDelete: (e: React.MouseEvent) => void
}) {
  return (
    <div
      className="group relative aspect-4/5 cursor-pointer overflow-hidden rounded-xl border border-(--border-default) bg-(--bg-secondary) shadow-(--shadow-sm) transition-all hover:border-(--accent) hover:shadow-(--shadow-md)"
      onClick={onView}
    >
      <img
        src={getImageSrc(image)}
        alt={image.post_title}
        className="h-full w-full object-cover"
        loading="lazy"
      />

      <div className="absolute inset-0 bg-linear-to-t from-black/88 via-black/36 to-transparent opacity-90 transition-opacity group-hover:opacity-100" />

      <div className="absolute left-2 top-2 flex gap-1.5">
        {image.source === "generated" ? (
          <span className="rounded-full bg-purple-600/90 px-2 py-1 text-[10px] font-semibold text-white shadow-sm">
            IA
          </span>
        ) : (
          <span className="rounded-full bg-blue-600/90 px-2 py-1 text-[10px] font-semibold text-white shadow-sm">
            Upload
          </span>
        )}
        {image.image_style && (
          <span className="rounded-full border border-white/10 bg-black/45 px-2 py-1 text-[10px] font-semibold text-white backdrop-blur-sm">
            {image.image_style}
          </span>
        )}
      </div>

      <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onView()
          }}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur-sm transition-colors hover:bg-white/25"
          title="Visualizar"
        >
          <Eye className="h-4 w-4" />
        </button>
        <button
          onClick={onDelete}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur-sm transition-colors hover:bg-red-500/70"
          title="Excluir"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-1.5 p-3">
        <span className="line-clamp-2 text-sm font-semibold leading-tight text-white drop-shadow-sm">
          {image.post_title}
        </span>
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-medium text-white/78">
          <span className="rounded-full bg-black/35 px-2 py-1 backdrop-blur-sm">
            {image.source === "generated" ? "Gerada por IA" : "Upload"}
          </span>
          {image.image_aspect_ratio && (
            <span className="rounded-full bg-black/35 px-2 py-1 backdrop-blur-sm">
              {image.image_aspect_ratio}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function GenerateImageDialog({
  open,
  onOpenChange,
  generateMutation,
  onGenerated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  generateMutation: ReturnType<typeof useGenerateStandaloneImage>
  onGenerated: () => void
}) {
  const [prompt, setPrompt] = useState("")
  const [style, setStyle] = useState<ImageStyle>("clean")
  const [aspectRatio, setAspectRatio] = useState<ImageAspectRatio>("4:5")
  const [subType, setSubType] = useState<ImageSubType | null>(null)
  const [visualDirection, setVisualDirection] = useState<ImageVisualDirection>("auto")
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null)

  const handleGenerate = () => {
    if (!prompt.trim()) {
      toast.error("Digite um prompt para gerar a imagem")
      return
    }

    generateMutation.mutate(
      {
        prompt: prompt.trim(),
        style,
        aspect_ratio: aspectRatio,
        sub_type: style === "infographic" ? subType : null,
        visual_direction: visualDirection,
      },
      {
        onSuccess: (generatedImage) => {
          setGeneratedUrl(generatedImage.image_url)
          toast.success("Imagem gerada com sucesso!")
          onGenerated()
        },
        onError: (err) => toast.error(err instanceof Error ? err.message : "Erro ao gerar"),
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-(--accent)" />
            Gerar Imagem com IA
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4 pt-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-(--text-primary)">Estilo</label>
            <Tabs value={style} onValueChange={(v) => setStyle(v as ImageStyle)}>
              <TabsList className="w-full">
                <TabsTrigger value="clean" className="flex-1">
                  Clean
                </TabsTrigger>
                <TabsTrigger value="with_text" className="flex-1">
                  Com Texto
                </TabsTrigger>
                <TabsTrigger value="infographic" className="flex-1">
                  Infográfico
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {style === "infographic" && (
            <div>
              <label className="mb-1.5 block text-sm font-medium text-(--text-primary)">
                Tipo de Infográfico
              </label>
              <Tabs
                value={subType ?? "metrics"}
                onValueChange={(v) => setSubType(v as ImageSubType)}
              >
                <TabsList className="w-full">
                  <TabsTrigger value="metrics" className="flex-1">
                    Métricas
                  </TabsTrigger>
                  <TabsTrigger value="steps" className="flex-1">
                    Passos
                  </TabsTrigger>
                  <TabsTrigger value="comparison" className="flex-1">
                    Comparação
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium text-(--text-primary)">
              Prompt / Título
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={
                style === "with_text"
                  ? "Título que aparecerá na imagem..."
                  : "Descreva o conceito visual da imagem..."
              }
              rows={3}
              className="w-full resize-none rounded-md border border-(--border-default) bg-(--bg-secondary) px-3 py-2 text-sm text-(--text-primary) placeholder:text-(--text-tertiary) focus:outline-none focus:ring-2 focus:ring-(--accent)"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-(--text-primary)">
                Proporção
              </label>
              <Select
                value={aspectRatio}
                onValueChange={(v) => setAspectRatio(v as ImageAspectRatio)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="4:5">4:5 (LinkedIn)</SelectItem>
                  <SelectItem value="1:1">1:1 (Quadrado)</SelectItem>
                  <SelectItem value="16:9">16:9 (Paisagem)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-(--text-primary)">
                Direção Visual
              </label>
              <Select
                value={visualDirection}
                onValueChange={(v) => setVisualDirection(v as ImageVisualDirection)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Automática</SelectItem>
                  <SelectItem value="editorial">Editorial</SelectItem>
                  <SelectItem value="minimal">Minimalista</SelectItem>
                  <SelectItem value="bold">Impactante</SelectItem>
                  <SelectItem value="organic">Orgânico</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {generatedUrl && (
            <div className="overflow-hidden rounded-lg border border-(--border-default) bg-(--bg-secondary)">
              <img src={generatedUrl} alt="Preview" className="max-h-64 w-full object-contain" />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Fechar
            </Button>
            <Button onClick={handleGenerate} disabled={generateMutation.isPending}>
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Gerando...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Gerar Imagem
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function getDeleteDialogDescription(image: GalleryImage): string {
  const title = image.post_title.trim() || "este post"

  if (isDeleteBlockedForImage(image)) {
    return `A imagem do post \"${title}\" esta com status ${getGalleryPostStatusLabel(image.post_status).toLowerCase()} e nao pode ser removida da galeria agora. Altere o status do post antes de excluir a imagem.`
  }

  if (hasLinkedPostWarning(image)) {
    return `Esta imagem esta vinculada ao post \"${title}\". Se continuar, o post continuara no calendario, mas ficara sem a imagem associada.`
  }

  return "Esta imagem nao esta vinculada a nenhum post e sera removida permanentemente da galeria."
}

function isDeleteBlockedForImage(image: GalleryImage): boolean {
  return image.post_status === "scheduled" || image.post_status === "published"
}

function hasLinkedPostWarning(image: GalleryImage): boolean {
  return image.post_status !== "draft"
}

function getGalleryPostStatusLabel(status: string): string {
  switch (status) {
    case "approved":
      return "Aprovado"
    case "scheduled":
      return "Agendado"
    case "published":
      return "Publicado"
    case "failed":
      return "Falhou"
    case "draft":
    default:
      return "Rascunho"
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getDownloadBaseName(image: GalleryImage): string {
  const rawName = image.image_filename ?? image.post_title ?? "imagem-galeria"
  return sanitizeFileName(stripFileExtension(rawName))
}

function buildDownloadFilename(image: GalleryImage, typedName: string, mimeType?: string): string {
  const baseName = sanitizeFileName(typedName || getDownloadBaseName(image))
  const extension =
    getFileExtension(image.image_filename) ||
    getFileExtension(getImageSrc(image)) ||
    getExtensionFromMimeType(mimeType) ||
    "png"
  return `${baseName}.${extension}`
}

function getFileExtension(value: string | null | undefined): string {
  if (!value) return ""

  const normalizedValue = (value.includes("?") ? value.split("?")[0] : value) || ""
  const lastSegment = normalizedValue.split("/").pop() || normalizedValue
  const extension = lastSegment.split(".").pop()

  if (!extension || extension === lastSegment) return ""
  return extension.toLowerCase()
}

function stripFileExtension(value: string): string {
  return value.replace(/\.[^.]+$/, "")
}

function sanitizeFileName(value: string): string {
  const normalizedValue = value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[<>:"/\\|?*]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()

  return normalizedValue || "imagem-galeria"
}

function getExtensionFromMimeType(mimeType: string | undefined): string {
  switch (mimeType) {
    case "image/jpeg":
      return "jpg"
    case "image/png":
      return "png"
    case "image/webp":
      return "webp"
    case "image/gif":
      return "gif"
    case "image/svg+xml":
      return "svg"
    default:
      return ""
  }
}
