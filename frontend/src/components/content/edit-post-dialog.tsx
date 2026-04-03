"use client"

import { useEffect, useState } from "react"
import { AlertTriangle } from "lucide-react"
import {
  useUpdatePost,
  type ContentPost,
  type PostPillar,
  type HookType,
} from "@/lib/api/hooks/use-content"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const PILLAR_OPTIONS: { value: PostPillar; label: string }[] = [
  { value: "authority", label: "Autoridade" },
  { value: "case", label: "Caso" },
  { value: "vision", label: "Visão" },
]

const HOOK_OPTIONS: { value: HookType; label: string }[] = [
  { value: "loop_open", label: "Loop aberto" },
  { value: "contrarian", label: "Contrário" },
  { value: "identification", label: "Identificação" },
  { value: "shortcut", label: "Atalho" },
  { value: "benefit", label: "Benefício" },
  { value: "data", label: "Dado" },
]

interface EditPostDialogProps {
  post: ContentPost | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EditPostDialog({ post, open, onOpenChange }: EditPostDialogProps) {
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [pillar, setPillar] = useState<PostPillar>("authority")
  const [hookType, setHookType] = useState<HookType | "none">("none")
  const [hashtags, setHashtags] = useState("")
  const [publishDate, setPublishDate] = useState("")
  const [weekNumber, setWeekNumber] = useState("")
  const [syncWarning, setSyncWarning] = useState<string | null>(null)

  const updatePost = useUpdatePost()

  // Preencher form quando o post mudar
  useEffect(() => {
    if (!post) return
    setTitle(post.title)
    setBody(post.body)
    setPillar(post.pillar)
    setHookType(post.hook_type ?? "none")
    setHashtags(post.hashtags ?? "")
    setPublishDate(
      post.publish_date
        ? post.publish_date.slice(0, 16) // "YYYY-MM-DDTHH:mm"
        : "",
    )
    setWeekNumber(post.week_number ? String(post.week_number) : "")
    setSyncWarning(null)
  }, [post])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!post) return
    const result = await updatePost.mutateAsync({
      postId: post.id,
      data: {
        title,
        body,
        pillar,
        hook_type: hookType === "none" ? null : hookType,
        hashtags: hashtags || null,
        character_count: body.length,
        publish_date: publishDate || null,
        week_number: weekNumber ? parseInt(weekNumber, 10) : null,
      },
    })
    if (result.linkedin_sync_warning) {
      setSyncWarning(result.linkedin_sync_warning)
    } else {
      onOpenChange(false)
    }
  }

  const charCount = body.length
  const isOverLimit = charCount > 3000

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar post</DialogTitle>
        </DialogHeader>

        {syncWarning && (
          <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{syncWarning}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-2">
          <div className="grid gap-1.5">
            <Label htmlFor="edit-title">Título</Label>
            <Input
              id="edit-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Título interno do post"
              required
            />
          </div>

          <div className="grid gap-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="edit-body">Conteúdo</Label>
              <span
                className={`text-xs ${isOverLimit ? "text-(--danger)" : "text-(--text-tertiary)"}`}
              >
                {charCount} / 3000
              </span>
            </div>
            <Textarea
              id="edit-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={10}
              className="resize-none text-sm"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Pilar</Label>
              <Select value={pillar} onValueChange={(v) => setPillar(v as PostPillar)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PILLAR_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1.5">
              <Label>Tipo de gancho</Label>
              <Select
                value={hookType}
                onValueChange={(v) => setHookType(v as HookType | "none")}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Nenhum</SelectItem>
                  {HOOK_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="edit-publish-date">Data de publicação</Label>
              <Input
                id="edit-publish-date"
                type="datetime-local"
                value={publishDate}
                onChange={(e) => setPublishDate(e.target.value)}
              />
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="edit-week">Semana</Label>
              <Input
                id="edit-week"
                type="number"
                min={1}
                max={54}
                value={weekNumber}
                onChange={(e) => setWeekNumber(e.target.value)}
                placeholder="1–54"
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="edit-hashtags">Hashtags</Label>
            <Input
              id="edit-hashtags"
              value={hashtags}
              onChange={(e) => setHashtags(e.target.value)}
              placeholder="#marketing #automacao"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => { setSyncWarning(null); onOpenChange(false) }}
            >
              {syncWarning ? "Fechar" : "Cancelar"}
            </Button>
            {!syncWarning && (
              <Button type="submit" disabled={updatePost.isPending || isOverLimit}>
                {updatePost.isPending ? "Salvando…" : "Salvar alterações"}
              </Button>
            )}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
