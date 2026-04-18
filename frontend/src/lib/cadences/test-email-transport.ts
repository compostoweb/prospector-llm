import type { Cadence } from "@/lib/api/hooks/use-cadences"
import type { EmailAccount } from "@/lib/api/hooks/use-email-accounts"

export interface TestEmailTransportSummary {
  status: "configured" | "fallback" | "missing" | "loading"
  shortLabel: string
  label: string
  hint: string
}

const PROVIDER_LABELS: Record<string, string> = {
  unipile_gmail: "Unipile Gmail",
  google_oauth: "Gmail OAuth",
  smtp: "SMTP",
}

function getProviderLabel(providerType: string | null | undefined): string | null {
  if (!providerType) {
    return null
  }
  return PROVIDER_LABELS[providerType] ?? providerType
}

export function buildTestEmailTransportSummary({
  cadence,
  emailAccounts,
  isCadenceLoading = false,
  isEmailAccountsLoading = false,
}: {
  cadence?: Pick<Cadence, "email_account_id"> | null | undefined
  emailAccounts?: EmailAccount[] | undefined
  isCadenceLoading?: boolean
  isEmailAccountsLoading?: boolean
}): TestEmailTransportSummary {
  if (isCadenceLoading || (cadence?.email_account_id && isEmailAccountsLoading && !emailAccounts)) {
    return {
      status: "loading",
      shortLabel: "Carregando transporte",
      label: "Carregando conta de envio",
      hint: "Buscando a conta ou fallback que será usado no teste.",
    }
  }

  if (cadence?.email_account_id) {
    const account = emailAccounts?.find((item) => item.id === cadence.email_account_id)
    if (!account) {
      return {
        status: "missing",
        shortLabel: "Conta indisponível",
        label: "Conta da cadência não encontrada",
        hint: "A cadência aponta para uma conta removida, inacessível ou ainda não carregada.",
      }
    }

    const providerLabel =
      PROVIDER_LABELS[account.effective_provider_type] ?? account.effective_provider_type
    const fromLabel = account.from_name?.trim() || account.display_name.trim() || account.email_address

    return {
      status: "configured",
      shortLabel: `${fromLabel} <${account.email_address}>`,
      label: `${fromLabel} <${account.email_address}>`,
      hint: account.outbound_uses_fallback
        ? `Conta vinculada na cadência; o envio sai via ${providerLabel} usando o fallback configurado.`
        : `Conta vinculada na cadência; o envio sai via ${providerLabel}.`,
    }
  }

  return {
    status: "fallback",
    shortLabel: "Gmail integrado do tenant",
    label: "Gmail integrado do tenant/projeto",
    hint: "Sem conta específica na cadência; o teste usa o fallback de e-mail configurado via Unipile.",
  }
}

export function buildTestEmailSuccessMessage({
  toEmail,
  summary,
  providerType,
}: {
  toEmail: string
  summary: TestEmailTransportSummary
  providerType?: string | null
}): string {
  const resolvedTransport =
    summary.status === "configured" || summary.status === "fallback"
      ? summary.shortLabel
      : getProviderLabel(providerType)

  if (!resolvedTransport) {
    return `Teste enviado para ${toEmail}`
  }

  return `Teste enviado para ${toEmail} via ${resolvedTransport}`
}