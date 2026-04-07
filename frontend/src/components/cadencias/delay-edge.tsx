"use client"

import { memo } from "react"
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from "@xyflow/react"
import { Clock, Plus } from "lucide-react"

export interface DelayEdgeData {
  dayOffset: number
  sourceIndex: number
  onInsertAfter?: (sourceIndex: number) => void
}

export const DelayEdge = memo(function DelayEdge({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  data,
}: EdgeProps) {
  const d = data as unknown as DelayEdgeData
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.25,
  })

  const dayOffset = d?.dayOffset ?? 0
  const isImmediate = dayOffset === 0
  const label = isImmediate ? "Imediato" : `${dayOffset} dia${dayOffset > 1 ? "s" : ""}`

  return (
    <>
      <BaseEdge id={id} path={edgePath} className="[&]:stroke-slate-400 [&]:stroke-[2.5]" />

      <EdgeLabelRenderer>
        <div
          className="nodrag nopan pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2"
          style={{ left: labelX, top: labelY, zIndex: 1000 }} // required by ReactFlow EdgeLabelRenderer
        >
          <div className="group flex flex-col items-center gap-1.5">
            {/* Badge de intervalo */}
            <div className="flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5 text-sm font-semibold text-orange-600 shadow-sm">
              <Clock size={13} strokeWidth={2.5} />
              {label}
            </div>

            {/* Botão inserir passo */}
            {d?.onInsertAfter && (
              <button
                type="button"
                onClick={() => d.onInsertAfter?.(d.sourceIndex)}
                className="flex h-5 w-5 items-center justify-center rounded-full border border-dashed border-slate-300 bg-white text-slate-400 opacity-0 shadow-sm transition-all hover:border-blue-400 hover:text-blue-600 group-hover:opacity-100"
                title="Inserir passo aqui"
                aria-label="Inserir passo entre estes dois"
              >
                <Plus size={10} />
              </button>
            )}
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  )
})
