"use client"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { useSendVoiceMessage, type SuggestTone } from "@/lib/api/hooks/use-inbox"
import {
  Send,
  Sparkles,
  Mic,
  Square,
  Loader2,
  ChevronDown,
  Trash2,
  Upload,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onSuggest: (tone: SuggestTone) => void
  isSending: boolean
  isSuggesting: boolean
  chatId: string
}

const TONES: { value: SuggestTone; label: string }[] = [
  { value: "formal", label: "Formal" },
  { value: "casual", label: "Casual" },
  { value: "objetiva", label: "Objetiva" },
  { value: "consultiva", label: "Consultiva" },
]

type RecordingState = "idle" | "recording" | "preview"

export function ChatInput({
  value,
  onChange,
  onSend,
  onSuggest,
  isSending,
  isSuggesting,
  chatId,
}: ChatInputProps) {
  const [showTones, setShowTones] = useState(false)

  // Audio recording state
  const [recordingState, setRecordingState] = useState<RecordingState>("idle")
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [recordingTime, setRecordingTime] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const sendVoice = useSendVoiceMessage()

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  // ── Audio recording ─────────────────────────────────────────────────

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        setAudioBlob(blob)
        setAudioUrl(URL.createObjectURL(blob))
        setRecordingState("preview")
        stream.getTracks().forEach((t) => t.stop())
      }

      mediaRecorder.start()
      setRecordingState("recording")
      setRecordingTime(0)
      timerRef.current = setInterval(() => {
        setRecordingTime((t) => {
          if (t >= 59) {
            stopRecording()
            return 60
          }
          return t + 1
        })
      }, 1000)
    } catch {
      // Mic permission denied — silently ignore
    }
  }

  function stopRecording() {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    mediaRecorderRef.current?.stop()
  }

  function discardRecording() {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    setAudioBlob(null)
    setAudioUrl(null)
    setRecordingState("idle")
    setRecordingTime(0)
  }

  async function sendRecording() {
    if (!audioBlob) return
    await sendVoice.mutateAsync({ chatId, audioBlob })
    discardRecording()
  }

  const formatSeconds = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <div className="border-t border-(--border-default) bg-(--bg-surface) p-3">
      {/* Audio recording overlay */}
      {recordingState !== "idle" && (
        <div className="mb-2 flex items-center gap-2 rounded-md border border-(--border-default) bg-(--bg-overlay) px-3 py-2">
          {recordingState === "recording" && (
            <>
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
              <span className="text-xs font-medium text-(--text-primary)">
                Gravando {formatSeconds(recordingTime)}
              </span>
              <span className="flex-1" />
              <button
                type="button"
                onClick={stopRecording}
                className="flex items-center gap-1 rounded-md bg-red-500 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-red-600"
              >
                <Square size={10} aria-hidden="true" />
                Parar
              </button>
            </>
          )}

          {recordingState === "preview" && audioUrl && (
            <>
              <audio src={audioUrl} controls className="h-8 flex-1" preload="metadata" />
              <button
                type="button"
                onClick={discardRecording}
                aria-label="Descartar gravação"
                className="rounded-md p-1.5 text-(--text-tertiary) transition-colors hover:bg-(--bg-surface) hover:text-(--danger)"
              >
                <Trash2 size={14} aria-hidden="true" />
              </button>
              <Button
                size="sm"
                onClick={sendRecording}
                disabled={sendVoice.isPending}
              >
                {sendVoice.isPending ? (
                  <Loader2 size={14} className="mr-1 animate-spin" />
                ) : (
                  <Upload size={14} className="mr-1" aria-hidden="true" />
                )}
                Enviar áudio
              </Button>
            </>
          )}
        </div>
      )}

      {/* Text input + actions */}
      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          placeholder="Digite sua mensagem…"
          className="min-h-10 resize-none"
        />

        <div className="flex shrink-0 gap-1">
          {/* AI suggest button */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowTones((v) => !v)}
              disabled={isSuggesting}
              aria-label="Sugestão de resposta IA"
              className={cn(
                "flex h-9 items-center gap-1 rounded-md border border-(--border-default) px-2.5 text-xs font-medium transition-colors",
                isSuggesting
                  ? "text-(--text-disabled)"
                  : "text-(--accent) hover:bg-(--accent-subtle)",
              )}
            >
              {isSuggesting ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Sparkles size={14} aria-hidden="true" />
              )}
              <ChevronDown size={10} aria-hidden="true" />
            </button>

            {showTones && (
              <div className="absolute bottom-full right-0 z-10 mb-1 w-36 rounded-md border border-(--border-default) bg-(--bg-surface) py-1 shadow-lg">
                {TONES.map((tone) => (
                  <button
                    key={tone.value}
                    type="button"
                    onClick={() => {
                      setShowTones(false)
                      onSuggest(tone.value)
                    }}
                    className="flex w-full px-3 py-1.5 text-left text-xs text-(--text-primary) transition-colors hover:bg-(--bg-overlay)"
                  >
                    {tone.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mic button */}
          <button
            type="button"
            onClick={recordingState === "idle" ? startRecording : undefined}
            disabled={recordingState !== "idle"}
            aria-label="Gravar áudio"
            className="flex h-9 w-9 items-center justify-center rounded-md border border-(--border-default) text-(--text-secondary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-primary) disabled:opacity-40"
          >
            <Mic size={14} aria-hidden="true" />
          </button>

          {/* Send */}
          <Button
            onClick={onSend}
            disabled={isSending || !value.trim()}
            className="h-9"
          >
            {isSending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
