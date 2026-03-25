"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { env } from "@/env"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface AudioFile {
  id: string
  tenant_id: string
  name: string
  s3_key: string
  url: string
  content_type: string
  size_bytes: number
  duration_seconds: number | null
  language: string
  created_at: string | null
  updated_at: string | null
}

interface AudioFileListResponse {
  items: AudioFile[]
  total: number
}

// ── Hooks de Query ────────────────────────────────────────────────────

/** Lista todos os áudios pré-gravados do tenant */
export function useAudioFiles() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["audio-files"],
    queryFn: async (): Promise<AudioFileListResponse> => {
      const res = await fetch(`${env.NEXT_PUBLIC_API_URL}/audio-files`, {
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      })
      if (!res.ok) throw new Error("Falha ao carregar áudios")
      return res.json()
    },
    staleTime: 30_000,
    enabled: !!session?.accessToken,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

/** Upload de um novo arquivo de áudio */
export function useUploadAudioFile() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      file,
      name,
      language,
    }: {
      file: File
      name: string
      language: string
    }): Promise<AudioFile> => {
      const form = new FormData()
      form.append("file", file)
      form.append("name", name)
      form.append("language", language)

      const res = await fetch(`${env.NEXT_PUBLIC_API_URL}/audio-files`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.accessToken}` },
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro ao enviar áudio" }))
        throw new Error(err.detail ?? "Erro ao enviar áudio")
      }
      const data = await res.json()
      return data.audio_file
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audio-files"] })
    },
  })
}

/** Deleta um arquivo de áudio */
export function useDeleteAudioFile() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (audioFileId: string): Promise<void> => {
      const res = await fetch(`${env.NEXT_PUBLIC_API_URL}/audio-files/${audioFileId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      })
      if (!res.ok) throw new Error("Falha ao deletar áudio")
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audio-files"] })
    },
  })
}
