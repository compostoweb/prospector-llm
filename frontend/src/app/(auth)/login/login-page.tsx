import { auth } from "@/lib/auth/config"
import { redirect } from "next/navigation"
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button"

interface Props {
  searchParams: Promise<{ error?: string }>
}

const ERROR_MESSAGES: Record<string, string> = {
  auth_failed: "Falha na autenticação. Tente novamente.",
  session_expired: "Sessão expirada. Faça login novamente.",
  OAuthCallback: "Erro no callback OAuth. Tente novamente.",
  default: "Ocorreu um erro. Tente novamente.",
}

export default async function LoginPage({ searchParams }: Props) {
  const session = await auth()
  const { error } = await searchParams

  // Se a sessão existe mas o erro é session_expired, não redirecionar
  // (o token do backend expirou — o NextAuth pode ainda ter a sessão em cache)
  if (session && error !== "session_expired") redirect("/dashboard")

  const errorMessage = error ? (ERROR_MESSAGES[error] ?? ERROR_MESSAGES.default) : null

  return (
    <main className="flex min-h-screen items-center justify-center bg-(--bg-page) px-4">
      <div className="w-full max-w-sm rounded-lg border border-(--border-default) bg-(--bg-surface) p-8 shadow-(--shadow-md)">
        {/* Logo / Título */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-(--text-primary)">Prospector</h1>
          <p className="mt-1 text-sm text-(--text-secondary)">Sistema de prospecção B2B</p>
        </div>

        {/* Mensagem de erro */}
        {errorMessage && (
          <div
            role="alert"
            className="mb-6 rounded-md bg-(--danger-subtle) px-4 py-3 text-sm text-(--danger-subtle-fg)"
          >
            {errorMessage}
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
