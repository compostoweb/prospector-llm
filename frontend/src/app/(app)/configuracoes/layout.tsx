import { SettingsTabsNav } from "@/components/layout/settings-tabs-nav"

export default function ConfiguracoesLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <SettingsTabsNav />
      {children}
    </div>
  )
}
