/**
 * app/auth/callback/page.tsx
 *
 * Recebe o token JWT do backend após Google OAuth e cria a sessão NextAuth.
 * O backend redireciona para: /auth/callback?token=<JWT>
 *
 * Server Component — `signIn()` server-side funciona corretamente aqui
 * (NextAuth v5 define cookies no render cycle do Server Component).
 */

import { redirect } from "next/navigation"
import { signIn } from "@/lib/auth/config"
import { AuthError } from "next-auth"

interface Props {
  searchParams: Promise<{ token?: string }>
}

export default async function CallbackPage({ searchParams }: Props) {
  const { token } = await searchParams

  if (!token) {
    redirect("/login?error=no_token")
  }

  try {
    await signIn("backend-google", {
      access_token: token,
      redirectTo: "/dashboard",
    })
  } catch (error) {
    // AuthError = credenciais inválidas ou /auth/me falhou
    if (error instanceof AuthError) {
      redirect("/login?error=auth_failed")
    }
    // NEXT_REDIRECT (sucesso) deve ser re-lançado para o framework do Next.js
    throw error
  }

  // Linha não atingível (o signIn sempre redireciona ou lança)
  redirect("/login?error=auth_failed")
}
