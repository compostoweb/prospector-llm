"use client"

/**
 * CarouselEditor — Editor visual de carrossel multi-imagem (até 9).
 *
 * Permite:
 * - Adicionar imagens via upload (input file)
 * - Reordenar com drag-drop nativo HTML5 (sem dependências adicionais)
 * - Remover imagens individuais
 * - Mostra contador n/9 e validação visual de mínimo 2 imagens
 */

import { GripVertical, ImagePlus, Loader2, Plus, Trash2, X } from "lucide-react"
import Image from "next/image"
import { useRef, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  CarouselImageItem,
  useAddCarouselImage,
  useRemoveCarouselImage,
  useReorderCarousel,
} from "@/lib/api/hooks/use-content"

const MAX_IMAGES = 9
const MIN_IMAGES_TO_PUBLISH = 2

interface CarouselEditorProps {
  postId: string
  images: CarouselImageItem[]
  onImportFromGallery?: () => void
  disabled?: boolean
}

export function CarouselEditor({
  postId,
  images,
  onImportFromGallery,
  disabled = false,
}: CarouselEditorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [overIndex, setOverIndex] = useState<number | null>(null)
  // Ordenação local otimista durante drag — base = images ordenadas por position
  const sorted = [...images].sort((a, b) => a.position - b.position)

  const addImage = useAddCarouselImage()
  const removeImage = useRemoveCarouselImage()
  const reorder = useReorderCarousel()

  const isUploading = addImage.isPending
  const isReordering = reorder.isPending
  const isRemoving = removeImage.isPending
  const isBusy = disabled || isUploading || isReordering || isRemoving

  const handleAddClick = () => {
    if (sorted.length >= MAX_IMAGES) {
      toast.error(`Máximo de ${MAX_IMAGES} imagens (limite do LinkedIn).`)
      return
    }
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    // Permite múltiplos uploads sequenciais respeitando limite
    const remaining = MAX_IMAGES - sorted.length
    const toUpload = Array.from(files).slice(0, remaining)
    for (const file of toUpload) {
      try {
        await addImage.mutateAsync({ postId, file })
      } catch {
        // Erro já é exibido via toast no hook
        break
      }
    }
    // Reset input para permitir reupload do mesmo arquivo
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleRemove = (imageId: string) => {
    removeImage.mutate({ postId, imageId })
  }

  // ── Drag & Drop nativo ─────────────────────────────────────────────
  const handleDragStart = (index: number) => (e: React.DragEvent) => {
    setDraggedIndex(index)
    e.dataTransfer.effectAllowed = "move"
    // Firefox precisa de setData
    e.dataTransfer.setData("text/plain", String(index))
  }

  const handleDragOver = (index: number) => (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
    if (draggedIndex !== null && draggedIndex !== index) {
      setOverIndex(index)
    }
  }

  const handleDragLeave = () => {
    setOverIndex(null)
  }

  const handleDrop = (dropIndex: number) => (e: React.DragEvent) => {
    e.preventDefault()
    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null)
      setOverIndex(null)
      return
    }
    const newOrder = [...sorted]
    const [moved] = newOrder.splice(draggedIndex, 1)
    if (moved) newOrder.splice(dropIndex, 0, moved)
    setDraggedIndex(null)
    setOverIndex(null)
    reorder.mutate({ postId, order: newOrder.map((img) => img.id) })
  }

  const handleDragEnd = () => {
    setDraggedIndex(null)
    setOverIndex(null)
  }

  const tooFewImages = sorted.length > 0 && sorted.length < MIN_IMAGES_TO_PUBLISH

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Carrossel</span>
          <span
            className={`text-xs ${
              sorted.length >= MAX_IMAGES
                ? "text-amber-600"
                : tooFewImages
                  ? "text-red-600"
                  : "text-muted-foreground"
            }`}
          >
            {sorted.length}/{MAX_IMAGES}
            {tooFewImages && ` — mínimo ${MIN_IMAGES_TO_PUBLISH} para publicar`}
          </span>
        </div>
        <div className="flex gap-2">
          {onImportFromGallery && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onImportFromGallery}
              disabled={isBusy || sorted.length >= MAX_IMAGES}
            >
              <ImagePlus className="mr-1 h-4 w-4" /> Importar da galeria
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddClick}
            disabled={isBusy || sorted.length >= MAX_IMAGES}
          >
            {isUploading ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <Plus className="mr-1 h-4 w-4" />
            )}
            Adicionar imagem
          </Button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {sorted.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-muted p-8 text-center text-sm text-muted-foreground">
          Nenhuma imagem ainda. Adicione pelo menos {MIN_IMAGES_TO_PUBLISH} imagens para publicar
          este carrossel.
        </div>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {sorted.map((img, index) => {
            const isDragging = draggedIndex === index
            const isOver = overIndex === index && draggedIndex !== index
            return (
              <div
                key={img.id}
                draggable={!isBusy}
                onDragStart={handleDragStart(index)}
                onDragOver={handleDragOver(index)}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop(index)}
                onDragEnd={handleDragEnd}
                className={`group relative shrink-0 cursor-move rounded-md border-2 transition-all ${
                  isDragging
                    ? "opacity-40"
                    : isOver
                      ? "border-primary scale-105"
                      : "border-transparent"
                }`}
                style={{ width: 140, height: 140 }}
              >
                <div className="relative h-full w-full overflow-hidden rounded-md bg-muted">
                  <Image
                    src={img.image_url}
                    alt={`Imagem ${index + 1}`}
                    fill
                    sizes="140px"
                    className="object-cover"
                    unoptimized
                  />
                </div>
                {/* Badge posição */}
                <div className="absolute left-1 top-1 rounded bg-black/70 px-1.5 py-0.5 text-xs font-medium text-white">
                  {index + 1}
                </div>
                {/* Handle de drag */}
                <div className="absolute right-1 top-1 rounded bg-black/70 p-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <GripVertical className="h-3 w-3 text-white" />
                </div>
                {/* Remover */}
                <button
                  type="button"
                  onClick={() => handleRemove(img.id)}
                  disabled={isBusy}
                  className="absolute bottom-1 right-1 rounded bg-red-500 p-1 opacity-0 transition-opacity hover:bg-red-600 group-hover:opacity-100 disabled:opacity-50"
                  title="Remover imagem"
                >
                  <Trash2 className="h-3 w-3 text-white" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {(isReordering || isRemoving) && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          {isReordering ? "Reordenando..." : "Removendo..."}
        </div>
      )}
    </div>
  )
}

// Re-export para uso em outros componentes
export { MAX_IMAGES as CAROUSEL_MAX_IMAGES, MIN_IMAGES_TO_PUBLISH as CAROUSEL_MIN_IMAGES }

// Suprime warning de import não usado dos ícones reservados para extensão futura
const _IconsReserved = { X }
void _IconsReserved
