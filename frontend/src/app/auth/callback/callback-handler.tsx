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

interface Props {
  token?: string | undefined
}

export function CallbackHandler({ token }: Props) {
  const router = useRouter()
  const called = useRef(false)

  useEffect(() => {
    // Guard contra double-invoke (React StrictMode monta duas vezes em dev)
    if (called.current) return
    called.current = true

    if (!token) {
      router.replace("/login?error=no_token")
      return
    }

    signIn("backend-google", {
      access_token: token,
      redirect: false,
    }).then((result) => {
      if (!result || result.error) {
        router.replace("/login?error=auth_failed")
      } else {
        // Força reload completo para hidratar a sessão no Server Component (layout)
        window.location.href = "/dashboard"
      }
    }).catch(() => {
      router.replace("/login?error=auth_failed")
    })
  }, [token, router])

  return (
    <div className="flex min-h-screen items-center justify-center bg-(--bg-page)">
      <p className="text-sm text-(--text-secondary)">Autenticando…</p>
    </div>
  )
}
