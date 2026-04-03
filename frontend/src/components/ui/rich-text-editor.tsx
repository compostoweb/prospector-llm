"use client"

import { useCallback, useEffect, useRef } from "react"
import { useEditor, EditorContent, type Editor } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import { ResizableImage } from "./resizable-image-extension"
import Link from "@tiptap/extension-link"
import Placeholder from "@tiptap/extension-placeholder"
import TextAlign from "@tiptap/extension-text-align"
import Underline from "@tiptap/extension-underline"
import {
  Bold,
  Italic,
  UnderlineIcon,
  Strikethrough,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Link as LinkIcon,
  ImageIcon,
  List,
  ListOrdered,
  Undo,
  Redo,
} from "lucide-react"
import { cn } from "@/lib/utils"

// ── Toolbar ───────────────────────────────────────────────────────────

function ToolbarButton({
  onClick,
  active,
  title,
  children,
}: {
  onClick: () => void
  active?: boolean
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => {
        e.preventDefault() // mantém foco no editor
        onClick()
      }}
      title={title}
      className={cn(
        "flex h-7 w-7 items-center justify-center rounded text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary)",
        active && "bg-(--brand-subtle) text-(--brand)",
      )}
    >
      {children}
    </button>
  )
}

function Divider() {
  return <div className="mx-1 h-5 w-px bg-(--border-default)" />
}

function Toolbar({ editor }: { editor: Editor }) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const setLink = useCallback(() => {
    const prev = editor.getAttributes("link").href as string | undefined
    const url = window.prompt("URL do link:", prev ?? "https://")
    if (url === null) return
    if (url === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run()
  }, [editor])

  const handleImageFile = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = (ev) => {
        const src = ev.target?.result as string
        if (src) editor.chain().focus().setImage({ src }).run()
      }
      reader.readAsDataURL(file) // base64 inline — ideal para assinaturas de e-mail
      e.target.value = "" // reset para permitir re-upload do mesmo arquivo
    },
    [editor],
  )

  return (
    <div className="flex flex-wrap items-center gap-0.5 border-b border-(--border-default) bg-(--bg-surface) px-2 py-1.5">
      {/* Histórico */}
      <ToolbarButton onClick={() => editor.chain().focus().undo().run()} title="Desfazer (Ctrl+Z)">
        <Undo size={13} />
      </ToolbarButton>
      <ToolbarButton onClick={() => editor.chain().focus().redo().run()} title="Refazer (Ctrl+Y)">
        <Redo size={13} />
      </ToolbarButton>
      <Divider />

      {/* Formatação inline */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBold().run()}
        active={editor.isActive("bold")}
        title="Negrito (Ctrl+B)"
      >
        <Bold size={13} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleItalic().run()}
        active={editor.isActive("italic")}
        title="Itálico (Ctrl+I)"
      >
        <Italic size={13} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        active={editor.isActive("underline")}
        title="Sublinhado (Ctrl+U)"
      >
        <UnderlineIcon size={13} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleStrike().run()}
        active={editor.isActive("strike")}
        title="Tachado"
      >
        <Strikethrough size={13} />
      </ToolbarButton>
      <Divider />

      {/* Alinhamento */}
      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign("left").run()}
        active={editor.isActive({ textAlign: "left" })}
        title="Alinhar à esquerda"
      >
        <AlignLeft size={13} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign("center").run()}
        active={editor.isActive({ textAlign: "center" })}
        title="Centralizar"
      >
        <AlignCenter size={13} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().setTextAlign("right").run()}
        active={editor.isActive({ textAlign: "right" })}
        title="Alinhar à direita"
      >
        <AlignRight size={13} />
      </ToolbarButton>
      <Divider />

      {/* Listas */}
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        active={editor.isActive("bulletList")}
        title="Lista com marcadores"
      >
        <List size={13} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        active={editor.isActive("orderedList")}
        title="Lista numerada"
      >
        <ListOrdered size={13} />
      </ToolbarButton>
      <Divider />

      {/* Link */}
      <ToolbarButton
        onClick={setLink}
        active={editor.isActive("link")}
        title="Inserir / editar link"
      >
        <LinkIcon size={13} />
      </ToolbarButton>

      {/* Imagem — upload local → base64 inline */}
      <ToolbarButton onClick={() => fileInputRef.current?.click()} title="Inserir imagem (local)">
        <ImageIcon size={13} />
      </ToolbarButton>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        aria-label="Inserir imagem"
        className="hidden"
        onChange={handleImageFile}
      />
    </div>
  )
}

// ── Props ─────────────────────────────────────────────────────────────

interface RichTextEditorProps {
  value: string // HTML
  onChange: (html: string) => void
  placeholder?: string
  className?: string
  minHeight?: number
}

// ── Componente principal ──────────────────────────────────────────────

export function RichTextEditor({
  value,
  onChange,
  placeholder = "Digite aqui...",
  className,
  minHeight = 160,
}: RichTextEditorProps) {
  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      ResizableImage.configure({ allowBase64: true }),
      Link.configure({ openOnClick: false, HTMLAttributes: { rel: "noopener noreferrer" } }),
      Placeholder.configure({ placeholder }),
    ],
    content: value,
    onUpdate: ({ editor }) => {
      // Retorna "" se o editor estiver vazio (evita "<p></p>" no banco)
      const html = editor.isEmpty ? "" : editor.getHTML()
      onChange(html)
    },
  })

  // Sincroniza conteúdo externo (ex: após "Sincronizar do Gmail")
  // Só atualiza se o valor externo for diferente do que está no editor,
  // para não criar loop com o onUpdate acima.
  useEffect(() => {
    if (!editor) return
    const current = editor.isEmpty ? "" : editor.getHTML()
    if (value !== current) {
      editor.commands.setContent(value) // if (value !== current) já evita loop
    }
  }, [value, editor])

  if (!editor) return null

  return (
    <div
      className={cn(
        "overflow-hidden rounded-md border border-(--border-default) bg-(--bg-surface) focus-within:border-(--accent) focus-within:ring-1 focus-within:ring-(--accent)",
        className,
      )}
    >
      <Toolbar editor={editor} />
      <EditorContent
        editor={editor}
        className="prose prose-sm prose-invert max-w-none px-3 py-2 text-sm text-(--text-primary) focus:outline-none [&_.tiptap]:min-h-(--editor-min-h) [&_.tiptap]:outline-none [&_.tiptap_p.is-editor-empty:first-child::before]:pointer-events-none [&_.tiptap_p.is-editor-empty:first-child::before]:float-left [&_.tiptap_p.is-editor-empty:first-child::before]:h-0 [&_.tiptap_p.is-editor-empty:first-child::before]:text-(--text-tertiary) [&_.tiptap_p.is-editor-empty:first-child::before]:content-[attr(data-placeholder)]"
        style={{ "--editor-min-h": `${minHeight}px` } as React.CSSProperties}
      />
    </div>
  )
}
