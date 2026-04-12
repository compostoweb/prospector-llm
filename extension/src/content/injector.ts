import { MESSAGE_TYPES } from "../shared/contracts";
import { buildPreviewKey } from "../shared/linkedin-normalizer";
import type { CapturePreview, CapturedFrom } from "../shared/types";
import { collectLikelyPostContainers, extractLinkedInPost } from "./dom-parser";

const BUTTON_ATTRIBUTE = "data-prospector-capture-button";
const BUTTON_CLASSNAME = "prospector-capture-button";
let runtimeListenerRegistered = false;

function showToast(message: string): void {
  const existing = document.getElementById("prospector-extension-toast");
  if (existing) {
    existing.remove();
  }

  const toast = document.createElement("div");
  toast.id = "prospector-extension-toast";
  toast.textContent = message;
  toast.style.position = "fixed";
  toast.style.right = "20px";
  toast.style.bottom = "20px";
  toast.style.zIndex = "999999";
  toast.style.padding = "10px 14px";
  toast.style.borderRadius = "12px";
  toast.style.background = "#0f172a";
  toast.style.color = "#f8fafc";
  toast.style.fontSize = "13px";
  toast.style.boxShadow = "0 10px 30px rgba(15, 23, 42, 0.35)";
  document.body.appendChild(toast);
  window.setTimeout(() => toast.remove(), 2400);
}

function createCaptureButton(
  container: HTMLElement,
  capturedFrom: CapturedFrom,
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Selecionar post";
  button.className = BUTTON_CLASSNAME;
  button.style.display = "inline-flex";
  button.style.alignItems = "center";
  button.style.justifyContent = "center";
  button.style.height = "28px";
  button.style.padding = "0 11px";
  button.style.borderRadius = "999px";
  button.style.border = "1px solid rgba(15, 118, 110, 0.35)";
  button.style.background = "rgba(236, 253, 245, 0.96)";
  button.style.color = "#0f766e";
  button.style.cursor = "pointer";
  button.style.fontSize = "11px";
  button.style.fontWeight = "600";
  button.style.whiteSpace = "nowrap";
  button.style.boxShadow = "0 6px 18px rgba(15, 118, 110, 0.12)";
  button.style.pointerEvents = "auto";

  button.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();

    const preview = extractLinkedInPost(container, capturedFrom);
    if (!preview) {
      showToast("Nao foi possivel capturar este post.");
      return;
    }

    const response = await chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.SAVE_CAPTURED_POST,
      payload: preview,
    });

    if (response?.ok) {
      showToast("Post adicionado a selecao. Abra a extensao para importar.");
      return;
    }

    showToast(response?.error ?? "Falha ao salvar preview do post.");
  });

  return button;
}

function ensureRelativePosition(element: HTMLElement): void {
  if (window.getComputedStyle(element).position === "static") {
    element.style.position = "relative";
  }
}

function findInjectionTarget(container: HTMLElement): HTMLElement {
  const headerArea = container.querySelector<HTMLElement>(
    ".update-components-actor, .feed-shared-actor",
  );
  if (headerArea instanceof HTMLElement) {
    ensureRelativePosition(headerArea);
    return headerArea;
  }

  ensureRelativePosition(container);
  return container;
}

function createCaptureButtonHost(
  target: HTMLElement,
  postContainer: HTMLElement,
  capturedFrom: CapturedFrom,
): HTMLDivElement {
  const host = document.createElement("div");
  host.setAttribute(BUTTON_ATTRIBUTE, "1");
  host.style.position = "absolute";
  host.style.top = target.matches(".update-components-actor, .feed-shared-actor")
    ? "0"
    : "10px";
  host.style.right = target.matches(".update-components-actor, .feed-shared-actor")
    ? "0"
    : "12px";
  host.style.zIndex = "20";
  host.style.display = "flex";
  host.style.justifyContent = "flex-end";
  host.style.pointerEvents = "none";
  host.appendChild(createCaptureButton(postContainer, capturedFrom));
  return host;
}

function collectLinkedInPosts(
  scope: ParentNode,
  capturedFrom: CapturedFrom,
): CapturePreview[] {
  const previews = new Map<string, CapturePreview>();

  for (const container of collectLikelyPostContainers(scope)) {
    const preview = extractLinkedInPost(container, capturedFrom);
    if (!preview) {
      continue;
    }
    previews.set(buildPreviewKey(preview), preview);
  }

  return Array.from(previews.values());
}

function installButtonsInScope(
  scope: ParentNode,
  capturedFrom: CapturedFrom,
): void {
  const containers = collectLikelyPostContainers(scope);

  containers.forEach((container) => {
    if (container.querySelector(`[${BUTTON_ATTRIBUTE}]`)) {
      return;
    }

    if (!extractLinkedInPost(container, capturedFrom)) {
      return;
    }

    const target = findInjectionTarget(container);
    const host = createCaptureButtonHost(target, container, capturedFrom);
    target.appendChild(host);
  });
}

function registerRuntimeHandlers(capturedFrom: CapturedFrom): void {
  if (runtimeListenerRegistered) {
    return;
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS) {
      return undefined;
    }

    sendResponse({
      ok: true,
      data: collectLinkedInPosts(document, capturedFrom),
    });
    return true;
  });

  runtimeListenerRegistered = true;
}

export function initializeLinkedInCapture(capturedFrom: CapturedFrom): void {
  installButtonsInScope(document, capturedFrom);
  registerRuntimeHandlers(capturedFrom);

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        installButtonsInScope(node, capturedFrom);
      });
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}
