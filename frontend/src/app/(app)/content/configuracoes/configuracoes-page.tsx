"use client"

import { useEffect, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { ExternalLink, Linkedin, CheckCircle, AlertCircle, Loader2, Save } from "lucide-react"
import {
  useContentSettings,
  useUpdateContentSettings,
  useLinkedInContentAccount,
} from "@/lib/api/hooks/use-content"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useSession } from "next-auth/react"
import { useQueryClient } from "@tanstack/react-query"
import { contentKeys } from "@/lib/api/hooks/use-content"

export default function ConfiguracoesPage() {
  const { data: settings, isLoading } = useContentSettings()
  const update = useUpdateContentSettings()
  const { data: linkedinAccount, isLoading: loadingLinkedin } = useLinkedInContentAccount()
  const { data: session } = useSession()
  const searchParams = useSearchParams()
  const router = useRouter()
  const queryClient = useQueryClient()

  // Banner de resultado do OAuth LinkedIn
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null)

  useEffect(() => {
    const connected = searchParams.get("linkedin_connected")
    const error = searchParams.get("linkedin_error")
    if (connected) {
      setBanner({ type: "success", message: "Conta LinkedIn conectada com sucesso!" })
      // Invalidar cache para refletir a nova conta
      queryClient.invalidateQueries({ queryKey: contentKeys.linkedinStatus() })
      router.replace("/content/configuracoes")
    } else if (error) {
      setBanner({ type: "error", message: decodeURIComponent(error) })
      router.replace("/content/configuracoes")
    }
  }, [searchParams, router, queryClient])

  const [form, setForm] = useState({
    author_name: "",
    author_voice: "",
    default_publish_time: "",
    posts_per_week: 3,
  })

  const [isDirty, setIsDirty] = useState(false)
  useEffect(() => {
    if (!settings) return
    setForm({
      author_name: settings.author_name ?? "",
      author_voice: settings.author_voice ?? "",
      default_publish_time: settings.default_publish_time ?? "",
      posts_per_week: settings.posts_per_week,
    })
  }, [settings])

  function handleChange(field: keyof typeof form, value: string | number) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setIsDirty(true)
  }

  async function handleSave() {
    await update.mutateAsync({
      author_name: form.author_name || null,
      author_voice: form.author_voice || null,
      default_publish_time: form.default_publish_time || null,
      posts_per_week: form.posts_per_week,
    })
    setIsDirty(false)
  }

  async function handleConnectLinkedIn() {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/content/linkedin/auth-url`,
      {
        headers: { Authorization: `Bearer ${session?.accessToken ?? ""}` },
      },
    )
    const json = await res.json()
    if (json.url) {
      window.location.href = json.url
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-6 w-6 animate-spin text-(--text-tertiary)" />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-4xl">
      {/* Banner OAuth resultado */}
      {banner && (
        <div
          className={`lg:col-span-2 flex items-center gap-2 rounded-md px-3 py-2.5 text-sm ${
            banner.type === "success"
              ? "bg-(--success-subtle) text-(--success-subtle-fg)"
              : "bg-(--danger-subtle) text-(--danger-subtle-fg)"
          }`}
        >
          {banner.type === "success" ? (
            <CheckCircle className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          <span className="flex-1">{banner.message}</span>
          <button
            type="button"
            aria-label="Fechar"
            onClick={() => setBanner(null)}
            className="opacity-70 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      )}
      {/* Perfil do autor */}
      <section className="bg-(--bg-surface) rounded-(--radius-lg) border border-(--border-default) p-5 shadow-(--shadow-sm) flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-(--text-primary)">Perfil do autor</h2>

        <div className="grid gap-1.5">
          <Label htmlFor="author_name">Nome do autor</Label>
          <Input
            id="author_name"
            value={form.author_name}
            onChange={(e) => handleChange("author_name", e.target.value)}
            placeholder="Ex: João Silva"
          />
          <p className="text-xs text-(--text-tertiary)">
            Usado nos prompts de geração para personalizar o estilo.
          </p>
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor="author_voice">Voz e estilo do autor</Label>
          <Textarea
            id="author_voice"
            value={form.author_voice}
            onChange={(e) => handleChange("author_voice", e.target.value)}
            placeholder="Descreva o estilo de escrita, tom, temas preferidos, público-alvo...&#10;&#10;Ex: Escrevo para gestores de PMEs, prefiro linguagem direta sem jargões, uso dados e exemplos concretos, nunca uso emojis."
            rows={6}
            className="resize-none text-sm"
          />
          <p className="text-xs text-(--text-tertiary)">
            Quanto mais detalhado, mais fiel ao seu estilo será o conteúdo gerado.
          </p>
        </div>
      </section>

      {/* Agenda */}
      <section className="bg-(--bg-surface) rounded-(--radius-lg) border border-(--border-default) p-5 shadow-(--shadow-sm) flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-(--text-primary)">Agenda de publicação</h2>

        <div className="grid gap-1.5">
          <Label htmlFor="default_publish_time">Horário padrão de publicação</Label>
          <Input
            id="default_publish_time"
            type="time"
            value={form.default_publish_time}
            onChange={(e) => handleChange("default_publish_time", e.target.value)}
          />
          <p className="text-xs text-(--text-tertiary)">
            Horário pré-preenchido ao agendar um post (fuso horário local).
          </p>
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor="posts_per_week">Posts por semana</Label>
          <Input
            id="posts_per_week"
            type="number"
            min={1}
            max={7}
            value={form.posts_per_week}
            onChange={(e) => handleChange("posts_per_week", parseInt(e.target.value, 10) || 1)}
            className="w-24"
          />
          <p className="text-xs text-(--text-tertiary)">
            Meta de publicações semanais — usado para sugestões de temas.
          </p>
        </div>

        {/* LinkedIn */}
        <div className="mt-2 rounded-(--radius-md) border border-(--border-default) p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Linkedin className="h-4 w-4 text-[#0A66C2]" />
            <span className="text-sm font-medium text-(--text-primary)">Conta LinkedIn</span>
          </div>

          {loadingLinkedin ? (
            <div className="flex items-center gap-2 text-xs text-(--text-tertiary)">
              <Loader2 className="h-3 w-3 animate-spin" />
              Verificando conexão…
            </div>
          ) : linkedinAccount?.is_active ? (
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-(--success) mt-0.5 shrink-0" />
              <div>
                <p className="text-sm text-(--text-primary)">
                  {linkedinAccount.display_name ?? linkedinAccount.person_urn}
                </p>
                {linkedinAccount.token_expires_at && (
                  <p className="text-xs text-(--text-tertiary)">
                    Token expira em{" "}
                    {new Date(linkedinAccount.token_expires_at).toLocaleDateString("pt-BR")}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-xs text-(--text-secondary)">
                <AlertCircle className="h-3.5 w-3.5 text-(--warning)" />
                Nenhuma conta conectada
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2 w-fit"
                onClick={handleConnectLinkedIn}
              >
                <Linkedin className="h-3.5 w-3.5 text-[#0A66C2]" />
                Conectar LinkedIn
                <ExternalLink className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>
      </section>

      {/* Footer — botão salvar */}
      <div className="lg:col-span-2 flex justify-end">
        <Button
          onClick={handleSave}
          disabled={!isDirty || update.isPending}
          className="gap-2"
        >
          {update.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Salvando…
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Salvar alterações
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
