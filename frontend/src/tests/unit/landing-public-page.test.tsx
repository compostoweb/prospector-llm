/**
 * tests/unit/landing-public-page.test.tsx
 *
 * Testa os 3 templates de LandingPublicPage (pdf, link, email_sequence)
 * e o template de calculadora, verificando texto, estrutura e comportamento
 * em cada layout.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import LandingPublicPage from "@/components/content/inbound/landing-public-page"
import type { LandingPagePublicData } from "@/lib/content-inbound/types"

// ── Mock do env para evitar erro de import ────────────────────────────────

vi.mock("@/env", () => ({
  env: {
    NEXT_PUBLIC_API_URL: "http://localhost:8000",
  },
}))

// ── Factories de page mock ────────────────────────────────────────────────

function makePage(overrides: Partial<LandingPagePublicData> = {}): LandingPagePublicData {
  return {
    id: "lp-1",
    lead_magnet_id: "lm-1",
    lead_magnet_type: "pdf",
    lead_magnet_title: "Guia de Automação",
    lead_magnet_description: "Descrição do guia",
    file_url: "https://cdn.example.com/guia.pdf",
    cta_text: null,
    slug: "guia-automacao",
    title: "Guia Completo de Automação B2B",
    subtitle: "Aprenda a automatizar sem aumentar equipe",
    hero_image_url: null,
    benefits: ["Clareza de diagnóstico", "Aplicação imediata", "Sem teoria solta"],
    social_proof_count: 120,
    author_bio: "Time especializado em B2B complexo.",
    author_photo_url: null,
    meta_title: null,
    meta_description: null,
    publisher_name: null,
    features: null,
    expected_result: null,
    badge_text: null,
    public_url: "https://app.compostoweb.com.br/lm/guia-automacao",
    ...overrides,
  }
}

// ── Template PDF (Full/Rich) ──────────────────────────────────────────────

describe("Template PDF (Full/Rich)", () => {
  it("renderiza título e subtítulo", () => {
    render(<LandingPublicPage page={makePage()} />)
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Guia Completo de Automação B2B",
    )
    expect(screen.getByText("Aprenda a automatizar sem aumentar equipe")).toBeInTheDocument()
  })

  it("renderiza social proof badge", () => {
    render(<LandingPublicPage page={makePage({ social_proof_count: 85 })} />)
    expect(screen.getByText("85+ empresas interessadas")).toBeInTheDocument()
  })

  it("não renderiza badge de social proof quando count = 0", () => {
    render(<LandingPublicPage page={makePage({ social_proof_count: 0 })} />)
    expect(screen.queryByText(/empresas interessadas/)).not.toBeInTheDocument()
  })

  it("renderiza os 3 benefits da lista", () => {
    render(<LandingPublicPage page={makePage()} />)
    expect(screen.getByText("Clareza de diagnóstico")).toBeInTheDocument()
    expect(screen.getByText("Aplicação imediata")).toBeInTheDocument()
    expect(screen.getByText("Sem teoria solta")).toBeInTheDocument()
  })

  it("renderiza autor bio", () => {
    render(<LandingPublicPage page={makePage()} />)
    expect(screen.getByText("Time especializado em B2B complexo.")).toBeInTheDocument()
  })

  it("renderiza formulário com campos obrigatórios", () => {
    render(<LandingPublicPage page={makePage()} />)
    expect(screen.getByPlaceholderText("Seu nome")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Seu melhor e-mail")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Empresa")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Cargo")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("WhatsApp ou telefone")).toBeInTheDocument()
  })

  it("renderiza botão CTA padrão quando cta_text é null", () => {
    render(<LandingPublicPage page={makePage({ cta_text: null })} />)
    expect(screen.getByRole("button", { name: /receber material/i })).toBeInTheDocument()
  })

  it("usa cta_text customizado quando definido", () => {
    render(<LandingPublicPage page={makePage({ cta_text: "Baixar playbook agora" })} />)
    expect(screen.getByRole("button", { name: /baixar playbook agora/i })).toBeInTheDocument()
  })

  it("NÃO renderiza a seção 'Entrar na sequência'", () => {
    render(<LandingPublicPage page={makePage()} />)
    expect(screen.queryByText("Entrar na sequencia")).not.toBeInTheDocument()
  })
})

// ── Template Link (Minimal) ──────────────────────────────────────────────

describe("Template Link (Minimal)", () => {
  const page = makePage({
    lead_magnet_type: "link",
    title: "Planilha de Controle Operacional",
    subtitle: "Uma planilha prática para o seu time.",
    file_url: "https://notion.so/planilha-b2b",
    cta_text: null,
    benefits: ["Item 1", "Item 2"],
    social_proof_count: 0,
  })

  it("renderiza título centralizado", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Planilha de Controle Operacional",
    )
  })

  it("renderiza badge 'Acesso imediato'", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText("Acesso imediato")).toBeInTheDocument()
  })

  it("renderiza label 'Receber por e-mail'", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText(/receber por e-mail/i)).toBeInTheDocument()
  })

  it("renderiza formulário", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByPlaceholderText("Seu nome")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Seu melhor e-mail")).toBeInTheDocument()
  })

  it("renderiza botão CTA com fallback 'Receber material' quando cta_text é null", () => {
    render(<LandingPublicPage page={page} />)
    // sharedForm usa page.cta_text || "Receber material" — 'Acessar agora' é o h2 do card
    expect(screen.getByRole("button", { name: /receber material/i })).toBeInTheDocument()
  })

  it("renderiza benefits quando presentes", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText("Item 1")).toBeInTheDocument()
    expect(screen.getByText("Item 2")).toBeInTheDocument()
  })

  it("NÃO renderiza os cards 'Clareza de diagnóstico' da template Rich", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.queryByText("Clareza de diagnostico")).not.toBeInTheDocument()
  })

  it("não renderiza section de steps de sequência", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.queryByText("O que chega no seu email")).not.toBeInTheDocument()
  })
})

// ── Template Email Sequence (Trust) ──────────────────────────────────────

describe("Template Email Sequence (Trust/Sequence)", () => {
  const page = makePage({
    lead_magnet_type: "email_sequence",
    title: "Sequência B2B: Do Lead a Cliente",
    subtitle: "Três emails com o que realmente importa.",
    file_url: null,
    cta_text: "Quero entrar",
    social_proof_count: 200,
  })

  it("renderiza título", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Sequência B2B: Do Lead a Cliente",
    )
  })

  it("renderiza badge 'Sequencia de emails'", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText(/sequencia de emails/i)).toBeInTheDocument()
  })

  it("renderiza badge de social proof com 200+", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText("200+ empresas inscritas")).toBeInTheDocument()
  })

  it("renderiza os 3 steps da sequência (01, 02, 03)", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText("01")).toBeInTheDocument()
    expect(screen.getByText("02")).toBeInTheDocument()
    expect(screen.getByText("03")).toBeInTheDocument()
    expect(screen.getByText("Boas-vindas")).toBeInTheDocument()
    expect(screen.getByText("Conteudo principal")).toBeInTheDocument()
    expect(screen.getByText("Proximos passos")).toBeInTheDocument()
  })

  it("renderiza label 'O que chega no seu email'", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText("O que chega no seu email")).toBeInTheDocument()
  })

  it("renderiza botão CTA com cta_text customizado", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByRole("button", { name: /quero entrar/i })).toBeInTheDocument()
  })

  it("renderiza badge da Composto Web com author_bio", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText("Composto Web")).toBeInTheDocument()
    expect(screen.getByText("Time especializado em B2B complexo.")).toBeInTheDocument()
  })

  it("NÃO renderiza botão 'Abrir calculadora'", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.queryByRole("link", { name: /abrir calculadora/i })).not.toBeInTheDocument()
  })
})

// ── Template Calculator ──────────────────────────────────────────────────

describe("Template Calculator (Full/Rich com CTA especial)", () => {
  const page = makePage({
    lead_magnet_type: "calculator",
    title: "Calculadora de ROI da Automação",
    subtitle: null,
    file_url: null,
  })

  it("renderiza botão 'Abrir calculadora' em vez de formulário", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByRole("link", { name: /abrir calculadora/i })).toBeInTheDocument()
  })

  it("NÃO renderiza campo de nome (sem formulário)", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.queryByPlaceholderText("Seu nome")).not.toBeInTheDocument()
  })

  it("renderiza label 'Acesso interativo'", () => {
    render(<LandingPublicPage page={page} />)
    expect(screen.getByText("Acesso interativo")).toBeInTheDocument()
  })
})

// ── Comportamento do formulário compartilhado ────────────────────────────

describe("Formulário compartilhado — preenchimento e envio", () => {
  it("submissão com fetch bem-sucedido redireciona para /obrigado", async () => {
    const assignMock = vi.fn()
    Object.defineProperty(window, "location", {
      value: { assign: assignMock },
      writable: true,
    })

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ lm_lead_id: "uuid-1", sendpulse_sync_status: "pending" }),
      }),
    )

    render(<LandingPublicPage page={makePage()} />)

    fireEvent.change(screen.getByPlaceholderText("Seu nome"), {
      target: { value: "João Silva" },
    })
    fireEvent.change(screen.getByPlaceholderText("Seu melhor e-mail"), {
      target: { value: "joao@empresa.com.br" },
    })
    fireEvent.submit(screen.getByPlaceholderText("Seu nome").closest("form") as HTMLFormElement)

    await vi.waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith("/lm/guia-automacao/obrigado")
    })

    vi.unstubAllGlobals()
  })

  it("submissão com erro da API exibe mensagem de erro", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Lead magnet inativo" }),
      }),
    )

    render(<LandingPublicPage page={makePage()} />)

    fireEvent.submit(screen.getByPlaceholderText("Seu nome").closest("form") as HTMLFormElement)

    await vi.waitFor(() => {
      expect(screen.getByText("Lead magnet inativo")).toBeInTheDocument()
    })

    vi.unstubAllGlobals()
  })

  it("botão fica desabilitado durante o envio", async () => {
    let resolveRequest!: (value: unknown) => void
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValueOnce(
        new Promise((resolve) => {
          resolveRequest = resolve
        }),
      ),
    )

    render(<LandingPublicPage page={makePage()} />)
    const button = screen.getByRole("button", { name: /receber material/i })

    fireEvent.submit(button.closest("form") as HTMLFormElement)

    await vi.waitFor(() => {
      expect(button).toBeDisabled()
    })

    resolveRequest({ ok: true, json: async () => ({}) })
    vi.unstubAllGlobals()
  })
})
