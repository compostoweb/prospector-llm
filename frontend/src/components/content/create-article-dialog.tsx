"use client"

import { useState } from "react"
import { Sparkles, Loader2 } from "lucide-react"
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
import { useScrapeArticleUrl, type ArticleCreateInput } from "@/lib/api/hooks/use-content-articles"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: ArticleCreateInput) => Promise<void> | void
  isPending?: boolean
}

export function CreateArticleDialog({ open, onOpenChange, onSubmit, isPending }: Props) {
  const [sourceUrl, setSourceUrl] = useState("")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [thumbnailUrl, setThumbnailUrl] = useState("")
  const [commentary, setCommentary] = useState("")
  const [firstComment, setFirstComment] = useState("")
  const [autoScraped, setAutoScraped] = useState(false)

  const scrapeMutation = useScrapeArticleUrl()

  const handleScrape = async () => {
    if (!sourceUrl.trim()) return
    const meta = await scrapeMutation.mutateAsync(sourceUrl.trim())
    if (meta.title && !title) setTitle(meta.title)
    if (meta.description && !description) setDescription(meta.description)
    if (meta.thumbnail_url && !thumbnailUrl) setThumbnailUrl(meta.thumbnail_url)
    setAutoScraped(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit({
      source_url: sourceUrl.trim(),
      title: title.trim(),
      description: description.trim() || null,
      thumbnail_url: thumbnailUrl.trim() || null,
      commentary: commentary.trim() || null,
      first_comment_text: firstComment.trim() || null,
      auto_scraped: autoScraped,
    })
    setSourceUrl("")
    setTitle("")
    setDescription("")
    setThumbnailUrl("")
    setCommentary("")
    setFirstComment("")
    setAutoScraped(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-150">
        <DialogHeader>
          <DialogTitle>Novo artigo (link share LinkedIn)</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="url">URL fonte *</Label>
            <div className="flex gap-2">
              <Input
                id="url"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder="https://compostoweb.com.br/blog/..."
                type="url"
                required
              />
              <Button
                type="button"
                onClick={handleScrape}
                disabled={!sourceUrl.trim() || scrapeMutation.isPending}
                variant="outline"
                className="gap-2"
              >
                {scrapeMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Auto-scrape
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">Título *</Label>
            <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="desc">Descrição</Label>
            <Textarea
              id="desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="thumb">Thumbnail URL</Label>
            <Input
              id="thumb"
              value={thumbnailUrl}
              onChange={(e) => setThumbnailUrl(e.target.value)}
              placeholder="https://..."
            />
            {thumbnailUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={thumbnailUrl}
                alt="thumb preview"
                className="h-24 w-40 rounded object-cover"
              />
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="comm">Comentário do post (opcional)</Label>
            <Textarea
              id="comm"
              value={commentary}
              onChange={(e) => setCommentary(e.target.value)}
              rows={3}
              placeholder="Texto que aparece acima do card de link"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="fc">Primeiro comentário (opcional)</Label>
            <Textarea
              id="fc"
              value={firstComment}
              onChange={(e) => setFirstComment(e.target.value)}
              rows={2}
              placeholder="Comentário a ser postado logo após a publicação"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!sourceUrl.trim() || !title.trim() || isPending}>
              {isPending ? "Criando..." : "Criar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
