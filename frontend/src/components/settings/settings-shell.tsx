import type { ReactNode } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type SettingsPageWidth = "compact" | "content" | "wide"

const widthClasses: Record<SettingsPageWidth, string> = {
  compact: "max-w-none",
  content: "max-w-none",
  wide: "max-w-none",
}

interface SettingsPageShellProps {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  width?: SettingsPageWidth
  className?: string
}

export function SettingsPageShell({
  title,
  description,
  actions,
  children,
  width = "wide",
  className,
}: SettingsPageShellProps) {
  return (
    <div
      className={cn(
        "w-full pb-8 lg:pb-10",
        widthClasses[width],
        className,
      )}
    >
      <div className="space-y-5 lg:space-y-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl space-y-1.5">
            <h1 className="text-2xl font-semibold tracking-tight text-(--text-primary)">{title}</h1>
            {description ? (
              <p className="text-sm leading-6 text-(--text-secondary)">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
        {children}
      </div>
    </div>
  )
}

interface SettingsPanelProps {
  title?: string
  description?: string
  headerAside?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
  headerClassName?: string
}

export function SettingsPanel({
  title,
  description,
  headerAside,
  children,
  className,
  contentClassName,
  headerClassName,
}: SettingsPanelProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      {title || description || headerAside ? (
        <CardHeader className={cn("gap-1 p-4 pb-0 sm:p-5 sm:pb-0", headerClassName)}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1">
              {title ? <CardTitle className="text-base font-semibold">{title}</CardTitle> : null}
              {description ? <CardDescription>{description}</CardDescription> : null}
            </div>
            {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
          </div>
        </CardHeader>
      ) : null}
      <CardContent className={cn("p-4 sm:p-5", contentClassName)}>{children}</CardContent>
    </Card>
  )
}

interface SettingsCalloutProps {
  icon?: ReactNode
  title?: string
  children: ReactNode
  className?: string
}

export function SettingsCallout({ icon, title, children, className }: SettingsCalloutProps) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-xl border border-(--info-subtle) bg-(--info-subtle) px-4 py-3.5",
        className,
      )}
    >
      {icon ? <div className="mt-0.5 shrink-0 text-(--info)">{icon}</div> : null}
      <div className="space-y-1 text-sm leading-6 text-(--info-subtle-fg)">
        {title ? <p className="font-semibold">{title}</p> : null}
        <div>{children}</div>
      </div>
    </div>
  )
}
