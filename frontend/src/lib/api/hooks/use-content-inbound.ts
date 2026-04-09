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
