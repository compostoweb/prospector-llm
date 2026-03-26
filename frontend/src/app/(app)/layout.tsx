import { auth } from "@/lib/auth/config"
import { redirect } from "next/navigation"
import { Sidebar } from "@/components/layout/sidebar"
import { EventsProvider } from "@/components/providers/events-provider"

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth()
  if (!session) redirect("/login")

  return (
    <EventsProvider>
      <div className="flex h-screen overflow-hidden bg-(--bg-page)">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </EventsProvider>
  )
}
