import { ColdEmailTabsNav } from "@/components/layout/cold-email-tabs-nav"

export default function ColdEmailLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 lg:gap-3 pt-0 lg:pt-0">
      <ColdEmailTabsNav />
      {children}
    </div>
  )
}
