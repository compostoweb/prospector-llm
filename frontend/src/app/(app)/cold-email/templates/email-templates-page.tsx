"use client"

import { useState } from "react"
import { Plus, FileText, Edit2, Trash2, X, Eye, EyeOff } from "lucide-react"
import {
  useEmailTemplates,
  useCreateEmailTemplate,
  useUpdateEmailTemplate,
  useDeleteEmailTemplate,
  type EmailTemplate,
  type CreateEmailTemplateBody,
} from "@/lib/api/hooks/use-email-templates"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface TemplateFormProps {
  initial?: EmailTemplate | undefined
  onClose: () => void
}

function TemplateForm({ initial, onClose }: TemplateFormProps) {
  const create = useCreateEmailTemplate()
  const update = useUpdateEmailTemplate()

  const [name, setName] = useState(initial?.name ?? "")
  const [category, setCategory] = useState(initial?.category ?? "")
  const [subject, setSubject] = useState(initial?.subject ?? "")
  const [bodyHtml, setBodyHtml] = useState(initial?.body_html ?? "")
  const [description, setDescription] = useState(initial?.description ?? "")
  const [error, setError] = useState<string | null>(null)

  const [showPreview, setShowPreview] = useState(false)
  const isLoading = create.isPending || update.isPending

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!name.trim()) {
      setError("Nome obrigatório")
      return
    }
    if (!subject.trim()) {
      setError("Assunto obrigatório")
      return
    }
    if (!bodyHtml.trim()) {
      setError("Corpo obrigatório")
      return
    }

    const body: CreateEmailTemplateBody = {
      name: name.trim(),
      description: description.trim() || null,
      category: category.trim() || null,
      subject: subject.trim(),
      body_html: bodyHtml,
    }

    try {
      if (initial) {
        await update.mutateAsync({ id: initial.id, ...body })
      } else {
        await create.mutateAsync(body)
      }
      onClose()
    } catch {
      setError("Erro ao salvar template")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className={cn(
          "flex w-full overflow-hidden rounded-lg border border-(--border-default) bg-(--bg-surface) shadow-(--shadow-lg) transition-all",
          showPreview ? "max-w-5xl" : "max-w-2xl",
        )}
      >
        {/* ── Form ───────────────────────────────────────────────── */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between border-b border-(--border-default) px-5 py-4">
            <h2 className="font-semibold text-(--text-primary)">
              {initial ? "Editar Template" : "Novo Template"}
            </h2>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setShowPreview((v) => !v)}
                title={showPreview ? "Fechar preview" : "Pré-visualizar HTML"}
                className="rounded p-1.5 text-(--text-tertiary) hover:bg-(--bg-overlay) hover:text-(--text-primary)"
              >
                {showPreview ? (
                  <EyeOff size={15} aria-hidden="true" />
                ) : (
                  <Eye size={15} aria-hidden="true" />
                )}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded p-1.5 text-(--text-tertiary) hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                aria-label="Fechar"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
          </div>

          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4 p-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="tmpl-name">Nome</Label>
                <Input
                  id="tmpl-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ex: Primeiro contato SaaS"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tmpl-category">Categoria</Label>
                <Input
                  id="tmpl-category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="Ex: prospecção, follow-up"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tmpl-subject">Assunto</Label>
              <Input
                id="tmpl-subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Ex: Ideia para {{company}}"
              />
              <p className="text-xs text-(--text-tertiary)">
                Use {`{{name}}`}, {`{{company}}`}, {`{{job_title}}`} como variáveis dinâmicas.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tmpl-desc">Descrição (opcional)</Label>
              <Input
                id="tmpl-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descreva quando usar este template"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tmpl-body">Corpo HTML</Label>
              <Textarea
                id="tmpl-body"
                value={bodyHtml}
                onChange={(e) => setBodyHtml(e.target.value)}
                rows={10}
                placeholder="<p>Olá {{name}},</p><p>...</p>"
                className="font-mono text-xs"
              />
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? "Salvando…" : initial ? "Salvar alterações" : "Criar template"}
              </Button>
            </div>
          </form>
        </div>

        {/* ── Preview ─────────────────────────────────────────────── */}
        {showPreview && (
          <div className="w-105 shrink-0 border-l border-(--border-default) flex flex-col">
            <div className="border-b border-(--border-default) px-4 py-3">
              <p className="text-xs font-medium text-(--text-secondary)">Preview</p>
              {subject && (
                <p className="mt-0.5 text-sm font-medium text-(--text-primary) truncate">
                  {subject}
                </p>
              )}
            </div>
            <div className="flex-1 overflow-hidden bg-white">
              {bodyHtml.trim() ? (
                <iframe
                  title="Preview do e-mail"
                  srcDoc={bodyHtml}
                  sandbox="allow-same-origin"
                  className="h-full min-h-105 w-full border-0"
                />
              ) : (
                <div className="flex h-full items-center justify-center p-6 text-center">
                  <p className="text-sm text-gray-400">
                    Digite o HTML do corpo para visualizar o preview.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function EmailTemplatesPage() {
  const { data: templates, isLoading } = useEmailTemplates()
  const deleteTemplate = useDeleteEmailTemplate()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<EmailTemplate | null>(null)

  function openNew() {
    setEditing(null)
    setShowForm(true)
  }

  function openEdit(t: EmailTemplate) {
    setEditing(t)
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setEditing(null)
  }

  async function handleDelete(id: string) {
    if (!confirm("Remover template?")) return
    await deleteTemplate.mutateAsync(id)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-(--text-primary)">Templates de E-mail</h1>
          <p className="text-sm text-(--text-secondary)">
            Templates reutilizáveis para suas cadências de e-mail
          </p>
        </div>
        <Button onClick={openNew} className="flex items-center gap-1.5">
          <Plus size={14} aria-hidden="true" />
          Novo template
        </Button>
      </div>

      {/* Lista */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-(--bg-overlay)" />
          ))}
        </div>
      ) : templates && templates.length > 0 ? (
        <div className="space-y-2">
          {templates.map((t) => (
            <div
              key={t.id}
              className="flex items-center justify-between rounded-lg border border-(--border-default) bg-(--bg-surface) px-4 py-3 shadow-(--shadow-sm)"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-(--text-primary) truncate">{t.name}</p>
                  {t.category && (
                    <span className="shrink-0 rounded bg-(--accent)/10 px-1.5 py-0.5 text-[10px] font-medium text-(--accent)">
                      {t.category}
                    </span>
                  )}
                  {!t.is_active && (
                    <span className="shrink-0 rounded bg-(--bg-overlay) px-1.5 py-0.5 text-[10px] text-(--text-disabled)">
                      inativo
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-(--text-tertiary) truncate">
                  Assunto: {t.subject}
                </p>
              </div>
              <div className="ml-4 flex shrink-0 gap-1">
                <button
                  type="button"
                  onClick={() => openEdit(t)}
                  className="rounded p-1.5 text-(--text-tertiary) hover:bg-(--bg-overlay) hover:text-(--text-primary)"
                  aria-label="Editar template"
                >
                  <Edit2 size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(t.id)}
                  disabled={deleteTemplate.isPending}
                  className="rounded p-1.5 text-(--text-tertiary) hover:bg-(--danger-subtle) hover:text-(--danger) disabled:opacity-50"
                  aria-label="Remover template"
                >
                  <Trash2 size={14} aria-hidden="true" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={FileText}
          title="Nenhum template criado"
          description="Templates reutilizáveis agilizam a criação de cadências de e-mail"
          action={
            <Button onClick={openNew} className="flex items-center gap-1.5">
              <Plus size={14} aria-hidden="true" />
              Novo template
            </Button>
          }
        />
      )}

      {/* Form modal */}
      {showForm && <TemplateForm initial={editing ?? undefined} onClose={closeForm} />}
    </div>
  )
}
