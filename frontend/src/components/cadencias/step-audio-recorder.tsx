"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { CheckCircle2, Loader2, Mic, RotateCcw, Square, Upload } from "lucide-react"
import { useUploadAudioFile, type AudioFile } from "@/lib/api/hooks/use-audio-files"

interface StepAudioRecorderProps {
  defaultName: string
  onUploaded: (audioFile: AudioFile) => void
}

const LANGUAGE_OPTIONS = [
  { value: "pt-BR", label: "Português (BR)" },
  { value: "en-US", label: "English (US)" },
  { value: "es-ES", label: "Español" },
] as const

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`
}

function buildRecordedFile(blob: Blob, name: string): File {
  const normalizedName =
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "audio-gravado"

  const extension = blob.type.includes("ogg") ? "ogg" : blob.type.includes("wav") ? "wav" : "webm"

  return new File([blob], `${normalizedName}.${extension}`, {
    type: blob.type || "audio/webm",
  })
}

export function StepAudioRecorder({ defaultName, onUploaded }: StepAudioRecorderProps) {
  const uploadAudioFile = useUploadAudioFile()
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [audioName, setAudioName] = useState(defaultName)
  const [language, setLanguage] = useState<(typeof LANGUAGE_OPTIONS)[number]["value"]>("pt-BR")
  const [isRecording, setIsRecording] = useState(false)
  const [recordDuration, setRecordDuration] = useState(0)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const clearRecording = useCallback(() => {
    if (recordedUrl) {
      URL.revokeObjectURL(recordedUrl)
    }
    setRecordedBlob(null)
    setRecordedUrl(null)
    setRecordDuration(0)
  }, [recordedUrl])

  useEffect(() => {
    setAudioName(defaultName)
  }, [defaultName])

  const startRecording = useCallback(async () => {
    setError(null)
    setSuccess(null)
    clearRecording()

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Seu navegador não suporta gravação de áudio.")
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const preferredMimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm"

      streamRef.current = stream
      chunksRef.current = []

      const recorder = new MediaRecorder(stream, { mimeType: preferredMimeType })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || preferredMimeType,
        })
        const url = URL.createObjectURL(blob)
        setRecordedBlob(blob)
        setRecordedUrl(url)
        stopTimer()
        stopStream()
      }

      recorder.start(250)
      setIsRecording(true)
      setRecordDuration(0)

      const startedAt = Date.now()
      timerRef.current = setInterval(() => {
        setRecordDuration(Math.floor((Date.now() - startedAt) / 1000))
      }, 250)
    } catch {
      stopTimer()
      stopStream()
      setError("Não foi possível acessar o microfone. Verifique as permissões do navegador.")
    }
  }, [clearRecording, stopStream, stopTimer])

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state === "inactive") {
      return
    }

    recorder.stop()
    setIsRecording(false)
    stopTimer()
  }, [stopTimer])

  const discardRecording = useCallback(() => {
    setError(null)
    setSuccess(null)
    clearRecording()
  }, [clearRecording])

  const handleUpload = useCallback(async () => {
    if (!recordedBlob) {
      setError("Grave um áudio antes de salvar.")
      return
    }

    if (!audioName.trim()) {
      setError("Informe um nome para o áudio.")
      return
    }

    setError(null)
    setSuccess(null)

    try {
      const audioFile = await uploadAudioFile.mutateAsync({
        file: buildRecordedFile(recordedBlob, audioName),
        name: audioName.trim(),
        language,
      })

      onUploaded(audioFile)
      setSuccess("Áudio salvo e selecionado neste passo.")
      clearRecording()
      setAudioName(defaultName)
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Erro ao salvar gravação.")
    }
  }, [audioName, clearRecording, defaultName, language, onUploaded, recordedBlob, uploadAudioFile])

  useEffect(() => {
    return () => {
      stopTimer()
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop()
      } else {
        stopStream()
      }
      if (recordedUrl) {
        URL.revokeObjectURL(recordedUrl)
      }
    }
  }, [recordedUrl, stopStream, stopTimer])

  return (
    <div className="space-y-3 rounded-xl border border-dashed border-gray-200 bg-gray-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-gray-700">Gravar agora</p>
          <p className="text-[11px] leading-relaxed text-gray-500">
            Grave dentro do passo, salve na biblioteca e associe o áudio automaticamente.
          </p>
        </div>

        {isRecording ? (
          <div className="flex items-center gap-2 rounded-full bg-rose-50 px-2.5 py-1 text-[11px] font-semibold text-rose-600">
            <span className="h-2 w-2 rounded-full bg-rose-500" />
            {formatDuration(recordDuration)}
          </div>
        ) : null}
      </div>

      {!recordedBlob ? (
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          className={`flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
            isRecording
              ? "bg-rose-600 text-white hover:bg-rose-700"
              : "border border-gray-200 bg-white text-gray-700 hover:border-blue-300 hover:text-blue-700"
          }`}
        >
          {isRecording ? <Square size={14} /> : <Mic size={14} />}
          {isRecording ? "Parar gravação" : "Começar gravação"}
        </button>
      ) : (
        <div className="space-y-3">
          <audio controls src={recordedUrl ?? undefined} className="w-full" />

          <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-gray-600">Nome do áudio</label>
              <input
                type="text"
                value={audioName}
                onChange={(event) => setAudioName(event.target.value)}
                placeholder="Ex: Abertura LinkedIn"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-gray-600">Idioma</label>
              <select
                value={language}
                onChange={(event) =>
                  setLanguage(event.target.value as (typeof LANGUAGE_OPTIONS)[number]["value"])
                }
                aria-label="Idioma do áudio gravado"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={discardRecording}
              className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 transition-colors hover:border-gray-300 hover:text-gray-700"
            >
              <RotateCcw size={13} />
              Descartar
            </button>

            <button
              type="button"
              onClick={handleUpload}
              disabled={uploadAudioFile.isPending}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-60"
            >
              {uploadAudioFile.isPending ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  Salvando…
                </>
              ) : (
                <>
                  <Upload size={13} />
                  Salvar na biblioteca
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {success ? (
        <p className="flex items-center gap-1.5 text-[11px] text-green-600">
          <CheckCircle2 size={12} />
          {success}
        </p>
      ) : null}

      {error ? <p className="text-[11px] text-rose-600">{error}</p> : null}
    </div>
  )
}
