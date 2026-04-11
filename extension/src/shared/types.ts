export type CaptureDestinationType = "reference" | "engagement";
export type CapturedFrom = "feed" | "post_detail" | "unknown";
export type CaptureResult = "created" | "merged";
export type EngagementPostType = "reference" | "icp";

export interface ExtensionUserSummary {
  id: string;
  email: string;
  name: string | null;
  is_superuser: boolean;
}

export interface LinkedInConnectionStatus {
  connected: boolean;
  display_name: string | null;
}

export interface ExtensionFeatures {
  capture_reference: boolean;
  capture_engagement: boolean;
}

export interface EngagementSessionSummary {
  id: string;
  status: string;
  scan_source: string;
  created_at: string;
}

export interface ExtensionBootstrap {
  user: ExtensionUserSummary;
  linkedin: LinkedInConnectionStatus;
  features: ExtensionFeatures;
  recent_engagement_sessions: EngagementSessionSummary[];
}

export interface ExtensionSession {
  accessToken: string;
  expiresAt: string;
  user: ExtensionUserSummary;
}

export interface CapturePreview {
  post_url: string | null;
  post_text: string;
  author_name: string | null;
  author_title: string | null;
  author_company: string | null;
  author_profile_url: string | null;
  likes: number;
  comments: number;
  shares: number;
  post_type: EngagementPostType;
  captured_from: CapturedFrom;
  page_url: string | null;
  captured_at: string;
}

export interface ActiveTabPostCandidateDiagnostic {
  tag_name: string;
  text_excerpt: string | null;
  has_post_url: boolean;
  has_author_name: boolean;
  has_author_title: boolean;
  has_metrics: boolean;
  discard_reason: string | null;
}

export interface ActiveTabPostScanDiagnostic {
  page_url: string | null;
  is_linkedin: boolean;
  captured_from: CapturedFrom;
  static_container_count: number;
  action_anchor_count: number;
  action_bar_count: number;
  candidate_container_count: number;
  accepted_post_count: number;
  discard_reason_counts: Record<string, number>;
  sample_candidates: ActiveTabPostCandidateDiagnostic[];
  error_message: string | null;
}

export interface ActiveTabPostScanResult {
  posts: CapturePreview[];
  diagnostic: ActiveTabPostScanDiagnostic;
}

export interface CaptureRequestPayload {
  destination: {
    type: CaptureDestinationType;
    session_id: string | null;
  };
  post: {
    post_url: string | null;
    post_text: string;
    author_name: string | null;
    author_title: string | null;
    author_company: string | null;
    author_profile_url: string | null;
    likes: number;
    comments: number;
    shares: number;
    post_type: EngagementPostType;
  };
  client_context: {
    captured_from: CapturedFrom;
    page_url: string | null;
    captured_at: string;
    extension_version: string;
  };
}

export interface CaptureResponse {
  destination: CaptureDestinationType;
  result: CaptureResult;
  dedup_key: string | null;
  reference_id?: string | null;
  session_id?: string | null;
  engagement_post_id?: string | null;
}

export interface ImportedPostStatusCandidate {
  candidate_key: string;
  post_url: string | null;
  canonical_post_url?: string | null;
  post_text: string;
  author_name: string | null;
}

export interface ImportedPostStatusMatch {
  candidate_key: string;
  imported: boolean;
  destination_type?: CaptureDestinationType | null;
  linked_object_type?: string | null;
  linked_object_id?: string | null;
}

export interface ImportedPostStatusResponse {
  matches: ImportedPostStatusMatch[];
}

export interface ExtensionConfig {
  apiBaseUrl: string;
}

export interface ExtensionState {
  session: ExtensionSession | null;
  bootstrap: ExtensionBootstrap | null;
  preview: CapturePreview | null;
  config: ExtensionConfig;
}
