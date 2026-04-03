import { FileText, Sparkles, Settings2 } from "lucide-react"
import { ContentTabLink } from "@/components/content/content-tab-link"

const tabs = [
  { href: "/content", label: "Calendário", icon: FileText },
  { href: "/content/gerar", label: "Gerar com IA", icon: Sparkles },
  { href: "/content/configuracoes", label: "Configurações", icon: Settings2 },
]

export default function ContentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-(--text-primary)">Content Hub</h1>
        <p className="text-sm text-(--text-secondary) mt-1">
          Calendário editorial, geração com IA e publicação no LinkedIn
        </p>
      </div>

      <nav className="flex gap-1 border-b border-(--border-default)">
        {tabs.map(({ href, label, icon: Icon }) => (
          <ContentTabLink key={href} href={href} label={label} Icon={Icon} />
        ))}
      </nav>

      {children}
    </div>
  )
}
