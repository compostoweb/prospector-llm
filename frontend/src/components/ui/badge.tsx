import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-(--accent-subtle) text-(--accent-subtle-fg)",
        outline: "border border-(--border-default) text-(--text-secondary)",
        success: "bg-(--success-subtle) text-(--success-subtle-fg)",
        warning: "bg-(--warning-subtle) text-(--warning-subtle-fg)",
        danger: "bg-(--danger-subtle) text-(--danger-subtle-fg)",
        neutral: "bg-(--neutral-subtle) text-(--neutral-subtle-fg)",
        info: "bg-(--info-subtle) text-(--info-subtle-fg)",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
