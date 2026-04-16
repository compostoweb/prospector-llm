import { redirect } from "next/navigation"
import { auth } from "@/lib/auth/config"
import ClientesPage from "./clientes-page"

export default async function ClientesRoutePage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }
  if (!session.user.is_superuser) {
    redirect("/dashboard")
  }
  return <ClientesPage />
}
