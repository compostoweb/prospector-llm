import NextAuth, { type DefaultSession } from "next-auth"
import Credentials from "next-auth/providers/credentials"
import { jwtDecode } from "jwt-decode"

// ── Type augmentation ────────────────────────────────────────────────

declare module "next-auth" {
  interface Session {
    accessToken: string
    user: DefaultSession["user"] & {
      id: string
      tenant_id: string
      is_superuser: boolean
    }
  }

  interface User {
    id: string
    is_superuser: boolean
    access_token: string
  }
}

// ── Backend JWT payload ──────────────────────────────────────────────

interface BackendJWTPayload {
  type: "user"
  user_id: string
  email: string
  is_superuser: boolean
  name?: string
  exp: number
}

// ── NextAuth config ──────────────────────────────────────────────────

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      id: "backend-google",
      name: "Google via Backend",
      credentials: {
        access_token: { type: "text" },
      },
      async authorize(credentials) {
        const token = credentials["access_token"] as string | undefined
        if (!token) return null

        const response = await fetch(`${process.env["API_URL"]}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        })

        if (!response.ok) return null

        const user = (await response.json()) as {
          id: string
          email: string
          name: string | null
          is_superuser: boolean
        }

        return {
          id: user.id,
          email: user.email,
          name: user.name,
          is_superuser: user.is_superuser,
          access_token: token,
        }
      },
    }),
  ],

  callbacks: {
    jwt({ token, user }) {
      // Preenchido no primeiro sign-in
      if (user) {
        token["user_id"] = user.id
        token["is_superuser"] = user.is_superuser
        token["access_token"] = user.access_token

        // Extrai o `exp` do JWT do backend para controlar refresh
        try {
          const decoded = jwtDecode<BackendJWTPayload>(user.access_token)
          token["access_token_expires"] = decoded.exp * 1000
        } catch {
          token["access_token_expires"] = Date.now() + 60 * 60 * 1000
        }
      }

      // Token ainda válido — retorna sem modificação
      if (Date.now() < (token["access_token_expires"] as number)) {
        return token
      }

      // Token expirado — sessão inválida (backend não tem refresh endpoint)
      return { ...token, error: "TokenExpired" }
    },

    session({ session, token }) {
      session.accessToken = token["access_token"] as string
      session.user.id = token["user_id"] as string
      session.user.is_superuser = token["is_superuser"] as boolean
      // tenant_id não existe no sistema atual — placeholder para multi-tenant futuro
      session.user.tenant_id = ""
      return session
    },
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },

  session: { strategy: "jwt" },

  trustHost: true,
})
