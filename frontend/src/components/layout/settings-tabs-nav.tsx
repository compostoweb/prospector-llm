"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { User, Zap, Volume2, Music, Plug, Settings, Mail, Linkedin } from "lucide-react"
import { cn } from "@/lib/utils"

const tabs = [
  { href: "/configuracoes/conta", label: "Conta", icon: User },
  { href: "/configuracoes/llm", label: "Modelos LLM", icon: Zap },
  { href: "/configuracoes/voz", label: "Vozes TTS", icon: Volume2 },
  { href: "/configuracoes/audios", label: "Áudios", icon: Music },
  { href: "/configuracoes/unipile", label: "Unipile", icon: Plug },
  { href: "/configuracoes/integracoes", label: "Integrações", icon: Settings },
  { href: "/configuracoes/email-accounts", label: "Contas de E-mail", icon: Mail },
  { href: "/configuracoes/linkedin-accounts", label: "Contas LinkedIn", icon: Linkedin },
] as const

export function SettingsTabsNav() {
  const pathname = usePathname()

  return (
    <div className="border-b border-(--border-default) mb-6">
      <nav aria-label="Configurações" className="flex overflow-x-auto -mb-px">
        {tabs.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/")
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm transition-colors",
                active
                  ? "border-(--accent) text-(--accent-subtle-fg) font-medium"
                  : "border-transparent text-(--text-secondary) hover:border-(--border-default) hover:text-(--text-primary)",
              )}
            >
              <Icon size={15} aria-hidden="true" className="shrink-0" />
              <span>{label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
