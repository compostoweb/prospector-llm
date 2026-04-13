"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import {
  useAudioFiles,
  useUploadAudioFile,
  useDeleteAudioFile,
} from "@/lib/api/hooks/use-audio-files"
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
  Music,
  Upload,
  Trash2,
  Play,
  Pause,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileAudio,
  Mic,
  Square,
  RotateCcw,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { SettingsPageShell, SettingsPanel } from "@/components/settings/settings-shell"

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const ACCEPTED_TYPES = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/webm"]

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—"
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export default function AudiosPage() {
  const { data: audioData, isLoading } = useAudioFiles()
  const uploadAudio = useUploadAudioFile()
  const deleteAudio = useDeleteAudioFile()

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playingId, setPlayingId] = useState<string | null>(null)

  // Upload file state
  const [name, setName] = useState("")
  const [language, setLanguage] = useState("pt-BR")
  const [file, setFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  // Recorder state
  const [activeTab, setActiveTab] = useState<"upload" | "record">("upload")
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const recorderAudioRef = useRef<HTMLAudioElement | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null)
  const [isPlayingPreview, setIsPlayingPreview] = useState(false)
  const [recordDuration, setRecordDuration] = useState(0)
  const [recorderError, setRecorderError] = useState<string | null>(null)
  const [recName, setRecName] = useState("")
  const [recLanguage, setRecLanguage] = useState("pt-BR")
  const [recUploadError, setRecUploadError] = useState<string | null>(null)
  const [recUploadSuccess, setRecUploadSuccess] = useState(false)

  const audioFiles = audioData?.items ?? []

  // ── Recording helpers ───────────────────────────────────────────────

  const startRecording = useCallback(async () => {
    setRecorderError(null)
    setRecordedBlob(null)
    if (recordedUrl) {
      URL.revokeObjectURL(recordedUrl)
      setRecordedUrl(null)
    }
    setRecordDuration(0)
    setRecUploadSuccess(false)
    setRecUploadError(null)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm"
      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        const url = URL.createObjectURL(blob)
        setRecordedBlob(blob)
        setRecordedUrl(url)
        // Stop all tracks to release mic
        stream.getTracks().forEach((t) => t.stop())
        if (timerRef.current) {
          clearInterval(timerRef.current)
          timerRef.current = null
        }
      }

      recorder.start(250) // collect chunks every 250ms
      setIsRecording(true)

      // Duration timer
      const start = Date.now()
      timerRef.current = setInterval(() => {
        setRecordDuration(Math.floor((Date.now() - start) / 1000))
      }, 500)
    } catch {
      setRecorderError(
        "Não foi possível acessar o microfone. Verifique as permissões do navegador.",
      )
    }
  }, [recordedUrl])

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  function discardRecording() {
    if (recordedUrl) URL.revokeObjectURL(recordedUrl)
    setRecordedBlob(null)
    setRecordedUrl(null)
    setRecordDuration(0)
    setIsPlayingPreview(false)
    if (recorderAudioRef.current) recorderAudioRef.current.pause()
  }

  function togglePreview() {
    if (!recorderAudioRef.current || !recordedUrl) return
    if (isPlayingPreview) {
      recorderAudioRef.current.pause()
      setIsPlayingPreview(false)
    } else {
      recorderAudioRef.current.src = recordedUrl
      recorderAudioRef.current.play()
      setIsPlayingPreview(true)
    }
  }

  function handlePreviewEnded() {
    setIsPlayingPreview(false)
  }

  async function handleSaveRecording() {
    setRecUploadError(null)
    setRecUploadSuccess(false)

    if (!recordedBlob) {
      setRecUploadError("Grave um áudio primeiro.")
      return
    }
    if (!recName.trim()) {
      setRecUploadError("Informe um nome para o áudio.")
      return
    }

    const ext = recordedBlob.type.includes("webm") ? "webm" : "ogg"
    const recordedFile = new File([recordedBlob], `gravacao.${ext}`, {
      type: recordedBlob.type,
    })

    try {
      await uploadAudio.mutateAsync({
        file: recordedFile,
        name: recName.trim(),
        language: recLanguage,
      })
      setRecUploadSuccess(true)
      setRecName("")
      discardRecording()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao salvar gravação"
      setRecUploadError(msg)
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recordedUrl) URL.revokeObjectURL(recordedUrl)
      if (timerRef.current) clearInterval(timerRef.current)
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop()
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0]
    if (!selected) return
    if (selected.size > MAX_FILE_SIZE) {
      setUploadError("Arquivo muito grande. Máximo: 10 MB.")
      setFile(null)
      return
    }
    if (!ACCEPTED_TYPES.includes(selected.type) && !selected.type.startsWith("audio/")) {
      setUploadError("Formato não suportado. Use MP3, WAV, OGG ou M4A.")
      setFile(null)
      return
    }
    setUploadError(null)
    setFile(selected)
  }

  async function handleUpload() {
    setUploadError(null)
    setUploadSuccess(false)

    if (!file) {
      setUploadError("Selecione um arquivo de áudio.")
      return
    }
    if (!name.trim()) {
      setUploadError("Informe um nome para o áudio.")
      return
    }

    try {
      await uploadAudio.mutateAsync({
        file,
        name: name.trim(),
        language,
      })
      setUploadSuccess(true)
      setName("")
      setFile(null)
      // Reset file input
      const input = document.getElementById("audio-file-upload") as HTMLInputElement
      if (input) input.value = ""
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao enviar áudio"
      setUploadError(msg)
    }
  }

  function handlePlay(audioUrl: string, id: string) {
    if (!audioRef.current) return

    if (playingId === id) {
      audioRef.current.pause()
      setPlayingId(null)
      return
    }

    audioRef.current.src = audioUrl
    audioRef.current.play()
    setPlayingId(id)
  }

  function handleAudioEnded() {
    setPlayingId(null)
  }

  async function handleDelete(id: string) {
    try {
      await deleteAudio.mutateAsync(id)
      if (playingId === id) {
        audioRef.current?.pause()
        setPlayingId(null)
      }
    } catch {
      // Hook already handles error
    }
  }

  return (
    <SettingsPageShell
      title="Biblioteca de Áudios"
      description="Envie ou grave voice notes e mantenha a biblioteca acessível sem empilhar seções desnecessariamente."
      width="wide"
    >
      <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="flex gap-1 rounded-md border border-(--border-default) bg-(--bg-surface) p-1">
            <button
              type="button"
              onClick={() => setActiveTab("upload")}
              className={cn(
                "flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors",
                activeTab === "upload"
                  ? "bg-(--accent-subtle) text-(--accent-subtle-fg)"
                  : "text-(--text-secondary) hover:text-(--text-primary)",
              )}
            >
              <Upload className="h-3.5 w-3.5" />
              Enviar arquivo
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("record")}
              className={cn(
                "flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors",
                activeTab === "record"
                  ? "bg-(--accent-subtle) text-(--accent-subtle-fg)"
                  : "text-(--text-secondary) hover:text-(--text-primary)",
              )}
            >
              <Mic className="h-3.5 w-3.5" />
              Gravar áudio
            </button>
          </div>

          {activeTab === "upload" ? (
            <SettingsPanel
              title="Enviar novo áudio"
              description="Faça upload de um arquivo pronto para reutilizar em cadências."
            >
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                  <div>
                    <Label className="mb-1 block text-xs">Nome do áudio</Label>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Ex: Apresentação comercial"
                      className="h-8 text-xs"
                    />
                  </div>
                  <div>
                    <Label className="mb-1 block text-xs">Idioma</Label>
                    <Select value={language} onValueChange={setLanguage}>
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
                  <Label htmlFor="audio-file-upload" className="mb-1 block text-xs">
                    Arquivo de áudio (MP3, WAV, OGG — até 10 MB)
                  </Label>
                  <input
                    id="audio-file-upload"
                    type="file"
                    accept="audio/*"
                    onChange={handleFileChange}
                    title="Selecione um arquivo de áudio"
                    className="block w-full text-xs text-(--text-secondary) file:mr-2 file:rounded file:border-0 file:bg-(--bg-surface) file:px-3 file:py-1.5 file:text-xs file:font-medium"
                  />
                </div>

                {uploadError ? (
                  <div className="flex items-center gap-2 text-xs text-(--danger-fg)">
                    <AlertCircle className="h-3.5 w-3.5" />
                    {uploadError}
                  </div>
                ) : null}

                {uploadSuccess ? (
                  <div className="flex items-center gap-2 text-xs text-(--success-fg)">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Áudio enviado com sucesso!
                  </div>
                ) : null}

                <Button
                  onClick={handleUpload}
                  disabled={uploadAudio.isPending || !file || !name.trim()}
                  size="sm"
                >
                  {uploadAudio.isPending ? (
                    <>
                      <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                      Enviando…
                    </>
                  ) : (
                    <>
                      <Upload className="mr-1 h-3.5 w-3.5" />
                      Enviar áudio
                    </>
                  )}
                </Button>
              </div>
            </SettingsPanel>
          ) : (
            <SettingsPanel
              title="Gravar áudio"
              description="Grave rapidamente uma voice note e já salve na biblioteca."
            >
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                  <div>
                    <Label className="mb-1 block text-xs">Nome do áudio</Label>
                    <Input
                      value={recName}
                      onChange={(e) => setRecName(e.target.value)}
                      placeholder="Ex: Apresentação comercial"
                      className="h-8 text-xs"
                    />
                  </div>
                  <div>
                    <Label className="mb-1 block text-xs">Idioma</Label>
                    <Select value={recLanguage} onValueChange={setRecLanguage}>
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

                <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-(--border-default) bg-(--bg-surface) py-6">
                  {!isRecording && !recordedBlob ? (
                    <>
                      <button
                        type="button"
                        onClick={startRecording}
                        className="flex h-14 w-14 items-center justify-center rounded-full bg-(--danger) text-white transition-transform hover:scale-105 active:scale-95"
                        title="Iniciar gravação"
                      >
                        <Mic className="h-6 w-6" />
                      </button>
                      <p className="text-xs text-(--text-tertiary)">
                        Clique para iniciar a gravação
                      </p>
                    </>
                  ) : null}

                  {isRecording ? (
                    <>
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-(--danger)" />
                        <span className="tabular-nums text-sm font-medium text-(--text-primary)">
                          {formatDuration(recordDuration)}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={stopRecording}
                        className="flex h-14 w-14 items-center justify-center rounded-full bg-(--border-default) text-(--text-primary) transition-transform hover:scale-105 active:scale-95"
                        title="Parar gravação"
                      >
                        <Square className="h-5 w-5" />
                      </button>
                      <p className="text-xs text-(--text-tertiary)">Gravando… Clique para parar.</p>
                    </>
                  ) : null}

                  {!isRecording && recordedBlob ? (
                    <>
                      <div className="flex items-center gap-2">
                        <span className="tabular-nums text-sm font-medium text-(--text-primary)">
                          {formatDuration(recordDuration)}
                        </span>
                        <span className="text-xs text-(--text-disabled)">
                          ({formatFileSize(recordedBlob.size)})
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={togglePreview}
                          className="gap-1"
                        >
                          {isPlayingPreview ? (
                            <>
                              <Pause className="h-3.5 w-3.5" />
                              Pausar
                            </>
                          ) : (
                            <>
                              <Play className="h-3.5 w-3.5" />
                              Ouvir prévia
                            </>
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={discardRecording}
                          className="gap-1 text-(--danger-fg) hover:text-(--danger-fg)"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          Descartar
                        </Button>
                      </div>
                    </>
                  ) : null}
                </div>

                {recorderError ? (
                  <div className="flex items-center gap-2 text-xs text-(--danger-fg)">
                    <AlertCircle className="h-3.5 w-3.5" />
                    {recorderError}
                  </div>
                ) : null}

                {recUploadError ? (
                  <div className="flex items-center gap-2 text-xs text-(--danger-fg)">
                    <AlertCircle className="h-3.5 w-3.5" />
                    {recUploadError}
                  </div>
                ) : null}

                {recUploadSuccess ? (
                  <div className="flex items-center gap-2 text-xs text-(--success-fg)">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Áudio gravado e salvo com sucesso!
                  </div>
                ) : null}

                <Button
                  onClick={handleSaveRecording}
                  disabled={uploadAudio.isPending || !recordedBlob || !recName.trim()}
                  size="sm"
                >
                  {uploadAudio.isPending ? (
                    <>
                      <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                      Salvando…
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                      Salvar gravação
                    </>
                  )}
                </Button>

                <audio ref={recorderAudioRef} onEnded={handlePreviewEnded} className="hidden" />
              </div>
            </SettingsPanel>
          )}

          <SettingsPanel
            title="Boas práticas"
            description="Arquivos curtos e nomes claros facilitam o uso em cadências."
          >
            <p className="text-sm leading-6 text-(--text-secondary)">
              Use nomes que indiquem intenção, idioma ou etapa da cadência. Isso reduz confusão ao
              escolher voice notes no momento do envio.
            </p>
          </SettingsPanel>
        </div>

        <SettingsPanel
          title={`Áudios enviados (${audioFiles.length})`}
          description="Biblioteca central para revisão, reprodução e remoção dos arquivos disponíveis."
        >
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-(--text-tertiary)">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando áudios…
            </div>
          ) : audioFiles.length === 0 ? (
            <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-(--border-default) py-8 text-center">
              <FileAudio className="h-8 w-8 text-(--text-disabled)" />
              <p className="text-sm text-(--text-disabled)">Nenhum áudio enviado ainda.</p>
              <p className="text-xs text-(--text-tertiary)">
                Envie ou grave o primeiro áudio usando o painel lateral.
              </p>
            </div>
          ) : (
            <div className="grid gap-2">
              {audioFiles.map((af) => (
                <div
                  key={af.id}
                  className="flex items-center justify-between rounded-xl border border-(--border-default) bg-(--bg-surface) px-4 py-3"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <Music className="h-4 w-4 shrink-0 text-(--accent)" />
                    <div className="min-w-0">
                      <span className="block truncate text-sm font-medium text-(--text-primary)">
                        {af.name}
                      </span>
                      <span className="text-[11px] text-(--text-disabled)">
                        {af.language} · {formatFileSize(af.size_bytes)} ·{" "}
                        {formatDuration(af.duration_seconds)}
                      </span>
                    </div>
                  </div>

                  <div className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handlePlay(af.url, af.id)}
                      className="h-7 px-2"
                      title={playingId === af.id ? "Pausar" : "Reproduzir"}
                    >
                      {playingId === af.id ? (
                        <Pause className="h-3.5 w-3.5" />
                      ) : (
                        <Play className="h-3.5 w-3.5" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(af.id)}
                      disabled={deleteAudio.isPending}
                      className="h-7 px-2 text-(--danger-fg) hover:text-(--danger-fg)"
                      title="Excluir áudio"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SettingsPanel>
      </div>

      <audio ref={audioRef} onEnded={handleAudioEnded} className="hidden" />
    </SettingsPageShell>
  )
}
