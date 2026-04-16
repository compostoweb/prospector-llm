import { redirect } from "next/navigation"
import { auth } from "@/lib/auth/config"
import EquipePage from "./equipe-page"

export default async function EquipeRoutePage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }
  if (!session.user.is_superuser && session.user.tenant_role !== "tenant_admin") {
    redirect("/dashboard")
  }
  return <EquipePage />
}
