import { auth } from "@/lib/auth/config"
import { redirect } from "next/navigation"
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button"
import { resolveAuthErrorState } from "@/lib/auth/auth-error-state"

interface Props {
  searchParams: Promise<{ error?: string; message?: string }>
}

export default async function LoginPage({ searchParams }: Props) {
  const session = await auth()
  const { error, message } = await searchParams

  // Se a sessão existe mas o erro é session_expired, não redirecionar
  // (o token do backend expirou — o NextAuth pode ainda ter a sessão em cache)
  if (session && error !== "session_expired") redirect("/dashboard")

  const errorState = error ? resolveAuthErrorState(error, message) : null

  return (
    <main className="flex min-h-screen items-center justify-center bg-(--bg-page) px-4">
      <div className="w-full max-w-sm rounded-lg border border-(--border-default) bg-(--bg-surface) p-8 shadow-(--shadow-md)">
        {/* Logo / Título */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-(--text-primary)">Prospector</h1>
          <p className="mt-1 text-sm text-(--text-secondary)">Sistema de prospecção B2B</p>
        </div>

        {/* Mensagem de erro */}
        {errorState && (
          <div
            role="alert"
            className="mb-6 rounded-md bg-(--danger-subtle) px-4 py-3 text-sm text-(--danger-subtle-fg)"
          >
            {errorState.banner}
          </div>
        )}

        {/* Botão Google */}
        <GoogleSignInButton />

        <p className="mt-6 text-center text-xs text-(--text-tertiary)">
          Acesso restrito à equipe Composto Web
        </p>
      </div>
    </main>
  )
}
