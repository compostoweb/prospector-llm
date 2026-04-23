"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { BadgeChannel } from "@/components/shared/badge-channel"
import {
  useGenerateTaskContent,
  useManualTask,
  useMarkTaskDone,
  useReopenTask,
  useRegenerateTaskContent,
  useSendTask,
  useSkipTask,
  useUpdateTaskContent,
} from "@/lib/api/hooks/use-manual-tasks"
import {
  formatTaskDateTime,
  getNextTaskId,
  getPreviousTaskId,
  getTaskSelectionAfterAdvance,
} from "@/components/tarefas/task-queue-utils"
import { cn, manualTaskTypeLabel } from "@/lib/utils"
import {
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Copy,
  ExternalLink,
  FileText,
  Keyboard,
  Loader2,
  RefreshCw,
  Send,
  SkipForward,
  Sparkles,
  Volume2,
  WandSparkles,
} from "lucide-react"

interface TaskDetailDialogProps {
  taskId: string
  open: boolean
  onClose: () => void
  taskIdsInOrder?: string[]
  onAdvanceSelection?: (taskId: string | null) => void
  onOpenTask?: (taskId: string) => void
}

export function TaskDetailDialog({
  taskId,
  open,
  onClose,
  taskIdsInOrder = [],
  onAdvanceSelection,
  onOpenTask,
}: TaskDetailDialogProps) {
  const { data: task, isLoading } = useManualTask(taskId)
  const generate = useGenerateTaskContent()
  const regenerate = useRegenerateTaskContent()
  const updateContent = useUpdateTaskContent()
  const sendTask = useSendTask()
  const markDone = useMarkTaskDone()
  const skipTask = useSkipTask()
  const reopenTask = useReopenTask()

  const [editedText, setEditedText] = useState("")
  const [isEditing, setIsEditing] = useState(false)
  const [doneNotes, setDoneNotes] = useState("")
  const [showDoneForm, setShowDoneForm] = useState(false)

  const isBusy =
    generate.isPending ||
    regenerate.isPending ||
    updateContent.isPending ||
    sendTask.isPending ||
    markDone.isPending ||
    skipTask.isPending ||
    reopenTask.isPending

  const currentText = task?.edited_text ?? task?.generated_text ?? task?.manual_task_detail ?? ""
  const canGenerate = task?.status === "pending"
  const canSend = task?.status === "content_generated"
  const canReopen = task?.status === "done_external" || task?.status === "skipped"
  const isTerminal =
    task?.status === "sent" || task?.status === "done_external" || task?.status === "skipped"
  const canOpenLinkedIn = !!task?.lead?.linkedin_url && task.channel !== "email"
  const taskTitle = task?.lead?.name ?? "Lead"
  const executedAt =
    task?.sent_at ??
    (task?.status === "done_external" || task?.status === "skipped" ? task.updated_at : null)
  const previousTaskId = useMemo(
    () => getPreviousTaskId(taskIdsInOrder, taskId),
    [taskId, taskIdsInOrder],
  )
  const nextTaskId = useMemo(() => getNextTaskId(taskIdsInOrder, taskId), [taskId, taskIdsInOrder])
  const manualTaskLabel = manualTaskTypeLabel(task?.manual_task_type)
  const manualTaskInstruction = task?.manual_task_detail ?? null

  const executionGuidance = task
    ? task.channel === "email"
      ? "Revise o texto, copie se necessário e conclua no canal de email usado pela operação."
      : task.channel === "manual_task"
        ? "Use a instrução operacional abaixo, copie o conteúdo se existir e conclua a etapa no canal externo indicado."
        : "Abra o perfil do lead, copie a mensagem e execute a ação manualmente com menos troca de contexto."
    : ""

  const handleCopyContent = useCallback(async () => {
    if (!currentText.trim()) {
      toast.error("Não há conteúdo para copiar")
      return
    }

    try {
      await navigator.clipboard.writeText(currentText)
      toast.success("Conteúdo copiado")
    } catch {
      toast.error("Falha ao copiar o conteúdo")
    }
  }, [currentText])

  useEffect(() => {
    setEditedText("")
    setIsEditing(false)
    setDoneNotes("")
    setShowDoneForm(false)
  }, [taskId])

  useEffect(() => {
    if (!open) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target instanceof HTMLElement ? event.target : null
      const isTypingTarget = target?.closest("textarea, input, [contenteditable='true']") !== null

      if (event.altKey && event.key === "ArrowLeft" && previousTaskId && !isTypingTarget) {
        event.preventDefault()
        onAdvanceSelection?.(previousTaskId)
        onOpenTask?.(previousTaskId)
        return
      }

      if (event.altKey && event.key === "ArrowRight" && nextTaskId && !isTypingTarget) {
        event.preventDefault()
        onAdvanceSelection?.(nextTaskId)
        onOpenTask?.(nextTaskId)
        return
      }

      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key.toLowerCase() === "c") {
        event.preventDefault()
        void handleCopyContent()
        return
      }

      if (
        (event.metaKey || event.ctrlKey) &&
        event.shiftKey &&
        event.key.toLowerCase() === "l" &&
        canOpenLinkedIn &&
        task?.lead?.linkedin_url
      ) {
        event.preventDefault()
        window.open(task.lead.linkedin_url, "_blank", "noopener,noreferrer")
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [
    canOpenLinkedIn,
    handleCopyContent,
    nextTaskId,
    onAdvanceSelection,
    onOpenTask,
    open,
    previousTaskId,
    task?.lead?.linkedin_url,
  ])

  function handleTerminalSuccess(message: string) {
    const nextTaskIdAfterAction = getTaskSelectionAfterAdvance(taskIdsInOrder, taskId)
    onAdvanceSelection?.(nextTaskIdAfterAction)
    onClose()

    if (nextTaskIdAfterAction && onOpenTask) {
      toast.success(message, {
        description: "A próxima linha já ficou selecionada na fila.",
        action: {
          label: "Abrir próxima",
          onClick: () => onOpenTask(nextTaskIdAfterAction),
        },
      })
      return
    }

    toast.success(message)
  }

  function handleStartEdit() {
    setEditedText(currentText)
    setIsEditing(true)
  }

  function handleNavigateTask(targetTaskId: string | null) {
    if (!targetTaskId) {
      return
    }

    onAdvanceSelection?.(targetTaskId)
    onOpenTask?.(targetTaskId)
  }

  async function handleSaveEdit() {
    if (!task) return
    await updateContent.mutateAsync({ taskId: task.id, edited_text: editedText })
    setIsEditing(false)
  }

  async function handleGenerate() {
    if (!task) return
    await generate.mutateAsync(task.id)
  }

  async function handleRegenerate() {
    if (!task) return
    await regenerate.mutateAsync(task.id)
  }

  async function handleSend() {
    if (!task) return
    await sendTask.mutateAsync(task.id)
    handleTerminalSuccess("Tarefa enviada")
  }

  async function handleDone() {
    if (!task) return
    await markDone.mutateAsync({
      taskId: task.id,
      ...(doneNotes ? { notes: doneNotes } : {}),
    })
    setShowDoneForm(false)
    setDoneNotes("")
    handleTerminalSuccess("Tarefa marcada como feita externamente")
  }

  async function handleSkip() {
    if (!task) return
    await skipTask.mutateAsync(task.id)
    handleTerminalSuccess("Tarefa pulada")
  }

  async function handleReopen() {
    if (!task) return
    await reopenTask.mutateAsync(task.id)
    toast.success("Tarefa reaberta para correção")
  }

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <TooltipProvider delayDuration={120}>
        <DialogContent className="w-[min(96vw,88rem)] max-w-none border-0 bg-transparent p-0 shadow-none">
          <div className="relative px-4 md:px-14">
            {previousTaskId && (
              <div className="absolute left-0 top-1/2 z-20 hidden -translate-y-1/2 md:flex">
                <ActionTooltip content="Volta para a tarefa anterior da fila." side="right">
                  <button
                    type="button"
                    onClick={() => handleNavigateTask(previousTaskId)}
                    className="flex h-11 w-11 items-center justify-center rounded-full border border-(--border-default) bg-(--bg-surface) text-(--text-primary) shadow-(--shadow-md) transition-colors hover:bg-(--bg-overlay)"
                    aria-label="Abrir tarefa anterior"
                  >
                    <ChevronLeft size={18} aria-hidden="true" />
                  </button>
                </ActionTooltip>
              </div>
            )}

            {nextTaskId && (
              <div className="absolute right-0 top-1/2 z-20 hidden -translate-y-1/2 md:flex">
                <ActionTooltip content="Avança para a próxima tarefa da fila." side="left">
                  <button
                    type="button"
                    onClick={() => handleNavigateTask(nextTaskId)}
                    className="flex h-11 w-11 items-center justify-center rounded-full border border-(--border-default) bg-(--bg-surface) text-(--text-primary) shadow-(--shadow-md) transition-colors hover:bg-(--bg-overlay)"
                    aria-label="Abrir próxima tarefa"
                  >
                    <ChevronRight size={18} aria-hidden="true" />
                  </button>
                </ActionTooltip>
              </div>
            )}

            <div className="flex max-h-[88vh] flex-col overflow-hidden rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-lg">
              <DialogHeader className="shrink-0 border-b border-(--border-default) px-6 py-5">
                <DialogTitle>{isLoading ? "Carregando…" : `Tarefa — ${taskTitle}`}</DialogTitle>
                <DialogDescription>
                  {task && (
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <BadgeChannel
                        channel={task.channel}
                        manualTaskType={task.manual_task_type}
                        className="px-2.5 py-1"
                      />
                      <span>Passo {task.step_number}</span>
                      {task.lead?.company && (
                        <>
                          <span className="text-(--text-disabled)">·</span>
                          <span>{task.lead.company}</span>
                        </>
                      )}
                      {task.cadence_name && (
                        <>
                          <span className="text-(--text-disabled)">·</span>
                          <span>{task.cadence_name}</span>
                        </>
                      )}
                    </div>
                  )}
                </DialogDescription>
              </DialogHeader>

              {isLoading ? (
                <div className="flex h-40 items-center justify-center">
                  <Loader2 size={24} className="animate-spin text-(--text-tertiary)" />
                </div>
              ) : task ? (
                <div className="flex-1 overflow-y-auto">
                  <div className="grid gap-6 px-6 py-5 lg:grid-cols-[minmax(0,1.55fr)_320px]">
                    <div className="space-y-5">
                      <section className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                              Execução assistida
                            </p>
                            <h3 className="mt-1 text-base font-semibold text-(--text-primary)">
                              {currentText
                                ? "Mensagem pronta para revisar e executar"
                                : "Preparar conteúdo da tarefa"}
                            </h3>
                            <p className="mt-1 text-sm text-(--text-secondary)">
                              {executionGuidance}
                            </p>
                          </div>

                          <div className="flex flex-wrap gap-2">
                            <ActionTooltip content="Copia a mensagem atual para você executar a ação fora do sistema.">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={handleCopyContent}
                                disabled={!currentText.trim()}
                              >
                                <Copy size={14} aria-hidden="true" />
                                Copiar conteúdo
                              </Button>
                            </ActionTooltip>

                            {canOpenLinkedIn && task.lead?.linkedin_url && (
                              <ActionTooltip content="Abre o perfil do lead em nova aba para reduzir troca de contexto.">
                                <Button asChild size="sm" variant="outline">
                                  <a
                                    href={task.lead.linkedin_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    <ExternalLink size={14} aria-hidden="true" />
                                    Abrir perfil no LinkedIn
                                  </a>
                                </Button>
                              </ActionTooltip>
                            )}

                            {!isTerminal && currentText && (
                              <ActionTooltip content="Pede uma nova versão para refinar o texto atual com IA.">
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="secondary"
                                  onClick={handleRegenerate}
                                  disabled={isBusy}
                                >
                                  {regenerate.isPending ? (
                                    <Loader2 size={14} className="animate-spin" />
                                  ) : (
                                    <WandSparkles size={14} aria-hidden="true" />
                                  )}
                                  Melhorar com IA
                                </Button>
                              </ActionTooltip>
                            )}
                          </div>
                        </div>

                        {manualTaskLabel && (
                          <div
                            className={cn(
                              "mt-4 rounded-lg border p-3",
                              task.manual_task_type === "call" &&
                                "border-(--danger) bg-(--danger-subtle) text-(--danger-subtle-fg)",
                              task.manual_task_type === "whatsapp" &&
                                "border-(--success) bg-(--success-subtle) text-(--success-subtle-fg)",
                              task.manual_task_type === "linkedin_post_comment" &&
                                "border-(--warning) bg-(--warning-subtle) text-(--warning-subtle-fg)",
                              (!task.manual_task_type || task.manual_task_type === "other") &&
                                "border-(--info) bg-(--info-subtle) text-(--info-subtle-fg)",
                            )}
                          >
                            <p className="text-xs font-semibold uppercase tracking-wide">
                              Ação manual em destaque
                            </p>
                            <p className="mt-1 text-sm font-semibold">{manualTaskLabel}</p>
                            {manualTaskInstruction && (
                              <p className="mt-1 text-sm">{manualTaskInstruction}</p>
                            )}
                          </div>
                        )}

                        <div className="mt-4 space-y-3">
                          {isEditing ? (
                            <div className="space-y-2">
                              <Textarea
                                value={editedText}
                                onChange={(event) => setEditedText(event.target.value)}
                                rows={10}
                                placeholder="Edite o conteúdo da mensagem…"
                              />
                              <div className="flex flex-wrap gap-2">
                                <ActionTooltip content="Salva a revisão manual deste texto antes de enviar ou copiar.">
                                  <Button
                                    size="sm"
                                    onClick={handleSaveEdit}
                                    disabled={isBusy || !editedText.trim()}
                                  >
                                    {updateContent.isPending ? (
                                      <Loader2 size={14} className="animate-spin" />
                                    ) : (
                                      "Salvar edição"
                                    )}
                                  </Button>
                                </ActionTooltip>
                                <ActionTooltip content="Descarta a edição atual e volta para a última versão salva.">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => setIsEditing(false)}
                                  >
                                    Cancelar
                                  </Button>
                                </ActionTooltip>
                              </div>
                            </div>
                          ) : currentText ? (
                            <>
                              <div className="rounded-lg border border-(--border-default) bg-(--bg-overlay) p-4 text-sm leading-6 whitespace-pre-wrap text-(--text-primary)">
                                {currentText}
                              </div>
                              {!isTerminal && (
                                <ActionTooltip content="Abre o editor para ajustar manualmente a mensagem desta tarefa.">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="link"
                                    onClick={handleStartEdit}
                                  >
                                    Editar texto
                                  </Button>
                                </ActionTooltip>
                              )}
                            </>
                          ) : (
                            <div className="rounded-lg border border-dashed border-(--border-default) bg-(--bg-overlay) p-8 text-center text-sm text-(--text-tertiary)">
                              Nenhum conteúdo gerado ainda. Gere uma versão com IA para seguir na
                              execução.
                            </div>
                          )}
                        </div>
                      </section>

                      {task.generated_audio_url && (
                        <section className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
                          <p className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                            <Volume2 size={12} aria-hidden="true" />
                            Áudio gerado
                          </p>
                          <audio
                            src={task.generated_audio_url}
                            controls
                            className="mt-3 h-10 w-full"
                            preload="metadata"
                          />
                        </section>
                      )}

                      {showDoneForm && (
                        <section className="rounded-xl border border-(--border-default) bg-(--bg-overlay) p-4 shadow-(--shadow-sm)">
                          <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                            Confirmação externa
                          </p>
                          <p className="mt-1 text-sm text-(--text-secondary)">
                            Registre um contexto curto do que foi executado fora do sistema para
                            preservar o histórico.
                          </p>
                          <div className="mt-3 space-y-2">
                            <Textarea
                              value={doneNotes}
                              onChange={(event) => setDoneNotes(event.target.value)}
                              rows={3}
                              placeholder="Ex: Enviei manualmente pelo LinkedIn e personalizei a abertura."
                            />
                            <div className="flex flex-wrap gap-2">
                              <ActionTooltip content="Registra a tarefa como concluída fora do sistema usando as notas preenchidas.">
                                <Button size="sm" onClick={handleDone} disabled={isBusy}>
                                  {markDone.isPending ? (
                                    <Loader2 size={14} className="animate-spin" />
                                  ) : (
                                    "Confirmar execução externa"
                                  )}
                                </Button>
                              </ActionTooltip>
                              <ActionTooltip content="Fecha este formulário sem marcar a tarefa como concluída externamente.">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setShowDoneForm(false)}
                                >
                                  Cancelar
                                </Button>
                              </ActionTooltip>
                            </div>
                          </div>
                        </section>
                      )}
                    </div>

                    <aside className="space-y-4">
                      <section className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm)">
                        <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                          Contexto da tarefa
                        </p>
                        <div className="mt-3 space-y-3 text-sm">
                          <InfoRow label="Lead" value={task.lead?.name ?? "Lead desconhecido"} />
                          <InfoRow label="Empresa" value={task.lead?.company ?? "—"} />
                          <InfoRow label="Cargo" value={task.lead?.job_title ?? "—"} />
                          <InfoRow label="Cadência" value={task.cadence_name ?? "—"} />
                          {manualTaskLabel && (
                            <InfoRow label="Tipo manual" value={manualTaskLabel} />
                          )}
                          <InfoRow label="Criada em" value={formatTaskDateTime(task.created_at)} />
                          <InfoRow
                            label="Atualizada em"
                            value={formatTaskDateTime(task.updated_at)}
                          />
                          <InfoRow label="Execução" value={formatTaskDateTime(executedAt)} />
                        </div>
                      </section>
                    </aside>

                    <section className="rounded-xl border border-(--border-default) bg-(--bg-surface) p-4 shadow-(--shadow-sm) lg:col-span-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                        Próximo passo sugerido
                      </p>
                      <div className="mt-3 grid gap-3 text-sm text-(--text-secondary) lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_280px] lg:items-start">
                        <div className="grid gap-3 md:grid-cols-2 lg:col-span-2">
                          <GuidanceItem
                            icon={FileText}
                            tone="info"
                            title={currentText ? "Revise o texto" : "Gere a primeira versão"}
                            description={
                              currentText
                                ? "Faça ajustes rápidos e mantenha o contexto da cadência antes de executar."
                                : "Use IA para produzir uma base antes de seguir para execução manual ou envio."
                            }
                          />
                          <GuidanceItem
                            icon={Clock3}
                            tone={canSend ? "success" : "warning"}
                            title={canSend ? "Concluir esta etapa" : "Preparar execução"}
                            description={
                              task.channel === "manual_task" && manualTaskInstruction
                                ? manualTaskInstruction
                                : canSend
                                  ? "Envie via sistema ou marque como feita externamente se a execução ocorrer fora daqui."
                                  : "Abra o canal correto e mantenha o lead acessível para reduzir cliques extras."
                            }
                          />
                        </div>

                        <div className="space-y-3">
                          {task.notes && (
                            <p className="rounded-lg bg-(--bg-overlay) px-3 py-2 text-xs">
                              Notas: {task.notes}
                            </p>
                          )}
                          <div className="rounded-lg border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2 text-xs text-(--text-secondary)">
                            <div className="mb-1 flex items-center gap-1 font-medium text-(--text-primary)">
                              <Keyboard size={12} aria-hidden="true" />
                              Atalhos
                            </div>
                            <p>Alt + ← anterior · Alt + → próxima</p>
                            <p>Ctrl/Cmd + Shift + C copiar · Ctrl/Cmd + Shift + L abrir LinkedIn</p>
                          </div>
                        </div>
                      </div>
                    </section>
                  </div>
                </div>
              ) : null}

              {task && (!isTerminal || canReopen) && (
                <DialogFooter className="shrink-0 border-t border-(--border-default) bg-(--bg-surface)/95 px-6 py-4 backdrop-blur supports-backdrop-filter:bg-(--bg-surface)/90">
                  {canReopen && (
                    <ActionTooltip content="Reabre a tarefa para corrigir texto, revisar a execução e devolver para a fila ativa.">
                      <Button variant="outline" onClick={handleReopen} disabled={isBusy}>
                        {reopenTask.isPending ? (
                          <Loader2 size={14} className="mr-1.5 animate-spin" />
                        ) : (
                          <RefreshCw size={14} className="mr-1.5" aria-hidden="true" />
                        )}
                        Reabrir tarefa
                      </Button>
                    </ActionTooltip>
                  )}

                  {canGenerate && (
                    <ActionTooltip content="Cria a primeira versão da mensagem para esta tarefa usando IA.">
                      <Button onClick={handleGenerate} disabled={isBusy}>
                        {generate.isPending ? (
                          <Loader2 size={14} className="mr-1.5 animate-spin" />
                        ) : (
                          <Sparkles size={14} className="mr-1.5" aria-hidden="true" />
                        )}
                        Gerar com IA
                      </Button>
                    </ActionTooltip>
                  )}

                  {canSend && (
                    <>
                      <ActionTooltip content="Gera outra versão da mensagem antes do envio final.">
                        <Button onClick={handleRegenerate} variant="outline" disabled={isBusy}>
                          {regenerate.isPending ? (
                            <Loader2 size={14} className="mr-1.5 animate-spin" />
                          ) : (
                            <RefreshCw size={14} className="mr-1.5" aria-hidden="true" />
                          )}
                          Gerar nova versão
                        </Button>
                      </ActionTooltip>
                      <ActionTooltip content="Dispara a mensagem diretamente pelo sistema e avança a fila.">
                        <Button onClick={handleSend} disabled={isBusy}>
                          {sendTask.isPending ? (
                            <Loader2 size={14} className="mr-1.5 animate-spin" />
                          ) : (
                            <Send size={14} className="mr-1.5" aria-hidden="true" />
                          )}
                          Enviar via sistema
                        </Button>
                      </ActionTooltip>
                    </>
                  )}

                  {!showDoneForm && (
                    <ActionTooltip content="Abre o formulário para registrar que a tarefa foi feita fora do sistema.">
                      <Button
                        variant="outline"
                        onClick={() => setShowDoneForm(true)}
                        disabled={isBusy}
                      >
                        <CheckCircle size={14} className="mr-1.5" aria-hidden="true" />
                        Feito externamente
                      </Button>
                    </ActionTooltip>
                  )}

                  <ActionTooltip content="Pula esta tarefa sem executar e segue o fluxo operacional.">
                    <Button variant="outline" onClick={handleSkip} disabled={isBusy}>
                      {skipTask.isPending ? (
                        <Loader2 size={14} className="mr-1.5 animate-spin" />
                      ) : (
                        <SkipForward size={14} className="mr-1.5" aria-hidden="true" />
                      )}
                      Pular
                    </Button>
                  </ActionTooltip>
                </DialogFooter>
              )}
            </div>
          </div>
        </DialogContent>
      </TooltipProvider>
    </Dialog>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-(--border-subtle) pb-2 last:border-b-0 last:pb-0">
      <span className="text-xs uppercase tracking-wide text-(--text-tertiary)">{label}</span>
      <span className="text-right text-(--text-primary)">{value}</span>
    </div>
  )
}

