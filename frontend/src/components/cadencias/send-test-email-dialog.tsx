"use client"

import { useEffect, useState } from "react"
import { Mail, Loader2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface SendTestEmailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (email: string) => void
  isPending?: boolean
  title?: string
  description?: string
  suggestedEmails?: string[]
  contextLabel?: string | null
  subjectPreview?: string | null
  transportLabel?: string | null
  transportHint?: string | null
}

export function SendTestEmailDialog({
  open,
  onOpenChange,
  onSubmit,
  isPending = false,
  title = "Enviar teste por e-mail",
  description = "Escolha ou digite o endereço que deve receber este teste.",
  suggestedEmails = [],
  contextLabel,
  subjectPreview,
  transportLabel,
  transportHint,
}: SendTestEmailDialogProps) {
  const [email, setEmail] = useState("")

  useEffect(() => {
    if (!open) {
      setEmail("")
    }
  }, [open, suggestedEmails])

  const uniqueSuggestions = [...new Set(suggestedEmails.map((item) => item.trim()).filter(Boolean))]

  function handleSubmit() {
    const normalized = email.trim()
    if (!normalized) {
      return
    }
    onSubmit(normalized)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md"
        onOpenAutoFocus={(event) => {
          event.preventDefault()
        }}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail size={16} aria-hidden="true" />
            {title}
          </DialogTitle>
          <DialogDescription className="mb-2">{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {contextLabel && (
            <div className="rounded-md border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2 text-sm font-bold text-(--accent)">
              Conteúdo: <span className="font-medium text-(--text-primary)">{contextLabel}</span>
            </div>
          )}

          {subjectPreview && (
            <div className="rounded-md border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2 text-sm font-bold text-(--accent)">
              Assunto previsto:{" "}
              <span className="font-medium text-(--text-primary)">{subjectPreview}</span>
            </div>
          )}

          {(transportLabel || transportHint) && (
            <div className="rounded-md border border-(--border-subtle) bg-(--bg-overlay) px-3 py-2 text-sm  font-bold text-(--accent)">
              <p>
                Conta do teste:{" "}
                {transportLabel ? (
                  <span className="font-medium text-(--text-primary)">{transportLabel}</span>
                ) : null}
              </p>
              {transportHint && (
                <p className="mt-1 font-normal text-xs text-(--text-primary)">{transportHint}</p>
              )}
            </div>
          )}

          <div className="space-y-2 pb-1">
            <label className="text-sm font-bold text-(--text-secondary)" htmlFor="test-email-input">
              Endereço de destino
            </label>
            <Input
              id="test-email-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="teste@empresa.com"
              autoComplete="email"
            />
          </div>

          {uniqueSuggestions.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-(--text-secondary)">Sugestões</p>
              <div className="flex flex-wrap gap-2">
                {uniqueSuggestions.map((suggestion) => (
                  <Button
                    key={suggestion}
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setEmail(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="pt-2">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button type="button" onClick={handleSubmit} disabled={isPending || !email.trim()}>
            {isPending ? <Loader2 size={14} className="animate-spin" aria-hidden="true" /> : null}
            Enviar teste
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
