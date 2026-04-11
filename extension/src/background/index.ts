import { loginWithGoogle, logout } from "./auth";
import {
  createEngagementSession,
  fetchBootstrap,
  importLinkedInPost,
  resolveImportedPosts,
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
import {
  buildPreviewKey,
  normalizePreview,
} from "../shared/linkedin-normalizer";
import type {
  ActiveTabPostScanResult,
  CapturePreview,
  EngagementSessionSummary,
  ExtensionState,
  ImportedPostStatusCandidate,
} from "../shared/types";

function getExtensionVersion(): string {
  return chrome.runtime.getManifest().version;
}

async function ensureSidePanelBehavior(): Promise<void> {
  if (!("sidePanel" in chrome) || !chrome.sidePanel) {
    return;
  }

  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
}

void ensureSidePanelBehavior();

chrome.runtime.onInstalled.addListener(() => {
  void ensureSidePanelBehavior();
});

chrome.runtime.onStartup.addListener(() => {
  void ensureSidePanelBehavior();
});

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

function buildEmptyActiveTabScanResult(
  url: string | null,
  errorMessage: string | null,
): ActiveTabPostScanResult {
  const capturedFrom =
    url && (url.includes("/posts/") || url.includes("/feed/update/"))
      ? "post_detail"
      : url && url.includes("linkedin.com")
        ? "feed"
        : "unknown";

  return {
    posts: [],
    diagnostic: {
      page_url: url,
      is_linkedin: !!url && url.includes("linkedin.com"),
      captured_from: capturedFrom,
      static_container_count: 0,
      action_anchor_count: 0,
      action_bar_count: 0,
      candidate_container_count: 0,
      accepted_post_count: 0,
      discard_reason_counts: {},
      sample_candidates: [],
      error_message: errorMessage,
    },
  };
}

async function scanActiveTab(): Promise<ActiveTabPostScanResult> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    return buildEmptyActiveTabScanResult(null, "Nenhuma aba ativa encontrada.");
  }

  const url = tab.url ?? "";
  if (!url.includes("linkedin.com")) {
    return buildEmptyActiveTabScanResult(
      url,
      "A aba ativa nao esta em uma pagina do LinkedIn.",
    );
  }

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        type InPageCandidateDiagnostic = {
          tag_name: string;
          text_excerpt: string | null;
          has_post_url: boolean;
          has_author_name: boolean;
          has_author_title: boolean;
          has_metrics: boolean;
          discard_reason: string | null;
        };

        type InPageDiagnostic = {
          page_url: string | null;
          is_linkedin: boolean;
          captured_from: "feed" | "post_detail" | "unknown";
          static_container_count: number;
          action_anchor_count: number;
          action_bar_count: number;
          candidate_container_count: number;
          accepted_post_count: number;
          discard_reason_counts: Record<string, number>;
          sample_candidates: InPageCandidateDiagnostic[];
          error_message: string | null;
        };

        type InPageCapturePreview = {
          post_url: string | null;
          post_text: string;
          author_name: string | null;
          author_title: string | null;
          author_company: string | null;
          author_profile_url: string | null;
          likes: number;
          comments: number;
          shares: number;
          post_type: "reference" | "icp";
          captured_from: "feed" | "post_detail" | "unknown";
          page_url: string | null;
          captured_at: string;
        };

        type InPageScanResult = {
          posts: InPageCapturePreview[];
          diagnostic: InPageDiagnostic;
        };

        const actionTextPattern =
          /\b(gostar|like|comentar|comment|compartilhar|share|repost|enviar|send)\b/i;
        const timestampPattern =
          /^(\d+\s*(min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo)\b|edited|editado|promoted|patrocinado)$/i;
        const postUrlSelectors = [
          ".update-components-actor__meta-link",
          ".feed-shared-actor__container-link",
          ".feed-shared-actor__meta-link",
          ".update-components-actor__sub-description-link",
          ".feed-shared-actor__sub-description-link",
          'a[href*="/posts/"]',
          'a[href*="/feed/update/"]',
          'a[href*="/activity-"]',
        ];
        const postUrnAttributeSelectors =
          "[data-urn], [data-id], [data-activity-urn], [data-entity-urn], [data-update-urn], [data-content-urn]";
        const postUrnPattern = /urn:li:(activity|share):\d+/i;
        const authorNameSelectors = [
          ".update-components-actor__title span[aria-hidden='true']",
          ".feed-shared-actor__name",
          ".update-components-actor__name",
          ".update-components-actor__title",
          ".feed-shared-actor__title",
          ".feed-shared-actor__meta a",
        ];
        const authorTitleSelectors = [
          ".update-components-actor__description",
          ".feed-shared-actor__description",
          ".update-components-actor__subtitle span[aria-hidden='true']",
          ".update-components-actor__sub-description",
          ".feed-shared-actor__sub-description",
        ];
        const postTextSelectors = [
          ".update-components-text span[dir='ltr']",
          ".update-components-text",
          ".feed-shared-update-v2__description-wrapper span[dir='ltr']",
          ".feed-shared-update-v2__description-wrapper",
          ".feed-shared-update-v2__description",
          ".feed-shared-text span[dir='ltr']",
          ".feed-shared-text",
          ".break-words",
          ".attributed-text-segment-list__content",
          ".update-components-update-v2__commentary",
          ".update-components-update-v2__commentary .break-words",
        ];
        const metricScopeSelectors = [
          ".social-details-social-counts",
          ".social-details-social-activity",
          ".feed-shared-social-action-bar",
        ];
        const staticContainerSelectors = [
          "div.feed-shared-update-v2",
          "div.occludable-update",
          "div[data-id^='urn:li:activity:']",
          "div[data-urn^='urn:li:activity:']",
          "article",
          ".update-components-actor",
        ];
        const headerScopeSelectors = [
          ".update-components-actor",
          ".feed-shared-actor",
          ".update-components-actor__container",
          ".feed-shared-actor__container",
        ];

        const capturedFrom: InPageCapturePreview["captured_from"] =
          window.location.pathname.includes("/posts/") ||
          window.location.pathname.includes("/feed/update/")
            ? "post_detail"
            : "feed";

        function normalizeWhitespace(
          value: string | null | undefined,
        ): string | null {
          if (!value) {
            return null;
          }
          const normalized = value.replace(/\s+/g, " ").trim();
          return normalized.length > 0 ? normalized : null;
        }

        function isVisible(element: HTMLElement | null): element is HTMLElement {
          if (!element) {
            return false;
          }
          const style = window.getComputedStyle(element);
          if (style.display === "none" || style.visibility === "hidden") {
            return false;
          }
          const rect = element.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0;
        }

        function isActionOrNoiseText(value: string): boolean {
          if (actionTextPattern.test(value)) return true;
          if (timestampPattern.test(value)) return true;
          if (/^(seguir|follow|conectar|connect)$/i.test(value)) return true;
          return false;
        }

        function getHeaderScope(root: ParentNode): ParentNode {
          for (const selector of headerScopeSelectors) {
            const element = root.querySelector<HTMLElement>(selector);
            if (element) {
              return element;
            }
          }
          return root;
        }

        function collectVisibleTextCandidates(root: ParentNode, minLength = 12): string[] {
          const values: string[] = [];
          const seen = new Set<string>();
          const elements = root.querySelectorAll<HTMLElement>("span, div, p, a, li");
          for (const element of elements) {
            if (!isVisible(element)) {
              continue;
            }
            const text = normalizeWhitespace(element.innerText);
            if (!text || text.length < minLength || text.length > 700) {
              continue;
            }
            if (isActionOrNoiseText(text) || seen.has(text)) {
              continue;
            }
            seen.add(text);
            values.push(text);
          }
          return values;
        }

        function chooseLongestText(values: string[]): string | null {
          const sorted = [...values].sort((left, right) => right.length - left.length);
          return sorted[0] ?? null;
        }

        function firstText(
          root: ParentNode,
          selectors: string[],
        ): string | null {
          for (const selector of selectors) {
            const element = root.querySelector<HTMLElement>(selector);
            const value = normalizeWhitespace(element?.innerText);
            if (value) {
              return value;
            }
          }
          return null;
        }

        function normalizeLinkedInPostUrl(
          rawUrl: string | null | undefined,
        ): string | null {
          const cleaned = normalizeWhitespace(rawUrl);
          if (!cleaned) {
            return null;
          }

          try {
            const parsed = new URL(cleaned, window.location.origin);
            const updateEntityUrn = normalizeWhitespace(
              parsed.searchParams.get("updateEntityUrn"),
            );
            if (updateEntityUrn && postUrnPattern.test(updateEntityUrn)) {
              return `${parsed.origin}/feed/update/${updateEntityUrn.replace(/\/+$/, "")}/`;
            }

            const pathname = parsed.pathname.replace(/\/+$/, "");
            if (
              pathname.includes("/posts/") ||
              pathname.includes("/feed/update/") ||
              pathname.includes("/activity-")
            ) {
              return `${parsed.origin}${pathname}/`;
            }
          } catch {
            return cleaned;
          }

          return null;
        }

        function buildLinkedInFeedUrlFromUrn(postUrn: string | null): string | null {
          const normalizedUrn = normalizeWhitespace(postUrn);
          if (!normalizedUrn || !postUrnPattern.test(normalizedUrn)) {
            return null;
          }
          return `https://www.linkedin.com/feed/update/${normalizedUrn}/`;
        }

        function extractPostUrn(root: ParentNode): string | null {
          const candidates: string[] = [];

          if (root instanceof HTMLElement) {
            candidates.push(
              ...[
                root.dataset.urn,
                root.dataset.id,
                root.dataset.activityUrn,
                root.dataset.entityUrn,
                root.dataset.updateUrn,
                root.dataset.contentUrn,
                root.getAttribute("data-urn"),
                root.getAttribute("data-id"),
                root.getAttribute("data-activity-urn"),
                root.getAttribute("data-entity-urn"),
                root.getAttribute("data-update-urn"),
                root.getAttribute("data-content-urn"),
              ].filter((value): value is string => !!value),
            );
          }

          for (const element of root.querySelectorAll<HTMLElement>(postUrnAttributeSelectors)) {
            const attributeCandidates = [
              element.dataset.urn,
              element.dataset.id,
              element.dataset.activityUrn,
              element.dataset.entityUrn,
              element.dataset.updateUrn,
              element.dataset.contentUrn,
              element.getAttribute("data-urn"),
              element.getAttribute("data-id"),
              element.getAttribute("data-activity-urn"),
              element.getAttribute("data-entity-urn"),
              element.getAttribute("data-update-urn"),
              element.getAttribute("data-content-urn"),
            ];
            for (const candidate of attributeCandidates) {
              if (!candidate) {
                continue;
              }
              candidates.push(candidate);
            }
          }

          for (const candidate of candidates) {
            const match = candidate.match(postUrnPattern);
            if (match) {
              return match[0];
            }
          }

          return null;
        }

        function firstPostUrl(root: ParentNode): string | null {
          for (const selector of postUrlSelectors) {
            const anchor = root.querySelector<HTMLAnchorElement>(selector);
            const href = normalizeLinkedInPostUrl(anchor?.href);
            if (href) {
              return href;
            }
          }
          const anchors = root.querySelectorAll<HTMLAnchorElement>("a[href]");
          for (const anchor of anchors) {
            const href = normalizeLinkedInPostUrl(anchor.href);
            if (!href) {
              continue;
            }
            if (
              href.includes("/posts/") ||
              href.includes("/feed/update/") ||
              href.includes("/activity-")
            ) {
              return href;
            }
          }
          return buildLinkedInFeedUrlFromUrn(extractPostUrn(root));
        }

        function parseMetricValue(rawText: string | null): number {
          if (!rawText) return 0;
          const normalized = rawText
            .toLowerCase()
            .replace(/\./g, "")
            .replace(/,/g, ".");
          const match = normalized.match(/(\d+(?:\.\d+)?)(\s*[km])?/);
          if (!match) return 0;
          const base = Number(match[1]);
          if (Number.isNaN(base)) return 0;
          const suffix = match[2]?.trim();
          if (suffix === "k") return Math.round(base * 1000);
          if (suffix === "m") return Math.round(base * 1000000);
          return Math.round(base);
        }

        function getMetricScope(root: ParentNode): ParentNode {
          for (const selector of metricScopeSelectors) {
            const scope = root.querySelector<HTMLElement>(selector);
            if (scope) {
              return scope;
            }
          }
          return root;
        }

        function findMetric(root: ParentNode, pattern: RegExp): number {
          const scope = getMetricScope(root);
          const elements = scope.querySelectorAll<HTMLElement>(
            "button, span, li, div",
          );
          for (const element of elements) {
            const text = normalizeWhitespace(element.innerText);
            if (!text || !pattern.test(text.toLowerCase())) {
              continue;
            }
            return parseMetricValue(text);
          }
          return 0;
        }

        function fallbackAuthorName(root: ParentNode): string | null {
          const headerScope = getHeaderScope(root);
          const candidates = collectVisibleTextCandidates(headerScope, 3);
          for (const candidate of candidates) {
            if (candidate.length > 80 || isActionOrNoiseText(candidate)) {
              continue;
            }
            if (/\b(linkedin|premium|seguir|follow|repost)\b/i.test(candidate)) {
              continue;
            }
            return candidate;
          }
          return null;
        }

        function fallbackAuthorTitle(
          root: ParentNode,
          authorName: string | null,
        ): string | null {
          const headerScope = getHeaderScope(root);
          const candidates = collectVisibleTextCandidates(headerScope, 6);
          for (const candidate of candidates) {
            if (candidate === authorName) {
              continue;
            }
            if (candidate.length > 160 || isActionOrNoiseText(candidate)) {
              continue;
            }
            return candidate;
          }
          return null;
        }

        function fallbackPostText(
          root: ParentNode,
          authorName: string | null,
          authorTitle: string | null,
        ): string | null {
          const candidates = collectVisibleTextCandidates(root, 20);
          const filtered = candidates.filter((candidate) => {
            if (candidate === authorName || candidate === authorTitle) {
              return false;
            }
            if (candidate.length < 20 || candidate.length > 1500) {
              return false;
            }
            return !isActionOrNoiseText(candidate);
          });
          return chooseLongestText(filtered);
        }

        function parseAuthorCompany(authorTitle: string | null): string | null {
          if (!authorTitle) return null;
          const parts = authorTitle
            .split(/ at | na | \| | - /i)
            .map((item) => item.trim())
            .filter(Boolean);
          if (parts.length < 2) return null;
          return parts[1] ?? null;
        }

        function getActionSignature(text: string): string {
          const matches = text
            .toLowerCase()
            .match(/gostar|like|comentar|comment|compartilhar|share|repost|enviar|send/g);
          return matches ? Array.from(new Set(matches)).sort().join("|") : "";
        }

        function findActionAnchors(scope: ParentNode): HTMLElement[] {
          const anchors = scope.querySelectorAll<HTMLElement>("button, span, div");
          return Array.from(anchors).filter((element) => {
            const text = normalizeWhitespace(element.innerText);
            return !!text && text.length <= 40 && actionTextPattern.test(text);
          });
        }

        function findActionBarFromAnchor(anchor: HTMLElement): HTMLElement | null {
          let current: HTMLElement | null = anchor;
          for (let depth = 0; current && depth < 6; depth += 1) {
            const text = normalizeWhitespace(current.innerText) ?? "";
            const signature = getActionSignature(text);
            if (signature.split("|").filter(Boolean).length >= 3) {
              return current;
            }
            current = current.parentElement;
          }
          return null;
        }

        function looksLikePostContainer(container: HTMLElement): boolean {
          const textCandidates = collectVisibleTextCandidates(container, 20);
          const longestText = chooseLongestText(textCandidates);
          if (!longestText || longestText.length < 20) {
            return false;
          }
          const allText = normalizeWhitespace(container.innerText) ?? "";
          if (allText.length < 40 || allText.length > 9000) {
            return false;
          }
          const hasPostUrl = !!firstPostUrl(container);
          const hasMetrics =
            findMetric(container, /like|curt/) > 0 ||
            findMetric(container, /comment|coment/) > 0 ||
            findMetric(container, /repost|share|compart/) > 0;
          const hasHeader = !!firstText(getHeaderScope(container), authorNameSelectors);
          return hasPostUrl || hasMetrics || hasHeader;
        }

        function findContainerFromActionBar(actionBar: HTMLElement): HTMLElement | null {
          let current: HTMLElement | null = actionBar;
          for (let depth = 0; current && depth < 8; depth += 1) {
            if (looksLikePostContainer(current)) {
              return current;
            }
            current = current.parentElement;
          }
          return null;
        }

        function collectLikelyPostContainers(): {
          containers: HTMLElement[];
          actionAnchorCount: number;
          actionBarCount: number;
          staticContainerCount: number;
        } {
          const containers = new Set<HTMLElement>();
          const actionBars = new Set<HTMLElement>();
          let staticContainerCount = 0;

          for (const selector of staticContainerSelectors) {
            const elements = Array.from(document.querySelectorAll<HTMLElement>(selector));
            staticContainerCount += elements.length;
            for (const element of elements) {
              if (looksLikePostContainer(element)) {
                containers.add(element);
              }
            }
          }

          const actionAnchors = findActionAnchors(document);
          for (const anchor of actionAnchors) {
            const actionBar = findActionBarFromAnchor(anchor);
            if (!actionBar) {
              continue;
            }
            actionBars.add(actionBar);
            const container = findContainerFromActionBar(actionBar);
            if (container) {
              containers.add(container);
            }
          }

          return {
            containers: Array.from(containers),
            actionAnchorCount: actionAnchors.length,
            actionBarCount: actionBars.size,
            staticContainerCount,
          };
        }

        function buildPreviewKey(preview: InPageCapturePreview): string {
          return [
            preview.post_url ?? "",
            preview.author_name ?? "",
            preview.post_text.slice(0, 160),
            preview.captured_from,
          ].join("::");
        }

        const previews = new Map<string, InPageCapturePreview>();
        const discardReasonCounts = new Map<string, number>();
        const sampleCandidates: InPageCandidateDiagnostic[] = [];
        const scan = collectLikelyPostContainers();
        const containers = scan.containers;

        function registerDiscardReason(reason: string): void {
          discardReasonCounts.set(reason, (discardReasonCounts.get(reason) ?? 0) + 1);
        }

        for (const container of containers) {
          const authorName =
            firstText(getHeaderScope(container), authorNameSelectors) ??
            fallbackAuthorName(container);
          const authorTitle =
            firstText(getHeaderScope(container), authorTitleSelectors) ??
            fallbackAuthorTitle(container, authorName);
          const postText =
            firstText(container, postTextSelectors) ??
            fallbackPostText(container, authorName, authorTitle);
          const postUrl = firstPostUrl(container);
          const likes = findMetric(container, /like|curt/);
          const comments = findMetric(container, /comment|coment/);
          const shares = findMetric(container, /repost|share|compart/);
          const hasMetrics = likes > 0 || comments > 0 || shares > 0;
          const resolvedPostText = postText;

          let discardReason: string | null = null;
          if (!resolvedPostText) {
            discardReason = "missing_post_text";
          } else if (!authorName && !postUrl && !hasMetrics) {
            discardReason = "missing_author_and_signals";
          }

          if (sampleCandidates.length < 8) {
            sampleCandidates.push({
              tag_name: container.tagName.toLowerCase(),
              text_excerpt: resolvedPostText?.slice(0, 120) ?? null,
              has_post_url: !!postUrl,
              has_author_name: !!authorName,
              has_author_title: !!authorTitle,
              has_metrics: hasMetrics,
              discard_reason: discardReason,
            });
          }

          if (discardReason || !resolvedPostText) {
            const effectiveDiscardReason = discardReason ?? "missing_post_text";
            registerDiscardReason(effectiveDiscardReason);
            continue;
          }

          const preview: InPageCapturePreview = {
            post_url: postUrl,
            post_text: resolvedPostText,
            author_name: authorName,
            author_title: authorTitle,
            author_company: parseAuthorCompany(authorTitle),
            author_profile_url: null,
            likes,
            comments,
            shares,
            post_type: capturedFrom === "post_detail" ? "icp" : "reference",
            captured_from: capturedFrom,
            page_url: window.location.href,
            captured_at: new Date().toISOString(),
          };

          previews.set(buildPreviewKey(preview), preview);
        }

        const posts = Array.from(previews.values()).slice(0, 25);
        const discard_reason_counts = Object.fromEntries(discardReasonCounts.entries());

        return {
          posts,
          diagnostic: {
            page_url: window.location.href,
            is_linkedin: window.location.hostname.includes("linkedin.com"),
            captured_from: capturedFrom,
            static_container_count: scan.staticContainerCount,
            action_anchor_count: scan.actionAnchorCount,
            action_bar_count: scan.actionBarCount,
            candidate_container_count: containers.length,
            accepted_post_count: posts.length,
            discard_reason_counts,
            sample_candidates: sampleCandidates,
            error_message: posts.length === 0 ? "Nenhum post valido foi confirmado pelas heuristicas atuais." : null,
          },
        } satisfies InPageScanResult;
      },
    });

    const scanResult = results[0]?.result as ActiveTabPostScanResult | undefined;
    if (scanResult) {
      try {
        const response = (await chrome.tabs.sendMessage(tab.id, {
          type: MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS,
        })) as ExtensionMessageResponse<CapturePreview[]>;
        if (response.ok && (response.data?.length ?? 0) > 0) {
          const posts = response.data ?? [];
          return {
            posts,
            diagnostic: {
              ...scanResult.diagnostic,
              accepted_post_count: posts.length,
            },
          };
        }
      } catch {
        // Mantem fallback do scan direto da aba.
      }
      return scanResult;
    }

    const response = (await chrome.tabs.sendMessage(tab.id, {
      type: MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS,
    })) as ExtensionMessageResponse<CapturePreview[]>;
    if (response.ok) {
      const posts = response.data ?? [];
      return {
        posts,
        diagnostic: {
          page_url: url,
          is_linkedin: true,
          captured_from:
            url.includes("/posts/") || url.includes("/feed/update/")
              ? "post_detail"
              : "feed",
          static_container_count: 0,
          action_anchor_count: 0,
          action_bar_count: 0,
          candidate_container_count: posts.length,
          accepted_post_count: posts.length,
          discard_reason_counts: {},
          sample_candidates: [],
          error_message: null,
        },
      };
    }
    return buildEmptyActiveTabScanResult(
      url,
      "A extensao nao conseguiu ler posts da pagina ativa.",
    );
  } catch (error) {
    if (
      error instanceof Error &&
      error.message.includes("Receiving end does not exist")
    ) {
      return buildEmptyActiveTabScanResult(
        url,
        "O content script nao respondeu e o scan direto da aba falhou.",
      );
    }
    const errorMessage =
      error instanceof Error ? error.message : "Falha desconhecida ao analisar a aba ativa.";
    return buildEmptyActiveTabScanResult(url, errorMessage);
  }
}

