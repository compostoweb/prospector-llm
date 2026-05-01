"use client"

import { useState } from "react"
import { format, parseISO } from "date-fns"
import { ptBR } from "date-fns/locale"
import {
  Plus,
  Trash2,
  Calendar,
  CheckCircle2,
  ExternalLink,
  Image as ImageIcon,
  Send,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  useContentArticles,
  useCreateArticle,
  useDeleteArticle,
  useApproveArticle,
  usePublishArticleNow,
  type ArticleStatus,
  type ContentArticle,
} from "@/lib/api/hooks/use-content-articles"
import { CreateArticleDialog } from "@/components/content/create-article-dialog"
import { EditArticleDialog } from "@/components/content/edit-article-dialog"

const STATUS_LABEL: Record<ArticleStatus, string> = {
  draft: "Rascunho",
  approved: "Aprovado",
  scheduled: "Agendado",
  publishing: "Publicando",
  published: "Publicado",
  failed: "Falhou",
  deleted: "Excluído",
}

const STATUS_VARIANT: Record<ArticleStatus, "default" | "outline" | "success" | "warning" | "danger" | "neutral" | "info"> = {
  draft: "outline",
  approved: "info",
  scheduled: "warning",
  publishing: "warning",
  published: "success",
  failed: "danger",
  deleted: "neutral",
}

export default function ArticlesPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const { data: list = [], isLoading } = useContentArticles()
  const createMutation = useCreateArticle()
  const deleteMutation = useDeleteArticle()
  const approveMutation = useApproveArticle()
  const publishNowMutation = usePublishArticleNow()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-(--text-primary)">
            Artigos (link share LinkedIn)
          </h2>
          <p className="text-sm text-(--text-secondary)">
            Compartilha URL externa via Posts API com thumbnail e comentário
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Novo artigo
        </Button>
      </div>

      {isLoading && <p className="text-sm text-(--text-secondary)">Carregando...</p>}

      {!isLoading && list.length === 0 && (
        <div className="rounded-lg border border-dashed border-(--border-default) p-8 text-center">
          <ExternalLink className="mx-auto h-10 w-10 text-(--text-tertiary)" />
          <p className="mt-3 text-sm text-(--text-secondary)">Nenhum artigo criado ainda.</p>
        </div>
      )}

      {list.length > 0 && (
        <div className="grid gap-3">
          {list.map((art: ContentArticle) => (
            <div
              key={art.id}
              className="flex items-start gap-3 rounded-lg border border-(--border-default) bg-(--bg-card) p-3 hover:border-(--accent) transition-colors"
            >
              <div className="h-20 w-32 shrink-0 overflow-hidden rounded bg-(--bg-tertiary)">
                {art.thumbnail_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={art.thumbnail_url} alt="" className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center">
                    <ImageIcon className="h-6 w-6 text-(--text-tertiary)" />
                  </div>
                )}
              </div>

              <button
                type="button"
                className="flex-1 text-left"
                onClick={() => setEditingId(art.id)}
              >
                <div className="flex items-center gap-2">
                  <span className="line-clamp-1 font-medium text-(--text-primary)">
                    {art.title || "(sem título)"}
                  </span>
                  <Badge variant={STATUS_VARIANT[art.status]}>{STATUS_LABEL[art.status]}</Badge>
                </div>
                {art.description && (
                  <p className="mt-1 line-clamp-2 text-xs text-(--text-secondary)">
                    {art.description}
                  </p>
                )}
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-(--text-secondary)">
                  <a
                    href={art.source_url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1 hover:text-(--accent)"
                  >
                    <ExternalLink className="h-3 w-3" />
                    URL fonte
                  </a>
                  {art.scheduled_for && (
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {format(parseISO(art.scheduled_for), "dd/MM 'às' HH:mm", {
                        locale: ptBR,
                      })}
                    </span>
                  )}
                  {art.published_at && (
                    <span className="inline-flex items-center gap-1 text-(--success)">
                      <CheckCircle2 className="h-3 w-3" />
                      {format(parseISO(art.published_at), "dd/MM/yyyy", {
                        locale: ptBR,
                      })}
                    </span>
                  )}
                  {art.error_message && (
                    <span className="text-(--destructive)">
                      Erro: {art.error_message.substring(0, 60)}
                    </span>
                  )}
                </div>
              </button>

              <div className="flex flex-col gap-1">
                {art.status === "draft" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => approveMutation.mutate(art.id)}
                  >
                    Aprovar
                  </Button>
                )}
                {(art.status === "approved" || art.status === "draft") && (
                  <Button
                    size="sm"
                    variant="default"
                    className="gap-1"
                    onClick={() => {
                      if (confirm("Publicar agora no LinkedIn?")) publishNowMutation.mutate(art.id)
                    }}
                    disabled={publishNowMutation.isPending}
                  >
                    <Send className="h-3 w-3" />
                    Publicar
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    if (confirm("Mover artigo para a lixeira?")) deleteMutation.mutate(art.id)
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateArticleDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={async (data) => {
          await createMutation.mutateAsync(data)
          setCreateOpen(false)
        }}
        isPending={createMutation.isPending}
      />

      {editingId && (
        <EditArticleDialog
          articleId={editingId}
          open={!!editingId}
          onOpenChange={(open) => !open && setEditingId(null)}
        />
      )}
    </div>
  )
}
