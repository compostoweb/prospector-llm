import { ColdEmailTabsNav } from "@/components/layout/cold-email-tabs-nav"

export default function ColdEmailLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <ColdEmailTabsNav />
      {children}
    </div>
  )
}
