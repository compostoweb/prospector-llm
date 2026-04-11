import type {
  CapturePreview,
  CaptureRequestPayload,
  CaptureDestinationType,
} from "./types";

export function normalizeWhitespace(
  value: string | null | undefined,
): string | null {
  if (!value) return null;
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 0 ? normalized : null;
}

export function clampMetric(value: number | null | undefined): number {
  if (!value || Number.isNaN(value)) return 0;
  return Math.max(0, Math.floor(value));
}

export function normalizePreview(preview: CapturePreview): CapturePreview {
  return {
    ...preview,
    post_url: normalizeWhitespace(preview.post_url),
    post_text: normalizeWhitespace(preview.post_text) ?? "",
    author_name: normalizeWhitespace(preview.author_name),
    author_title: normalizeWhitespace(preview.author_title),
    author_company: normalizeWhitespace(preview.author_company),
    author_profile_url: normalizeWhitespace(preview.author_profile_url),
    likes: clampMetric(preview.likes),
    comments: clampMetric(preview.comments),
    shares: clampMetric(preview.shares),
  };
}

export function buildPreviewKey(preview: CapturePreview): string {
  const normalized = normalizePreview(preview);
  return [
    normalized.post_url ?? "",
    normalized.author_name ?? "",
    normalized.post_text.slice(0, 160),
    normalized.captured_from,
  ].join("::");
}

export function buildCaptureRequest(
  preview: CapturePreview,
  destinationType: CaptureDestinationType,
  sessionId: string | null,
  extensionVersion: string,
): CaptureRequestPayload {
  const normalized = normalizePreview(preview);
  return {
    destination: {
      type: destinationType,
      session_id: destinationType === "engagement" ? sessionId : null,
    },
    post: {
      post_url: normalized.post_url,
      post_text: normalized.post_text,
      author_name: normalized.author_name,
      author_title: normalized.author_title,
      author_company: normalized.author_company,
      author_profile_url: normalized.author_profile_url,
      likes: normalized.likes,
      comments: normalized.comments,
      shares: normalized.shares,
      post_type:
        destinationType === "reference" ? "reference" : normalized.post_type,
    },
    client_context: {
      captured_from: normalized.captured_from,
      page_url: normalized.page_url,
      captured_at: normalized.captured_at,
      extension_version: extensionVersion,
    },
  };
}
