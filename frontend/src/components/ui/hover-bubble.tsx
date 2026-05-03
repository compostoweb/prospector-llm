"use client"

import { type ReactNode, useState } from "react"
import { createPortal } from "react-dom"
import { cn } from "@/lib/utils"

interface HoverBubbleProps {
  children: ReactNode
  content: ReactNode
  side?: "right" | "top" | "bottom"
  align?: "center" | "start"
  className?: string
  contentClassName?: string
  sideOffset?: number
}

export function HoverBubble({
  children,
  content,
  side = "right",
  align = "center",
  className,
  contentClassName,
  sideOffset = 12,
}: HoverBubbleProps) {
  const [rect, setRect] = useState<DOMRect | null>(null)

  const top = rect
    ? side === "top"
      ? rect.top - sideOffset
      : side === "bottom"
        ? rect.bottom + sideOffset
        : align === "start"
          ? rect.top
          : rect.top + rect.height / 2
    : 0

  const left = rect
    ? side === "right"
      ? rect.right + sideOffset
      : rect.left + rect.width / 2
    : 0

  const transform = side === "right"
    ? align === "start"
      ? "translateY(0)"
      : "translateY(-50%)"
    : side === "top"
      ? "translate(-50%, -100%)"
      : "translateX(-50%)"

  return (
    <span
      className={cn("inline-flex", className)}
      onMouseEnter={(event) => setRect(event.currentTarget.getBoundingClientRect())}
      onMouseLeave={() => setRect(null)}
      onFocus={(event) => setRect(event.currentTarget.getBoundingClientRect())}
      onBlur={() => setRect(null)}
    >
      {children}
      {rect && typeof document !== "undefined"
        ? createPortal(
            <div
              className={cn(
                "app-tooltip fixed max-w-72 rounded-[14px] border px-3 py-2 text-sm font-medium leading-snug shadow-lg",
                contentClassName,
              )}
              style={{ top, left, transform, zIndex: 2147483647 }}
              role="tooltip"
            >
              {content}
            </div>,
            document.body,
          )
        : null}
    </span>
  )
}
