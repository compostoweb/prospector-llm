"use client"

import type { ContactQualityBucket, EmailVerificationStatus } from "@/lib/api/hooks/use-leads"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

interface ContactQualityBadgeProps {
  qualityBucket: ContactQualityBucket | null
  qualityScore: number | null
  verificationStatus: EmailVerificationStatus | null
  source?: string | null
  compact?: boolean
  className?: string
}

const bucketLabel: Record<ContactQualityBucket, string> = {
  green: "Verde",
  orange: "Laranja",
  red: "Vermelho",
}

const bucketVariant: Record<ContactQualityBucket, "success" | "warning" | "danger"> = {
  green: "success",
  orange: "warning",
  red: "danger",
}

const verificationLabel: Record<EmailVerificationStatus, string> = {
  valid: "Válido",
  accept_all: "Accept-all",
  unknown: "Desconhecido",
  invalid: "Inválido",
  disposable: "Descartável",
  abuse: "Abuso",
  do_not_mail: "Não enviar",
  spamtrap: "Spamtrap",
  webmail: "Webmail",
}

export function ContactQualityBadge({
  qualityBucket,
  qualityScore,
  verificationStatus,
  source,
  compact = false,
  className,
}: ContactQualityBadgeProps) {
  if (!qualityBucket && !verificationStatus) {
    return null
  }

  const bucket = qualityBucket ?? "red"
  const score = qualityScore !== null ? `${Math.round(qualityScore * 100)}%` : "—"
  const verification = verificationStatus ? verificationLabel[verificationStatus] : "Sem validação"

  return (
    <TooltipProvider delayDuration={120}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span>
            <Badge
              variant={bucketVariant[bucket]}
              className={cn(
                "rounded-(--radius-full)",
                compact && "px-1.5 py-0 text-[10px]",
                className,
              )}
            >
              {bucketLabel[bucket]}
            </Badge>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-64 text-xs leading-relaxed">
          <div className="space-y-1">
            <p className="font-medium">Qualidade {bucketLabel[bucket].toLowerCase()}</p>
            <p>Score: {score}</p>
            <p>Verificação: {verification}</p>
            <p>Fonte: {source || "não informada"}</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
