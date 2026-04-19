"use client"

import { useState, useRef, useMemo, useEffect } from "react"
import {
  useTTSProviders,
  useTTSVoices,
  useCreateVoice,
  useDeleteVoice,
  useTestTTS,
} from "@/lib/api/hooks/use-tts"
import { useTenant, useUpdateIntegrations } from "@/lib/api/hooks/use-tenant"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Volume2,
  Play,
  Trash2,
  Upload,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Search,
  Star,
  Mic,
  Square,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { SettingsPageShell, SettingsPanel } from "@/components/settings/settings-shell"

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
const VOICES_PER_PAGE = 5

const PROVIDER_LABELS: Record<string, string> = {
  elevenlabs: "ElevenLabs",
  edge: "Edge TTS",
  speechify: "Speechify",
  voicebox: "Voicebox",
  xtts: "XTTS v2",
}

export default function VozPage() {
  const { data: providersData } = useTTSProviders()
  const { data: tenant } = useTenant()
  const createVoice = useCreateVoice()
  const deleteVoice = useDeleteVoice()
  const testTTS = useTestTTS()
  const updateIntegrations = useUpdateIntegrations()
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const integration = tenant?.integration ?? null
  const ttsDefaultVoiceIds = useMemo<Record<string, string>>(
    () => integration?.tts_default_voice_ids ?? {},
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(integration?.tts_default_voice_ids)],
  )
  const ttsDefaultProvider = integration?.tts_default_provider ?? null

  const [selectedProvider, setSelectedProvider] = useState<string>("elevenlabs")
  const [newName, setNewName] = useState("")
  const [newLanguage, setNewLanguage] = useState("pt-BR")
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [consent, setConsent] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  // ── Gravação ao vivo ───────────────────────────────────────────────
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const recordingPreviewRef = useRef<HTMLAudioElement | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null)
  const [recordingError, setRecordingError] = useState<string | null>(null)

  // Voice search/filter state
  const [voiceSearch, setVoiceSearch] = useState("")
  const [languageFilter, setLanguageFilter] = useState("all")
  const [visibleCount, setVisibleCount] = useState(VOICES_PER_PAGE)

  // Cleanup: libera URL do blob e timer ao desmontar
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (recordedUrl) URL.revokeObjectURL(recordedUrl)
    }
  }, [recordedUrl])

  // Busca vozes do provider selecionado (só roda quando selectedProvider está definido)
  const { data: voicesData, isLoading: loadingVoices } = useTTSVoices(selectedProvider)

  const providers = providersData?.providers ?? []
  const allVoices = voicesData?.voices ?? []
  const providerVoices = allVoices

  // Sincroniza selectedProvider com o primeiro provider disponível na API
  useEffect(() => {
    if (providers.length > 0 && !providers.includes(selectedProvider)) {
      const first = providers[0]
      if (first) setSelectedProvider(first)
    }
  }, [providers]) // eslint-disable-line react-hooks/exhaustive-deps

  // Extract unique languages for filter
  const languages = useMemo(() => {
    const langs = new Set(providerVoices.map((v) => v.language))
    return Array.from(langs).sort()
  }, [providerVoices])

  // Filter + search
  const filteredVoices = useMemo(() => {
    let result = providerVoices
    if (languageFilter !== "all") {
      result = result.filter((v) => v.language === languageFilter)
    }
    if (voiceSearch.trim()) {
      const q = voiceSearch.toLowerCase()
      result = result.filter(
        (v) => v.name.toLowerCase().includes(q) || v.id.toLowerCase().includes(q),
      )
    }
    // Voz padrão do provider atual sempre em primeiro
    const defaultVoiceId = ttsDefaultVoiceIds[selectedProvider]
    if (defaultVoiceId) {
      result = [...result].sort((a, b) =>
        a.id === defaultVoiceId ? -1 : b.id === defaultVoiceId ? 1 : 0,
      )
    }
    return result
  }, [providerVoices, languageFilter, voiceSearch, ttsDefaultVoiceIds, selectedProvider])

  const visibleVoices = filteredVoices.slice(0, visibleCount)
  const hasMore = visibleCount < filteredVoices.length

  // Reset visible count when filters change
  function handleSearchChange(value: string) {
    setVoiceSearch(value)
    setVisibleCount(VOICES_PER_PAGE)
  }

  function handleLanguageChange(value: string) {
    setLanguageFilter(value)
    setVisibleCount(VOICES_PER_PAGE)
  }

  function formatDuration(seconds: number) {
    const m = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0")
    const s = (seconds % 60).toString().padStart(2, "0")
    return `${m}:${s}`
  }

  async function startRecording() {
    setRecordingError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        const url = URL.createObjectURL(blob)
        setRecordedBlob(blob)
        setRecordedUrl(url)
        stream.getTracks().forEach((t) => t.stop())
      }
      recorder.start()
      mediaRecorderRef.current = recorder
      setIsRecording(true)
      setRecordingSeconds(0)
      timerRef.current = setInterval(() => setRecordingSeconds((s) => s + 1), 1000)
    } catch {
      setRecordingError("Permissão de microfone negada ou indisponível.")
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
    mediaRecorderRef.current = null
    setIsRecording(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  function clearRecording() {
    if (recordedUrl) URL.revokeObjectURL(recordedUrl)
    setRecordedBlob(null)
    setRecordedUrl(null)
    setRecordingSeconds(0)
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > MAX_FILE_SIZE) {
      setUploadError("Arquivo muito grande. Máximo: 5 MB.")
      setAudioFile(null)
      return
    }
    // Descarta gravação ao escolher arquivo
    clearRecording()
    setUploadError(null)
    setAudioFile(file)
  }

  async function handleUpload() {
    setUploadError(null)
    setUploadSuccess(false)

    const fileToUpload = recordedBlob
      ? new File([recordedBlob], `${newName.trim() || "gravacao"}.webm`, { type: "audio/webm" })
      : audioFile

    if (!fileToUpload) {
      setUploadError("Grave ou selecione um arquivo de áudio.")
      return
    }
    if (!newName.trim()) {
      setUploadError("Informe um nome para a voz.")
      return
    }
    if (selectedProvider === "speechify" && !consent) {
      setUploadError("É necessário consentir para clonagem de voz na Speechify.")
      return
    }

    try {
      await createVoice.mutateAsync({
        provider: selectedProvider,
        name: newName.trim(),
        language: newLanguage,
        audioFile: fileToUpload,
      })
      setUploadSuccess(true)
      setNewName("")
      setAudioFile(null)
      clearRecording()
      setConsent(false)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao criar voz"
      setUploadError(msg)
    }
  }

  async function handleTest(provider: string, voiceId: string) {
    const blob = await testTTS.mutateAsync({ provider, voice_id: voiceId })
    const url = URL.createObjectURL(blob)
    if (audioRef.current) {
      audioRef.current.src = url
      await audioRef.current.play()
    }
  }

  async function handleDelete(provider: string, voiceId: string) {
    await deleteVoice.mutateAsync({ provider, voiceId })
  }

  async function handleSetDefault(voiceId: string, provider: string) {
    const isAlreadyDefault = ttsDefaultVoiceIds[provider] === voiceId
    if (isAlreadyDefault) {
      // Desmarca: remove o provider do mapa e limpa o provider padrão se for o mesmo
      const updated = { ...ttsDefaultVoiceIds }
      delete updated[provider]
      await updateIntegrations.mutateAsync({
        tts_default_provider: ttsDefaultProvider === provider ? null : ttsDefaultProvider,
        tts_default_voice_ids: updated,
      })
    } else {
      await updateIntegrations.mutateAsync({
        tts_default_provider: provider,
        tts_default_voice_ids: {
          ...ttsDefaultVoiceIds,
          [provider]: voiceId,
        },
      })
    }
  }

  return (
    <SettingsPageShell
      title="Vozes TTS"
      description="Gerencie vozes disponíveis e crie novas clonagens sem desperdiçar área útil no desktop."
      width="wide"
    >
      {/* Padrão do Sistema */}
      {(ttsDefaultProvider || Object.keys(ttsDefaultVoiceIds).length > 0) && (
        <SettingsPanel
          title="Padrão do Sistema"
          description="Voice ID pré-selecionado ao criar uma nova cadência com voz."
        >
          <div className="flex flex-wrap gap-4">
            {Object.entries(ttsDefaultVoiceIds).map(([provider, voiceId]) => (
              <div
                key={provider}
                className={cn(
                  "flex items-center gap-2 rounded-md border px-3 py-2 text-xs",
                  ttsDefaultProvider === provider
                    ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                    : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary)",
                )}
              >
                <Star className="h-3 w-3 shrink-0" />
                <span className="font-medium">{PROVIDER_LABELS[provider] ?? provider}:</span>
                <code className="max-w-40 truncate font-mono">{voiceId}</code>
              </div>
            ))}
          </div>
        </SettingsPanel>
      )}

      {providers.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {providers.map((p) => (
            <button
              key={p}
              onClick={() => {
                setSelectedProvider(p)
                setVisibleCount(VOICES_PER_PAGE)
                setVoiceSearch("")
                setLanguageFilter("all")
              }}
              className={cn(
                "rounded-md border px-4 py-2 text-sm font-medium transition-colors",
                selectedProvider === p
                  ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                  : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:bg-(--bg-overlay)",
              )}
            >
              {PROVIDER_LABELS[p] ?? p}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.45fr)_360px]">
        <SettingsPanel
          title={`Vozes disponíveis — ${PROVIDER_LABELS[selectedProvider] ?? selectedProvider}`}
          description="Filtre por idioma, teste rapidamente e mantenha a lista de vozes mais útil no topo da tela."
        >
          {loadingVoices ? (
            <div className="flex items-center gap-2 text-sm text-(--text-tertiary)">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando vozes…
            </div>
          ) : providerVoices.length === 0 ? (
            <p className="text-sm text-(--text-disabled)">Nenhuma voz encontrada.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row">
                <div className="relative flex-1">
                  <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-(--text-tertiary)" />
                  <Input
                    value={voiceSearch}
                    onChange={(e) => handleSearchChange(e.target.value)}
                    placeholder="Buscar por nome ou ID…"
                    className="h-8 pl-8 text-xs"
                  />
                </div>
                <Select value={languageFilter} onValueChange={handleLanguageChange}>
                  <SelectTrigger className="h-8 w-full text-xs sm:w-44">
                    <SelectValue placeholder="Idioma" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all" className="text-xs">
                      Todos os idiomas
                    </SelectItem>
                    {languages.map((lang) => (
                      <SelectItem key={lang} value={lang} className="text-xs">
                        {lang}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <p className="text-xs text-(--text-tertiary)">
                {filteredVoices.length === providerVoices.length
                  ? `${providerVoices.length} vozes`
                  : `${filteredVoices.length} de ${providerVoices.length} vozes`}
              </p>

              {filteredVoices.length === 0 ? (
                <p className="text-sm text-(--text-disabled)">Nenhuma voz corresponde à busca.</p>
              ) : (
                <>
                  <div className="grid gap-2">
                    {visibleVoices.map((v) => (
                      <div
                        key={v.id}
                        className="flex items-center justify-between rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-3"
                      >
                        <div className="flex items-center gap-3 overflow-hidden">
                          <Volume2 className="h-4 w-4 shrink-0 text-(--text-tertiary)" />
                          <div className="min-w-0">
                            <span className="block truncate text-sm font-medium text-(--text-primary)">
                              {v.name}
                            </span>
                            <span className="text-[11px] text-(--text-disabled)">
                              {v.language} · {v.is_cloned ? "clone" : "built-in"}
                            </span>
                          </div>
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleTest(v.provider, v.id)}
                            disabled={testTTS.isPending}
                            title="Testar voz"
                            className="h-7 px-2"
                          >
                            <Play className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleSetDefault(v.id, v.provider)}
                            disabled={updateIntegrations.isPending}
                            title="Definir como padrão para este provider"
                            className={cn(
                              "h-7 px-2",
                              ttsDefaultVoiceIds[v.provider] === v.id
                                ? "text-(--accent)"
                                : "text-(--text-tertiary)",
                            )}
                          >
                            <Star
                              className={cn(
                                "h-3.5 w-3.5",
                                ttsDefaultVoiceIds[v.provider] === v.id && "fill-current",
                              )}
                            />
                          </Button>
                          {v.is_cloned ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(v.provider, v.id)}
                              disabled={deleteVoice.isPending}
                              className="h-7 px-2 text-(--danger-fg) hover:text-(--danger-fg)"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>

                  {hasMore ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setVisibleCount((c) => c + VOICES_PER_PAGE)}
                      className="w-full"
                    >
                      Carregar mais ({filteredVoices.length - visibleCount} restantes)
                    </Button>
                  ) : null}
                </>
              )}
            </div>
          )}
        </SettingsPanel>

        <div className="space-y-3 lg:sticky lg:top-4 lg:self-start">
          <SettingsPanel
            title="Clonar nova voz"
            description="Use um áudio curto e limpo para gerar uma voz reutilizável nas cadências."
          >
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-1 lg:grid-cols-1">
                <div>
                  <Label className="mb-1 block text-sm">Nome da voz</Label>
                  <Input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="Ex: Minha voz"
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <Label className="mb-1 block text-sm">Idioma</Label>
                  <Select value={newLanguage} onValueChange={setNewLanguage}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pt-BR" className="text-xs">
                        Português (BR)
                      </SelectItem>
                      <SelectItem value="en-US" className="text-xs">
                        English (US)
                      </SelectItem>
                      <SelectItem value="es-ES" className="text-xs">
                        Español
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Gravação ao vivo */}
              <div className="space-y-2">
                <Label className="block text-sm text-center text-(--text-secondary)">
                  Áudio de referência
                </Label>

                {!recordedBlob ? (
                  <>
                    {!isRecording ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() => void startRecording()}
                        className="w-full gap-2 text-(--accent) border-(--accent) hover:border-(--accent-hover) hover:text-(--accent-hover) hover:bg-(--accent-subtle)"
                      >
                        <Mic className="h-3.5 w-3.5" />
                        Gravar agora
                      </Button>
                    ) : (
                      <div className="flex items-center gap-3 rounded-md border border-(--danger-fg) bg-(--bg-surface) px-3 py-2">
                        <span className="inline-block h-2.5 w-2.5 shrink-0 animate-pulse rounded-full bg-(--danger-fg)" />
                        <span className="font-mono text-sm font-medium text-(--danger-fg)">
                          {formatDuration(recordingSeconds)}
                        </span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={stopRecording}
                          className="ml-auto h-6 gap-1.5 px-2 text-(--danger-fg)"
                        >
                          <Square className="h-3 w-3 fill-current" />
                          Parar
                        </Button>
                      </div>
                    )}

                    <div className="flex items-center gap-2 text-xs text-(--text-secondary)">
                      <div className="h-px flex-1 bg-(--border-default)" />
                      ou
                      <div className="h-px flex-1 bg-(--border-default)" />
                    </div>

                    <Label
                      htmlFor="voice-audio-upload"
                      className={cn(
                        "flex w-full cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed px-3 py-2.5 text-xs font-medium transition-colors",
                        audioFile
                          ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                          : "border-green-700 text-green-700 hover:border-(--accent) hover:text-(--accent)",
                      )}
                    >
                      <Upload className="h-3.5 w-3.5 shrink-0" />
                      {audioFile ? audioFile.name : "Escolher arquivo de áudio"}
                      <input
                        id="voice-audio-upload"
                        type="file"
                        accept="audio/*"
                        onChange={handleFileChange}
                        className="sr-only"
                      />
                    </Label>
                    <p className="text-[11px] text-(--text-secondary) text-center">
                      MP3, WAV ou WebM · 10–30s · até 5 MB
                    </p>
                  </>
                ) : (
                  <div className="space-y-2 rounded-md border border-(--success-fg) bg-(--bg-surface) p-3">
                    <div className="flex items-center gap-2 text-xs">
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-(--success-fg)" />
                      <span className="font-medium text-(--text-primary)">
                        {formatDuration(recordingSeconds)} gravados
                      </span>
                      <button
                        type="button"
                        onClick={clearRecording}
                        title="Descartar gravação"
                        className="ml-auto rounded p-0.5 text-(--text-tertiary) hover:text-(--danger-fg)"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <audio
                      ref={recordingPreviewRef}
                      src={recordedUrl ?? undefined}
                      controls
                      className="h-8 w-full"
                    />
                  </div>
                )}

                {recordingError && <p className="text-xs text-(--danger-fg)">{recordingError}</p>}
              </div>

              {selectedProvider === "speechify" ? (
                <label className="flex items-center gap-2 text-xs text-(--text-secondary)">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                    className="rounded border-(--border-default) accent-(--accent)"
                  />
                  Consinto com a clonagem de voz pela Speechify API
                </label>
              ) : null}

              {uploadError ? (
                <div className="flex items-center gap-2 text-xs text-(--danger-fg)">
                  <AlertCircle className="h-3.5 w-3.5" />
                  {uploadError}
                </div>
              ) : null}

              {uploadSuccess ? (
                <div className="flex items-center gap-2 text-xs text-(--success-fg)">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Voz criada com sucesso!
                </div>
              ) : null}

              <Button
                onClick={handleUpload}
                disabled={createVoice.isPending || (!audioFile && !recordedBlob) || !newName.trim()}
                size="sm"
                className="w-full mx-auto flex"
              >
                {createVoice.isPending ? (
                  <>
                    <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                    Enviando…
                  </>
                ) : (
                  <>
                    <Upload className="mr-1 h-3.5 w-3.5 " />
                    Criar voz
                  </>
                )}
              </Button>
            </div>
          </SettingsPanel>

          <SettingsPanel
            title="Boas práticas"
            description="Clonagens melhores começam com um áudio de referência melhor."
          >
            <p className="text-sm leading-6 text-(--text-secondary)">
              Prefira gravações limpas, sem ruído de fundo e com entonação próxima ao uso final.
              Isso reduz retrabalho e economiza tempo ao testar várias vozes.
            </p>
          </SettingsPanel>
        </div>
      </div>

      <audio ref={audioRef} className="hidden" />
    </SettingsPageShell>
  )
}
