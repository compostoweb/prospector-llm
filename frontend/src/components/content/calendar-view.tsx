"use client"

import {
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  getDay,
  format,
  isSameDay,
  isSameMonth,
  addMonths,
  subMonths,
  parseISO,
} from "date-fns"
import { ptBR } from "date-fns/locale"
import { ChevronLeft, ChevronRight, Plus } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/content/post-badges"
import { EditPostDialog } from "@/components/content/edit-post-dialog"
import { CreatePostDialog } from "@/components/content/create-post-dialog"
import { type ContentPost } from "@/lib/api/hooks/use-content"
import { cn } from "@/lib/utils"

interface CalendarViewProps {
  posts: ContentPost[]
}

const WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

export function CalendarView({ posts }: CalendarViewProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [editPost, setEditPost] = useState<ContentPost | null>(null)
  const [createDate, setCreateDate] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd })

  // Padding de dias antes do início do mês (domingo = 0)
  const startPad = getDay(monthStart)

  // Mapear posts com publish_date para o mapa dia → posts
  const postsByDay = new Map<string, ContentPost[]>()
  for (const post of posts) {
    if (!post.publish_date) continue
    const key = format(parseISO(post.publish_date), "yyyy-MM-dd")
    const existing = postsByDay.get(key) ?? []
    postsByDay.set(key, [...existing, post])
  }

  function handleDayClick(day: Date) {
    const dateStr = format(day, "yyyy-MM-dd") + "T09:00"
    setCreateDate(dateStr)
    setCreateOpen(true)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header do mês */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
          className="p-1 rounded hover:bg-(--bg-overlay) text-(--text-secondary)"
          aria-label="Mês anterior"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        <h2 className="text-sm font-semibold text-(--text-primary) capitalize">
          {format(currentMonth, "MMMM yyyy", { locale: ptBR })}
        </h2>

        <button
          type="button"
          onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
          className="p-1 rounded hover:bg-(--bg-overlay) text-(--text-secondary)"
          aria-label="Próximo mês"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Grid */}
      <div className="rounded-lg border border-(--border-default) overflow-hidden">
        {/* Cabeçalho dos dias */}
        <div className="grid grid-cols-7 bg-(--bg-overlay)">
          {WEEKDAYS.map((d) => (
            <div
              key={d}
              className="text-center text-xs font-medium text-(--text-tertiary) py-2"
            >
              {d}
            </div>
          ))}
        </div>

        {/* Dias */}
        <div className="grid grid-cols-7 divide-x divide-y divide-(--border-subtle)">
          {/* Padding inicial */}
          {Array.from({ length: startPad }).map((_, i) => (
            <div key={`pad-${i}`} className="h-28 bg-(--bg-overlay) opacity-40" />
          ))}

          {days.map((day) => {
            const key = format(day, "yyyy-MM-dd")
            const dayPosts = postsByDay.get(key) ?? []
            const isToday = isSameDay(day, new Date())

            return (
              <div
                key={key}
                className={cn(
                  "h-28 p-1.5 flex flex-col gap-1 bg-(--bg-surface) group",
                  !isSameMonth(day, currentMonth) && "opacity-40",
                )}
              >
                {/* Número do dia + botão adicionar */}
                <div className="flex items-center justify-between">
                  <span
                    className={cn(
                      "text-xs font-medium w-5 h-5 flex items-center justify-center rounded-full",
                      isToday
                        ? "bg-(--accent) text-white"
                        : "text-(--text-secondary)",
                    )}
                  >
                    {format(day, "d")}
                  </span>
                  <button
                    type="button"
                    aria-label={`Criar post em ${format(day, "dd/MM")}`}
                    onClick={() => handleDayClick(day)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-(--accent-subtle) text-(--text-tertiary)"
                  >
                    <Plus className="h-3 w-3" />
                  </button>
                </div>

                {/* Posts do dia */}
                <div className="flex flex-col gap-0.5 overflow-y-auto flex-1 min-h-0">
                  {dayPosts.slice(0, 3).map((post) => (
                    <button
                      key={post.id}
                      type="button"
                      onClick={() => setEditPost(post)}
                      className="text-left truncate text-[10px] px-1 py-0.5 rounded bg-(--accent-subtle) text-(--accent-subtle-fg) hover:opacity-80 transition-opacity leading-tight"
                    >
                      {post.title}
                    </button>
                  ))}
                  {dayPosts.length > 3 && (
                    <span className="text-[10px] text-(--text-tertiary) px-1">
                      +{dayPosts.length - 3} mais
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Legenda */}
      <div className="flex items-center gap-4 flex-wrap">
        {(["draft", "approved", "scheduled", "published"] as const).map((s) => (
          <div key={s} className="flex items-center gap-1.5">
            <StatusBadge status={s} />
          </div>
        ))}
        <p className="text-xs text-(--text-tertiary) ml-auto">
          Clique em um dia para criar post · Clique no título para editar
        </p>
      </div>

      <EditPostDialog
        post={editPost}
        open={!!editPost}
        onOpenChange={(v) => { if (!v) setEditPost(null) }}
      />
      <CreatePostDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        defaultPublishDate={createDate ?? undefined}
      />
    </div>
  )
}
