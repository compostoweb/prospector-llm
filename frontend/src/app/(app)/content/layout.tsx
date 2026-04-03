import { ContentTabs } from "@/components/content/content-tab-link"

export default function ContentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-(--text-primary)">Content Hub</h1>
        <p className="text-sm text-(--text-secondary) mt-1">
          Calendário editorial, geração com IA e publicação no LinkedIn
        </p>
      </div>

      <ContentTabs />

      {children}
    </div>
  )
}
