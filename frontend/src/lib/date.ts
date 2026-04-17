import { format } from "date-fns"
import { ptBR } from "date-fns/locale"
import { toZonedTime, fromZonedTime } from "date-fns-tz"

const TZ = "America/Sao_Paulo"

/** Formata ISO date string no fuso America/Sao_Paulo */
export function formatDateBR(isoString: string, fmt: string = "dd MMM yyyy 'às' HH:mm"): string {
  const zonedDate = toZonedTime(isoString, TZ)
  return format(zonedDate, fmt, { locale: ptBR })
}

/**
 * Converte valor de datetime-local (interpretado como horário SP)
 * para ISO string UTC para enviar ao backend.
 * Ex: "2026-04-05T20:25" → "2026-04-05T23:25:00.000Z"
 */
export function localDateToUTC(datetimeLocal: string): string {
  return fromZonedTime(datetimeLocal, TZ).toISOString()
}

export function utcToLocalDateTimeInputValue(isoString: string | null | undefined): string {
  if (!isoString) return ""
  return format(toZonedTime(isoString, TZ), "yyyy-MM-dd'T'HH:mm")
}

export function getDayOfMonthFromLocalDateTime(
  datetimeLocal: string | null | undefined,
): number | null {
  if (!datetimeLocal || datetimeLocal.length < 10) return null
  const day = Number(datetimeLocal.slice(8, 10))
  return Number.isNaN(day) ? null : day
}

export function isFutureLocalDateTime(datetimeLocal: string | null | undefined): boolean {
  if (!datetimeLocal) return false
  const parsed = fromZonedTime(datetimeLocal, TZ)
  return !Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now()
}

export function isFutureUTCDate(isoString: string | null | undefined): boolean {
  if (!isoString) return false
  const parsed = new Date(isoString)
  return !Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now()
}
