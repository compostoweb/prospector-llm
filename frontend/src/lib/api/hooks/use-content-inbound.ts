"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSession } from "next-auth/react"
import { env } from "@/env"
import type {
  ContentLandingPage,
  ContentLandingPageUpsertInput,
  ContentLeadMagnet,
  ContentLeadMagnetCreateInput,
  ContentLeadMagnetUpdateInput,
  ContentLMLead,
  LeadMagnetMetrics,
  LeadMagnetPostLinkInput,
  LeadMagnetStatus,
  SendPulseRetryResult,
} from "@/lib/content-inbound/types"

function buildAuthHeaders(accessToken?: string, includeJson = false): HeadersInit {
  const headers: HeadersInit = {}
  if (includeJson) {
    headers["Content-Type"] = "application/json"
  }
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }
  return headers
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : "Falha ao processar requisição do Content Hub"
    throw new Error(detail)
  }

  return payload as T
}

export const contentInboundKeys = {
  all: ["content", "inbound"] as const,
  leadMagnets: () => [...contentInboundKeys.all, "lead-magnets"] as const,
  landingPage: (leadMagnetId: string | null) =>
    [...contentInboundKeys.all, "landing-page", leadMagnetId] as const,
  metrics: (leadMagnetId: string | null) =>
    [...contentInboundKeys.all, "metrics", leadMagnetId] as const,
  leads: (leadMagnetId: string | null) =>
    [...contentInboundKeys.all, "leads", leadMagnetId] as const,
}

export function useContentLeadMagnets() {
  const { data: session } = useSession()

  return useQuery({
    queryKey: contentInboundKeys.leadMagnets(),
    queryFn: async () => {
      const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets`, {
        headers: buildAuthHeaders(session?.accessToken),
      })
      return parseApiResponse<ContentLeadMagnet[]>(response)
    },
    enabled: !!session?.accessToken,
  })
}

export function useCreateContentLeadMagnet() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: ContentLeadMagnetCreateInput) => {
      const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets`, {
        method: "POST",
        headers: buildAuthHeaders(session?.accessToken, true),
        body: JSON.stringify(body),
      })
      return parseApiResponse<ContentLeadMagnet>(response)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leadMagnets() })
    },
  })
}

export function useUpdateContentLeadMagnet() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      leadMagnetId,
      body,
    }: {
      leadMagnetId: string
      body: ContentLeadMagnetUpdateInput
    }) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}`,
        {
          method: "PUT",
          headers: buildAuthHeaders(session?.accessToken, true),
          body: JSON.stringify(body),
        },
      )
      return parseApiResponse<ContentLeadMagnet>(response)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leadMagnets() })
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.metrics(variables.leadMagnetId),
      })
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.landingPage(variables.leadMagnetId),
      })
    },
  })
}

export function useDeleteLeadMagnet() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (leadMagnetId: string) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}`,
        {
          method: "DELETE",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { detail?: string }
        throw new Error(data.detail ?? "Erro ao excluir lead magnet")
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leadMagnets() })
    },
  })
}

export function useUpdateLeadMagnetStatus() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      leadMagnetId,
      status,
    }: {
      leadMagnetId: string
      status: LeadMagnetStatus
    }) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/status`,
        {
          method: "PATCH",
          headers: buildAuthHeaders(session?.accessToken, true),
          body: JSON.stringify({ status }),
        },
      )
      return parseApiResponse<ContentLeadMagnet>(response)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leadMagnets() })
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.metrics(variables.leadMagnetId),
      })
    },
  })
}

export function useLeadMagnetMetrics(leadMagnetId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: contentInboundKeys.metrics(leadMagnetId),
    queryFn: async () => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/metrics`,
        {
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<LeadMagnetMetrics>(response)
    },
    enabled: !!session?.accessToken && !!leadMagnetId,
  })
}

export function useLeadMagnetLeads(leadMagnetId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: contentInboundKeys.leads(leadMagnetId),
    queryFn: async () => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/leads`,
        {
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<ContentLMLead[]>(response)
    },
    enabled: !!session?.accessToken && !!leadMagnetId,
  })
}

export function useConvertLeadMagnetLead() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ leadMagnetId, lmLeadId }: { leadMagnetId: string; lmLeadId: string }) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/leads/${lmLeadId}/convert`,
        {
          method: "PATCH",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<{ lm_lead_id: string; lead_id: string }>(response)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leads(variables.leadMagnetId) })
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.metrics(variables.leadMagnetId),
      })
    },
  })
}

export function useRetryLeadMagnetLeadSendPulse() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ leadMagnetId, lmLeadId }: { leadMagnetId: string; lmLeadId: string }) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/leads/${lmLeadId}/retry-sendpulse`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<ContentLMLead>(response)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leads(variables.leadMagnetId) })
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.metrics(variables.leadMagnetId),
      })
    },
  })
}

export function useRetryFailedLeadMagnetSendPulse() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (leadMagnetId: string) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/sendpulse/retry-failed`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<SendPulseRetryResult>(response)
    },
    onSuccess: (_, leadMagnetId) => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leads(leadMagnetId) })
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.metrics(leadMagnetId) })
    },
  })
}

