import { Suspense } from "react"
import NovaCampanhaPage from "./nova-campanha-page"

export default function Page() {
  return (
    <Suspense>
      <NovaCampanhaPage />
    </Suspense>
  )
}
