"use client"

import { useState, useEffect } from "react"
import { format, parseISO } from "date-fns"
import { Save, Calendar, Send, Upload, X } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { useQuery } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import {
  useUpdateArticle,
  useUploadArticleThumbnail,
  useScheduleArticle,
  usePublishArticleNow,
  useApproveArticle,
  type ContentArticle,
} from "@/lib/api/hooks/use-content-articles"

interface Props {
  articleId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EditArticleDialog({ articleId, open, onOpenChange }: Props) {
  const { data: session } = useSession()
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? ""

  const { data: art, isLoading } = useQuery({
    queryKey: ["content-articles", articleId],
    queryFn: async () => {
      const res = await fetch(`${apiBase}/api/content/articles/${articleId}`, {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      })
      if (!res.ok) throw new Error("Erro ao buscar artigo")
      return res.json() as Promise<ContentArticle>
    },
    enabled: !!session?.accessToken && !!articleId && open,
  })

  const updateMutation = useUpdateArticle()
  const uploadThumb = useUploadArticleThumbnail()
  const scheduleMutation = useScheduleArticle()
  const publishNow = usePublishArticleNow()
  const approveMutation = useApproveArticle()

  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [commentary, setCommentary] = useState("")
  const [firstComment, setFirstComment] = useState("")
  const [scheduledFor, setScheduledFor] = useState("")

  useEffect(() => {
    if (art) {
      setTitle(art.title)
      setDescription(art.description ?? "")
      setCommentary(art.commentary ?? "")
      setFirstComment(art.first_comment_text ?? "")
      setScheduledFor(
        art.scheduled_for ? format(parseISO(art.scheduled_for), "yyyy-MM-dd'T'HH:mm") : "",
      )
    }
  }, [art])

  if (!art && isLoading) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Carregando...</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    )
  }

  if (!art) return null

  const handleSave = async () => {
    await updateMutation.mutateAsync({
      id: art.id,
      data: {
        title,
        description: description || null,
        commentary: commentary || null,
        first_comment_text: firstComment || null,
      },
    })
  }

  const handleSchedule = async () => {
    if (!scheduledFor) return
    const iso = new Date(scheduledFor).toISOString()
    await scheduleMutation.mutateAsync({ id: art.id, scheduled_for: iso })
  }

  const handlePublishNow = async () => {
    if (!confirm("Publicar agora no LinkedIn?")) return
    await publishNow.mutateAsync(art.id)
    onOpenChange(false)
  }

  const handleUploadThumb = async (file: File) => {
    await uploadThumb.mutateAsync({ id: art.id, file })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] sm:max-w-200 overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Artigo
            <Badge variant="outline">{art.status}</Badge>
            {art.linkedin_post_urn && (
              <Badge variant="info">URN: {art.linkedin_post_urn}</Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1">
            <Label className="text-xs text-(--text-tertiary)">URL fonte</Label>
            <a
              href={art.source_url}
              target="_blank"
              rel="noreferrer"
              className="block text-sm text-(--accent) hover:underline truncate"
            >
              {art.source_url}
            </a>
          </div>

          <div className="space-y-2">
            <Label>Thumbnail</Label>
            <div className="flex items-center gap-3">
              {art.thumbnail_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={art.thumbnail_url}
                  alt="thumb"
                  className="h-24 w-40 rounded object-cover"
                />
              ) : (
                <div className="flex h-24 w-40 items-center justify-center rounded border border-dashed border-(--border-default) text-xs">
                  Sem thumb
                </div>
              )}
              <label className="cursor-pointer">
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) void handleUploadThumb(f)
                  }}
                />
                <span className="inline-flex items-center gap-2 rounded-md border border-(--border-default) px-3 py-1.5 text-sm hover:bg-(--bg-tertiary)">
                  <Upload className="h-4 w-4" />
                  Subir thumbnail
                </span>
              </label>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Título</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>

          <div className="space-y-2">
            <Label>Descrição</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          <div className="space-y-2">
            <Label>Comentário do post</Label>
            <Textarea
              value={commentary}
              onChange={(e) => setCommentary(e.target.value)}
              rows={4}
              placeholder="Texto que aparece acima do card de link no feed"
            />
          </div>

          <div className="space-y-2">
            <Label>Primeiro comentário</Label>
            <Textarea
              value={firstComment}
              onChange={(e) => setFirstComment(e.target.value)}
              rows={2}
            />
            {art.first_comment_status && (
              <p className="text-xs text-(--text-tertiary)">
                Status: {art.first_comment_status}
                {art.first_comment_error && ` — ${art.first_comment_error}`}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Agendar publicação</Label>
            <div className="flex gap-2">
              <Input
                type="datetime-local"
                value={scheduledFor}
                onChange={(e) => setScheduledFor(e.target.value)}
              />
              <Button
                type="button"
                onClick={handleSchedule}
                disabled={!scheduledFor || scheduleMutation.isPending}
                variant="outline"
                className="gap-2"
              >
                <Calendar className="h-4 w-4" />
                Agendar
              </Button>
            </div>
          </div>

          {art.status === "published" && (
            <div className="rounded-md border border-(--border-default) bg-(--bg-tertiary) p-3 grid grid-cols-4 gap-3 text-center">
              <div>
                <p className="text-xs text-(--text-tertiary)">Impressões</p>
                <p className="font-medium">{art.impressions}</p>
              </div>
              <div>
                <p className="text-xs text-(--text-tertiary)">Likes</p>
                <p className="font-medium">{art.likes}</p>
              </div>
              <div>
                <p className="text-xs text-(--text-tertiary)">Comentários</p>
                <p className="font-medium">{art.comments}</p>
              </div>
              <div>
                <p className="text-xs text-(--text-tertiary)">Engagement</p>
                <p className="font-medium">
                  {art.engagement_rate != null ? `${(art.engagement_rate * 100).toFixed(2)}%` : "—"}
                </p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            <X className="h-4 w-4" />
            Fechar
          </Button>
          {art.status === "draft" && (
            <Button variant="outline" onClick={() => approveMutation.mutate(art.id)}>
              Aprovar
            </Button>
          )}
          <Button onClick={handleSave} disabled={updateMutation.isPending} className="gap-2">
            <Save className="h-4 w-4" />
            Salvar
          </Button>
          {(art.status === "draft" || art.status === "approved") && (
            <Button onClick={handlePublishNow} disabled={publishNow.isPending} className="gap-2">
              <Send className="h-4 w-4" />
              Publicar agora
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
