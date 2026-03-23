import { test, expect } from "@playwright/test"

/**
 * Testes E2E da página de login e comportamento de auth.
 *
 * Pre-requisito: servidor Next.js rodando em http://localhost:3000
 * com NEXTAUTH_SECRET configurado em .env.local.
 *
 * Nenhum backend é necessário para estes testes — apenas o servidor
 * Next.js com JWT de sessão vazio (sessão ausente = não autenticado).
 */

// ── Página de login ──────────────────────────────────────────────────

test.describe("Login page", () => {
  test("renderiza heading 'Prospector'", async ({ page }) => {
    await page.goto("/login")
    await expect(page.getByRole("heading", { name: "Prospector", level: 1 })).toBeVisible()
  })

  test("renderiza subtítulo de sistema B2B", async ({ page }) => {
    await page.goto("/login")
    await expect(page.getByText("Sistema de prospecção B2B")).toBeVisible()
  })

  test("renderiza botão 'Entrar com Google'", async ({ page }) => {
    await page.goto("/login")
    await expect(page.getByRole("button", { name: /entrar com google/i })).toBeVisible()
  })

  test("renderiza mensagem de acesso restrito", async ({ page }) => {
    await page.goto("/login")
    await expect(page.getByText("Acesso restrito à equipe Composto Web")).toBeVisible()
  })

  test("não exibe alerta de erro sem query param", async ({ page }) => {
    await page.goto("/login")
    await expect(page.getByRole("alert")).not.toBeVisible()
  })

  test("exibe mensagem de erro para ?error=auth_failed", async ({ page }) => {
    await page.goto("/login?error=auth_failed")
    await expect(page.getByRole("alert")).toContainText("Falha na autenticação")
  })

  test("exibe mensagem de erro para ?error=session_expired", async ({ page }) => {
    await page.goto("/login?error=session_expired")
    await expect(page.getByRole("alert")).toContainText("Sessão expirada")
  })

  test("exibe mensagem de erro para ?error=OAuthCallback", async ({ page }) => {
    await page.goto("/login?error=OAuthCallback")
    await expect(page.getByRole("alert")).toContainText("Erro no callback OAuth")
  })

  test("exibe mensagem genérica para código de erro desconhecido", async ({ page }) => {
    await page.goto("/login?error=codigo_desconhecido")
    await expect(page.getByRole("alert")).toContainText("Ocorreu um erro")
  })

  test("clicar no botão Google inicia navegação para a URL do backend", async ({ page }) => {
    await page.goto("/login")

    // Captura a navegação disparada pelo clique, sem aguardar que complete
    const [request] = await Promise.all([
      page
        .waitForRequest((req) => req.url().includes("/auth/google/login"), { timeout: 3000 })
        .catch(() => null),
      page.getByRole("button", { name: /entrar com google/i }).click(),
    ])

    // Verifica que tentou navegar para a URL correta do backend
    if (request) {
      expect(request.url()).toContain("/auth/google/login")
    } else {
      // Se não capturou a request, ao menos verificamos que a URL mudou
      // (o browser pode redirecionar antes do interceptor capturar)
      expect(page.url()).toContain("google")
    }
  })
})

// ── Redirects de rotas protegidas ────────────────────────────────────

test.describe("Rotas protegidas — redireciona para /login sem sessão", () => {
  test("/dashboard redireciona para /login", async ({ page }) => {
    await page.goto("/dashboard")
    await expect(page).toHaveURL(/\/login/)
  })

  test("/leads redireciona para /login", async ({ page }) => {
    await page.goto("/leads")
    await expect(page).toHaveURL(/\/login/)
  })

  test("/cadencias redireciona para /login", async ({ page }) => {
    await page.goto("/cadencias")
    await expect(page).toHaveURL(/\/login/)
  })

  test("/configuracoes/conta redireciona para /login", async ({ page }) => {
    await page.goto("/configuracoes/conta")
    await expect(page).toHaveURL(/\/login/)
  })

  test("/configuracoes/llm redireciona para /login", async ({ page }) => {
    await page.goto("/configuracoes/llm")
    await expect(page).toHaveURL(/\/login/)
  })

  test("/configuracoes/unipile redireciona para /login", async ({ page }) => {
    await page.goto("/configuracoes/unipile")
    await expect(page).toHaveURL(/\/login/)
  })

  test("/configuracoes/integracoes redireciona para /login", async ({ page }) => {
    await page.goto("/configuracoes/integracoes")
    await expect(page).toHaveURL(/\/login/)
  })

  test("raiz / redireciona para /dashboard (que redireciona para /login)", async ({ page }) => {
    await page.goto("/")
    await expect(page).toHaveURL(/\/login/)
  })
})
