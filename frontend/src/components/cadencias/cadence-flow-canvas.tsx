"use client"

import { useCallback, useEffect, useMemo, useRef } from "react"
import {
  ReactFlow,
  Background,
  Controls,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { Mail, Linkedin, MessageSquare, ClipboardList, Plus } from "lucide-react"
import type { CadenceChannel, CadenceStep } from "@/lib/api/hooks/use-cadences"
import { StepNode, type StepNodeData } from "@/components/cadencias/step-node"
import { DelayEdge } from "@/components/cadencias/delay-edge"
import { cn } from "@/lib/utils"

const NODE_TYPES: NodeTypes = {
  stepNode: StepNode,
}

const EDGE_TYPES: EdgeTypes = {
  delayEdge: DelayEdge,
}

// Layout constants
const NODE_WIDTH = 320
const NODE_X = 0
const START_Y = 0
const STEP_STRIDE = 280
const START_NODE_HEIGHT = 48
const NODE_ESTIMATED_HEIGHT = 180
const NODE_MIN_VERTICAL_GAP = 28
const NODE_COLUMN_THRESHOLD = 220

function positionsMatch(a: { x: number; y: number }, b: { x: number; y: number }): boolean {
  return Math.abs(a.x - b.x) < 1 && Math.abs(a.y - b.y) < 1
}

function getStepInvalidReason(step: CadenceStep): string | null {
  const hasManualText = step.message_template.trim().length > 0

  if (step.use_voice && step.audio_file_id) {
    return null
  }

  if (hasManualText || step.email_template_id) {
    return null
  }

  if (step.use_voice) {
    return "Nenhum audio gravado ou texto manual foi definido. Neste caso, o sistema vai gerar o roteiro com IA e converter em voz via TTS no envio."
  }

  return "Nenhum conteudo manual foi definido. Este passo vai usar geracao automatica por IA no envio."
}

function normalizeStepNodeSpacing(nodes: Node[]): Node[] {
  const stepNodes = nodes
    .filter((node) => node.type === "stepNode")
    .map((node) => ({
      ...node,
      position: { ...node.position },
    }))

  const columns: Node[][] = []

  for (const node of [...stepNodes].sort((a, b) => a.position.x - b.position.x)) {
    const existingColumn = columns.find(
      (column) => Math.abs(column[0]?.position.x ?? 0 - node.position.x) <= NODE_COLUMN_THRESHOLD,
    )

    if (existingColumn) {
      existingColumn.push(node)
    } else {
      columns.push([node])
    }
  }

  for (const column of columns) {
    column.sort((a, b) => a.position.y - b.position.y)

    let previousBottom: number | null = null
    for (const node of column) {
      if (previousBottom !== null) {
        const minY = previousBottom + NODE_MIN_VERTICAL_GAP
        if (node.position.y < minY) {
          node.position.y = minY
        }
      }

      previousBottom = node.position.y + NODE_ESTIMATED_HEIGHT
    }
  }

  const normalizedNodeMap = new Map(stepNodes.map((node) => [node.id, node]))
  return nodes.map((node) => normalizedNodeMap.get(node.id) ?? node)
}

// Canais disponíveis no toolbar lateral
const TOOLBAR_CHANNELS: {
  channel: CadenceChannel
  label: string
  icon: React.ReactNode
  colorClass: string
}[] = [
  {
    channel: "email",
    label: "E-mail",
    icon: <Mail size={14} />,
    colorClass: "text-green-700 hover:bg-green-50",
  },
  {
    channel: "linkedin_connect",
    label: "Conectar",
    icon: <Linkedin size={14} />,
    colorClass: "text-blue-700 hover:bg-blue-50",
  },
  {
    channel: "linkedin_dm",
    label: "DM",
    icon: <MessageSquare size={14} />,
    colorClass: "text-blue-700 hover:bg-blue-50",
  },
  {
    channel: "manual_task",
    label: "Tarefa",
    icon: <ClipboardList size={14} />,
    colorClass: "text-amber-700 hover:bg-amber-50",
  },
]

interface CadenceFlowCanvasProps {
  steps: CadenceStep[]
  selectedIndex: number | null
  onSelectStep: (index: number) => void
  onStepPositionChange: (index: number, position: { x: number; y: number }) => void
  onAddStep: (channel?: CadenceChannel) => void
  onInsertAfter: (afterIndex: number) => void
  onDeleteStep: (index: number) => void
  onDuplicateStep: (index: number) => void
  onMoveUp: (index: number) => void
  onMoveDown: (index: number) => void
}

export function CadenceFlowCanvas({
  steps,
  selectedIndex,
  onSelectStep,
  onStepPositionChange,
  onAddStep,
  onInsertAfter,
  onDeleteStep,
  onDuplicateStep,
  onMoveUp,
  onMoveDown,
}: CadenceFlowCanvasProps) {
  // ─── Nodos canônicos (derivados dos steps) ────────────────────────
  const computedNodes = useMemo<Node[]>(() => {
    const allNodes: Node[] = []

    // Nó START
    allNodes.push({
      id: "start",
      type: "default",
      position: { x: NODE_X, y: START_Y },
      data: { label: "Início da Cadência" },
      style: {
        background: "#f0fdf4",
        border: "1.5px solid #16a34a",
        borderRadius: 24,
        color: "#16a34a",
        fontWeight: 700,
        fontSize: 12,
        padding: "8px 20px",
        width: NODE_WIDTH,
        textAlign: "center",
      },
      draggable: false,
      selectable: false,
    })

    // Um nó por passo
    steps.forEach((step, index) => {
      const y = START_Y + START_NODE_HEIGHT + 48 + index * STEP_STRIDE
      const position = step.layout ? { x: step.layout.x, y: step.layout.y } : { x: NODE_X, y }
      const invalidReason = getStepInvalidReason(step)
      const isInvalid = invalidReason !== null

      const nodeData: StepNodeData = {
        index,
        channel: step.channel,
        stepType: step.step_type ?? null,
        dayOffset: step.day_offset,
        messageTemplate: step.message_template,
        audioFileId: step.audio_file_id ?? null,
        emailTemplateId: step.email_template_id ?? null,
        useVoice: step.use_voice,
        isSelected: selectedIndex === index,
        isInvalid,
        invalidReason,
        isFirst: index === 0,
        isLast: index === steps.length - 1,
        totalSteps: steps.length,
        onSelect: onSelectStep,
        onDelete: onDeleteStep,
        onDuplicate: onDuplicateStep,
        onMoveUp,
        onMoveDown,
      }

      allNodes.push({
        id: `step-${index}`,
        type: "stepNode",
        position,
        data: nodeData as unknown as Record<string, unknown>,
        draggable: true,
        selectable: true,
      })
    })

    return normalizeStepNodeSpacing(allNodes)
  }, [steps, selectedIndex, onSelectStep, onDeleteStep, onDuplicateStep, onMoveUp, onMoveDown])

  // ─── Arestas canônicas ────────────────────────────────────────────
  const computedEdges = useMemo<Edge[]>(() => {
    const allEdges: Edge[] = []
    if (steps.length === 0) return allEdges

    allEdges.push({
      id: "edge-start",
      source: "start",
      target: "step-0",
      type: "delayEdge",
      data: { dayOffset: steps[0]?.day_offset ?? 0, sourceIndex: -1 } as Record<string, unknown>,
      animated: false,
    })

    steps.forEach((_, index) => {
      if (index >= steps.length - 1) return
      const nextStep = steps[index + 1]
      allEdges.push({
        id: `edge-${index}`,
        source: `step-${index}`,
        target: `step-${index + 1}`,
        type: "delayEdge",
        data: {
          dayOffset: nextStep?.day_offset ?? 0,
          sourceIndex: index,
          onInsertAfter: onInsertAfter,
        } as Record<string, unknown>,
        animated: false,
      })
    })

    return allEdges
  }, [steps, onInsertAfter])

  // ─── Estado ReactFlow — permite drag real sem snap-back ───────────
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(computedNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(computedEdges)
  const pendingNodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map())

  // Sincroniza nós a partir do estado persistido dos steps, mas preserva
  // momentaneamente a última posição solta até o estado do editor acompanhar.
  useEffect(() => {
    const computedNodeIds = new Set(computedNodes.map((node) => node.id))
    for (const nodeId of [...pendingNodePositionsRef.current.keys()]) {
      if (!computedNodeIds.has(nodeId)) {
        pendingNodePositionsRef.current.delete(nodeId)
      }
    }

    setNodes(
      computedNodes.map((node) => {
        const pendingPosition = pendingNodePositionsRef.current.get(node.id)
        if (!pendingPosition) {
          return node
        }

        if (positionsMatch(pendingPosition, node.position)) {
          pendingNodePositionsRef.current.delete(node.id)
          return node
        }

        return {
          ...node,
          position: pendingPosition,
        }
      }),
    )
  }, [computedNodes, setNodes])
  useEffect(() => {
    setEdges(computedEdges)
  }, [computedEdges, setEdges])

  // ─── Drag visual — persiste a posição no step correspondente ──────
  const handleNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (node.type !== "stepNode") return

      const index = Number(node.id.replace("step-", ""))
      if (!Number.isNaN(index)) {
        pendingNodePositionsRef.current.set(node.id, node.position)
        onStepPositionChange(index, node.position)
      }
    },
    [onStepPositionChange],
  )

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (node.type !== "stepNode") return

      const index = Number(node.id.replace("step-", ""))
      if (!Number.isNaN(index)) {
        onSelectStep(index)
      }
    },
    [onSelectStep],
  )

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-gray-200 bg-[#eef0f8] shadow-sm [&_.react-flow__node:focus-visible]:outline-none [&_.react-flow__node]:outline-none">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onNodeDragStop={handleNodeDragStop}
        fitView
        fitViewOptions={{ padding: 0.35, maxZoom: 1 }}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        panOnScroll={true}
        zoomOnScroll={true}
        panOnDrag={[2]}
        proOptions={{ hideAttribution: true }}
        className="h-full rounded-xl"
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="#c7cbd8" />
        <Controls
          showInteractive={false}
          position="bottom-left"
          className="[&>button]:border-gray-200 [&>button]:bg-white [&>button]:text-gray-500 [&>button:hover]:bg-gray-50"
        />
      </ReactFlow>

      {/* Toolbar direita — atalhos de canal */}
      <div className="absolute right-3 top-3 z-10 flex flex-col gap-0.5 rounded-xl border border-gray-200 bg-white p-1.5 shadow-md">
        <p className="px-2 pb-1 pt-1.5 text-[9px] font-bold uppercase tracking-widest text-gray-400">
          Adicionar
        </p>
        {TOOLBAR_CHANNELS.map(({ channel, label, icon, colorClass }) => (
          <button
            key={channel}
            type="button"
            onClick={() => onAddStep(channel)}
            title={`Adicionar passo: ${label}`}
            className={cn(
              "flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
              colorClass,
            )}
          >
            {icon}
            <span>{label}</span>
          </button>
        ))}
        <div className="mx-2 my-1 border-t border-gray-100" />
        <button
          type="button"
          onClick={() => onAddStep()}
          title="Adicionar passo com canal padrão"
          className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-50"
        >
          <Plus size={13} />
          <span>Padrão</span>
        </button>
      </div>

      {/* Estado vazio */}
      {steps.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2">
          <p className="text-sm font-medium text-gray-400">Nenhum passo adicionado</p>
          <p className="text-xs text-gray-300">Use o painel à direita para adicionar →</p>
        </div>
      )}
    </div>
  )
}
