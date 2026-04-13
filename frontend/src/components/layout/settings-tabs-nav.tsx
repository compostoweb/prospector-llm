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
    <div className="border-b border-(--border-default) bg-(--bg-page)">
      <nav
        aria-label="Configurações"
        className="-mb-px flex w-full overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {tabs.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/")
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm transition-colors md:px-4",
                active
                  ? "border-(--accent) font-medium text-(--accent-subtle-fg)"
                  : "border-transparent text-(--text-secondary) hover:border-(--border-default) hover:text-(--text-primary)",
              )}
            >
              <Icon size={15} aria-hidden="true" className="shrink-0" />
              <span className="whitespace-nowrap">{label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
