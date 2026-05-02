import { redirect } from "next/navigation"
import { auth } from "@/lib/auth/config"
import AuditoriaSegurancaPage from "./auditoria-page"

export default async function AuditoriaSegurancaRoutePage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }
  if (!session.user.is_superuser) {
    redirect("/dashboard")
  }
  return <AuditoriaSegurancaPage />
}