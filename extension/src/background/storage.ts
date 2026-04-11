import type {
  CapturePreview,
  ExtensionBootstrap,
  ExtensionConfig,
  ExtensionSession,
} from "../shared/types";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV
    ? "http://localhost:8000"
    : "https://api.prospector.compostoweb.com.br");
const SESSION_KEY = "prospector.session";
const PREVIEW_KEY = "prospector.preview";
const BOOTSTRAP_KEY = "prospector.bootstrap";
const CONFIG_KEY = "prospector.config";

function normalizeApiBaseUrl(value: string | null | undefined): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return DEFAULT_API_BASE_URL;
  }
  return trimmed.replace(/\/+$/, "");
}

type SessionArea = typeof chrome.storage.session | typeof chrome.storage.local;

function getSessionArea(): SessionArea {
  return chrome.storage.session ?? chrome.storage.local;
}

export async function getConfig(): Promise<ExtensionConfig> {
  const result = await chrome.storage.local.get(CONFIG_KEY);
  const config = result[CONFIG_KEY] as ExtensionConfig | undefined;
  return {
    apiBaseUrl: normalizeApiBaseUrl(config?.apiBaseUrl),
  };
}

export async function setConfig(config: ExtensionConfig): Promise<void> {
  await chrome.storage.local.set({
    [CONFIG_KEY]: { apiBaseUrl: normalizeApiBaseUrl(config.apiBaseUrl) },
  });
}

export async function getSession(): Promise<ExtensionSession | null> {
  const result = await getSessionArea().get(SESSION_KEY);
  return (result[SESSION_KEY] as ExtensionSession | undefined) ?? null;
}

export async function setSession(session: ExtensionSession): Promise<void> {
  await getSessionArea().set({ [SESSION_KEY]: session });
}

export async function clearSession(): Promise<void> {
  await getSessionArea().remove(SESSION_KEY);
}

export async function getBootstrap(): Promise<ExtensionBootstrap | null> {
  const result = await getSessionArea().get(BOOTSTRAP_KEY);
  return (result[BOOTSTRAP_KEY] as ExtensionBootstrap | undefined) ?? null;
}

export async function setBootstrap(
  bootstrap: ExtensionBootstrap,
): Promise<void> {
  await getSessionArea().set({ [BOOTSTRAP_KEY]: bootstrap });
}

export async function clearBootstrap(): Promise<void> {
  await getSessionArea().remove(BOOTSTRAP_KEY);
}

export async function getPreview(): Promise<CapturePreview | null> {
  const result = await getSessionArea().get(PREVIEW_KEY);
  return (result[PREVIEW_KEY] as CapturePreview | undefined) ?? null;
}

export async function setPreview(preview: CapturePreview): Promise<void> {
  await getSessionArea().set({ [PREVIEW_KEY]: preview });
}

export async function clearPreview(): Promise<void> {
  await getSessionArea().remove(PREVIEW_KEY);
}
