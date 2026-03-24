import Link from "next/link"
import type { CadencePerformance } from "@/lib/api/hooks/use-analytics"

interface CadencePerformanceTableProps {
  data: CadencePerformance[]
  isLoading?: boolean
}

export function CadencePerformanceTable({ data, isLoading }: CadencePerformanceTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-10 animate-pulse rounded-md bg-(--bg-overlay)" />
        ))}
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-(--text-tertiary)">
        Nenhuma cadência com dados no período
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-(--border-subtle)">
            <th className="pb-2 pr-3 font-medium text-(--text-tertiary)">Cadência</th>
            <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">Leads</th>
            <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">Envios</th>
            <th className="pb-2 pr-3 text-right font-medium text-(--text-tertiary)">Respostas</th>
            <th className="pb-2 text-right font-medium text-(--text-tertiary)">Taxa</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.cadence_id} className="border-b border-(--border-subtle) last:border-0">
              <td className="py-2 pr-3">
                <Link
                  href={`/cadencias/${row.cadence_id}`}
                  className="font-medium text-(--text-primary) hover:text-(--accent)"
                >
                  {row.cadence_name}
                </Link>
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-(--text-secondary)">
                {row.leads_active}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-(--text-secondary)">
                {row.steps_sent}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-(--text-secondary)">
                {row.replies}
              </td>
              <td className="py-2 text-right tabular-nums font-medium text-(--text-primary)">
                {row.reply_rate}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
