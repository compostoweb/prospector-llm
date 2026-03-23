/**
 * app/auth/callback/page.tsx
 *
 * Server Component que extrai o token da URL (Next.js 15: searchParams é uma Promise)
 * e delega ao CallbackHandler (Client Component) que chama signIn() do lado cliente.
 *
 * Por que Client Component?
 * No NextAuth v5 beta, signIn() server-side em Route Handlers não define o cookie de
 * sessão corretamente. Usar next-auth/react no cliente é o caminho confiável.
 */

import { Suspense } from "react"
import { CallbackHandler } from "./callback-handler"

interface Props {
  searchParams: Promise<{ token?: string }>
}

export default async function CallbackPage({ searchParams }: Props) {
  const { token } = await searchParams

  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-(--bg-page)">
          <p className="text-sm text-(--text-secondary)">Autenticando…</p>
        </div>
      }
    >
      <CallbackHandler token={token} />
    </Suspense>
  )
}
