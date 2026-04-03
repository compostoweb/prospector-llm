import { type Metadata } from "next"
import EmailTemplatesPage from "./email-templates-page"

export const metadata: Metadata = {
  title: "Templates de E-mail",
}

export default function Page() {
  return <EmailTemplatesPage />
}
