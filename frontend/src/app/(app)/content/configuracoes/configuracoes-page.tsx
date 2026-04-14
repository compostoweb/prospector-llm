"use client"

import { useEffect, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import {
  ExternalLink,
  Linkedin,
  CheckCircle,
  AlertCircle,
  Loader2,
  Save,
  AlertTriangle,
  BarChart2,
  RefreshCw,
  BookOpen,
  Eye,
  EyeOff,
} from "lucide-react"
import {
  useContentSettings,
  useUpdateContentSettings,
  useLinkedInContentAccount,
  useSyncVoyager,
  useNotionColumns,
  useSaveNotionMappings,
  type NotionDatabaseColumn,
  type NotionColumnMappings,
} from "@/lib/api/hooks/use-content"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useSession } from "next-auth/react"
import { useQueryClient } from "@tanstack/react-query"
import { contentKeys } from "@/lib/api/hooks/use-content"

const UNMAPPED_NOTION_COLUMN = "__unmapped__"

export default function ConfiguracoesPage() {
  const { data: settings, isLoading } = useContentSettings()
  const update = useUpdateContentSettings()
  const { data: linkedinAccount, isLoading: loadingLinkedin } = useLinkedInContentAccount()
  const syncVoyager = useSyncVoyager()
  const notionColumns = useNotionColumns()
  const saveMappings = useSaveNotionMappings()
  const { data: session } = useSession()
  const searchParams = useSearchParams()
  const router = useRouter()
  const queryClient = useQueryClient()

  // Banner de resultado do OAuth LinkedIn
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null)
  const [syncResult, setSyncResult] = useState<{ created: number; updated: number } | null>(null)

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

  // Notion form (api key nunca é pré-preenchida — só enviada se o usuário digitar)
  const [notionForm, setNotionForm] = useState({ api_key: "", database_id: "" })
  const [notionDirty, setNotionDirty] = useState(false)
  const [showNotionKey, setShowNotionKey] = useState(false)
  const [mappingForm, setMappingForm] = useState<Partial<NotionColumnMappings>>({
    title: "",
    body: "",
  })
  const [mappingDirty, setMappingDirty] = useState(false)
  useEffect(() => {
    if (!settings) return
    setNotionForm((prev) => ({ ...prev, database_id: settings.notion_database_id ?? "" }))
    if (settings.notion_column_mappings) {
      setMappingForm(settings.notion_column_mappings)
    }
  }, [settings])

  function handleNotionChange(field: keyof typeof notionForm, value: string) {
    setNotionForm((prev) => ({ ...prev, [field]: value }))
    setNotionDirty(true)
  }

  async function handleSaveNotion() {
    const payload: Record<string, string | null> = {
      notion_database_id: notionForm.database_id || null,
    }
    // Só envia a chave se o usuário digitou algo novo
    if (notionForm.api_key) {
      payload.notion_api_key = notionForm.api_key
    }
    await update.mutateAsync(payload)
    setNotionDirty(false)
    setNotionForm((prev) => ({ ...prev, api_key: "" }))
  }

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

  const [syncError, setSyncError] = useState<string | null>(null)

  async function handleSyncNow() {
    setSyncError(null)
    setSyncResult(null)
    try {
      const result = await syncVoyager.mutateAsync()
      if (!result.success) {
        setSyncError(result.error ?? "Erro desconhecido na sincronização")
        return
      }
      setSyncResult({ created: result.posts_created, updated: result.posts_updated })
      setTimeout(() => setSyncResult(null), 10000)
    } catch {
      // erro HTTP mostrado via syncVoyager.isError
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
          {!form.author_voice && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>
                Configure sua voz para que a IA gere posts no seu estilo. Sem isso, será usado um
                template genérico.
              </span>
            </div>
          )}
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

      {/* Analytics — sincronização de métricas via Unipile */}
      {linkedinAccount?.is_active && (
        <section className="lg:col-span-2 bg-(--bg-surface) rounded-lg border border-(--border-default) p-5 shadow-(--shadow-sm) flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <BarChart2 className="h-4 w-4 text-(--text-secondary)" />
            <h2 className="text-sm font-semibold text-(--text-primary)">Analytics</h2>
            <span className="ml-auto text-xs px-1.5 py-0.5 rounded bg-(--accent-subtle) text-(--accent-fg)">
              Perfil pessoal
            </span>
          </div>

          {linkedinAccount.has_unipile ? (
            <>
              <p className="text-sm text-(--text-secondary)">
                Importação automática de métricas (impressões, reações, comentários,
                compartilhamentos) dos seus posts do LinkedIn via conta Unipile conectada.
              </p>

              <div className="flex items-center gap-3 pt-1 border-t border-(--border-default)">
                <div className="flex-1">
                  <p className="text-xs text-(--text-secondary)">
                    Sincronização automática: 3x/dia (08h, 14h, 20h)
                  </p>
                  {linkedinAccount.last_voyager_sync_at && (
                    <p className="text-xs text-(--text-tertiary)">
                      Último sync:{" "}
                      {new Date(linkedinAccount.last_voyager_sync_at).toLocaleString("pt-BR")}
                    </p>
                  )}
                  {syncResult && (
                    <p className="text-xs text-(--success)">
                      Sync concluído: {syncResult.created} posts importados, {syncResult.updated}{" "}
                      métricas atualizadas
                    </p>
                  )}
                  {syncError && <p className="text-xs text-(--danger)">{syncError}</p>}
                  {syncVoyager.isError && (
                    <p className="text-xs text-(--danger)">
                      {syncVoyager.error instanceof Error
                        ? syncVoyager.error.message
                        : "Erro no sync"}
                    </p>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSyncNow}
                  disabled={syncVoyager.isPending}
                  className="gap-1.5 shrink-0"
                >
                  {syncVoyager.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5" />
                  )}
                  Sincronizar agora
                </Button>
              </div>
            </>
          ) : (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>
                Para importar métricas dos seus posts, conecte sua conta LinkedIn via Unipile em{" "}
                <a
                  href="/configuracoes/linkedin-accounts"
                  className="underline font-medium hover:text-amber-900 dark:hover:text-amber-100"
                >
                  Configurações do Sistema → Contas LinkedIn
                </a>
                .
              </span>
            </div>
          )}
        </section>
      )}

      {/* Notion */}
      <section className="lg:col-span-2 bg-(--bg-surface) rounded-lg border border-(--border-default) p-5 shadow-(--shadow-sm) flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-(--text-secondary)" />
          <h2 className="text-sm font-semibold text-(--text-primary)">Integração Notion</h2>
        </div>

        <p className="text-sm text-(--text-secondary)">
          Configure para importar posts do seu Calendário Editorial do Notion diretamente para o
          Content Hub. Use uma{" "}
          <a
            href="https://www.notion.so/my-integrations"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-(--text-primary)"
          >
            Internal Integration
          </a>{" "}
          e adicione ela ao banco de dados no Notion.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="notion_api_key">API Key (Integration Token)</Label>
            <div className="relative">
              <Input
                id="notion_api_key"
                type={showNotionKey ? "text" : "password"}
                value={notionForm.api_key}
                onChange={(e) => handleNotionChange("api_key", e.target.value)}
                placeholder={
                  settings?.notion_api_key_set
                    ? "••••••••••••••• (configurada)"
                    : "secret_xxxxxxxxxxx"
                }
                className="pr-10"
                autoComplete="off"
              />
              <button
                type="button"
                onClick={() => setShowNotionKey((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-(--text-tertiary) hover:text-(--text-primary)"
                aria-label={showNotionKey ? "Ocultar chave" : "Mostrar chave"}
              >
                {showNotionKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-xs text-(--text-tertiary)">
              Comece com <code className="font-mono">secret_</code>. Deixe em branco para manter a
              chave atual.
            </p>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="notion_database_id">Database ID</Label>
            <Input
              id="notion_database_id"
              value={notionForm.database_id}
              onChange={(e) => handleNotionChange("database_id", e.target.value)}
              placeholder="eb13873b127340c0b6841814971c177a"
            />
            <p className="text-xs text-(--text-tertiary)">
              UUID extraído da URL do banco:{" "}
              <code className="font-mono">
                notion.so/…/<strong>ID</strong>
              </code>
            </p>
          </div>
        </div>

        {settings?.notion_api_key_set && settings.notion_database_id && (
          <div className="flex items-center gap-2 text-xs text-(--success-default)">
            <CheckCircle className="h-3.5 w-3.5 shrink-0" />
            Notion configurado — botão &quot;Importar do Notion&quot; disponível na lista de posts.
          </div>
        )}

        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSaveNotion}
            disabled={!notionDirty || update.isPending}
            className="gap-2"
          >
            {update.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            Salvar Notion
          </Button>
        </div>

        {/* Mapeamento de colunas */}
        {settings?.notion_api_key_set && settings.notion_database_id && (
          <div className="border-t border-(--border-default) pt-4 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-(--text-primary)">Mapeamento de colunas</p>
                <p className="text-xs text-(--text-tertiary)">
                  Vincule as colunas do seu banco Notion aos campos do Content Hub.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => notionColumns.refetch()}
                disabled={notionColumns.isFetching}
                className="gap-2 shrink-0"
              >
                {notionColumns.isFetching ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
                Carregar colunas
              </Button>
            </div>

            {notionColumns.isError && (
              <p className="text-xs text-(--danger)">
                {notionColumns.error instanceof Error
                  ? notionColumns.error.message
                  : "Erro ao buscar colunas"}
              </p>
            )}

            {notionColumns.data && notionColumns.data.length > 0 && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(
                    [
                      { key: "title", label: "Título do post", required: true },
                      { key: "body", label: "Texto do post", required: true },
                      { key: "pillar", label: "Pilar", required: false },
                      { key: "status", label: "Status", required: false },
                      { key: "publish_date", label: "Data de publicação", required: false },
                      { key: "week_number", label: "Nº da semana", required: false },
                      { key: "hashtags", label: "Hashtags", required: false },
                    ] as { key: keyof NotionColumnMappings; label: string; required: boolean }[]
                  ).map(({ key, label, required }) => (
                    <div key={key} className="grid gap-1">
                      <Label htmlFor={`map_${key}`} className="text-xs">
                        {label}
                        {required && <span className="text-(--danger) ml-0.5">*</span>}
                      </Label>
                      <Select
                        value={mappingForm[key] ?? (required ? "" : UNMAPPED_NOTION_COLUMN)}
                        onValueChange={(val) => {
                          setMappingForm((prev) => ({
                            ...prev,
                            [key]: val === UNMAPPED_NOTION_COLUMN ? undefined : val,
                          }))
                          setMappingDirty(true)
                        }}
                      >
                        <SelectTrigger id={`map_${key}`} className="h-8 text-sm">
                          <SelectValue placeholder="Selecione a coluna…" />
                        </SelectTrigger>
                        <SelectContent>
                          {!required && (
                            <SelectItem value={UNMAPPED_NOTION_COLUMN}>
                              <span className="text-(--text-tertiary)">— não mapeado —</span>
                            </SelectItem>
                          )}
                          {notionColumns.data.map((col: NotionDatabaseColumn) => (
                            <SelectItem key={col.name} value={col.name}>
                              {col.name}
                              <span className="ml-1.5 text-[10px] text-(--text-tertiary)">
                                ({col.type})
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>

                <div className="flex justify-end">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={async () => {
                      if (!mappingForm.title || !mappingForm.body) return
                      await saveMappings.mutateAsync(mappingForm as NotionColumnMappings)
                      setMappingDirty(false)
                    }}
                    disabled={
                      !mappingDirty ||
                      !mappingForm.title ||
                      !mappingForm.body ||
                      saveMappings.isPending
                    }
                    className="gap-2"
                  >
                    {saveMappings.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Save className="h-3.5 w-3.5" />
                    )}
                    Salvar mapeamento
                  </Button>
                </div>

                {saveMappings.isSuccess && (
                  <p className="text-xs text-(--success) text-right">
                    Mapeamento salvo com sucesso.
                  </p>
                )}
                {saveMappings.isError && (
                  <p className="text-xs text-(--danger) text-right">
                    {saveMappings.error instanceof Error
                      ? saveMappings.error.message
                      : "Erro ao salvar mapeamento"}
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </section>

      {/* Footer — botão salvar */}
      <div className="lg:col-span-2 flex justify-end">
        <Button onClick={handleSave} disabled={!isDirty || update.isPending} className="gap-2">
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
