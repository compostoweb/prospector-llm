import { MESSAGE_TYPES } from "../shared/contracts";
import { buildPreviewKey } from "../shared/linkedin-normalizer";
import type { CapturePreview, CapturedFrom } from "../shared/types";
import { extractLinkedInPost } from "./dom-parser";

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
  button.textContent = "Salvar no Prospector";
  button.className = BUTTON_CLASSNAME;
  button.setAttribute(BUTTON_ATTRIBUTE, "1");
  button.style.marginTop = "10px";
  button.style.padding = "8px 12px";
  button.style.borderRadius = "999px";
  button.style.border = "1px solid #0a66c2";
  button.style.background = "#ffffff";
  button.style.color = "#0a66c2";
  button.style.cursor = "pointer";
  button.style.fontSize = "13px";
  button.style.fontWeight = "600";

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
      showToast("Post capturado. Abra a extensao para importar.");
      return;
    }

    showToast(response?.error ?? "Falha ao salvar preview do post.");
  });

  return button;
}

function findInjectionTarget(container: HTMLElement): HTMLElement {
  const actionBar = container.querySelector<HTMLElement>(
    ".social-actions-button",
  );
  if (actionBar?.parentElement instanceof HTMLElement) {
    return actionBar.parentElement;
  }
  return container;
}

function getPostContainers(scope: ParentNode): HTMLElement[] {
  return Array.from(
    scope.querySelectorAll<HTMLElement>(
      "div.feed-shared-update-v2, article, .update-components-actor",
    ),
  );
}

function collectLinkedInPosts(
  scope: ParentNode,
  capturedFrom: CapturedFrom,
): CapturePreview[] {
  const previews = new Map<string, CapturePreview>();

  for (const container of getPostContainers(scope)) {
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
  const containers = getPostContainers(scope);

  containers.forEach((container) => {
    if (container.querySelector(`[${BUTTON_ATTRIBUTE}]`)) {
      return;
    }

    if (!extractLinkedInPost(container, capturedFrom)) {
      return;
    }

    const target = findInjectionTarget(container);
    target.appendChild(createCaptureButton(container, capturedFrom));
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
