import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import {
  cn,
  formatRelativeTime,
  scoreVariant,
  truncate,
  channelLabel,
  intentConfig,
  slugify,
  formatBRL,
} from "@/lib/utils"

// ── cn ────────────────────────────────────────────────────────────────

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("a", "b")).toBe("a b")
  })

  it("deduplicates Tailwind classes — última vence", () => {
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500")
  })

  it("ignora valores falsy", () => {
    expect(cn("a", false, undefined, null, "b")).toBe("a b")
  })

  it("aceita objeto de condicionais", () => {
    expect(cn({ "text-red-500": true, "font-bold": false })).toBe("text-red-500")
  })

  it("retorna string vazia se sem argumentos", () => {
    expect(cn()).toBe("")
  })
})

// ── formatRelativeTime ────────────────────────────────────────────────

describe("formatRelativeTime", () => {
  const NOW = new Date("2024-06-15T12:00:00Z")

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("retorna 'agora' para menos de 60 segundos", () => {
    expect(formatRelativeTime(new Date("2024-06-15T11:59:30Z"))).toBe("agora")
  })

  it("retorna 'há N min' entre 1-59 minutos", () => {
    expect(formatRelativeTime(new Date("2024-06-15T11:57:00Z"))).toBe("há 3 min")
    expect(formatRelativeTime(new Date("2024-06-15T11:01:00Z"))).toBe("há 59 min")
  })

  it("retorna 'há Nh' entre 1-23 horas", () => {
    expect(formatRelativeTime(new Date("2024-06-15T10:00:00Z"))).toBe("há 2h")
  })

  it("retorna 'há N dias' entre 1-6 dias", () => {
    expect(formatRelativeTime(new Date("2024-06-12T12:00:00Z"))).toBe("há 3 dias")
  })

  it("retorna data curta para 7+ dias", () => {
    const result = formatRelativeTime(new Date("2024-06-01T12:00:00Z"))
    // Ex: "1 jun." — deve conter número e texto
    expect(result).toMatch(/\d+/)
    expect(result).not.toBe("agora")
  })

  it("aceita string ISO como argumento", () => {
    expect(formatRelativeTime("2024-06-15T11:59:30Z")).toBe("agora")
  })
})

// ── scoreVariant ──────────────────────────────────────────────────────

describe("scoreVariant", () => {
  it("retorna 'success' para score >= 71", () => {
    expect(scoreVariant(71)).toBe("success")
    expect(scoreVariant(100)).toBe("success")
    expect(scoreVariant(85)).toBe("success")
  })

  it("retorna 'warning' para score 41-70", () => {
    expect(scoreVariant(41)).toBe("warning")
    expect(scoreVariant(70)).toBe("warning")
    expect(scoreVariant(55)).toBe("warning")
  })

  it("retorna 'danger' para score <= 40", () => {
    expect(scoreVariant(0)).toBe("danger")
    expect(scoreVariant(40)).toBe("danger")
    expect(scoreVariant(20)).toBe("danger")
  })
})

// ── truncate ──────────────────────────────────────────────────────────

describe("truncate", () => {
  it("retorna string inalterada se dentro do limite", () => {
    expect(truncate("hello", 10)).toBe("hello")
    expect(truncate("hello", 5)).toBe("hello")
  })

  it("trunca e adiciona reticências se exceder o limite", () => {
    expect(truncate("hello world", 8)).toBe("hello w…")
  })

  it("trunca no limite mínimo", () => {
    expect(truncate("abc", 2)).toBe("a…")
  })
})

// ── channelLabel ──────────────────────────────────────────────────────

describe("channelLabel", () => {
  it("traduz linkedin_connect", () => {
    expect(channelLabel("linkedin_connect")).toBe("LinkedIn Connect")
  })

  it("traduz linkedin_dm", () => {
    expect(channelLabel("linkedin_dm")).toBe("LinkedIn DM")
  })

  it("traduz email", () => {
    expect(channelLabel("email")).toBe("E-mail")
  })

  it("retorna o próprio valor para canal desconhecido", () => {
    expect(channelLabel("whatsapp")).toBe("whatsapp")
  })
})

// ── intentConfig ──────────────────────────────────────────────────────

describe("intentConfig", () => {
  it("interest → success", () => {
    const r = intentConfig("interest")
    expect(r.label).toBe("Interesse")
    expect(r.variant).toBe("success")
  })

  it("objection → warning", () => {
    const r = intentConfig("objection")
    expect(r.label).toBe("Objeção")
    expect(r.variant).toBe("warning")
  })

  it("not_interested → danger", () => {
    const r = intentConfig("not_interested")
    expect(r.label).toBe("Sem interesse")
    expect(r.variant).toBe("danger")
  })

  it("neutral → neutral", () => {
    const r = intentConfig("neutral")
    expect(r.label).toBe("Neutro")
    expect(r.variant).toBe("neutral")
  })

  it("out_of_office → info", () => {
    const r = intentConfig("out_of_office")
    expect(r.label).toBe("Ausente")
    expect(r.variant).toBe("info")
  })

  it("intent desconhecido → fallback neutral", () => {
    const r = intentConfig("unknown_intent")
    expect(r.label).toBe("unknown_intent")
    expect(r.variant).toBe("neutral")
  })
})

// ── slugify ───────────────────────────────────────────────────────────

describe("slugify", () => {
  it("converte para minúsculas e substitui espaços por hífens", () => {
    expect(slugify("Hello World")).toBe("hello-world")
  })

  it("remove acentos via normalização NFD", () => {
    expect(slugify("Cadência Ação")).toBe("cadencia-acao")
  })

  it("remove caracteres especiais", () => {
    expect(slugify("foo@bar!baz")).toBe("foobarbaz")
  })

  it("colapsa múltiplos espaços em um único hífen", () => {
    expect(slugify("foo   bar")).toBe("foo-bar")
  })

  it("remove espaços nas extremidades", () => {
    expect(slugify("  hello  ")).toBe("hello")
  })

  it("retorna string vazia para input vazio", () => {
    expect(slugify("")).toBe("")
  })
})

// ── formatBRL ─────────────────────────────────────────────────────────

describe("formatBRL", () => {
  it("contém símbolo 'R$'", () => {
    expect(formatBRL(100)).toMatch(/R\$/)
  })

  it("formata zero", () => {
    const result = formatBRL(0)
    expect(result).toMatch(/R\$/)
    expect(result).toContain("0")
  })

  it("formata valor com centavos", () => {
    const result = formatBRL(9.99)
    expect(result).toMatch(/R\$/)
    expect(result).toContain("9")
  })

  it("formata valor grande", () => {
    const result = formatBRL(1050)
    expect(result).toMatch(/R\$/)
    // PT-BR usa ponto como separador de milhar: 1.050
    expect(result).toContain("1")
    expect(result).toContain("050")
  })
})
