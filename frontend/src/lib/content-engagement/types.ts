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
  author_name: string | null
  author_title: string | null
  author_company: string | null
  author_linkedin_urn: string | null
  author_profile_url: string | null
  post_url: string | null
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
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface EngagementSessionDetail extends EngagementSession {
  posts: EngagementPost[]
}

export interface IcpFilters {
  titles?: string[]
  sectors?: string[]
}

export interface RunScanRequest {
  linked_post_id?: string | null
  keywords?: string[]
  icp_filters?: IcpFilters
}

export interface RunScanResponse {
  session_id: string
  status: SessionStatus
}
