"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { BadgeChannel } from "@/components/shared/badge-channel"
import {
  useManualTask,
  useGenerateTaskContent,
  useRegenerateTaskContent,
  useUpdateTaskContent,
  useSendTask,
  useMarkTaskDone,
  useSkipTask,
} from "@/lib/api/hooks/use-manual-tasks"
import {
  Sparkles,
  RefreshCw,
  Send,
  CheckCircle,
  SkipForward,
  Volume2,
  Loader2,
} from "lucide-react"


interface TaskDetailDialogProps {
  taskId: string
  open: boolean
  onClose: () => void
}

export function TaskDetailDialog({ taskId, open, onClose }: TaskDetailDialogProps) {
  const { data: task, isLoading } = useManualTask(taskId)
  const generate = useGenerateTaskContent()
  const regenerate = useRegenerateTaskContent()
  const updateContent = useUpdateTaskContent()
  const sendTask = useSendTask()
  const markDone = useMarkTaskDone()
  const skipTask = useSkipTask()

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
    skipTask.isPending

  const currentText = task?.edited_text ?? task?.generated_text ?? ""
  const canGenerate = task?.status === "pending"
  const canSend = task?.status === "content_generated"
  const isTerminal = task?.status === "sent" || task?.status === "done_external" || task?.status === "skipped"

  function handleStartEdit() {
    setEditedText(currentText)
    setIsEditing(true)
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
  }

  async function handleDone() {
    if (!task) return
    await markDone.mutateAsync({
      taskId: task.id,
      ...(doneNotes ? { notes: doneNotes } : {}),
    })
    setShowDoneForm(false)
    setDoneNotes("")
  }

  async function handleSkip() {
    if (!task) return
    await skipTask.mutateAsync(task.id)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isLoading ? "Carregando…" : `Tarefa — ${task?.lead?.name ?? "Lead"}`}
          </DialogTitle>
          <DialogDescription>
            {task && (
              <span className="flex items-center gap-2">
                <BadgeChannel channel={task.channel} />
                <span>Passo {task.step_number}</span>
                {task.lead?.company && (
                  <>
                    <span className="text-(--text-disabled)">·</span>
                    <span>{task.lead.company}</span>
                  </>
                )}
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 size={24} className="animate-spin text-(--text-tertiary)" />
          </div>
        ) : task ? (
          <div className="space-y-4 pt-2">
            {/* Conteúdo gerado / editor */}
            {isEditing ? (
              <div className="space-y-2">
                <Textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  rows={6}
                  placeholder="Edite o conteúdo da mensagem…"
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleSaveEdit}
                    disabled={isBusy || !editedText.trim()}
                  >
                    {updateContent.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      "Salvar"
                    )}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setIsEditing(false)}>
                    Cancelar
                  </Button>
                </div>
              </div>
            ) : currentText ? (
              <div className="space-y-2">
                <p className="text-xs font-medium text-(--text-secondary)">Conteúdo da mensagem</p>
                <div className="rounded-md border border-(--border-default) bg-(--bg-overlay) p-3 text-sm text-(--text-primary) whitespace-pre-wrap">
                  {currentText}
                </div>
                {!isTerminal && (
                  <button
                    type="button"
                    onClick={handleStartEdit}
                    className="text-xs text-(--accent) hover:underline"
                  >
                    Editar texto
                  </button>
                )}
              </div>
            ) : (
              <div className="rounded-md border border-dashed border-(--border-default) bg-(--bg-overlay) p-6 text-center text-sm text-(--text-tertiary)">
                Nenhum conteúdo gerado ainda.
              </div>
            )}

            {/* Audio preview */}
            {task.generated_audio_url && (
              <div className="space-y-1">
                <p className="flex items-center gap-1 text-xs font-medium text-(--text-secondary)">
                  <Volume2 size={12} aria-hidden="true" />
                  Áudio gerado
                </p>
                <audio
                  src={task.generated_audio_url}
                  controls
                  className="h-8 w-full"
                  preload="metadata"
                />
              </div>
            )}

            {/* Done external form */}
            {showDoneForm && (
              <div className="space-y-2 rounded-md border border-(--border-default) bg-(--bg-overlay) p-3">
                <p className="text-xs font-medium text-(--text-secondary)">
                  Notas (opcional) — o que foi feito externamente
                </p>
                <Textarea
                  value={doneNotes}
                  onChange={(e) => setDoneNotes(e.target.value)}
                  rows={2}
                  placeholder="Ex: Enviei manualmente pelo LinkedIn…"
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleDone} disabled={isBusy}>
                    {markDone.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      "Confirmar"
                    )}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowDoneForm(false)}>
                    Cancelar
                  </Button>
                </div>
              </div>
            )}

            {/* Info extra */}
            {task.sent_at && (
              <p className="text-xs text-(--text-tertiary)">
                Enviada em {new Date(task.sent_at).toLocaleString("pt-BR")}
              </p>
            )}
            {task.notes && (
              <p className="text-xs text-(--text-secondary)">
                <span className="font-medium">Notas:</span> {task.notes}
              </p>
            )}
          </div>
        ) : null}

        {/* Footer com ações */}
        {task && !isTerminal && (
          <DialogFooter className="pt-4">
            {canGenerate && (
              <Button onClick={handleGenerate} disabled={isBusy}>
                {generate.isPending ? (
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                ) : (
                  <Sparkles size={14} className="mr-1.5" aria-hidden="true" />
                )}
                Gerar conteúdo
              </Button>
            )}

            {canSend && (
              <>
                <Button onClick={handleRegenerate} variant="outline" disabled={isBusy}>
                  {regenerate.isPending ? (
                    <Loader2 size={14} className="mr-1.5 animate-spin" />
                  ) : (
                    <RefreshCw size={14} className="mr-1.5" aria-hidden="true" />
                  )}
                  Regerar
                </Button>
                <Button onClick={handleSend} disabled={isBusy}>
                  {sendTask.isPending ? (
                    <Loader2 size={14} className="mr-1.5 animate-spin" />
                  ) : (
                    <Send size={14} className="mr-1.5" aria-hidden="true" />
                  )}
                  Enviar via sistema
                </Button>
              </>
            )}

            {!showDoneForm && (
              <Button
                variant="outline"
                onClick={() => setShowDoneForm(true)}
                disabled={isBusy}
              >
                <CheckCircle size={14} className="mr-1.5" aria-hidden="true" />
                Feito externamente
              </Button>
            )}

            <Button variant="outline" onClick={handleSkip} disabled={isBusy}>
              {skipTask.isPending ? (
                <Loader2 size={14} className="mr-1.5 animate-spin" />
              ) : (
                <SkipForward size={14} className="mr-1.5" aria-hidden="true" />
              )}
              Pular
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
