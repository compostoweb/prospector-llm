import PublicCalculator from "@/components/content/inbound/public-calculator"

interface Props {
  searchParams: Promise<{ lead_magnet_id?: string }>
}

export default async function CalculatorPage({ searchParams }: Props) {
  const { lead_magnet_id } = await searchParams
  return <PublicCalculator {...(lead_magnet_id ? { leadMagnetId: lead_magnet_id } : {})} />
}
