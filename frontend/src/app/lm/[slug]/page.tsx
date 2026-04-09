import { notFound } from "next/navigation"
import LandingPublicPage from "@/components/content/inbound/landing-public-page"
import { getPublicLandingPage } from "@/lib/content-inbound/public-api"

interface Props {
  params: Promise<{ slug: string }>
}

export default async function LeadMagnetLandingPage({ params }: Props) {
  const { slug } = await params
  const page = await getPublicLandingPage(slug)

  if (!page) {
    notFound()
  }

  return <LandingPublicPage page={page} />
}
