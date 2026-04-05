"use client"

import { useState } from "react"
import { Plus, Filter, Sparkles } from "lucide-react"
import { useContentPosts, type PostStatus, type PostPillar } from "@/lib/api/hooks/use-content"
import { CalendarView } from "@/components/content/calendar-view"
import { AiContentWizard } from "@/components/content/ai-content-wizard"
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
  const [wizardOpen, setWizardOpen] = useState(false)

  const { data: posts } = useContentPosts({
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
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => setWizardOpen(true)}
          >
            <Sparkles className="h-3.5 w-3.5" />
            Gerar com IA
          </Button>
          <Button size="sm" className="h-8 text-xs gap-1.5" onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
            Novo post
          </Button>
        </div>
      </div>

      {/* Conteúdo */}
      <CalendarView posts={posts ?? []} />

      <CreatePostDialog open={createOpen} onOpenChange={setCreateOpen} />
      <AiContentWizard open={wizardOpen} onOpenChange={setWizardOpen} />
    </div>
  )
}
