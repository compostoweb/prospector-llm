import { auth } from "@/lib/auth/config"

export default auth((req) => {
  // Usuário não autenticado → redireciona para /login
  if (!req.auth) {
    const loginUrl = new URL("/login", req.url)
    return Response.redirect(loginUrl)
  }
})

export const config = {
  matcher: [
    /*
     * Aplica middleware em todas as rotas, exceto:
     * - _next/static (arquivos estáticos)
     * - _next/image (otimização de imagens)
     * - favicon.ico
     * - login e rotas de auth (públicas)
     */
    "/((?!_next/static|_next/image|favicon.ico|login|auth|api/auth).*)",
  ],
}
