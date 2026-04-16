import { notFound } from "next/navigation"
import LandingThankYouPage from "@/components/content/inbound/landing-thankyou-page"
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

  return <LandingThankYouPage page={page} />
}
