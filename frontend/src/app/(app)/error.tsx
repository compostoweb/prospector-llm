"use client"

import { useEffect } from "react"
import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ErrorPageProps {
  error: Error & { digest?: string }
  reset: () => void
}

export default function AppError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("[AppError]", error)
  }, [error])

  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="flex max-w-md flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-(--danger-subtle)">
          <AlertTriangle size={24} className="text-(--danger)" aria-hidden="true" />
        </div>
        <h2 className="text-lg font-semibold text-(--text-primary)">Algo deu errado</h2>
        <p className="text-sm text-(--text-secondary)">
          Ocorreu um erro ao carregar esta página. Tente novamente ou volte para o dashboard.
        </p>
        <div className="flex gap-3">
          <Button variant="outline" size="sm" onClick={() => (window.location.href = "/dashboard")}>
            Ir para Dashboard
          </Button>
          <Button size="sm" onClick={reset}>
            Tentar novamente
          </Button>
        </div>
      </div>
    </div>
  )
}
