export type LeadMagnetType = "pdf" | "calculator" | "email_sequence" | "link"
export type LeadMagnetStatus = "draft" | "active" | "paused" | "archived"
export type LandingPageFormFieldKey =
  | "name"
  | "email"
  | "company"
  | "role"
  | "phone"
  | "linkedin_profile_url"
export type LMDistributionType = "comment" | "dm" | "link_bio"
export type LMLeadOrigin =
  | "linkedin_comment"
  | "linkedin_dm"
  | "landing_page"
  | "cold_outreach"
  | "direct"
  | "calculator"
export type LMSendPulseSyncStatus = "pending" | "processing" | "synced" | "failed" | "skipped"
export type LMSequenceStatus = "pending" | "active" | "completed" | "unsubscribed"
export type CalculatorRole = "ceo" | "cfo" | "gerente" | "analista" | "operacional"
export type CalculatorProcessType = "financeiro" | "juridico" | "operacional" | "atendimento" | "rh"
export type CalculatorCompanySegment =
  | "clinicas"
  | "industria"
  | "advocacia"
  | "contabilidade"
  | "varejo"
  | "servicos"
export type CalculatorCompanySize = "pequena" | "media" | "grande"
export type CalculatorProcessAreaSpan = "1" | "2-3" | "4+"
export type ContentGoal = "editorial" | "lead_magnet_launch"

export interface ContentLeadMagnet {
  id: string
  tenant_id: string
  type: LeadMagnetType
  title: string
  description: string | null
  status: LeadMagnetStatus
  file_url: string | null
  cta_text: string | null
  email_subject: string | null
  email_headline: string | null
  email_body_text: string | null
  email_cta_label: string | null
  sendpulse_list_id: string | null
  linked_calculator_id: string | null
  total_leads_captured: number
  total_downloads: number
  conversion_rate: number | null
  created_at: string
  updated_at: string
}

export interface ContentLeadMagnetCreateInput {
  type: LeadMagnetType
  title: string
  description?: string | null
  status?: LeadMagnetStatus
  file_url?: string | null
  cta_text?: string | null
  email_subject?: string | null
  email_headline?: string | null
  email_body_text?: string | null
  email_cta_label?: string | null
  sendpulse_list_id?: string | null
  linked_calculator_id?: string | null
}

export interface ContentLeadMagnetUpdateInput {
  type?: LeadMagnetType
  title?: string
  description?: string | null
  file_url?: string | null
  cta_text?: string | null
  email_subject?: string | null
  email_headline?: string | null
  email_body_text?: string | null
  email_cta_label?: string | null
  sendpulse_list_id?: string | null
  linked_calculator_id?: string | null
}

export interface ContentLandingPage {
  id: string
  tenant_id: string
  lead_magnet_id: string
  slug: string
  title: string
  subtitle: string | null
  hero_image_url: string | null
  benefits: string[]
  social_proof_count: number
  author_bio: string | null
  author_photo_url: string | null
  meta_title: string | null
  meta_description: string | null
  publisher_name: string | null
  features: Array<{ title: string; description: string }> | null
  expected_result: string | null
  badge_text: string | null
  form_fields?: LandingPageFormField[] | null
  published: boolean
  total_views: number
  total_submissions: number
  conversion_rate: number | null
  created_at: string
  updated_at: string
}

export interface ContentLandingPageUpsertInput {
  slug: string
  title: string
  subtitle?: string | null
  hero_image_url?: string | null
  benefits?: string[]
  social_proof_count?: number
  author_bio?: string | null
  author_photo_url?: string | null
  meta_title?: string | null
  meta_description?: string | null
  publisher_name?: string | null
  features?: Array<{ title: string; description: string }> | null
  expected_result?: string | null
  badge_text?: string | null
  form_fields?: LandingPageFormField[] | null
  published?: boolean
}

export interface LandingPageFormField {
  key: LandingPageFormFieldKey
  required: boolean
}

