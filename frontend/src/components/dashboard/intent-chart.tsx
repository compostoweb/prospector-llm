"use client"

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"
import type { IntentBreakdown } from "@/lib/api/hooks/use-analytics"

const INTENT_LABELS: Record<string, string> = {
  interest: "Interesse",
  objection: "Objeção",
  not_interested: "Sem interesse",
  neutral: "Neutro",
  out_of_office: "Ausente",
}

const INTENT_COLORS: Record<string, string> = {
  interest: "var(--success)",
  objection: "var(--warning)",
  not_interested: "var(--danger)",
  neutral: "var(--text-tertiary)",
  out_of_office: "var(--accent)",
}

interface IntentChartProps {
  data: IntentBreakdown[]
  isLoading?: boolean
}

export function IntentChart({ data, isLoading }: IntentChartProps) {
  const chartData = data.map((d) => ({
    name: INTENT_LABELS[d.intent] ?? d.intent,
    value: d.count,
    percentage: d.percentage,
    intent: d.intent,
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
        Sem respostas classificadas
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {chartData.map((entry) => (
            <Cell key={entry.intent} fill={INTENT_COLORS[entry.intent] ?? "var(--text-disabled)"} />
          ))}
        </Pie>
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
            "Respostas",
          ]}
        />
        <Legend
          wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }}
          iconSize={8}
          iconType="circle"
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
