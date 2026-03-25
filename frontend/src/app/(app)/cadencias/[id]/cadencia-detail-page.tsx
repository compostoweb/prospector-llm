"use client"

import { useParams } from "next/navigation"
import { useCadence } from "@/lib/api/hooks/use-cadences"
import { CadenceForm } from "@/components/cadencias/cadence-form"
import { Loader2 } from "lucide-react"

export default function CadenciaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: cadence, isLoading, error } = useCadence(id)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-(--text-tertiary)" />
      </div>
    )
  }

  if (error || !cadence) {
    return (
      <div className="py-20 text-center text-sm text-(--text-secondary)">
        Cadência não encontrada.
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-(--text-primary)">Editar cadência</h1>
        <p className="text-sm text-(--text-secondary)">{cadence.name}</p>
      </div>
      <CadenceForm cadence={cadence} />
    </div>
  )
}
