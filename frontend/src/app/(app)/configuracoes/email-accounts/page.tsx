import type { Metadata } from "next"
import EmailAccountsPage from "./email-accounts-page"

export const metadata: Metadata = {
  title: "E-mail Accounts | Prospector",
  description: "Gerencie contas de e-mail para envio de cold emails",
}

export default function Page() {
  return <EmailAccountsPage />
}
