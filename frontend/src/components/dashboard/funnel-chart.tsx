"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"
import type { FunnelItem } from "@/lib/api/hooks/use-analytics"

const STATUS_LABELS: Record<string, string> = {
  raw: "Bruto",
  enriched: "Enriquecido",
  in_cadence: "Em Cadência",
  converted: "Convertido",
  archived: "Arquivado",
}

const STATUS_COLORS: Record<string, string> = {
  raw: "var(--text-tertiary)",
  enriched: "var(--accent)",
  in_cadence: "var(--warning)",
  converted: "var(--success)",
  archived: "var(--text-disabled)",
}

interface FunnelChartProps {
  data: FunnelItem[]
  isLoading?: boolean
}

export function FunnelChart({ data, isLoading }: FunnelChartProps) {
  const chartData = data.map((d) => ({
    name: STATUS_LABELS[d.status] ?? d.status,
    count: d.count,
    percentage: d.percentage,
    status: d.status,
  }))

  if (isLoading) {
    return (
      <div className="flex h-52 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-(--border-default) border-t-(--accent)" />
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className="flex h-52 items-center justify-center text-sm text-(--text-tertiary)">
        Sem dados de funil
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 4, right: 40, left: 8, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
          width={90}
        />
        <Tooltip
          contentStyle={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-md)",
            fontSize: 12,
            color: "var(--text-primary)",
          }}
          formatter={(value: number, _name: string, props: { payload: { percentage: number } }) => [
            `${value} (${props.payload.percentage}%)`,
            "Leads",
          ]}
          cursor={{ fill: "var(--bg-overlay)" }}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={28}>
          {chartData.map((entry) => (
            <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? "var(--accent)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
