"use client"

import { useState } from "react"
import { useCreateContentPost, type PostPillar, type HookType } from "@/lib/api/hooks/use-content"
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

interface CreatePostDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreatePostDialog({ open, onOpenChange }: CreatePostDialogProps) {
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [pillar, setPillar] = useState<PostPillar>("authority")
  const [hookType, setHookType] = useState<HookType | "none">("none")
  const [hashtags, setHashtags] = useState("")
  const [publishDate, setPublishDate] = useState("")
  const [weekNumber, setWeekNumber] = useState("")

  const createPost = useCreateContentPost()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await createPost.mutateAsync({
      title,
      body,
      pillar,
      hook_type: hookType === "none" ? null : hookType,
      hashtags: hashtags || null,
      character_count: body.length,
      publish_date: publishDate || null,
      week_number: weekNumber ? parseInt(weekNumber, 10) : null,
    })
    onOpenChange(false)
    resetForm()
  }

  function resetForm() {
    setTitle("")
    setBody("")
    setPillar("authority")
    setHookType("none")
    setHashtags("")
    setPublishDate("")
    setWeekNumber("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Novo post</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="title">Título interno</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Semana 5 · Tema principal"
              required
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="body">Texto do post</Label>
            <Textarea
              id="body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Escreva o conteúdo do post..."
              rows={8}
              required
              className="resize-none font-mono text-sm"
            />
            <p className="text-xs text-(--text-tertiary) text-right">{body.length} / 3.000 chars</p>
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
              <Select value={hookType} onValueChange={(v) => setHookType(v as HookType | "none")}>
                <SelectTrigger>
                  <SelectValue placeholder="Nenhum" />
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
              <Label htmlFor="publish_date">Data de publicação</Label>
              <Input
                id="publish_date"
                type="datetime-local"
                value={publishDate}
                onChange={(e) => setPublishDate(e.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="week_number">Semana</Label>
              <Input
                id="week_number"
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
            <Label htmlFor="hashtags">Hashtags</Label>
            <Input
              id="hashtags"
              value={hashtags}
              onChange={(e) => setHashtags(e.target.value)}
              placeholder="#ia #processos #automacao"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createPost.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={createPost.isPending}>
              {createPost.isPending ? "Criando…" : "Criar post"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