export function useLandingPage(leadMagnetId: string | null) {
  const { data: session } = useSession()

  return useQuery({
    queryKey: contentInboundKeys.landingPage(leadMagnetId),
    queryFn: async () => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/landing-pages/${leadMagnetId}`,
        {
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      if (response.status === 404) {
        return null
      }
      return parseApiResponse<ContentLandingPage>(response)
    },
    enabled: !!session?.accessToken && !!leadMagnetId,
  })
}

export function useUpsertLandingPage() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      leadMagnetId,
      body,
    }: {
      leadMagnetId: string
      body: ContentLandingPageUpsertInput
    }) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/landing-pages/${leadMagnetId}`,
        {
          method: "PUT",
          headers: buildAuthHeaders(session?.accessToken, true),
          body: JSON.stringify(body),
        },
      )
      return parseApiResponse<ContentLandingPage>(response)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.landingPage(variables.leadMagnetId),
      })
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.metrics(variables.leadMagnetId),
      })
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leadMagnets() })
    },
  })
}

export function useLinkLeadMagnetPost() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      leadMagnetId,
      body,
    }: {
      leadMagnetId: string
      body: LeadMagnetPostLinkInput
    }) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/posts`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken, true),
          body: JSON.stringify(body),
        },
      )
      return parseApiResponse<{ id: string }>(response)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: contentInboundKeys.metrics(variables.leadMagnetId),
      })
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leadMagnets() })
    },
  })
}

// ---------------------------------------------------------------------------
// SendPulse integration test hooks
// ---------------------------------------------------------------------------

export interface SendPulseConnectionResult {
  status: "ok" | "error"
  message: string
  lists: Array<{ id: string | number; name: string; all_email_qty: number }> | null
}

export function useTestSendPulseConnection() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async () => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/sendpulse/test-connection`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<SendPulseConnectionResult>(response)
    },
  })
}

export interface TestWebhookInput {
  event_type: "subscribe" | "open" | "click" | "unsubscribe" | "sequence_completed"
  email: string
  list_id?: string
  link_url?: string
}

export interface TestWebhookResult {
  status: "ok" | "ignored"
  lm_lead_updated: boolean
  event_stored: boolean
  event_id: string | null
  message: string
}

export function useTestSendPulseWebhook() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async (body: TestWebhookInput) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/sendpulse/test-webhook`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken, true),
          body: JSON.stringify(body),
        },
      )
      return parseApiResponse<TestWebhookResult>(response)
    },
  })
}

export interface ExampleLeadMagnetResult extends ContentLeadMagnet {
  landing_page: ContentLandingPage
  public_url: string
}

export function useCreateExampleLeadMagnet() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/create-example`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<ExampleLeadMagnetResult>(response)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contentInboundKeys.leadMagnets() })
    },
  })
}

export function useUploadLeadMagnetPdf() {
  const { data: session } = useSession()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ leadMagnetId, file }: { leadMagnetId: string; file: File }) => {
      const formData = new FormData()
      formData.append("file", file)
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/upload-pdf`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken),
          body: formData,
        },
      )
      return parseApiResponse<ContentLeadMagnet>(response)
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(
        contentInboundKeys.leadMagnets(),
        (old: ContentLeadMagnet[] | undefined) =>
          old?.map((lm) => (lm.id === updated.id ? updated : lm)) ?? [updated],
      )
    },
  })
}

export function useUploadLandingPageImage() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async ({
      leadMagnetId,
      file,
      imageField,
    }: {
      leadMagnetId: string
      file: File
      imageField: "hero" | "author"
    }) => {
      const formData = new FormData()
      formData.append("file", file)
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/landing-pages/${leadMagnetId}/upload-lp-image?image_field=${imageField}`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken),
          body: formData,
        },
      )
      return parseApiResponse<{ url: string }>(response)
    },
  })
}

export function useImproveLandingPageField() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async (body: {
      field:
        | "title"
        | "subtitle"
        | "benefits"
        | "meta_title"
        | "meta_description"
        | "features"
        | "expected_result"
        | "badge_text"
        | "email_subject"
        | "email_headline"
        | "email_body_text"
        | "email_cta_label"
      current_value: string
      lead_magnet_title: string
      lead_magnet_type: string
      context?: string
    }) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/landing-pages/ai/improve-field`,
        {
          method: "POST",
          headers: buildAuthHeaders(session?.accessToken, true),
          body: JSON.stringify(body),
        },
      )
      return parseApiResponse<{ improved: string }>(response)
    },
  })
}

export function useLeadMagnetPdfPreviewUrl() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async (leadMagnetId: string) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/pdf-preview-url`,
        {
          method: "GET",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<{ url: string }>(response)
    },
  })
}

export function useLeadMagnetEmailPreview() {
  const { data: session } = useSession()

  return useMutation({
    mutationFn: async (leadMagnetId: string) => {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_URL}/api/content/lead-magnets/${leadMagnetId}/email-preview`,
        {
          method: "GET",
          headers: buildAuthHeaders(session?.accessToken),
        },
      )
      return parseApiResponse<{ html: string; subject: string }>(response)
    },
  })
}
