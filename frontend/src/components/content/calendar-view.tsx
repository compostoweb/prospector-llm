"use client"

import {
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  getDay,
  format,
  isSameDay,
  isToday as isTodayFn,
  isSameMonth,
  addMonths,
  subMonths,
} from "date-fns"
import { ptBR } from "date-fns/locale"
import { toZonedTime } from "date-fns-tz"
import { ChevronLeft, ChevronRight, Plus, CalendarCheck } from "lucide-react"
import { useState, useMemo } from "react"
import { type PostStatus } from "@/lib/api/hooks/use-content"
import { EditPostDialog } from "@/components/content/edit-post-dialog"
import { CreatePostDialog } from "@/components/content/create-post-dialog"
import { type ContentPost } from "@/lib/api/hooks/use-content"
import { cn } from "@/lib/utils"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { HoverBubble } from "@/components/ui/hover-bubble"

interface CalendarViewProps {
  posts: ContentPost[]
}

const WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

const STATUS_PILL: Record<PostStatus, string> = {
  draft: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  approved: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  scheduled: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  published: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
}

const STATUS_LABEL: Record<PostStatus, string> = {
  draft: "Rascunho",
  approved: "Aprovado",
  scheduled: "Agendado",
  published: "Publicado",
  failed: "Falhou",
}

