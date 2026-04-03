"use client"

import { useState } from "react"
import Link from "next/link"
import { Plus, Filter, Sparkles, LayoutGrid, CalendarDays } from "lucide-react"
import { useContentPosts, type PostStatus, type PostPillar } from "@/lib/api/hooks/use-content"
import { PostCard } from "@/components/content/post-card"
import { CalendarView } from "@/components/content/calendar-view"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { CreatePostDialog } from "@/components/content/create-post-dialog"

const STATUS_OPTIONS: { value: PostStatus | "all"; label: string }[] = [
  { value: "all", label: "Todos os status" },
  { value: "draft", label: "Rascunho" },
  { value: "approved", label: "Aprovado" },
  { value: "scheduled", label: "Agendado" },
  { value: "published", label: "Publicado" },
  { value: "failed", label: "Falhou" },
]

const PILLAR_OPTIONS: { value: PostPillar | "all"; label: string }[] = [
  { value: "all", label: "Todos os pilares" },
  { value: "authority", label: "Autoridade" },
  { value: "case", label: "Caso" },
  { value: "vision", label: "Visão" },
]

export default function ContentPage() {
  const [statusFilter, setStatusFilter] = useState<PostStatus | "all">("all")
  const [pillarFilter, setPillarFilter] = useState<PostPillar | "all">("all")
  const [createOpen, setCreateOpen] = useState(false)
  const [view, setView] = useState<"grid" | "calendar">("grid")

  const { data: posts, isLoading } = useContentPosts({
    ...(statusFilter !== "all" && { status: statusFilter }),
    ...(pillarFilter !== "all" && { pillar: pillarFilter }),
  })

  return (
    <div className="flex flex-col gap-5">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-(--text-tertiary)" />
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as PostStatus | "all")}
          >
            <SelectTrigger className="h-8 w-44 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value} className="text-xs">
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={pillarFilter}
            onValueChange={(v) => setPillarFilter(v as PostPillar | "all")}
          >
            <SelectTrigger className="h-8 w-44 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PILLAR_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value} className="text-xs">
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          {/* Toggle de visão */}
          <div className="flex items-center rounded-md border border-(--border-default) overflow-hidden h-8">
            <button
              type="button"
              aria-label="Visão grade"
              onClick={() => setView("grid")}
              className={`px-2.5 h-full flex items-center transition-colors ${view === "grid" ? "bg-(--accent) text-white" : "text-(--text-secondary) hover:bg-(--bg-overlay)"}`}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              aria-label="Visão calendário"
              onClick={() => setView("calendar")}
              className={`px-2.5 h-full flex items-center transition-colors ${view === "calendar" ? "bg-(--accent) text-white" : "text-(--text-secondary) hover:bg-(--bg-overlay)"}`}
            >
              <CalendarDays className="h-3.5 w-3.5" />
            </button>
          </div>

          <Button asChild variant="outline" size="sm" className="h-8 text-xs gap-1.5">
            <Link href="/content/gerar">
              <Sparkles className="h-3.5 w-3.5" />
              Gerar com IA
            </Link>
          </Button>
          <Button size="sm" className="h-8 text-xs gap-1.5" onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
            Novo post
          </Button>
        </div>
      </div>

      {/* Conteúdo */}
      {view === "calendar" ? (
        <CalendarView posts={posts ?? []} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 h-48 animate-pulse"
            />
          ))}
        </div>
      ) : !posts?.length ? (
        <EmptyState onGenerate={() => setCreateOpen(true)} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}

      <CreatePostDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}

function EmptyState({ onGenerate }: { onGenerate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
      <div className="h-12 w-12 rounded-full bg-(--accent-subtle) flex items-center justify-center">
        <Plus className="h-6 w-6 text-(--accent)" />
      </div>
      <div>
        <p className="text-sm font-medium text-(--text-primary)">Nenhum post ainda</p>
        <p className="text-sm text-(--text-secondary) mt-1">
          Crie seu primeiro post ou use a IA para gerar variações
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onGenerate}>
          Criar manualmente
        </Button>
        <Button asChild size="sm">
          <Link href="/content/gerar">
            <Sparkles className="h-3.5 w-3.5 mr-1.5" />
            Gerar com IA
          </Link>
        </Button>
      </div>
    </div>
  )
}
