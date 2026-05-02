import type {
  CapturePreview,
  CaptureRequestPayload,
  CapturedFrom,
  CaptureDestinationType,
  EngagementPostType,
  EngagementSessionSummary,
  ExtensionBootstrap,
  ExtensionConfig,
  ExtensionFeatures,
  ExtensionSession,
  ExtensionUserSummary,
  ImportedPostStatusCandidate,
  LinkedInConnectionStatus,
} from "./types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function expectRecord(value: unknown, label: string): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new Error(`${label} invalido.`);
  }
  return value;
}

function expectString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${label} invalido.`);
  }
  return value;
}

function expectNullableString(value: unknown, label: string): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  return expectString(value, label);
}

function expectBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") {
    throw new Error(`${label} invalido.`);
  }
  return value;
}

function expectNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${label} invalido.`);
  }
  return value;
}

function expectStringEnum<T extends string>(
  value: unknown,
  allowed: readonly T[],
  label: string,
): T {
  const normalized = expectString(value, label) as T;
  if (!allowed.includes(normalized)) {
    throw new Error(`${label} invalido.`);
  }
  return normalized;
}

function parseExtensionUserSummary(input: unknown): ExtensionUserSummary {
  const record = expectRecord(input, "user");
  return {
    id: expectString(record.id, "user.id"),
    email: expectString(record.email, "user.email"),
    name: expectNullableString(record.name, "user.name"),
    is_superuser: expectBoolean(record.is_superuser, "user.is_superuser"),
  };
}

function parseLinkedInConnectionStatus(input: unknown): LinkedInConnectionStatus {
  const record = expectRecord(input, "linkedin");
  return {
    connected: expectBoolean(record.connected, "linkedin.connected"),
    display_name: expectNullableString(record.display_name, "linkedin.display_name"),
  };
}

function parseExtensionFeatures(input: unknown): ExtensionFeatures {
  const record = expectRecord(input, "features");
  return {
    capture_reference: expectBoolean(record.capture_reference, "features.capture_reference"),
    capture_engagement: expectBoolean(record.capture_engagement, "features.capture_engagement"),
  };
}

function parseEngagementSessionSummary(input: unknown): EngagementSessionSummary {
  const record = expectRecord(input, "recent_engagement_session");
  return {
    id: expectString(record.id, "engagement_session.id"),
    status: expectString(record.status, "engagement_session.status"),
    scan_source: expectString(record.scan_source, "engagement_session.scan_source"),
    created_at: expectString(record.created_at, "engagement_session.created_at"),
  };
}

function parseEngagementPostType(value: unknown, label: string): EngagementPostType {
  return expectStringEnum(value, ["reference", "icp"], label);
}

function parseCapturedFrom(value: unknown, label: string): CapturedFrom {
  return expectStringEnum(value, ["feed", "post_detail", "unknown"], label);
}

export function parseExtensionConfig(input: unknown): ExtensionConfig {
  const record = expectRecord(input, "config");
  return {
    apiBaseUrl: expectString(record.apiBaseUrl, "config.apiBaseUrl"),
  };
}

export function parseExtensionSession(input: unknown): ExtensionSession {
  const record = expectRecord(input, "session");
  return {
    accessToken: expectString(record.accessToken, "session.accessToken"),
    expiresAt: expectString(record.expiresAt, "session.expiresAt"),
    user: parseExtensionUserSummary(record.user),
  };
}

export function parseExtensionBootstrap(input: unknown): ExtensionBootstrap {
  const record = expectRecord(input, "bootstrap");
  const recentSessions = record.recent_engagement_sessions;
  if (!Array.isArray(recentSessions)) {
    throw new Error("bootstrap.recent_engagement_sessions invalido.");
  }

  return {
    user: parseExtensionUserSummary(record.user),
    linkedin: parseLinkedInConnectionStatus(record.linkedin),
    features: parseExtensionFeatures(record.features),
    recent_engagement_sessions: recentSessions.map(parseEngagementSessionSummary),
  };
}

