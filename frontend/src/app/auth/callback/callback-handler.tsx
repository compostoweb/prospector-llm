"use client"

/**
 * CallbackHandler — Client Component
 *
 * Recebe o JWT do backend (via prop vinda do Server Component) e chama
 * signIn() do next-auth/react. Esta é a abordagem correta para NextAuth v5:
 * o signIn() server-side tem limitações em Route Handlers na versão beta.
 */

import { useEffect, useRef } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import { env } from "@/env"

interface Props {
  grantCode?: string | undefined
}

export function CallbackHandler({ grantCode }: Props) {
  const router = useRouter()
  const called = useRef(false)

  useEffect(() => {
    // Guard contra double-invoke (React StrictMode monta duas vezes em dev)
    if (called.current) return
    called.current = true

    if (!grantCode) {
      router.replace("/auth/error?error=no_grant")
      return
    }

    fetch(`${env.API_URL}/auth/session/exchange`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ grant_code: grantCode }),
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("grant_exchange_failed")
        }

        const payload = (await response.json()) as { access_token?: string }
        if (!payload.access_token) {
          throw new Error("missing_access_token")
        }

        return signIn("backend-google", {
          access_token: payload.access_token,
          redirect: false,
        })
      })
      .then((result) => {
        if (!result || result.error) {
          router.replace("/auth/error?error=auth_failed")
        } else {
          // Força reload completo para hidratar a sessão no Server Component (layout)
          window.location.href = "/dashboard"
        }
      })
      .catch(() => {
        router.replace("/auth/error?error=auth_failed")
      })
  }, [grantCode, router])

  return (
    <div className="flex min-h-screen items-center justify-center bg-(--bg-page)">
      <p className="text-sm text-(--text-secondary)">Autenticando…</p>
    </div>
  )
}
