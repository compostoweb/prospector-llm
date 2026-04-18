import { AlertCircle, ArrowLeft, Clock3, ShieldAlert, ShieldX, UserRoundX } from "lucide-react"
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { resolveAuthErrorState } from "@/lib/auth/auth-error-state"

interface Props {
  searchParams: Promise<{ error?: string; message?: string }>
}

const toneClasses = {
  danger: {
    badge: "bg-(--danger-subtle) text-(--danger-subtle-fg)",
    panel: "border-(--danger-subtle) bg-(--danger-subtle)",
  },
  warning: {
    badge: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
    panel: "border-(--warning-subtle) bg-(--warning-subtle)",
  },
  info: {
    badge: "bg-(--info-subtle) text-(--info-subtle-fg)",
    panel: "border-(--info-subtle) bg-(--info-subtle)",
  },
} as const

function resolveAuthIcon(errorCode: string) {
  switch (errorCode) {
    case "email_not_registered":
      return UserRoundX
    case "invalid_state":
    case "session_expired":
      return Clock3
    case "oauth_access_denied":
      return AlertCircle
    case "google_oauth_unconfigured":
    case "auth_failed":
      return ShieldX
    default:
      return ShieldAlert
  }
}

export default async function AuthErrorPage({ searchParams }: Props) {
  const { error, message } = await searchParams
  const state = resolveAuthErrorState(error, message)
  const tone = toneClasses[state.tone]
  const Icon = resolveAuthIcon(state.code)

  return (
    <main className="relative min-h-screen overflow-hidden bg-(--bg-page)">
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          backgroundImage:
            "linear-gradient(to right, var(--border-subtle) 1px, transparent 1px), linear-gradient(to bottom, var(--border-subtle) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
          maskImage: "radial-gradient(circle at center, black 30%, transparent 80%)",
        }}
      />
      <div className="pointer-events-none absolute -left-20 top-10 h-64 w-64 rounded-full bg-(--accent-subtle) blur-3xl" />
      <div className="pointer-events-none absolute -right-20 bottom-0 h-72 w-72 rounded-full bg-(--warning-subtle) blur-3xl" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid w-full gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="flex flex-col justify-center rounded-[28px] border border-(--border-subtle) bg-(--bg-surface)/80 p-8 shadow-(--shadow-lg) backdrop-blur sm:p-10">
            <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-(--border-default) bg-(--bg-overlay) px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-(--text-secondary)">
              Autenticação Prospector
            </div>
            <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-(--text-primary) sm:text-5xl">
              O acesso não pôde ser concluído.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-(--text-secondary) sm:text-lg">
              Tratamos esse retorno em uma tela dedicada para evitar respostas cruas do backend e
              deixar claro o que aconteceu com o seu login.
            </p>
            <div className="mt-8 flex flex-wrap gap-3 text-sm text-(--text-secondary)">
              <span className="rounded-full border border-(--border-default) bg-(--bg-overlay) px-3 py-1.5">
                Google OAuth via backend
              </span>
              <span className="rounded-full border border-(--border-default) bg-(--bg-overlay) px-3 py-1.5">
                Acesso restrito por usuário
              </span>
              <span className="rounded-full border border-(--border-default) bg-(--bg-overlay) px-3 py-1.5">
                Sessão protegida
              </span>
            </div>
          </section>

          <Card className="overflow-hidden rounded-[28px] border-(--border-default) shadow-(--shadow-lg)">
            <CardContent className="p-0">
              <div className="border-b border-(--border-subtle) bg-(--bg-surface) p-7">
                <div
                  className={`inline-flex h-14 w-14 items-center justify-center rounded-2xl ${tone.badge}`}
                >
                  <Icon className="h-6 w-6" />
                </div>
                <h2 className="mt-5 text-2xl font-semibold text-(--text-primary)">{state.title}</h2>
                <p className="mt-3 text-sm leading-6 text-(--text-secondary)">
                  {state.description}
                </p>
              </div>

              <div className="space-y-5 bg-(--bg-surface) p-7">
                <div className={`rounded-2xl border p-4 ${tone.panel}`}>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-(--text-secondary)">
                    O que significa
                  </p>
                  <p className="mt-2 text-sm leading-6 text-(--text-primary)">
                    {state.supportText}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-(--text-secondary)">
                    Próximos passos
                  </p>
                  <ul className="mt-3 space-y-3 text-sm leading-6 text-(--text-secondary)">
                    {state.nextSteps.map((step) => (
                      <li key={step} className="flex gap-3">
                        <span className="mt-1 h-2 w-2 rounded-full bg-(--accent)" />
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="space-y-3 pt-2">
                  {state.showRetry ? <GoogleSignInButton /> : null}
                  <Button
                    asChild
                    className="w-full"
                    variant={state.showRetry ? "outline" : "default"}
                  >
                    <a href="/login">
                      <ArrowLeft className="h-4 w-4" />
                      Voltar para o login
                    </a>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  )
}
