import type {
  CapturePreview,
  ExtensionBootstrap,
  ExtensionConfig,
  ExtensionSession,
} from "../shared/types";
import {
  parseCapturePreview,
  parseCapturePreviewArray,
  parseExtensionBootstrap,
  parseExtensionConfig,
  parseExtensionSession,
} from "../shared/validation";

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
const VOLATILE_STORAGE_KEYS = new Set([
  SESSION_KEY,
  PREVIEW_KEY,
  SELECTED_PREVIEWS_KEY,
  BOOTSTRAP_KEY,
]);

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

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new Error("API base URL invalida.");
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("API base URL deve usar http ou https.");
  }

  const isLocalHost = ["localhost", "127.0.0.1"].includes(parsed.hostname);
  const isTrustedProdHost =
    parsed.hostname === "api.prospector.compostoweb.com.br" ||
    parsed.hostname.endsWith(".compostoweb.com.br");

  if (import.meta.env.DEV) {
    if (!isLocalHost && !isTrustedProdHost) {
      throw new Error("API base URL fora da allowlist da extensao.");
    }
  } else {
    if (parsed.protocol !== "https:" || !isTrustedProdHost) {
      throw new Error("Em producao, a API da extensao deve usar host HTTPS autorizado.");
    }
  }

  parsed.pathname = "";
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString().replace(/\/+$/, "");
}

type StorageArea = chrome.storage.StorageArea;

function getPersistentStorageArea(): StorageArea {
  return chrome.storage.local;
}

function getVolatileStorageArea(): StorageArea | null {
  return chrome.storage.session ?? null;
}

function shouldUseVolatileStorage(key: string): boolean {
  return VOLATILE_STORAGE_KEYS.has(key);
}

async function getStoredValue<T>(
  key: string,
  parser: (value: unknown) => T,
): Promise<T | null> {
  const volatileArea = shouldUseVolatileStorage(key) ? getVolatileStorageArea() : null;
  if (volatileArea) {
    const volatileResult = await volatileArea.get(key);
    const volatileValue = volatileResult[key];
    if (volatileValue !== undefined) {
      try {
        return parser(volatileValue);
      } catch {
        await volatileArea.remove(key);
      }
    }
  }

  const persistentArea = getPersistentStorageArea();
  const persistentResult = await persistentArea.get(key);
  const persistentValue = persistentResult[key];
  if (persistentValue === undefined) {
    return null;
  }

  try {
    const parsed = parser(persistentValue);
    if (volatileArea) {
      await volatileArea.set({ [key]: parsed });
      await persistentArea.remove(key);
    }
    return parsed;
  } catch {
    await persistentArea.remove(key);
    return null;
  }
}

async function setStoredValue<T>(key: string, value: T): Promise<void> {
  const volatileArea = shouldUseVolatileStorage(key) ? getVolatileStorageArea() : null;
  if (volatileArea) {
    await volatileArea.set({ [key]: value });
    await getPersistentStorageArea().remove(key);
    return;
  }

  await getPersistentStorageArea().set({ [key]: value });
}

async function removeStoredValue(key: string): Promise<void> {
  await getPersistentStorageArea().remove(key);

  const volatileArea = getVolatileStorageArea();
  if (volatileArea) {
    await volatileArea.remove(key);
  }
}

export async function getConfig(): Promise<ExtensionConfig> {
  const result = await chrome.storage.local.get(CONFIG_KEY);
  const config = result[CONFIG_KEY];
  if (config === undefined) {
    return { apiBaseUrl: normalizeApiBaseUrl(DEFAULT_API_BASE_URL) };
  }

  try {
    const parsed = parseExtensionConfig(config);
    return {
      apiBaseUrl: normalizeApiBaseUrl(parsed.apiBaseUrl),
    };
  } catch {
    await chrome.storage.local.remove(CONFIG_KEY);
    return { apiBaseUrl: normalizeApiBaseUrl(DEFAULT_API_BASE_URL) };
  }
}

export async function setConfig(config: ExtensionConfig): Promise<void> {
  const parsedConfig = parseExtensionConfig(config);
  await chrome.storage.local.set({
    [CONFIG_KEY]: { apiBaseUrl: normalizeApiBaseUrl(parsedConfig.apiBaseUrl) },
  });
}

export async function getSession(): Promise<ExtensionSession | null> {
  return getStoredValue<ExtensionSession>(SESSION_KEY, parseExtensionSession);
}

export async function setSession(session: ExtensionSession): Promise<void> {
  await setStoredValue(SESSION_KEY, parseExtensionSession(session));
}

export async function clearSession(): Promise<void> {
  await removeStoredValue(SESSION_KEY);
}

export async function getBootstrap(): Promise<ExtensionBootstrap | null> {
  return getStoredValue<ExtensionBootstrap>(BOOTSTRAP_KEY, parseExtensionBootstrap);
}

export async function setBootstrap(
  bootstrap: ExtensionBootstrap,
): Promise<void> {
  await setStoredValue(BOOTSTRAP_KEY, parseExtensionBootstrap(bootstrap));
}

export async function clearBootstrap(): Promise<void> {
  await removeStoredValue(BOOTSTRAP_KEY);
}

export async function getPreview(): Promise<CapturePreview | null> {
  return getStoredValue<CapturePreview>(PREVIEW_KEY, parseCapturePreview);
}

export async function setPreview(preview: CapturePreview): Promise<void> {
  await setStoredValue(PREVIEW_KEY, parseCapturePreview(preview));
}

export async function clearPreview(): Promise<void> {
  await removeStoredValue(PREVIEW_KEY);
}

export async function getSelectedPreviews(): Promise<CapturePreview[]> {
  return (await getStoredValue<CapturePreview[]>(
    SELECTED_PREVIEWS_KEY,
    parseCapturePreviewArray,
  )) ?? [];
}

export async function setSelectedPreviews(
  previews: CapturePreview[],
): Promise<void> {
  await setStoredValue(SELECTED_PREVIEWS_KEY, parseCapturePreviewArray(previews));
}

export async function clearSelectedPreviews(): Promise<void> {
  await removeStoredValue(SELECTED_PREVIEWS_KEY);
}
