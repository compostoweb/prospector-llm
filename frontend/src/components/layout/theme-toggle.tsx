"use client"

import { useTheme } from "next-themes"
import { Sun, Moon, Monitor } from "lucide-react"
import { cn } from "@/lib/utils"

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme()

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
        "flex items-center gap-0.5 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-overlay)] p-0.5",
        className,
      )}
    >
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          role="radio"
          aria-checked={theme === value}
          aria-label={label}
          onClick={() => setTheme(value)}
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] transition-colors",
            theme === value
              ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-[var(--shadow-sm)]"
              : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]",
          )}
        >
          <Icon size={14} aria-hidden="true" />
        </button>
      ))}
    </div>
  )
}
