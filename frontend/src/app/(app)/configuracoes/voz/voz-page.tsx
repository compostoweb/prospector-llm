"use client"

import { useState, useRef, useMemo } from "react"
import {
  useTTSProviders,
  useTTSVoices,
  useCreateVoice,
  useDeleteVoice,
  useTestTTS,
} from "@/lib/api/hooks/use-tts"
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
} from "lucide-react"
import { cn } from "@/lib/utils"

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
const VOICES_PER_PAGE = 5

export default function VozPage() {
  const { data: providersData } = useTTSProviders()
  const { data: voicesData, isLoading: loadingVoices } = useTTSVoices()
  const createVoice = useCreateVoice()
  const deleteVoice = useDeleteVoice()
  const testTTS = useTestTTS()
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const [selectedProvider, setSelectedProvider] = useState<string>("speechify")
  const [newName, setNewName] = useState("")
  const [newLanguage, setNewLanguage] = useState("pt-BR")
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [consent, setConsent] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  // Voice search/filter state
  const [voiceSearch, setVoiceSearch] = useState("")
  const [languageFilter, setLanguageFilter] = useState("all")
  const [visibleCount, setVisibleCount] = useState(VOICES_PER_PAGE)
  const providers = providersData?.providers ?? []
  const allVoices = voicesData?.voices ?? []
  const providerVoices = allVoices.filter((v) => v.provider === selectedProvider)

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
    return result
  }, [providerVoices, languageFilter, voiceSearch])

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

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > MAX_FILE_SIZE) {
      setUploadError("Arquivo muito grande. Máximo: 5 MB.")
      setAudioFile(null)
      return
    }
    setUploadError(null)
    setAudioFile(file)
  }

  async function handleUpload() {
    setUploadError(null)
    setUploadSuccess(false)

    if (!audioFile) {
      setUploadError("Selecione um arquivo de áudio.")
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
        audioFile,
      })
      setUploadSuccess(true)
      setNewName("")
      setAudioFile(null)
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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-(--text-primary)">Gerenciamento de Vozes</h1>
        <p className="mt-1 text-sm text-(--text-secondary)">
          Gerencie vozes TTS clonadas para uso em cadências com voice notes.
        </p>
      </div>

      {/* Provider tabs */}
      <div className="flex gap-2">
        {(providers.length > 0 ? providers : ["speechify"]).map((p) => (
          <button
            key={p}
            onClick={() => setSelectedProvider(p)}
            className={cn(
              "rounded-md border px-4 py-2 text-sm font-medium transition-colors",
              selectedProvider === p
                ? "border-(--accent) bg-(--accent-subtle) text-(--accent-subtle-fg)"
                : "border-(--border-default) bg-(--bg-surface) text-(--text-secondary) hover:bg-(--bg-overlay)",
            )}
          >
            {p === "speechify" ? "Speechify" : p === "voicebox" ? "Voicebox" : p}
          </button>
        ))}
      </div>

      {/* Vozes existentes */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-(--text-primary)">
          Vozes disponíveis — {selectedProvider === "speechify" ? "Speechify" : "Voicebox"}
        </h2>

        {loadingVoices ? (
          <div className="flex items-center gap-2 text-sm text-(--text-tertiary)">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando vozes…
          </div>
        ) : providerVoices.length === 0 ? (
          <p className="text-sm text-(--text-disabled)">Nenhuma voz encontrada.</p>
        ) : (
          <div className="space-y-3">
            {/* Search + Language filter */}
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

            {/* Counter */}
            <p className="text-xs text-(--text-tertiary)">
              {filteredVoices.length === providerVoices.length
                ? `${providerVoices.length} vozes`
                : `${filteredVoices.length} de ${providerVoices.length} vozes`}
            </p>

            {/* Voice list */}
            {filteredVoices.length === 0 ? (
              <p className="text-sm text-(--text-disabled)">Nenhuma voz corresponde à busca.</p>
            ) : (
              <>
                <div className="grid gap-2">
                  {visibleVoices.map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center justify-between rounded-md border border-(--border-default) bg-(--bg-surface) px-4 py-2.5"
                    >
                      <div className="flex items-center gap-3 overflow-hidden">
                        <Volume2 className="h-4 w-4 shrink-0 text-(--text-tertiary)" />
                        <div className="min-w-0">
                          <span className="text-sm font-medium text-(--text-primary) truncate block">
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
                          className="h-7 px-2"
                        >
                          <Play className="h-3.5 w-3.5" />
                        </Button>
                        {v.is_cloned && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(v.provider, v.id)}
                            disabled={deleteVoice.isPending}
                            className="h-7 px-2 text-(--danger-fg) hover:text-(--danger-fg)"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {hasMore && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setVisibleCount((c) => c + VOICES_PER_PAGE)}
                    className="w-full"
                  >
                    Carregar mais ({filteredVoices.length - visibleCount} restantes)
                  </Button>
                )}
              </>
            )}
          </div>
        )}
      </section>

      {/* Upload de nova voz */}
      <section className="space-y-4 rounded-md border border-(--border-default) bg-(--bg-overlay) p-4">
        <div className="flex items-center gap-2">
          <Upload className="h-4 w-4 text-(--text-tertiary)" />
          <h2 className="text-sm font-semibold text-(--text-primary)">Clonar nova voz</h2>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="mb-1 block text-xs">Nome da voz</Label>
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Ex: Minha voz"
              className="h-8 text-xs"
            />
          </div>
          <div>
            <Label className="mb-1 block text-xs">Idioma</Label>
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

        <div>
          <Label htmlFor="voice-audio-upload" className="mb-1 block text-xs">
            Áudio de referência (10-30s, MP3/WAV, até 5MB)
          </Label>
          <input
            id="voice-audio-upload"
            type="file"
            accept="audio/*"
            onChange={handleFileChange}
            title="Selecione um arquivo de áudio para clonagem de voz"
            className="block w-full text-xs text-(--text-secondary) file:mr-2 file:rounded file:border-0 file:bg-(--bg-surface) file:px-3 file:py-1.5 file:text-xs file:font-medium"
          />
        </div>

        {selectedProvider === "speechify" && (
          <label className="flex items-center gap-2 text-xs text-(--text-secondary)">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="rounded border-(--border-default)"
            />
            Consinto com a clonagem de voz pela Speechify API
          </label>
        )}

        {uploadError && (
          <div className="flex items-center gap-2 text-xs text-(--danger-fg)">
            <AlertCircle className="h-3.5 w-3.5" />
            {uploadError}
          </div>
        )}

        {uploadSuccess && (
          <div className="flex items-center gap-2 text-xs text-(--success-fg)">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Voz criada com sucesso!
          </div>
        )}

        <Button
          onClick={handleUpload}
          disabled={createVoice.isPending || !audioFile || !newName.trim()}
          size="sm"
        >
          {createVoice.isPending ? (
            <>
              <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              Enviando…
            </>
          ) : (
            <>
              <Upload className="mr-1 h-3.5 w-3.5" />
              Criar voz
            </>
          )}
        </Button>
      </section>

      {/* Hidden audio player */}
      <audio ref={audioRef} className="hidden" />
    </div>
  )
}