export interface ContentLMLead {
  id: string
  tenant_id: string
  lead_magnet_id: string
  lm_post_id: string | null
  name: string
  email: string
  linkedin_profile_url: string | null
  company: string | null
  role: string | null
  phone: string | null
  origin: LMLeadOrigin
  capture_metadata: Record<string, unknown> | null
  sendpulse_list_id: string | null
  sendpulse_subscriber_id: string | null
  sendpulse_sync_status: LMSendPulseSyncStatus
  sendpulse_last_synced_at: string | null
  sendpulse_last_error: string | null
  sequence_status: LMSequenceStatus
  sequence_completed: boolean
  converted_via_email: boolean
  converted_to_lead: boolean
  lead_id: string | null
  downloaded_at: string | null
  created_at: string
  updated_at: string
}

export interface LeadMagnetMetrics {
  lead_magnet_id: string
  total_leads_captured: number
  total_synced_to_sendpulse: number
  total_sendpulse_pending: number
  total_sendpulse_failed: number
  total_sendpulse_skipped: number
  total_sequence_completed: number
  total_converted_via_email: number
  total_unsubscribed: number
  total_opens: number
  total_clicks: number
  landing_page_views: number
  landing_page_submissions: number
  landing_page_conversion_rate: number | null
  qualified_conversion_rate: number | null
}

export interface SendPulseRetryResult {
  queued: number
  skipped: number
}

export interface LandingPagePublicData {
  id: string
  lead_magnet_id: string
  lead_magnet_type: LeadMagnetType
  lead_magnet_title: string
  lead_magnet_description: string | null
  file_url: string | null
  cta_text: string | null
  slug: string
  title: string
  subtitle: string | null
  hero_image_url: string | null
  benefits: string[]
  social_proof_count: number
  author_bio: string | null
  author_photo_url: string | null
  meta_title: string | null
  meta_description: string | null
  publisher_name: string | null
  features: Array<{ title: string; description: string }> | null
  expected_result: string | null
  badge_text: string | null
  form_fields?: LandingPageFormField[] | null
  public_url: string
}

export interface LandingPagePublicCaptureInput {
  name: string
  email: string
  company?: string | null
  role?: string | null
  phone?: string | null
  linkedin_profile_url?: string | null
  session_id?: string | null
}

export interface LandingPagePublicCaptureResult {
  lm_lead_id: string
  sendpulse_sync_status: LMSendPulseSyncStatus
}

export interface InvestmentRange {
  min: number
  max: number
}

export interface CalculatorConfig {
  role_hourly_costs: Record<CalculatorRole, number>
  process_investment_ranges: Record<CalculatorProcessType, InvestmentRange>
}

export interface CalculatorCalculateInput {
  lead_magnet_id?: string | null
  pessoas: number
  horas_semana: number
  custo_hora?: number | null
  cargo: CalculatorRole
  retrabalho_pct: number
  tipo_processo: CalculatorProcessType
  company_segment?: CalculatorCompanySegment | null
  company_size?: CalculatorCompanySize | null
  process_area_span?: CalculatorProcessAreaSpan | null
  session_id?: string | null
}

export interface CalculatorCalculateResult {
  result_id: string
  custo_hora_sugerido: number
  custo_mensal: number
  custo_retrabalho: number
  custo_total_mensal: number
  custo_anual: number
  investimento_estimado_min: number
  investimento_estimado_max: number
  roi_estimado: number
  payback_meses: number
  mensagem_resultado: string
}

export interface CalculatorConvertInput {
  result_id: string
  name: string
  email: string
  company?: string | null
  role?: string | null
  phone?: string | null
  create_prospect?: boolean
}

export interface CalculatorConvertResult {
  result_id: string
  lm_lead_id: string | null
  lead_id: string | null
  sendpulse_sync_status: LMSendPulseSyncStatus | null
  diagnosis_email_sent: boolean
  internal_notification_sent: boolean
}

export interface LeadMagnetPostLinkInput {
  content_post_id?: string | null
  post_type?: "launch" | "relaunch" | "reminder"
  distribution_type?: LMDistributionType
  trigger_word?: string | null
  linkedin_post_urn?: string | null
  published_at?: string | null
}
