import type {
  CaptureRequestPayload,
  CaptureResponse,
  EngagementSessionSummary,
  ExtensionBootstrap,
  ExtensionConfig,
  ExtensionSession,
  ImportedPostStatusCandidate,
  ImportedPostStatusResponse,
} from "../shared/types";
import {
  parseCaptureRequestPayload,
  parseExtensionBootstrap,
  parseExtensionSession,
  parseImportedPostStatusCandidates,
} from "../shared/validation";

function buildHeaders(
  session: ExtensionSession | null,
  extensionVersion: string,
): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    "X-Client-Platform": "chrome_extension",
    "X-Extension-Id": chrome.runtime.id,
    "X-Extension-Version": extensionVersion,
  };
  if (session) {
    headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return headers;
}

async function parseJsonOrThrow<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) errorMessage = payload.detail;
    } catch {
      // ignore invalid json
    }
    throw new Error(errorMessage);
  }
  return (await response.json()) as T;
}

export async function startExtensionSession(
  config: ExtensionConfig,
  extensionVersion: string,
) {
  const response = await fetch(
    `${config.apiBaseUrl}/auth/extension/session/start`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        extension_id: chrome.runtime.id,
        extension_version: extensionVersion,
        browser: "chrome",
      }),
    },
  );

  return parseJsonOrThrow<{
    auth_session_id: string;
    authorization_url: string;
    expires_in: number;
  }>(response);
}

export async function exchangeGrant(
  config: ExtensionConfig,
  grantCode: string,
): Promise<ExtensionSession> {
  const response = await fetch(
    `${config.apiBaseUrl}/auth/extension/session/exchange`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        grant_code: grantCode,
        extension_id: chrome.runtime.id,
      }),
    },
  );
  const payload = await parseJsonOrThrow<{
    access_token: string;
    expires_at: string;
    user: ExtensionSession["user"];
  }>(response);

  return parseExtensionSession({
    accessToken: payload.access_token,
    expiresAt: payload.expires_at,
    user: payload.user,
  });
}

export async function fetchBootstrap(
  config: ExtensionConfig,
  session: ExtensionSession,
  extensionVersion: string,
): Promise<ExtensionBootstrap> {
  const response = await fetch(
    `${config.apiBaseUrl}/api/content/extension/bootstrap`,
    {
      headers: buildHeaders(session, extensionVersion),
    },
  );
  return parseExtensionBootstrap(await parseJsonOrThrow<ExtensionBootstrap>(response));
}

export async function importLinkedInPost(
  config: ExtensionConfig,
  session: ExtensionSession,
  extensionVersion: string,
  payload: CaptureRequestPayload,
): Promise<CaptureResponse> {
  const validatedPayload = parseCaptureRequestPayload(payload);
  const response = await fetch(
    `${config.apiBaseUrl}/api/content/extension/capture/linkedin-post`,
    {
      method: "POST",
      headers: buildHeaders(session, extensionVersion),
      body: JSON.stringify(validatedPayload),
    },
  );
  return parseJsonOrThrow<CaptureResponse>(response);
}

export async function createEngagementSession(
  config: ExtensionConfig,
  session: ExtensionSession,
  extensionVersion: string,
): Promise<EngagementSessionSummary> {
  const response = await fetch(
    `${config.apiBaseUrl}/api/content/extension/engagement/sessions`,
    {
      method: "POST",
      headers: buildHeaders(session, extensionVersion),
    },
  );
  return parseJsonOrThrow<EngagementSessionSummary>(response);
}

export async function resolveImportedPosts(
  config: ExtensionConfig,
  session: ExtensionSession,
  extensionVersion: string,
  candidates: ImportedPostStatusCandidate[],
): Promise<ImportedPostStatusResponse> {
  const validatedCandidates = parseImportedPostStatusCandidates(candidates);
  const response = await fetch(
    `${config.apiBaseUrl}/api/content/extension/capture/statuses`,
    {
      method: "POST",
      headers: buildHeaders(session, extensionVersion),
      body: JSON.stringify({ candidates: validatedCandidates }),
    },
  );
  return parseJsonOrThrow<ImportedPostStatusResponse>(response);
}