function GuidanceItem({
  icon: Icon,
  tone,
  title,
  description,
}: {
  icon: React.ElementType
  tone: "info" | "success" | "warning"
  title: string
  description: string
}) {
  const toneClassName = {
    info: {
      card: "border-(--info-subtle-fg)/20 bg-(--info-subtle)",
      icon: "bg-(--info) text-white",
    },
    success: {
      card: "border-(--success-subtle-fg)/20 bg-(--success-subtle)",
      icon: "bg-(--success) text-white",
    },
    warning: {
      card: "border-(--warning-subtle-fg)/20 bg-(--warning-subtle)",
      icon: "bg-(--warning) text-white",
    },
  }[tone]

  return (
    <div
      className={cn(
        "flex h-full items-center gap-3 rounded-lg border px-3 py-3",
        toneClassName.card,
      )}
    >
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-md shadow-(--shadow-sm)",
          toneClassName.icon,
        )}
      >
        <Icon size={16} aria-hidden="true" />
      </div>
      <div>
        <p className="font-medium text-(--text-primary)">{title}</p>
        <p className="mt-1 text-sm leading-5 text-(--text-secondary)">{description}</p>
      </div>
    </div>
  )
}

function ActionTooltip({
  content,
  children,
  side = "top",
}: {
  content: string
  children: React.ReactNode
  side?: React.ComponentProps<typeof TooltipContent>["side"]
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex">{children}</span>
      </TooltipTrigger>
      <TooltipContent side={side}>{content}</TooltipContent>
    </Tooltip>
  )
}
