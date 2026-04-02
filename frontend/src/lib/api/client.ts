import createClient, { type Middleware } from "openapi-fetch"
import { auth } from "@/lib/auth/config"
import { env } from "@/env"
import type { paths } from "./schema"

// Guarda para evitar múltiplos signOut simultâneos quando várias requests retornam 401
let _signingOut = false

// ── Client para Server Components (lê a sessão do servidor) ──────────

export async function createServerClient() {
  const session = await auth()
  const accessToken = session?.accessToken

  const client = createClient<paths>({
    baseUrl: env.API_URL,
  })

  if (accessToken) {
    const authMiddleware: Middleware = {
      onRequest({ request }) {
        request.headers.set("Authorization", `Bearer ${accessToken}`)
        return request
      },
    }
    client.use(authMiddleware)
  }

  return client
}

// ── Factory para Client Components (recebe token explicitamente) ─────

export function createBrowserClient(accessToken?: string) {
  const client = createClient<paths>({
    baseUrl: env.NEXT_PUBLIC_API_URL,
  })

  if (accessToken) {
    const authMiddleware: Middleware = {
      onRequest({ request }) {
        request.headers.set("Authorization", `Bearer ${accessToken}`)
        return request
      },
      onResponse({ response }) {
        // Token expirado → faz signOut (limpa cookie) e redireciona para login
        if (response.status === 401 && typeof window !== "undefined" && !_signingOut) {
          _signingOut = true
          void import("next-auth/react").then(({ signOut }) => {
            void signOut({ callbackUrl: "/login?error=session_expired" })
          })
        }
        return response
      },
    }
    client.use(authMiddleware)
  }

  return client
}

// ── Cliente tipado estático para uso em hooks (token injetado via middleware) ──

export const apiClient = createClient<paths>({
  baseUrl:
    typeof window === "undefined"
      ? (process.env["API_URL"] ?? "http://localhost:8000")
      : (process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000"),
})
