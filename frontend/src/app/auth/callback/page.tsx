/**
 * app/auth/callback/page.tsx
 *
 * Server Component que extrai o grant curto da URL (Next.js 15: searchParams é uma Promise)
 * e delega ao CallbackHandler (Client Component), que troca o grant por JWT no backend
 * antes de chamar signIn() do lado cliente.
 *
 * Por que Client Component?
 * No NextAuth v5 beta, signIn() server-side em Route Handlers não define o cookie de
 * sessão corretamente. Usar next-auth/react no cliente é o caminho confiável.
 */

import { Suspense } from "react"
import { CallbackHandler } from "./callback-handler"

interface Props {
  searchParams: Promise<{ grant_code?: string }>
}

export default async function CallbackPage({ searchParams }: Props) {
  const { grant_code: grantCode } = await searchParams

  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-(--bg-page)">
          <p className="text-sm text-(--text-secondary)">Autenticando…</p>
        </div>
      }
    >
      <CallbackHandler grantCode={grantCode} />
    </Suspense>
  )
}
