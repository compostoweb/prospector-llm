import { notFound } from "next/navigation"
import { ArrowRight, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { getPublicLandingPage } from "@/lib/content-inbound/public-api"

interface Props {
  params: Promise<{ slug: string }>
}

export default async function LeadMagnetThankYouPage({ params }: Props) {
  const { slug } = await params
  const page = await getPublicLandingPage(slug)

  if (!page) {
    notFound()
  }

  const calculatorHref = `/lm/calculadora?lead_magnet_id=${page.lead_magnet_id}`

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
          <p className="text-base leading-7 text-(--text-secondary)">
            Você entrou na sequência de nutrição e pode seguir com a próxima ação abaixo.
          </p>
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
                Baixar material
                <Download className="h-4 w-4" />
              </a>
            </Button>
          ) : (
            <div className="rounded-2xl border border-(--border-subtle) bg-(--bg-overlay) p-4 text-sm text-(--text-secondary)">
              O material será entregue nos próximos contatos de nutrição configurados para este
              fluxo.
            </div>
          )}

          <Button asChild variant="outline" className="justify-between">
            <a href={page.public_url}>
              Voltar para a pagina
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
