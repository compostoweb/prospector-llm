import { env } from "@/env"
import type { CalculatorConfig, LandingPagePublicData } from "@/lib/content-inbound/types"

async function parseResponse<T>(response: Response): Promise<T | null> {
  if (response.status === 404) {
    return null
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : "Falha ao buscar dados públicos do Content Hub"
    throw new Error(detail)
  }

  return payload as T
}

export async function getPublicLandingPage(slug: string): Promise<LandingPagePublicData | null> {
  const response = await fetch(`${env.API_URL}/api/content/landing-pages/public/${slug}`, {
    cache: "no-store",
  })
  return parseResponse<LandingPagePublicData>(response)
}

export async function getCalculatorConfig(): Promise<CalculatorConfig> {
  const response = await fetch(`${env.API_URL}/api/content/calculator/config`, {
    cache: "no-store",
  })

  const payload = await parseResponse<CalculatorConfig>(response)
  if (!payload) {
    throw new Error("Configuração da calculadora não encontrada")
  }
  return payload
}
