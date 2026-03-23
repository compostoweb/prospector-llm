import * as React from "react"
import { cn } from "@/lib/utils"

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-md border border-(--border-default) bg-(--bg-surface) px-3 py-1 text-sm text-(--text-primary) shadow-sm transition-colors",
          "placeholder:text-(--text-tertiary)",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          "focus:border-(--accent) focus:outline-none focus:ring-2 focus:ring-(--accent) focus:ring-offset-0",
          "disabled:cursor-not-allowed disabled:opacity-50 read-only:cursor-default",
          className,
        )}
        ref={ref}
        {...props}
      />
    )
  },
)
Input.displayName = "Input"

export { Input }
