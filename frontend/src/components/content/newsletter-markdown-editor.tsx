"use client"

import { useEffect, useMemo, useRef } from "react"
import {
  BlockTypeSelect,
  BoldItalicUnderlineToggles,
  CodeToggle,
  CreateLink,
  DiffSourceToggleWrapper,
  InsertCodeBlock,
  InsertImage,
  InsertTable,
  InsertThematicBreak,
  ListsToggle,
  MDXEditor,
  Separator,
  StrikeThroughSupSubToggles,
  UndoRedo,
  codeBlockPlugin,
  codeMirrorPlugin,
  diffSourcePlugin,
  headingsPlugin,
  imagePlugin,
  linkDialogPlugin,
  linkPlugin,
  listsPlugin,
  markdownShortcutPlugin,
  quotePlugin,
  tablePlugin,
  thematicBreakPlugin,
  toolbarPlugin,
  type MDXEditorMethods,
} from "@mdxeditor/editor"

interface NewsletterMarkdownEditorProps {
  value: string
  onChange: (value: string) => void
  height: number | string
  fullscreen?: boolean
  editorTheme?: "app" | "dark" | "light"
}

export function NewsletterMarkdownEditor({
  value,
  onChange,
  height,
  fullscreen = false,
  editorTheme = "app",
}: NewsletterMarkdownEditorProps) {
  const editorRef = useRef<MDXEditorMethods>(null)
  const overlayContainer = typeof document !== "undefined" ? document.body : null

  const plugins = useMemo(
    () => [
      headingsPlugin({ allowedHeadingLevels: [1, 2, 3, 4] }),
      listsPlugin(),
      quotePlugin(),
      thematicBreakPlugin(),
      linkPlugin(),
      linkDialogPlugin(),
      tablePlugin(),
      imagePlugin(),
      codeBlockPlugin({ defaultCodeBlockLanguage: "text" }),
      codeMirrorPlugin({
        codeBlockLanguages: {
          text: "Texto",
          js: "JavaScript",
          jsx: "JSX",
          ts: "TypeScript",
          tsx: "TSX",
          css: "CSS",
          html: "HTML",
          json: "JSON",
          python: "Python",
          bash: "Bash",
        },
      }),
      markdownShortcutPlugin(),
      diffSourcePlugin({ viewMode: "rich-text" }),
      toolbarPlugin({
        toolbarContents: () => (
          <DiffSourceToggleWrapper>
            <UndoRedo />
            <Separator />
            <BlockTypeSelect />
            <BoldItalicUnderlineToggles />
            <StrikeThroughSupSubToggles />
            <CodeToggle />
            <CreateLink />
            <Separator />
            <ListsToggle />
            <Separator />
            <InsertTable />
            <InsertImage />
            <InsertThematicBreak />
            <InsertCodeBlock />
          </DiffSourceToggleWrapper>
        ),
      }),
    ],
    [],
  )

  useEffect(() => {
    const currentMarkdown = editorRef.current?.getMarkdown()
    if (currentMarkdown !== undefined && currentMarkdown !== value) {
      editorRef.current?.setMarkdown(value)
    }
  }, [value])

  return (
    <div
      className={fullscreen ? "newsletter-mdx-shell newsletter-mdx-shell-fullscreen" : "newsletter-mdx-shell"}
      data-editor-theme={editorTheme}
      style={{ height }}
    >
      <MDXEditor
        ref={editorRef}
        markdown={value}
        onChange={(markdown, initialMarkdownNormalize) => {
          if (!initialMarkdownNormalize) onChange(markdown)
        }}
        plugins={plugins}
        contentEditableClassName="newsletter-mdx-prose"
        className="newsletter-mdx-editor"
        overlayContainer={overlayContainer}
        placeholder="Escreva ou cole o conteúdo da newsletter..."
        spellCheck
      />
    </div>
  )
}