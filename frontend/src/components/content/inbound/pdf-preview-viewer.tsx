"use client"

import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface RenderedPdfPage {
  pageNumber: number
  imageUrl: string
  width: number
  height: number
}

interface PdfPreviewViewerProps {
  fileData: Uint8Array
  className?: string
}

export default function PdfPreviewViewer({ fileData, className }: PdfPreviewViewerProps) {
  const [pages, setPages] = useState<RenderedPdfPage[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function renderPdf() {
      setPages([])
      setIsLoading(true)
      setError(null)

      try {
        const pdfData = fileData.slice()
        const pdfjs = await import("pdfjs-dist/legacy/build/pdf.mjs")
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs"
        const loadingTask = pdfjs.getDocument({ data: pdfData })
        const pdfDocument = await loadingTask.promise
        const nextPages: RenderedPdfPage[] = []

        for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber += 1) {
          const page = await pdfDocument.getPage(pageNumber)
          const viewport = page.getViewport({ scale: 1.25 })
          const canvas = document.createElement("canvas")
          const context = canvas.getContext("2d")

          if (!context) {
            throw new Error("Canvas indisponível para renderizar o PDF")
          }

          const pixelRatio = window.devicePixelRatio || 1
          canvas.width = Math.floor(viewport.width * pixelRatio)
          canvas.height = Math.floor(viewport.height * pixelRatio)
          context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

          await page.render({ canvas, canvasContext: context, viewport }).promise

          nextPages.push({
            pageNumber,
            imageUrl: canvas.toDataURL("image/png"),
            width: viewport.width,
            height: viewport.height,
          })
        }

        await pdfDocument.destroy()

        if (cancelled) {
          return
        }

        setPages(nextPages)
      } catch (cause) {
        if (cancelled) {
          return
        }

        setError(cause instanceof Error ? cause.message : "Falha ao renderizar o PDF")
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void renderPdf()

    return () => {
      cancelled = true
    }
  }, [fileData])

  if (isLoading) {
    return (
      <div className={cn("flex h-full items-center justify-center", className)}>
        <div className="flex items-center gap-2 text-sm text-(--text-secondary)">
          <Loader2 className="h-4 w-4 animate-spin" />
          Renderizando PDF...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className={cn(
          "flex h-full items-center justify-center rounded-lg border border-dashed border-(--border-default) bg-(--bg-surface) p-6 text-center text-sm text-(--text-secondary)",
          className,
        )}
      >
        {error}
      </div>
    )
  }

  return (
    <div className={cn("h-full overflow-y-auto rounded-lg bg-(--bg-page)", className)}>
      <div className="mx-auto flex max-w-4xl flex-col gap-6 py-4">
        {pages.map((page) => (
          <div
            key={page.pageNumber}
            className="overflow-hidden rounded-xl border border-(--border-default) bg-white shadow-sm"
          >
            <div className="border-b border-(--border-default) px-4 py-2 text-xs font-medium text-(--text-tertiary)">
              Página {page.pageNumber}
            </div>
            <img
              src={page.imageUrl}
              alt={`Página ${page.pageNumber} do PDF`}
              width={page.width}
              height={page.height}
              className="h-auto w-full"
            />
          </div>
        ))}
      </div>
    </div>
  )
}