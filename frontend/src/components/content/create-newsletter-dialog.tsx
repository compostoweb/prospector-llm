"use client"

import { useState } from "react"
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
import type { NewsletterCreateInput } from "@/lib/api/hooks/use-content-newsletters"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: NewsletterCreateInput) => Promise<void> | void
  isPending?: boolean
}

export function CreateNewsletterDialog({ open, onOpenChange, onSubmit, isPending }: Props) {
  const [title, setTitle] = useState("")
  const [subtitle, setSubtitle] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit({
      title: title.trim(),
      subtitle: subtitle.trim() || null,
    })
    setTitle("")
    setSubtitle("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-125">
        <DialogHeader>
          <DialogTitle>Nova edição da newsletter</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Título *</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Por que 70% dos pilotos com IA falham..."
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="subtitle">Subtítulo</Label>
            <Textarea
              id="subtitle"
              value={subtitle}
              onChange={(e) => setSubtitle(e.target.value)}
              placeholder="Subtítulo / hook curto (opcional)"
              rows={2}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!title.trim() || isPending}>
              {isPending ? "Criando..." : "Criar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
