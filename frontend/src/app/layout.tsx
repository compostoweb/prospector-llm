import type { Metadata } from "next"
import { DM_Sans } from "next/font/google"
import { SessionProvider } from "next-auth/react"
import { ThemeProvider } from "next-themes"
import { ReactQueryProvider } from "@/components/providers/react-query-provider"
import { auth } from "@/lib/auth/config"
import "@/styles/globals.css"

// ── Fonte ─────────────────────────────────────────────────────────────

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
})

// ── Metadados ─────────────────────────────────────────────────────────

export const metadata: Metadata = {
  title: {
    default: "Prospector",
    template: "%s | Prospector",
  },
  description: "Sistema de prospecção B2B automatizado",
  robots: { index: false, follow: false }, // app privado
}

// ── Layout ────────────────────────────────────────────────────────────

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Pré-carrega a sessão no servidor para evitar flash de "não autenticado"
  // e corrigir race condition em mutations antes do SessionProvider hidratar.
  const session = await auth()

  return (
    <html
      lang="pt-BR"
      className={dmSans.variable}
      suppressHydrationWarning // next-themes altera data-theme no client
    >
      <body>
        <SessionProvider session={session}>
          <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem>
            <ReactQueryProvider>{children}</ReactQueryProvider>
          </ThemeProvider>
        </SessionProvider>
      </body>
    </html>
  )
}
