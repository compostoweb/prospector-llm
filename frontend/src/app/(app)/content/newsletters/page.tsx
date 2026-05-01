"use client"

import { useState } from "react"
import { format, parseISO } from "date-fns"
import { ptBR } from "date-fns/locale"
import { Plus, Sparkles, Trash2, Calendar, CheckCircle2, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  useContentNewsletters,
  useCreateNewsletter,
  useDeleteNewsletter,
  type ContentNewsletter,
  type NewsletterStatus,
} from "@/lib/api/hooks/use-content-newsletters"
import { CreateNewsletterDialog } from "@/components/content/create-newsletter-dialog"
import { EditNewsletterDialog } from "@/components/content/edit-newsletter-dialog"

const STATUS_LABEL: Record<NewsletterStatus, string> = {
  draft: "Rascunho",
  validated: "Validada",
  approved: "Aprovada",
  scheduled: "Agendada",
  published: "Publicada",
  failed: "Falhou",
  deleted: "Excluída",
}

const STATUS_VARIANT: Record<
  NewsletterStatus,
  "default" | "outline" | "success" | "warning" | "danger" | "neutral" | "info"
> = {
  draft: "outline",
  validated: "info",
  approved: "info",
  scheduled: "warning",
  published: "success",
  failed: "danger",
  deleted: "neutral",
}

export default function NewslettersPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const { data: list = [], isLoading } = useContentNewsletters()
  const createMutation = useCreateNewsletter()
  const deleteMutation = useDeleteNewsletter()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-(--text-primary)">Newsletters quinzenais</h2>
          <p className="text-sm text-(--text-secondary)">
            Operação Inteligente — 1.000–1.400 palavras, 5 seções fixas
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Nova edição
        </Button>
      </div>

      {isLoading && <p className="text-sm text-(--text-secondary)">Carregando...</p>}

      {!isLoading && list.length === 0 && (
        <div className="rounded-lg border border-dashed border-(--border-default) p-8 text-center">
          <Sparkles className="mx-auto h-10 w-10 text-(--text-tertiary)" />
          <p className="mt-3 text-sm text-(--text-secondary)">
            Nenhuma newsletter criada ainda. Comece criando a primeira edição.
          </p>
        </div>
      )}

      {list.length > 0 && (
        <div className="grid gap-3">
          {list.map((nl: ContentNewsletter) => (
            <div
              key={nl.id}
              className="flex items-center justify-between rounded-lg border border-(--border-default) bg-(--bg-card) p-4 hover:border-(--accent) transition-colors"
            >
              <button
                type="button"
                className="flex-1 text-left"
                onClick={() => setEditingId(nl.id)}
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-(--text-secondary)" />
                  <span className="font-medium text-(--text-primary)">
                    Edição #{nl.edition_number}
                  </span>
                  <Badge variant={STATUS_VARIANT[nl.status]}>{STATUS_LABEL[nl.status]}</Badge>
                </div>
                <p className="mt-1 text-sm text-(--text-primary)">{nl.title}</p>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-(--text-secondary)">
                  {nl.central_theme && <span>Tema: {nl.central_theme}</span>}
                  {nl.word_count != null && <span>{nl.word_count} palavras</span>}
                  {nl.scheduled_for && (
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {format(parseISO(nl.scheduled_for), "dd/MM 'às' HH:mm", {
                        locale: ptBR,
                      })}
                    </span>
                  )}
                  {nl.status === "published" && nl.published_at && (
                    <span className="inline-flex items-center gap-1 text-(--success)">
                      <CheckCircle2 className="h-3 w-3" />
                      {format(parseISO(nl.published_at), "dd/MM/yyyy", {
                        locale: ptBR,
                      })}
                    </span>
                  )}
                </div>
              </button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  if (confirm(`Mover edição #${nl.edition_number} para a lixeira?`))
                    deleteMutation.mutate(nl.id)
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <CreateNewsletterDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={async (data) => {
          await createMutation.mutateAsync(data)
          setCreateOpen(false)
        }}
        isPending={createMutation.isPending}
      />

      {editingId && (
        <EditNewsletterDialog
          newsletterId={editingId}
          open={!!editingId}
          onOpenChange={(open) => !open && setEditingId(null)}
        />
      )}
    </div>
  )
}
