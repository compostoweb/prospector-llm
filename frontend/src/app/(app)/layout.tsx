import { auth } from "@/lib/auth/config"
import { parseSidebarCollapsedCookie, SIDEBAR_COLLAPSED_COOKIE } from "@/lib/sidebar-preferences"
import { redirect } from "next/navigation"
import { cookies } from "next/headers"
import { Sidebar } from "@/components/layout/sidebar"
import { EventsProvider } from "@/components/providers/events-provider"

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth()
  if (!session) redirect("/login")
  const cookieStore = await cookies()
  const initialSidebarCollapsed = parseSidebarCollapsedCookie(
    cookieStore.get(SIDEBAR_COLLAPSED_COOKIE)?.value,
  )

  return (
    <EventsProvider>
      <div className="flex h-screen overflow-hidden bg-(--bg-page)">
        <Sidebar initialSidebarCollapsed={initialSidebarCollapsed} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </EventsProvider>
  )
}
