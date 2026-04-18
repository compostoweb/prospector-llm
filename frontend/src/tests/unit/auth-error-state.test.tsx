import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import AuthErrorPage from "@/app/auth/error/page"
import { resolveAuthErrorState } from "@/lib/auth/auth-error-state"

vi.mock("@/env", () => ({
  env: {
    NEXT_PUBLIC_API_URL: "http://localhost:8000",
  },
}))

describe("resolveAuthErrorState", () => {
  it("mapeia email não cadastrado para um estado amigável", () => {
    const state = resolveAuthErrorState("email_not_registered")

    expect(state.title).toContain("Este email ainda não tem acesso")
    expect(state.banner).toContain("não está cadastrado")
    expect(state.showRetry).toBe(true)
  })

  it("usa a mensagem recebida quando o código é desconhecido", () => {
    const state = resolveAuthErrorState("erro_desconhecido", "Mensagem vinda do backend")

    expect(state.title).toContain("Não foi possível concluir seu acesso")
    expect(state.description).toBe("Mensagem vinda do backend")
  })
})

describe("AuthErrorPage", () => {
  it("renderiza a tela dedicada para email não cadastrado", async () => {
    render(
      await AuthErrorPage({
        searchParams: Promise.resolve({ error: "email_not_registered" }),
      }),
    )

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "O acesso não pôde ser concluído.",
    )
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
      "Este email ainda não tem acesso",
    )
    expect(screen.getByRole("button", { name: /entrar com google/i })).toBeInTheDocument()
  })

  it("remove a ação de retry quando a conta está inativa", async () => {
    render(
      await AuthErrorPage({
        searchParams: Promise.resolve({ error: "user_inactive" }),
      }),
    )

    expect(screen.queryByRole("button", { name: /entrar com google/i })).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: /voltar para o login/i })).toBeInTheDocument()
  })
})