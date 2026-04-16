import { ArrowRight, Download, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { LandingPagePublicData } from "@/lib/content-inbound/types"

interface Props {
  page: LandingPagePublicData
}

const SUBTITLE: Record<string, string> = {
  calculator: "Use o botão abaixo para abrir a calculadora.",
  pdf: "Use o botão abaixo para baixar o seu material.",
  link: "Use o botão abaixo para acessar o material.",
  email_sequence: "Em breve você receberá os e-mails no endereço informado.",
}

export default function LandingThankYouPage({ page }: Props) {
  const calculatorHref = `/lm/calculadora?lead_magnet_id=${page.lead_magnet_id}`
  const subtitle = SUBTITLE[page.lead_magnet_type] ?? "Em instantes você receberá seu material."
  const hasAction = page.lead_magnet_type === "calculator" || !!page.file_url

  return (
    <div className="min-h-screen bg-(--bg-page) px-6 py-10 text-(--text-primary)">
      <div className="mx-auto flex max-w-3xl flex-col gap-6 rounded-[28px] border border-(--border-default) bg-(--bg-surface) p-8 shadow-(--shadow-lg)">
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-(--text-tertiary)">
            Material liberado
          </p>
          <h1 className="text-4xl font-semibold leading-tight">
            Tudo certo. Seu acesso já está pronto.
          </h1>
          <p className="text-base leading-7 text-(--text-secondary)">{subtitle}</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {page.lead_magnet_type === "calculator" ? (
            <Button asChild className="justify-between">
              <a href={calculatorHref}>
                Abrir calculadora
                <ArrowRight className="h-4 w-4" />
              </a>
            </Button>
          ) : page.file_url ? (
            <Button asChild className="justify-between">
              <a href={page.file_url} target="_blank" rel="noreferrer">
                {page.lead_magnet_type === "link" ? (
                  <>
                    Acessar material
                    <ExternalLink className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    Baixar material
                    <Download className="h-4 w-4" />
                  </>
                )}
              </a>
            </Button>
          ) : null}

          <Button
            asChild
            variant="outline"
            className={["justify-between", !hasAction ? "md:col-span-2" : ""].join(" ")}
          >
            <a href="https://compostoweb.com.br" target="_blank" rel="noopener noreferrer">
              Ir para o site
              <ArrowRight className="h-4 w-4" />
            </a>
          </Button>
        </div>

        <div className="rounded-2xl bg-(--accent-subtle) p-5 text-sm leading-6 text-(--accent-subtle-fg)">
          Se fizer sentido, o próximo passo natural é comparar esse diagnóstico com o processo atual
          do seu time para decidir onde a automação realmente gera retorno.
        </div>
      </div>
    </div>
  )
}
