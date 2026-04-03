import { type Metadata } from "next"
import ColdEmailPage from "./cold-email-page"

export const metadata: Metadata = {
  title: "Cold Email",
}

export default function Page() {
  return <ColdEmailPage />
}
