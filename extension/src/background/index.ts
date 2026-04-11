import { loginWithGoogle, logout } from "./auth";
import {
  createEngagementSession,
  fetchBootstrap,
  importLinkedInPost,
} from "./api";
import {
  clearPreview,
  getBootstrap,
  getConfig,
  getPreview,
  getSession,
  setBootstrap,
  setConfig,
  setPreview,
} from "./storage";
import {
  MESSAGE_TYPES,
  type ExtensionMessage,
  type ExtensionMessageResponse,
} from "../shared/contracts";
import { normalizePreview } from "../shared/linkedin-normalizer";
import type {
  CapturePreview,
  EngagementSessionSummary,
  ExtensionState,
} from "../shared/types";

function getExtensionVersion(): string {
  return chrome.runtime.getManifest().version;
}

async function getState(): Promise<ExtensionState> {
  return {
    session: await getSession(),
    bootstrap: await getBootstrap(),
    preview: await getPreview(),
    config: await getConfig(),
  };
}

async function refreshBootstrap(): Promise<ExtensionState> {
  const config = await getConfig();
  const session = await getSession();
  if (!session) {
    return getState();
  }
  const bootstrap = await fetchBootstrap(
    config,
    session,
    getExtensionVersion(),
  );
  await setBootstrap(bootstrap);
  return getState();
}

async function listPostsFromActiveTab(): Promise<CapturePreview[]> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    return [];
  }

  const url = tab.url ?? "";
  if (!url.includes("linkedin.com")) {
    return [];
  }

  try {
    const response = (await chrome.tabs.sendMessage(tab.id, {
      type: MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS,
    })) as ExtensionMessageResponse<CapturePreview[]>;
    if (!response.ok) {
      throw new Error(response.error ?? "Falha ao listar posts da pagina.");
    }
    return response.data ?? [];
  } catch (error) {
    if (
      error instanceof Error &&
      error.message.includes("Receiving end does not exist")
    ) {
      return [];
    }
    throw error;
  }
}

async function createManualEngagementSession(): Promise<EngagementSessionSummary> {
  const config = await getConfig();
  const session = await getSession();
  if (!session) {
    throw new Error("Sessao ausente. Faca login novamente.");
  }

  const createdSession = await createEngagementSession(
    config,
    session,
    getExtensionVersion(),
  );
  await refreshBootstrap();
  return createdSession;
}

async function handleMessage(
  message: ExtensionMessage,
): Promise<ExtensionMessageResponse<unknown>> {
  switch (message.type) {
    case MESSAGE_TYPES.GET_STATE:
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.AUTH_LOGIN:
      await loginWithGoogle();
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.AUTH_LOGOUT:
      await logout();
      await clearPreview();
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS:
      return { ok: true, data: await listPostsFromActiveTab() };

    case MESSAGE_TYPES.SAVE_CAPTURED_POST:
      await setPreview(normalizePreview(message.payload));
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.IMPORT_CAPTURE: {
      const config = await getConfig();
      const session = await getSession();
      if (!session) {
        throw new Error("Sessao ausente. Faca login novamente.");
      }
      const captureResponse = await importLinkedInPost(
        config,
        session,
        getExtensionVersion(),
        message.payload,
      );
      await clearPreview();
      await refreshBootstrap();
      return { ok: true, data: captureResponse };
    }

    case MESSAGE_TYPES.GET_CONFIG:
      return { ok: true, data: await getConfig() };

    case MESSAGE_TYPES.CREATE_ENGAGEMENT_SESSION:
      return { ok: true, data: await createManualEngagementSession() };

    case MESSAGE_TYPES.SAVE_CONFIG:
      await setConfig(message.payload);
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.REFRESH_BOOTSTRAP:
      return { ok: true, data: await refreshBootstrap() };

    default:
      throw new Error("Mensagem da extensao nao suportada.");
  }
}

chrome.runtime.onMessage.addListener(
  (message: ExtensionMessage, _sender, sendResponse) => {
    void handleMessage(message)
      .then((response) => sendResponse(response))
      .catch((error: unknown) => {
        const message =
          error instanceof Error ? error.message : "Erro desconhecido";
        sendResponse({ ok: false, error: message });
      });

    return true;
  },
);
