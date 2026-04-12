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
const SELECTED_PREVIEWS_KEY = "prospector.selectedPreviews";
const BOOTSTRAP_KEY = "prospector.bootstrap";
const CONFIG_KEY = "prospector.config";

export const EXTENSION_STORAGE_KEYS = {
  session: SESSION_KEY,
  preview: PREVIEW_KEY,
  selectedPreviews: SELECTED_PREVIEWS_KEY,
  bootstrap: BOOTSTRAP_KEY,
  config: CONFIG_KEY,
} as const;

function normalizeApiBaseUrl(value: string | null | undefined): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return DEFAULT_API_BASE_URL;
  }
  return trimmed.replace(/\/+$/, "");
}

type StorageArea = chrome.storage.StorageArea;

function getPersistentStorageArea(): StorageArea {
  return chrome.storage.local;
}

function getLegacySessionArea(): StorageArea | null {
  return chrome.storage.session ?? null;
}

async function getStoredValue<T>(key: string): Promise<T | null> {
  const persistentResult = await getPersistentStorageArea().get(key);
  const persistentValue = persistentResult[key] as T | undefined;
  if (persistentValue !== undefined) {
    return persistentValue;
  }

  const legacySessionArea = getLegacySessionArea();
  if (!legacySessionArea) {
    return null;
  }

  const legacyResult = await legacySessionArea.get(key);
  const legacyValue = legacyResult[key] as T | undefined;
  if (legacyValue === undefined) {
    return null;
  }

  await getPersistentStorageArea().set({ [key]: legacyValue });
  await legacySessionArea.remove(key);
  return legacyValue;
}

async function setStoredValue<T>(key: string, value: T): Promise<void> {
  await getPersistentStorageArea().set({ [key]: value });
}

async function removeStoredValue(key: string): Promise<void> {
  await getPersistentStorageArea().remove(key);

  const legacySessionArea = getLegacySessionArea();
  if (legacySessionArea) {
    await legacySessionArea.remove(key);
  }
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
  return getStoredValue<ExtensionSession>(SESSION_KEY);
}

export async function setSession(session: ExtensionSession): Promise<void> {
  await setStoredValue(SESSION_KEY, session);
}

export async function clearSession(): Promise<void> {
  await removeStoredValue(SESSION_KEY);
}

export async function getBootstrap(): Promise<ExtensionBootstrap | null> {
  return getStoredValue<ExtensionBootstrap>(BOOTSTRAP_KEY);
}

export async function setBootstrap(
  bootstrap: ExtensionBootstrap,
): Promise<void> {
  await setStoredValue(BOOTSTRAP_KEY, bootstrap);
}

export async function clearBootstrap(): Promise<void> {
  await removeStoredValue(BOOTSTRAP_KEY);
}

export async function getPreview(): Promise<CapturePreview | null> {
  return getStoredValue<CapturePreview>(PREVIEW_KEY);
}

export async function setPreview(preview: CapturePreview): Promise<void> {
  await setStoredValue(PREVIEW_KEY, preview);
}

export async function clearPreview(): Promise<void> {
  await removeStoredValue(PREVIEW_KEY);
}

export async function getSelectedPreviews(): Promise<CapturePreview[]> {
  return (await getStoredValue<CapturePreview[]>(SELECTED_PREVIEWS_KEY)) ?? [];
}

export async function setSelectedPreviews(
  previews: CapturePreview[],
): Promise<void> {
  await setStoredValue(SELECTED_PREVIEWS_KEY, previews);
}

export async function clearSelectedPreviews(): Promise<void> {
  await removeStoredValue(SELECTED_PREVIEWS_KEY);
}
