import { NextResponse, type NextRequest } from "next/server"

const SESSION_COOKIE_NAMES = [
  "authjs.session-token",
  "__Secure-authjs.session-token",
  "next-auth.session-token",
  "__Secure-next-auth.session-token",
]

export default function middleware(req: NextRequest) {
  const hasSessionCookie = SESSION_COOKIE_NAMES.some((cookieName) =>
    Boolean(req.cookies.get(cookieName)?.value),
  )

  if (hasSessionCookie) {
    return NextResponse.next()
  }

  const loginUrl = new URL("/login", req.url)
  return NextResponse.redirect(loginUrl)
}

export const config = {
  matcher: [
    /*
     * Aplica middleware em todas as rotas, exceto:
     * - _next/static (arquivos estáticos)
     * - _next/image (otimização de imagens)
     * - favicon.ico
     * - login e rotas de auth (públicas)
     */
    "/((?!_next/static|_next/image|favicon.ico|login|auth|api/auth|lm).*)",
  ],
}
