import { redirect } from "next/navigation"

/** Raiz do app — redireciona para /dashboard */
export default function HomePage() {
  redirect("/dashboard")
}
