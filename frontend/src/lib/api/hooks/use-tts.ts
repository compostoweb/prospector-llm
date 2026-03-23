"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface TTSVoice {
  id: string
  name: string
  language: string
  provider: string
  is_cloned: boolean
}

export interface TTSVoicesResponse {
  providers: string[]
  total: number
  voices: TTSVoice[]
}

// ── Hooks de Query ────────────────────────────────────────────────────

/** Lista providers TTS configurados no backend */
export function useTTSProviders() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["tts", "providers"],
    queryFn: async (): Promise<{ providers: string[] }> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET("/tts/providers" as never)
      if (error) throw new Error("Falha ao carregar providers TTS")
      return data as { providers: string[] }
    },
    staleTime: 60 * 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

/** Lista todas as vozes TTS (todos os providers) — staleTime 1h */
export function useTTSVoices(provider?: string) {
  const { data: session } = useSession()
  const url = provider ? `/tts/voices/${provider}` : "/tts/voices"

  return useQuery({
    queryKey: ["tts", "voices", provider ?? "all"],
    queryFn: async (): Promise<TTSVoicesResponse> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(url as never)
      if (error) throw new Error("Falha ao carregar vozes TTS")
      return data as TTSVoicesResponse
    },
    staleTime: 60 * 60 * 1000,
    enabled: !!session?.accessToken,
    select: (data) => ({
      ...data,
      byProvider: data.voices.reduce<Record<string, TTSVoice[]>>((acc, v) => {
        const arr = acc[v.provider] ?? []
        arr.push(v)
        acc[v.provider] = arr
        return acc
      }, {}),
    }),
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

/** Cria voice clone via upload de áudio */
export function useCreateVoice() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      provider,
      name,
      language,
      audioFile,
    }: {
      provider: string
      name: string
      language: string
      audioFile: File
    }): Promise<TTSVoice> => {
      const token = session?.accessToken
      const baseUrl = process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000"

      const formData = new FormData()
      formData.append("name", name)
      formData.append("language", language)
      formData.append("audio", audioFile)

      const resp = await fetch(`${baseUrl}/tts/voices/${provider}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!resp.ok) {
        const detail = await resp.text()
        throw new Error(detail || "Falha ao criar voz")
      }
      return resp.json() as Promise<TTSVoice>
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tts", "voices"] })
    },
  })
}

/** Deleta voz clonada */
export function useDeleteVoice() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ provider, voiceId }: { provider: string; voiceId: string }) => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/tts/voices/${provider}/${voiceId}` as never)
      if (error) throw new Error("Falha ao deletar voz")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tts", "voices"] })
    },
  })
}

/** Testa TTS — retorna áudio blob */
export function useTestTTS() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async ({
      provider,
      voice_id,
      text,
      language,
    }: {
      provider: string
      voice_id: string
      text?: string
      language?: string
    }): Promise<Blob> => {
      const token = session?.accessToken
      const baseUrl = process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000"

      const resp = await fetch(`${baseUrl}/tts/test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          provider,
          voice_id,
          text: text ?? "Olá! Isso é um teste de voz do Prospector.",
          language: language ?? "pt-BR",
        }),
      })
      if (!resp.ok) throw new Error("Falha ao testar TTS")
      return resp.blob()
    },
  })
}
