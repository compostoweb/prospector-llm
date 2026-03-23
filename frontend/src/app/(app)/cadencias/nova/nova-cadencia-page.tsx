import { CadenceForm } from "@/components/cadencias/cadence-form"

export default function NovaCadenciaPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-(--text-primary)">Nova cadência</h1>
        <p className="text-sm text-(--text-secondary)">
          Configure os passos, canal e modelo LLM
        </p>
      </div>
      <CadenceForm />
    </div>
  )
}