export function CalendarView({ posts }: CalendarViewProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [editPost, setEditPost] = useState<ContentPost | null>(null)
  const [createDate, setCreateDate] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  // Opções de navegação rápida: 12 meses atrás + 6 à frente
  const monthNavOptions = useMemo(() => {
    const now = new Date()
    const options: { value: string; label: string }[] = []
    for (let i = 12; i >= 0; i--) {
      const d = startOfMonth(subMonths(now, i))
      options.push({
        value: format(d, "yyyy-MM"),
        label: format(d, "MMM yyyy", { locale: ptBR }),
      })
    }
    for (let i = 1; i <= 6; i++) {
      const d = startOfMonth(addMonths(now, i))
      options.push({
        value: format(d, "yyyy-MM"),
        label: format(d, "MMM yyyy", { locale: ptBR }),
      })
    }
    return options
  }, [])

  const currentMonthValue = format(startOfMonth(currentMonth), "yyyy-MM")

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd })

  // Padding de dias antes do início do mês (domingo = 0)
  const startPad = getDay(monthStart)

  // Mapear posts com publish_date para o mapa dia → posts
  const postsByDay = new Map<string, ContentPost[]>()
  for (const post of posts) {
    if (!post.publish_date) continue
    const key = format(toZonedTime(post.publish_date, "America/Sao_Paulo"), "yyyy-MM-dd")
    const existing = postsByDay.get(key) ?? []
    postsByDay.set(key, [...existing, post])
  }

  function handleDayClick(day: Date) {
    const dateStr = format(day, "yyyy-MM-dd") + "T09:00"
    setCreateDate(dateStr)
    setCreateOpen(true)
  }

  const isCurrentMonth = isSameDay(startOfMonth(currentMonth), startOfMonth(new Date()))

  return (
    <TooltipProvider delayDuration={120} skipDelayDuration={0}>
      <div className="flex flex-col gap-4">
        {/* Header do mês */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
            className="p-1 rounded hover:bg-(--bg-overlay) text-(--text-secondary)"
            aria-label="Mês anterior"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          <Select
            value={currentMonthValue}
            onValueChange={(v) => setCurrentMonth(startOfMonth(new Date(v + "-15")))}
          >
            <SelectTrigger className="h-8 w-36 text-sm font-semibold capitalize border-none shadow-none focus:ring-0 px-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {monthNavOptions.map((o) => (
                <SelectItem key={o.value} value={o.value} className="text-xs capitalize">
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <button
            type="button"
            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
            className="p-1 rounded hover:bg-(--bg-overlay) text-(--text-secondary)"
            aria-label="Próximo mês"
          >
            <ChevronRight className="h-4 w-4" />
          </button>

          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => setCurrentMonth(new Date())}
                className={cn(
                  "ml-2 inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md transition-all",
                  isCurrentMonth
                    ? "text-(--text-tertiary) border border-(--border-default) hover:bg-(--bg-overlay)"
                    : "bg-(--accent) text-white shadow-sm hover:opacity-90",
                )}
              >
                <CalendarCheck className="h-3 w-3" />
                Hoje
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              {isCurrentMonth ? "Você já está no mês atual" : "Voltar ao mês atual"}
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Grid */}
        <div className="rounded-lg border border-(--border-default) overflow-hidden">
          {/* Cabeçalho dos dias */}
          <div className="grid grid-cols-7 bg-(--bg-overlay)">
            {WEEKDAYS.map((d) => (
              <div key={d} className="text-center text-xs font-medium text-(--text-tertiary) py-2">
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
              const isToday = isTodayFn(day)

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
                        isToday ? "bg-(--accent) text-white" : "text-(--text-secondary)",
                      )}
                    >
                      {format(day, "d")}
                    </span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          aria-label={`Criar post em ${format(day, "dd/MM")}`}
                          onClick={() => handleDayClick(day)}
                          className="p-0.5 rounded-full bg-(--success-subtle) text-(--success) hover:bg-(--success) hover:text-white transition-colors"
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent side="top">
                        Criar post para {format(day, "dd 'de' MMMM", { locale: ptBR })}
                      </TooltipContent>
                    </Tooltip>
                  </div>

                  {/* Posts do dia */}
                  <div className="flex flex-col gap-0.5 overflow-y-auto flex-1 min-h-0">
                    {dayPosts.slice(0, 3).map((post) => (
                      <HoverBubble
                        key={post.id}
                        side="right"
                        align="start"
                        sideOffset={10}
                        className="w-full"
                        contentClassName="max-w-64 flex flex-col gap-1"
                        content={
                          <>
                            <div className="flex items-center gap-1.5">
                              <span
                                className={cn(
                                  "inline-block text-[10px] font-medium px-1.5 py-0.5 rounded",
                                  STATUS_PILL[post.status as PostStatus] ?? STATUS_PILL.draft,
                                )}
                              >
                                {STATUS_LABEL[post.status as PostStatus] ?? post.status}
                              </span>
                              {post.pillar && (
                                <span className="text-[10px] opacity-70 capitalize">
                                  {post.pillar === "authority"
                                    ? "Autoridade"
                                    : post.pillar === "case"
                                      ? "Caso"
                                      : "Visão"}
                                </span>
                              )}
                            </div>
                            {post.publish_date && (
                              <p className="text-[11px] opacity-90">
                                {format(
                                  toZonedTime(post.publish_date, "America/Sao_Paulo"),
                                  "dd/MM/yyyy 'às' HH:mm",
                                  { locale: ptBR },
                                )}
                              </p>
                            )}
                            {post.character_count && (
                              <p className="text-[11px] opacity-70">
                                {post.character_count} caracteres
                              </p>
                            )}
                            {post.hook_type && (
                              <p className="text-[11px] opacity-70">
                                Gancho: {post.hook_type.replace("_", " ")}
                              </p>
                            )}
                          </>
                        }
                      >
                          <button
                            type="button"
                            onClick={() => setEditPost(post)}
                            className={cn(
                              "text-left text-[10px] px-1 py-0.5 rounded hover:opacity-80 transition-opacity leading-tight w-full",
                              STATUS_PILL[post.status as PostStatus] ?? STATUS_PILL.draft,
                            )}
                          >
                            {post.pillar && (
                              <span
                                className={cn(
                                  "inline-block shrink-0 text-[9px] font-semibold px-1 py-0 rounded-full mr-0.5 align-middle",
                                  post.pillar === "authority" && "bg-(--accent)/20 text-(--accent)",
                                  post.pillar === "case" && "bg-(--success)/20 text-(--success)",
                                  post.pillar === "vision" && "bg-(--warning)/20 text-(--warning)",
                                )}
                              >
                                {post.pillar === "authority"
                                  ? "Aut"
                                  : post.pillar === "case"
                                    ? "Caso"
                                    : "Vis"}
                              </span>
                            )}
                            <span className="line-clamp-3 wrap-break-word">{post.title}</span>
                          </button>
                      </HoverBubble>
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
        <div className="flex items-center gap-3 flex-wrap">
          {(Object.keys(STATUS_LABEL) as PostStatus[]).map((s) => (
            <div key={s} className="flex items-center gap-1">
              <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium", STATUS_PILL[s])}>
                {STATUS_LABEL[s]}
              </span>
            </div>
          ))}
          <p className="text-xs text-(--text-tertiary) ml-auto">
            Clique em um dia para criar post · Clique no título para editar
          </p>
        </div>

        <EditPostDialog
          post={editPost}
          open={!!editPost}
          onOpenChange={(value) => {
            if (!value) {
              setEditPost(null)
            }
          }}
        />
        <CreatePostDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          {...(createDate ? { defaultPublishDate: createDate } : {})}
        />
      </div>
    </TooltipProvider>
  )
}
