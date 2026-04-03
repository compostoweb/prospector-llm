"use client"

/* eslint-disable @next/next/no-img-element */

/**
 * ResizableImage — extensão Tiptap com redimensionamento via drag lateral.
 *
 * HTML gerado: <img src="..." width="300" style="width:300px;max-width:100%">
 * Compatível com clientes de e-mail (atributo width + inline style).
 */

import { useCallback, useEffect, useRef, useState } from "react"
import Image from "@tiptap/extension-image"
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react"
import type { NodeViewProps } from "@tiptap/react"
import { cn } from "@/lib/utils"

// ── NodeView ──────────────────────────────────────────────────────────

function ResizableImageView({ node, updateAttributes, selected }: NodeViewProps) {
  const containerRef = useRef<HTMLSpanElement>(null)
  const [localWidth, setLocalWidth] = useState<number | null>(
    node.attrs.width ? Number(node.attrs.width) : null,
  )

  // Captura largura natural na primeira renderização (sem width definido)
  useEffect(() => {
    if (localWidth !== null) return
    const img = containerRef.current?.querySelector("img")
    if (!img) return

    const capture = () => {
      const w = img.naturalWidth
      if (w > 0) {
        const initial = Math.min(w, 560)
        setLocalWidth(initial)
        updateAttributes({ width: initial })
      }
    }

    if (img.complete) capture()
    else img.addEventListener("load", capture, { once: true })
  }, [localWidth, updateAttributes])

  const startResize = useCallback(
    (e: React.MouseEvent<HTMLSpanElement>) => {
      e.preventDefault()
      e.stopPropagation()

      const startX = e.clientX
      const startWidth = containerRef.current?.offsetWidth ?? localWidth ?? 200

      const onMove = (ev: MouseEvent) => {
        const newW = Math.max(48, startWidth + (ev.clientX - startX))
        setLocalWidth(newW)
      }

      const onUp = () => {
        const finalW = containerRef.current?.offsetWidth ?? localWidth
        if (finalW) updateAttributes({ width: Math.round(finalW) })
        document.removeEventListener("mousemove", onMove)
        document.removeEventListener("mouseup", onUp)
      }

      document.addEventListener("mousemove", onMove)
      document.addEventListener("mouseup", onUp)
    },
    [localWidth, updateAttributes],
  )

  return (
    <NodeViewWrapper
      ref={containerRef}
      as="span"
      data-drag-handle
      className={cn(
        "relative inline-block max-w-full align-bottom",
        selected && "ring-2 ring-(--accent) ring-offset-1",
      )}
      style={localWidth ? { width: `${localWidth}px` } : undefined}
    >
      <img
        src={node.attrs.src as string}
        alt={(node.attrs.alt as string | undefined) ?? ""}
        title={(node.attrs.title as string | undefined) ?? undefined}
        className="block h-auto w-full"
        draggable={false}
      />

      {/* Handle de redimensionamento — lado direito */}
      {selected && (
        <span
          onMouseDown={startResize}
          title="Arrastar para redimensionar"
          className="-right-1.5 absolute top-1/2 flex h-7 w-3 -translate-y-1/2 cursor-ew-resize items-center justify-center rounded bg-(--accent) shadow-md"
        >
          <span className="h-3 w-0 border-l border-r border-dotted border-white/80" />
        </span>
      )}

      {/* Badge de largura */}
      {selected && localWidth && (
        <span className="pointer-events-none absolute bottom-1 right-4 select-none rounded bg-black/60 px-1 py-0.5 text-[10px] leading-none text-white">
          {localWidth}px
        </span>
      )}
    </NodeViewWrapper>
  )
}

// ── Extensão ──────────────────────────────────────────────────────────

export const ResizableImage = Image.extend({
  inline: true,
  group: "inline",

  addAttributes() {
    return {
      ...this.parent?.(),
      width: {
        default: null,
        parseHTML: (el) => {
          const w = el.getAttribute("width") ?? el.style.width?.replace("px", "")
          return w ? parseInt(w) : null
        },
        renderHTML: (attrs) => {
          if (!attrs.width) return {}
          return {
            width: String(attrs.width),
            style: `width:${attrs.width}px;max-width:100%`,
          }
        },
      },
    }
  },

  addNodeView() {
    return ReactNodeViewRenderer(ResizableImageView)
  },
})