async function filterImportedPosts(
  scan: ActiveTabPostScanResult,
): Promise<ActiveTabPostScanResult> {
  if (scan.posts.length === 0) {
    return scan;
  }

  const config = await getConfig();
  const session = await getSession();
  if (!session) {
    return scan;
  }

  const candidates: ImportedPostStatusCandidate[] = scan.posts.map((preview) => {
    const normalized = normalizePreview(preview);
    return {
      candidate_key: buildPreviewKey(normalized),
      post_url: normalized.post_url,
      canonical_post_url: normalized.post_url,
      post_text: normalized.post_text,
      author_name: normalized.author_name,
    };
  });

  try {
    const statusResponse = await resolveImportedPosts(
      config,
      session,
      getExtensionVersion(),
      candidates,
    );
    const importedKeys = new Set(
      statusResponse.matches
        .filter((match) => match.imported)
        .map((match) => match.candidate_key),
    );
    if (importedKeys.size === 0) {
      return scan;
    }

    const filteredPosts = scan.posts.filter(
      (preview) => !importedKeys.has(buildPreviewKey(normalizePreview(preview))),
    );
    const alreadyImportedCount = scan.posts.length - filteredPosts.length;

    return {
      posts: filteredPosts,
      diagnostic: {
        ...scan.diagnostic,
        accepted_post_count: filteredPosts.length,
        discard_reason_counts: {
          ...scan.diagnostic.discard_reason_counts,
          already_imported:
            (scan.diagnostic.discard_reason_counts.already_imported ?? 0) +
            alreadyImportedCount,
        },
        error_message:
          filteredPosts.length === 0
            ? "Todos os posts detectados nesta pagina ja foram importados."
            : scan.diagnostic.error_message,
      },
    };
  } catch {
    return scan;
  }
}

async function listPostsFromActiveTab(): Promise<CapturePreview[]> {
  const scan = await filterImportedPosts(await scanActiveTab());
  return scan.posts;
}

async function getActiveTabScan(): Promise<ActiveTabPostScanResult> {
  return filterImportedPosts(await scanActiveTab());
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

    case MESSAGE_TYPES.GET_ACTIVE_TAB_SCAN:
      return { ok: true, data: await getActiveTabScan() };

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