export function parseCapturePreview(input: unknown): CapturePreview {
  const record = expectRecord(input, "preview");
  return {
    post_url: expectNullableString(record.post_url, "preview.post_url"),
    post_text: expectString(record.post_text, "preview.post_text"),
    author_name: expectNullableString(record.author_name, "preview.author_name"),
    author_title: expectNullableString(record.author_title, "preview.author_title"),
    author_company: expectNullableString(record.author_company, "preview.author_company"),
    author_profile_url: expectNullableString(
      record.author_profile_url,
      "preview.author_profile_url",
    ),
    likes: expectNumber(record.likes, "preview.likes"),
    comments: expectNumber(record.comments, "preview.comments"),
    shares: expectNumber(record.shares, "preview.shares"),
    post_type: parseEngagementPostType(record.post_type, "preview.post_type"),
    captured_from: parseCapturedFrom(record.captured_from, "preview.captured_from"),
    page_url: expectNullableString(record.page_url, "preview.page_url"),
    captured_at: expectString(record.captured_at, "preview.captured_at"),
  };
}

export function parseCapturePreviewArray(input: unknown): CapturePreview[] {
  if (!Array.isArray(input)) {
    throw new Error("selected_previews invalido.");
  }
  return input.map(parseCapturePreview);
}

export function parseCaptureRequestPayload(input: unknown): CaptureRequestPayload {
  const record = expectRecord(input, "capture_payload");
  const destination = expectRecord(record.destination, "capture_payload.destination");
  const post = expectRecord(record.post, "capture_payload.post");
  const clientContext = expectRecord(record.client_context, "capture_payload.client_context");

  return {
    destination: {
      type: expectStringEnum<CaptureDestinationType>(
        destination.type,
        ["reference", "engagement"],
        "capture_payload.destination.type",
      ),
      session_id: expectNullableString(
        destination.session_id,
        "capture_payload.destination.session_id",
      ),
    },
    post: {
      post_url: expectNullableString(post.post_url, "capture_payload.post.post_url"),
      post_text: expectString(post.post_text, "capture_payload.post.post_text"),
      author_name: expectNullableString(post.author_name, "capture_payload.post.author_name"),
      author_title: expectNullableString(post.author_title, "capture_payload.post.author_title"),
      author_company: expectNullableString(
        post.author_company,
        "capture_payload.post.author_company",
      ),
      author_profile_url: expectNullableString(
        post.author_profile_url,
        "capture_payload.post.author_profile_url",
      ),
      likes: expectNumber(post.likes, "capture_payload.post.likes"),
      comments: expectNumber(post.comments, "capture_payload.post.comments"),
      shares: expectNumber(post.shares, "capture_payload.post.shares"),
      post_type: parseEngagementPostType(post.post_type, "capture_payload.post.post_type"),
    },
    client_context: {
      captured_from: parseCapturedFrom(
        clientContext.captured_from,
        "capture_payload.client_context.captured_from",
      ),
      page_url: expectNullableString(clientContext.page_url, "capture_payload.client_context.page_url"),
      captured_at: expectString(clientContext.captured_at, "capture_payload.client_context.captured_at"),
      extension_version: expectString(
        clientContext.extension_version,
        "capture_payload.client_context.extension_version",
      ),
    },
  };
}

export function parseImportedPostStatusCandidates(
  input: unknown,
): ImportedPostStatusCandidate[] {
  if (!Array.isArray(input)) {
    throw new Error("candidates invalido.");
  }

  return input.map((candidate) => {
    const record = expectRecord(candidate, "candidate");
    return {
      candidate_key: expectString(record.candidate_key, "candidate.candidate_key"),
      post_url: expectNullableString(record.post_url, "candidate.post_url"),
      canonical_post_url: expectNullableString(
        record.canonical_post_url,
        "candidate.canonical_post_url",
      ),
      post_text: expectString(record.post_text, "candidate.post_text"),
      author_name: expectNullableString(record.author_name, "candidate.author_name"),
    };
  });
}