"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { Sun, Moon, Monitor } from "lucide-react"
import { cn } from "@/lib/utils"

interface ThemeToggleProps {
  className?: string
  collapsed?: boolean
}

const THEME_CYCLE = ["light", "dark", "system"] as const
type ThemeValue = (typeof THEME_CYCLE)[number]

const THEME_ICONS: Record<ThemeValue, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
}

const THEME_LABELS: Record<ThemeValue, string> = {
  light: "Tema claro",
  dark: "Tema escuro",
  system: "Tema do sistema",
}

export function ThemeToggle({ className, collapsed }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const selectedTheme: ThemeValue = mounted ? ((theme as ThemeValue | undefined) ?? "system") : "system"

  if (collapsed) {
    const current = selectedTheme
    const Icon = THEME_ICONS[current] ?? Monitor
    const nextTheme =
      THEME_CYCLE[(THEME_CYCLE.indexOf(current) + 1) % THEME_CYCLE.length] ?? "system"

    return (
      <button
        aria-label={`${THEME_LABELS[current]} — clique para alternar`}
        onClick={() => setTheme(nextTheme)}
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-md text-(--text-tertiary) transition-colors hover:bg-(--bg-overlay) hover:text-(--text-secondary)",
          className,
        )}
      >
        <Icon size={16} aria-hidden="true" />
      </button>
    )
  }

  const options = [
    { value: "light", icon: Sun, label: "Tema claro" },
    { value: "dark", icon: Moon, label: "Tema escuro" },
    { value: "system", icon: Monitor, label: "Tema do sistema" },
  ] as const

  return (
    <div
      role="radiogroup"
      aria-label="Tema de cores"
      className={cn(
        "flex items-center gap-0.5 rounded-md border border-(--border-default) bg-(--bg-overlay) p-0.5",
        className,
      )}
    >
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          role="radio"
          aria-checked={selectedTheme === value ? "true" : "false"}
          aria-label={label}
          onClick={() => setTheme(value)}
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-sm transition-colors",
            selectedTheme === value
              ? "bg-(--bg-surface) text-(--text-primary) shadow-(--shadow-sm)"
              : "text-(--text-tertiary) hover:text-(--text-secondary)",
          )}
        >
          <Icon size={14} aria-hidden="true" />
        </button>
      ))}
    </div>
  )
}
