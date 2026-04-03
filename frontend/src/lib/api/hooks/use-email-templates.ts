"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { createBrowserClient } from "@/lib/api/client"

// ── Tipos ─────────────────────────────────────────────────────────────

export interface EmailTemplate {
  id: string
  tenant_id: string
  name: string
  description: string | null
  category: string | null
  subject: string
  body_html: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateEmailTemplateBody {
  name: string
  description?: string | null
  category?: string | null
  subject: string
  body_html: string
}

export interface UpdateEmailTemplateBody {
  name?: string
  description?: string | null
  category?: string | null
  subject?: string
  body_html?: string
  is_active?: boolean
}

// ── Hooks de query ────────────────────────────────────────────────────

export function useEmailTemplates(category?: string, activeOnly?: boolean) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-templates", category, activeOnly],
    queryFn: async (): Promise<EmailTemplate[]> => {
      const client = createBrowserClient(session?.accessToken)
      const params = new URLSearchParams()
      if (category) params.set("category", category)
      if (activeOnly) params.set("active_only", "true")
      const url = `/email-templates${params.toString() ? `?${params.toString()}` : ""}`
      const { data, error } = await client.GET(url as never)
      if (error) throw new Error("Falha ao carregar templates de e-mail")
      return (data as EmailTemplate[]) ?? []
    },
    staleTime: 60 * 1000,
    enabled: !!session?.accessToken,
  })
}

export function useEmailTemplate(id: string) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: ["email-templates", id],
    queryFn: async (): Promise<EmailTemplate> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.GET(`/email-templates/${id}` as never)
      if (error) throw new Error("Falha ao carregar template")
      return data as EmailTemplate
    },
    enabled: !!session?.accessToken && !!id,
  })
}

// ── Mutations ─────────────────────────────────────────────────────────

export function useCreateEmailTemplate() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateEmailTemplateBody): Promise<EmailTemplate> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.POST("/email-templates" as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao criar template")
      return data as EmailTemplate
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["email-templates"] })
    },
  })
}

export function useUpdateEmailTemplate() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: UpdateEmailTemplateBody & { id: string }): Promise<EmailTemplate> => {
      const client = createBrowserClient(session?.accessToken)
      const { data, error } = await client.PATCH(`/email-templates/${id}` as never, {
        body: body as never,
      })
      if (error) throw new Error("Falha ao atualizar template")
      return data as EmailTemplate
    },
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: ["email-templates", vars.id] })
      void queryClient.invalidateQueries({ queryKey: ["email-templates"] })
    },
  })
}

export function useDeleteEmailTemplate() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const client = createBrowserClient(session?.accessToken)
      const { error } = await client.DELETE(`/email-templates/${id}` as never)
      if (error) throw new Error("Falha ao remover template")
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["email-templates"] })
    },
  })
}
