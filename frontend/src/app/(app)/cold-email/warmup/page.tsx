import type { Metadata } from "next"
import WarmupPage from "./warmup-page"

export const metadata: Metadata = {
  title: "Warmup | Prospector",
  description: "Aquecimento de contas de e-mail para melhorar entregabilidade",
}

export default function Page() {
  return <WarmupPage />
}
