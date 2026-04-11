// lib/content-engagement/types.ts
// Tipos para o LinkedIn Engagement Scanner (Content Hub)

export type SessionStatus = "running" | "completed" | "partial" | "failed"
export type EngagementPostType = "reference" | "icp"
export type CommentStatus = "pending" | "selected" | "posted" | "discarded"
export type HookType =
  | "loop_open"
  | "contrarian"
  | "identification"
  | "shortcut"
  | "benefit"
  | "data"
export type PostPillar = "authority" | "case" | "vision"
export type ScanSource = "linkedin_api" | "apify" | "manual"

export interface EngagementSessionEvent {
  id: string
  session_id: string
  event_type: string
  payload: Record<string, unknown> | null
  created_at: string
}

export interface GoogleDiscoveryQuery {
  id: string
  provider: string
  query_text: string
  criteria: Record<string, unknown> | null
  imported_session_id: string | null
  created_at: string
}

export interface EngagementComment {
  id: string
  engagement_post_id: string
  session_id: string
  comment_text: string
  variation: 1 | 2
  status: CommentStatus
  posted_at: string | null
  created_at: string
  updated_at: string
}

export interface EngagementPost {
  id: string
  session_id: string
  post_type: EngagementPostType
  source: string
  merged_sources: string[] | null
  merge_count: number
  author_name: string | null
  author_title: string | null
  author_company: string | null
  author_linkedin_urn: string | null
  author_profile_url: string | null
  post_url: string | null
  canonical_post_url: string | null
  dedup_key: string | null
  post_text: string
  post_published_at: string | null
  likes: number
  comments: number
  shares: number
  engagement_score: number | null
  hook_type: HookType | null
  pillar: PostPillar | null
  why_it_performed: string | null
  what_to_replicate: string | null
  is_saved: boolean
  created_at: string
  updated_at: string
  suggested_comments?: EngagementComment[]
}

export interface EngagementSession {
  id: string
  linked_post_id: string | null
  status: SessionStatus
  current_step: number | null
  references_found: number
  icp_posts_found: number
  comments_generated: number
  comments_posted: number
  scan_source: ScanSource
  selected_theme_ids: string[] | null
  selected_theme_titles: string[] | null
  manual_keywords: string[] | null
  effective_keywords: string[] | null
  linked_post_context_keywords: string[] | null
  icp_titles_used: string[] | null
  icp_sectors_used: string[] | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface EngagementSessionDetail extends EngagementSession {
  posts: EngagementPost[]
  events: EngagementSessionEvent[]
}

export interface IcpFilters {
  titles?: string[]
  sectors?: string[]
}

export interface RunScanRequest {
  linked_post_id?: string | null
  keywords?: string[]
  manual_keywords?: string[]
  selected_theme_ids?: string[]
  icp_filters?: IcpFilters
}

export interface RunScanResponse {
  session_id: string
  status: SessionStatus
}

export interface GoogleDiscoveryComposeRequest {
  keywords: string[]
  exact_phrases?: string[]
  titles?: string[]
  sectors?: string[]
  company?: string | null
  linked_post_id?: string | null
  max_queries?: number
}

export interface AddManualEngagementPostRequest {
  source?: "manual" | "google"
  post_url?: string | null
  post_text: string
  author_name?: string | null
  author_title?: string | null
  author_company?: string | null
  author_profile_url?: string | null
  post_type?: EngagementPostType
  likes?: number
  comments?: number
  shares?: number
}

export interface ImportExternalPostsRequest {
  discovery_query_id?: string | null
  posts: AddManualEngagementPostRequest[]
}

export interface ImportExternalPostsResponse {
  session_id: string
  created_count: number
  merged_count: number
  posts: EngagementPost[]
}
