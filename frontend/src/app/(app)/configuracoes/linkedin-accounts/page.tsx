import type { Metadata } from "next"
import LinkedInAccountsPage from "./linkedin-accounts-page"

export const metadata: Metadata = {
  title: "Contas LinkedIn | Prospector",
  description: "Gerencie contas LinkedIn para prospecção e cadências",
}

export default function Page() {
  return <LinkedInAccountsPage />
}
