import { signIn } from "@/lib/auth/config"
import { AuthError } from "next-auth"

export async function GET(request: Request): Promise<Response> {
  const { searchParams } = new URL(request.url)
  const token = searchParams.get("token")

  if (!token) {
    return Response.redirect(new URL("/login?error=no_token", request.url))
  }

  try {
    await signIn("backend-google", {
      access_token: token,
      redirectTo: "/dashboard",
    })
  } catch (error) {
    // AuthError = falha real na autenticação → redireciona para login
    if (error instanceof AuthError) {
      return Response.redirect(new URL("/login?error=auth_failed", request.url))
    }
    // Qualquer outro erro (incluindo NEXT_REDIRECT interno) deve ser re-lançado
    throw error
  }

  // Nunca atingido em caso de sucesso (o signIn redireciona via throw)
  return Response.redirect(new URL("/login?error=auth_failed", request.url))
}
