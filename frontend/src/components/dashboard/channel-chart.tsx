"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import { channelLabel } from "@/lib/utils"
import type { ChannelBreakdown } from "@/lib/api/hooks/use-analytics"

interface ChannelChartProps {
  data: ChannelBreakdown[]
  isLoading?: boolean
}

export function ChannelChart({ data, isLoading }: ChannelChartProps) {
  const chartData = data.map((d) => ({
    name: channelLabel(d.channel),
    Enviados: d.steps_sent,
    Respostas: d.replies,
  }))

  if (isLoading) {
    return (
      <div className="flex h-60 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-(--border-default) border-t-(--accent)" />
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
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
          cursor={{ fill: "var(--bg-overlay)" }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }} />
        <Bar dataKey="Enviados" fill="var(--accent)" radius={[4, 4, 0, 0]} maxBarSize={40} />
        <Bar dataKey="Respostas" fill="var(--success)" radius={[4, 4, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  )
}
