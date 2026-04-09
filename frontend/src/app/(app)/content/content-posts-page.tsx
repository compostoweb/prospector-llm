"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { isSameMonth, parseISO, startOfMonth, subMonths, format } from "date-fns"
import { ptBR } from "date-fns/locale"
import { Plus, Filter, Sparkles, LayoutGrid, List, RefreshCw } from "lucide-react"
import { NotionLogo } from "@/components/ui/notion-logo"
import { toast } from "sonner"
import {
  useContentPosts,
  useSyncVoyager,
  useContentSettings,
  type PostStatus,
  type PostPillar,
} from "@/lib/api/hooks/use-content"
import { PostCard } from "@/components/content/post-card"
import { PostListView, type SortKey } from "@/components/content/post-list-view"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { CreatePostDialog } from "@/components/content/create-post-dialog"
import { NotionImportDialog } from "@/components/content/notion-import-dialog"

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

export default function ContentPostsPage() {
  const [statusFilter, setStatusFilter] = useState<PostStatus | "all">("all")
  const [pillarFilter, setPillarFilter] = useState<PostPillar | "all">("all")
  const [monthFilter, setMonthFilter] = useState<string>("") // "2026-04" format
  const [createOpen, setCreateOpen] = useState(false)
  const [notionOpen, setNotionOpen] = useState(false)
  const [view, setView] = useState<"list" | "grid">("list")
  const [sortBy, setSortBy] = useState<SortKey>("recent")

  const { data: allPosts, isLoading } = useContentPosts({
    ...(statusFilter !== "all" && { status: statusFilter }),
    ...(pillarFilter !== "all" && { pillar: pillarFilter }),
  })
  const syncVoyager = useSyncVoyager()
  const { data: contentSettings } = useContentSettings()
  const notionConfigured = !!(
    contentSettings?.notion_api_key_set && contentSettings?.notion_database_id
  )

  // Filtro de mês client-side — mesma prioridade de data que o PostListView usa para exibir
  const posts = useMemo(() => {
    if (!allPosts || !monthFilter) return allPosts
    return allPosts.filter((post) => {
      const dateStr = post.published_at ?? post.publish_date ?? post.created_at
      if (!dateStr) return false
      try {
        return isSameMonth(parseISO(dateStr), parseISO(monthFilter + "-01"))
      } catch {
        return false
      }
    })
  }, [allPosts, monthFilter])

  // Últimos 12 meses como opções de Select
  const monthOptions = useMemo(() => {
    const now = new Date()
    return Array.from({ length: 12 }, (_, i) => {
      const d = startOfMonth(subMonths(now, i))
      return {
        value: format(d, "yyyy-MM"),
        label: format(d, "MMM yyyy", { locale: ptBR }),
      }
    })
  }, [])

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

          <Select
            value={monthFilter || "all"}
            onValueChange={(v) => setMonthFilter(v === "all" ? "" : v)}
          >
            <SelectTrigger className="h-8 w-36 text-xs">
              <SelectValue placeholder="Todos os meses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="text-xs">
                Todos os meses
              </SelectItem>
              {monthOptions.map((o) => (
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
              aria-label="Visão lista"
              onClick={() => setView("list")}
              className={`px-2.5 h-full flex items-center transition-colors ${view === "list" ? "bg-(--accent) text-white" : "text-(--text-secondary) hover:bg-(--bg-overlay)"}`}
            >
              <List className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              aria-label="Visão grade"
              onClick={() => setView("grid")}
              className={`px-2.5 h-full flex items-center transition-colors ${view === "grid" ? "bg-(--accent) text-white" : "text-(--text-secondary) hover:bg-(--bg-overlay)"}`}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1.5"
            disabled={syncVoyager.isPending}
            onClick={() =>
              syncVoyager.mutate(undefined, {
                onSuccess: () => toast.success("Métricas sincronizadas"),
                onError: (err) =>
                  toast.error(err instanceof Error ? err.message : "Erro ao sincronizar"),
              })
            }
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncVoyager.isPending ? "animate-spin" : ""}`} />
            {syncVoyager.isPending ? "Sincronizando…" : "Sincronizar métricas"}
          </Button>
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
          {notionConfigured && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
              onClick={() => setNotionOpen(true)}
            >
              <NotionLogo className="h-3.5 w-3.5" />
              Importar do Notion
            </Button>
          )}
        </div>
      </div>

      {/* Conteúdo */}
      {view === "list" ? (
        isLoading ? (
          <div className="rounded-lg border border-(--border-default) bg-(--bg-surface) p-4 h-48 animate-pulse" />
        ) : !posts?.length ? (
          <EmptyState onGenerate={() => setCreateOpen(true)} />
        ) : (
          <PostListView posts={posts} sortBy={sortBy} onSortChange={setSortBy} />
        )
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
      <NotionImportDialog open={notionOpen} onOpenChange={setNotionOpen} />
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
