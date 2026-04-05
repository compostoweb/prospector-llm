import { format } from "date-fns"
import { ptBR } from "date-fns/locale"
import { toZonedTime } from "date-fns-tz"

const TZ = "America/Sao_Paulo"

/** Formata ISO date string no fuso America/Sao_Paulo */
export function formatDateBR(
  isoString: string,
  fmt: string = "dd MMM yyyy 'às' HH:mm",
): string {
  const zonedDate = toZonedTime(isoString, TZ)
  return format(zonedDate, fmt, { locale: ptBR })
}
