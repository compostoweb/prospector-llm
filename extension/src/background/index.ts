import { loginWithGoogle, logout } from "./auth";
import {
  createEngagementSession,
  fetchBootstrap,
  importLinkedInPost,
  resolveImportedPosts,
} from "./api";
import {
  clearPreview,
  clearSelectedPreviews,
  getBootstrap,
  getConfig,
  getPreview,
  getSelectedPreviews,
  getSession,
  setBootstrap,
  setConfig,
  setPreview,
  setSelectedPreviews,
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
    selected_previews: await getSelectedPreviews(),
    config: await getConfig(),
  };
}

async function saveSelectedPreview(preview: CapturePreview): Promise<void> {
  const normalizedPreview = normalizePreview(preview);
  const nextPreviewKey = buildPreviewKey(normalizedPreview);
  const currentSelectedPreviews = await getSelectedPreviews();
  const dedupedPreviews = currentSelectedPreviews.filter(
    (candidate) => buildPreviewKey(candidate) !== nextPreviewKey,
  );

  await setSelectedPreviews([normalizedPreview, ...dedupedPreviews]);
  await setPreview(normalizedPreview);
}

async function removeSelectedPreview(candidateKey: string): Promise<void> {
  const currentSelectedPreviews = await getSelectedPreviews();
  const nextSelectedPreviews = currentSelectedPreviews.filter(
    (candidate) => buildPreviewKey(candidate) !== candidateKey,
  );

  await setSelectedPreviews(nextSelectedPreviews);

  const currentPreview = await getPreview();
  if (currentPreview && buildPreviewKey(currentPreview) === candidateKey) {
    const nextPreview = nextSelectedPreviews[0] ?? null;
    if (nextPreview) {
      await setPreview(nextPreview);
    } else {
      await clearPreview();
    }
  }
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

function scorePreview(preview: CapturePreview): number {
  const normalized = normalizePreview(preview);
  let score = 0;

  if (normalized.post_url) score += 8;
  if (normalized.author_name) score += 5;
  if (normalized.author_title) score += 3;
  if (normalized.likes + normalized.comments + normalized.shares > 0)
    score += 2;
  if (normalized.post_text.length >= 80) score += 4;
  else if (normalized.post_text.length >= 30) score += 2;

  if (
    /\b(gostou|liked|comentou|commented|repostou|reposted|compartilhou|shared)\b/i.test(
      normalized.author_name ?? "",
    )
  ) {
    score -= 12;
  }

  if (
    /\b(gostou|liked|comentou|commented|repostou|reposted|compartilhou|shared)\b/i.test(
      normalized.post_text.slice(0, 80),
    )
  ) {
    score -= 6;
  }

  return score;
}

function buildLoosePreviewKey(preview: CapturePreview): string {
  const normalized = normalizePreview(preview);
  const bodyPrefix = normalized.post_text
    .toLowerCase()
    .replace(/\s+/g, " ")
    .slice(0, 120);
  return [
    normalized.author_name?.toLowerCase() ?? "",
    bodyPrefix,
    normalized.captured_from,
  ].join("::");
}

function mergePreviewLists(...groups: CapturePreview[][]): CapturePreview[] {
  const byExactKey = new Map<string, CapturePreview>();
  const byLooseKey = new Map<string, string>();

  for (const group of groups) {
    for (const preview of group) {
      const normalized = normalizePreview(preview);
      const exactKey = buildPreviewKey(normalized);
      const looseKey = buildLoosePreviewKey(normalized);
      const existingExactKey = byLooseKey.get(looseKey) ?? exactKey;
      const current = byExactKey.get(existingExactKey);

      if (!current || scorePreview(normalized) > scorePreview(current)) {
        if (existingExactKey !== exactKey) {
          byExactKey.delete(existingExactKey);
        }
        byExactKey.set(exactKey, normalized);
        byLooseKey.set(looseKey, exactKey);
      }
    }
  }

  return Array.from(byExactKey.values());
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
        const socialContextPattern =
          /\b(gostou|liked|comentou|commented|repostou|reposted|compartilhou|shared|seguem a empresa|follows the company|conexoes seguem|connections follow|reagiram|reacted|reagiu|celebrou|celebrated|apoiou|supported|achou interessante|found insightful|achou engracado|found funny|amou|loved)\b/i;
        const socialProofPattern =
          /\b(e mais \d+|\d+\s*(reações|reactions|curtidas|likes|comentários|comments|compartilhamentos|shares|reposts)|pessoas\s+reagiram|people\s+reacted)\b/i;
        const timestampPattern =
          /^(\d+\s*(min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo)\b|edited|editado|promoted|patrocinado)$/i;
        const followCtaPattern =
          /\b(seguir|follow|conectar|connect|acessar meu site|acesse meu site|visit website|agende uma reunião|agendar uma reunião|agende|schedule a meeting|book a meeting)\b/i;
        const postTextCollapsePattern = /(?:\.\.\.|…)\s*(mais|more)\b/gi;
        const relativeTimeTokenPattern =
          /\b(\d+\s*(?:min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo))\b/i;
        const controlMenuAuthorPattern =
          /(?:publica(?:ç|c)[aã]o|publication|post)\s+(?:de|of|by)\s+(.+)$/i;
        const reactionPattern =
          /reaction|reactions|reac|curtida|curtidas|like|likes/i;
        const commentPattern =
          /comment|comments|comentario|comentarios|comentário|comentários/i;
        const sharePattern =
          /repost|reposts|share|shares|compartilhamento|compartilhamentos|compartilhar/i;
        const authorTitleNoisePattern =
          /\b(?:usu[aá]rio verificado|verified user|premium|perfil|profile|seguidores?|followers?|visibilidade|global|promovida|promoted)\b/gi;
        const postUrlSelectors = [
          ".update-components-actor__meta-link",
          ".feed-shared-actor__container-link",
          ".feed-shared-actor__meta-link",
          ".update-components-actor__sub-description-link",
          ".update-components-actor__sub-description-link a",
          ".update-components-actor__sub-description a",
          ".feed-shared-actor__sub-description-link",
          ".feed-shared-actor__sub-description-link a",
          'a[href*="/posts/"]',
          'a[href*="/feed/update/"]',
          'a[href*="/activity-"]',
          'a[href*="/activity/"]',
        ];
        const postUrnPattern = /urn:li:(activity|share|ugcPost|update):\d+/i;
        const encodedPostUrnPattern =
          /urn(?:%3A|:)li(?:%3A|:)(activity|share|ugcPost|update)(?:%3A|:)(\d+)/i;
        const reactionSocialProofOthersPattern =
          /(?:\be\s+mais\s+(\d+(?:[\.,]\d+)?)\s+pessoas\b|\band\s+(\d+(?:[\.,]\d+)?)\s+others\b)/i;
        const reactionSocialProofTotalPattern =
          /\b(\d+(?:[\.,]\d+)?)\s+(?:pessoas|people)\b/i;
        const metadataShareIdPattern =
          /(?:shareId|activityId|updateId)=(\d{15,25})/i;
        const metadataUgcPostIdPattern = /(?:postId|ugcPostId)=(\d{15,25})/i;
        const metadataKeyedUrnIdPattern =
          /(activity|share|ugcPost|update)(?:Urn|Id)?[:=](\d{15,25})/i;
        const rawLinkedInIdPattern = /(?:^|\D)(\d{19,20})(?:\D|$)/;
        const authorNameSelectors = [
          ".update-components-actor__meta-link span[aria-hidden='true']",
          ".update-components-actor__meta-link",
          ".update-components-actor__title a span[aria-hidden='true']",
          ".update-components-actor__title a",
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
          "span[data-testid='expandable-text-box']",
          ".update-components-update-v2__commentary span[dir='ltr']",
          ".update-components-update-v2__commentary",
          ".update-components-text-view span[dir='ltr']",
          ".update-components-text-view",
          ".update-components-text span[dir='ltr']",
          ".update-components-text",
          ".feed-shared-update-v2__description-wrapper span[dir='ltr']",
          ".feed-shared-update-v2__description-wrapper",
          ".feed-shared-update-v2__description span[dir='ltr']",
          ".feed-shared-update-v2__description",
          ".feed-shared-text span[dir='ltr']",
          ".feed-shared-text",
          ".attributed-text-segment-list__content",
          ".update-components-update-v2__commentary .break-words",
          ".feed-shared-update-v2__description .break-words",
        ];
        const metricScopeSelectors = [
          ".social-details-social-counts",
          ".social-details-social-activity",
          ".feed-shared-social-action-bar",
        ];
        const reactionCountSelectors = [
          ".social-details-social-counts__reactions-count",
          ".social-details-social-counts__social-proof-text",
          "[aria-label*='reaction']",
          "[aria-label*='reactions']",
          "[aria-label*='curtida']",
          "[aria-label*='curtidas']",
        ];
        const commentCountSelectors = [
          "button[aria-label*='comment']",
          "button[aria-label*='coment']",
          "a[aria-label*='comment']",
          "a[aria-label*='coment']",
          "span[aria-label*='comment']",
          "span[aria-label*='coment']",
        ];
        const shareCountSelectors = [
          "button[aria-label*='repost']",
          "button[aria-label*='share']",
          "button[aria-label*='compart']",
          "a[aria-label*='repost']",
          "a[aria-label*='share']",
          "a[aria-label*='compart']",
          "span[aria-label*='repost']",
          "span[aria-label*='share']",
          "span[aria-label*='compart']",
        ];
        const staticContainerSelectors = [
          "div.feed-shared-update-v2",
          "div.occludable-update",
          "div[data-id^='urn:li:activity:']",
          "div[data-urn^='urn:li:activity:']",
          "div[data-id^='urn:li:ugcPost:']",
          "div[data-id^='urn:li:share:']",
          "[data-urn*='urn:li:activity:']",
          "[data-urn*='urn:li:ugcPost:']",
          "article",
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

        function isVisible(
          element: HTMLElement | null,
        ): element is HTMLElement {
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

        function isSocialProofOrMetricsText(value: string): boolean {
          if (socialProofPattern.test(value)) return true;
          if (socialContextPattern.test(value)) return true;
          const withoutNumbers = value.replace(/\d+/g, "").trim();
          if (withoutNumbers.length < 15 && reactionPattern.test(value))
            return true;
          return false;
        }

        function getHeaderScope(root: ParentNode): ParentNode {
          for (const selector of headerScopeSelectors) {
            const elements = Array.from(
              root.querySelectorAll<HTMLElement>(selector),
            );
            if (elements.length === 0) continue;
            if (elements.length >= 2) {
              for (let i = elements.length - 1; i >= 0; i--) {
                const text = normalizeWhitespace(elements[i].innerText) ?? "";
                if (!socialContextPattern.test(text) && text.length > 3) {
                  return elements[i];
                }
              }
              return elements[elements.length - 1];
            }
            return elements[0];
          }
          return root;
        }

        function collectSearchRoots(root: ParentNode): ParentNode[] {
          const searchRoots: ParentNode[] = [root];
          let current = root instanceof HTMLElement ? root.parentElement : null;
          for (let depth = 0; current && depth < 20; depth += 1) {
            searchRoots.push(current);
            current = current.parentElement;
          }
          return searchRoots;
        }

        function collectVisibleTextCandidates(
          root: ParentNode,
          minLength = 12,
          maxLength = 700,
        ): string[] {
          const values: string[] = [];
          const seen = new Set<string>();
          const elements = root.querySelectorAll<HTMLElement>(
            "span, div, p, a, li",
          );
          for (const element of elements) {
            if (!isVisible(element)) {
              continue;
            }
            const text = normalizeWhitespace(element.innerText);
            if (!text || text.length < minLength || text.length > maxLength) {
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
          const sorted = [...values].sort(
            (left, right) => right.length - left.length,
          );
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

        function escapeRegExp(value: string): string {
          return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        }

        function sanitizeAuthorName(value: string | null): string | null {
          const cleaned = normalizeWhitespace(
            value
              ?.split(/\s*[·•]\s*/)[0]
              .replace(/[✓✔☑]/g, " ")
              .replace(/\s+\d+(?:º|°|st|nd|rd|th)\+?$/i, " "),
          );
          if (!cleaned || socialContextPattern.test(cleaned)) {
            return null;
          }
          return cleaned;
        }

        function sanitizeAuthorTitle(
          value: string | null,
          authorName: string | null,
        ): string | null {
          let cleaned = normalizeWhitespace(value);
          if (authorName && cleaned) {
            const authorPrefixPattern = new RegExp(
              `^${escapeRegExp(authorName)}\\s*[·•-]?\\s*`,
              "i",
            );
            cleaned = normalizeWhitespace(
              cleaned.replace(authorPrefixPattern, " "),
            );
          }
          if (
            !cleaned ||
            cleaned === authorName ||
            socialContextPattern.test(cleaned)
          ) {
            return null;
          }
          cleaned = normalizeWhitespace(
            cleaned
              .replace(followCtaPattern, " ")
              .replace(relativeTimeTokenPattern, " ")
              .replace(authorTitleNoisePattern, " ")
              .replace(/\b\d+(?:º|°|st|nd|rd|th)\+?\b/gi, " ")
              .replace(/[·•]/g, " "),
          );
          if (
            !cleaned ||
            cleaned === authorName ||
            timestampPattern.test(cleaned)
          ) {
            return null;
          }
          return cleaned;
        }

        function sanitizePostText(
          value: string | null,
          authorName: string | null,
          authorTitle: string | null,
        ): string | null {
          let cleaned = normalizeWhitespace(
            value?.replace(postTextCollapsePattern, " "),
          );
          if (!cleaned) return null;
          if (authorName && authorTitle) {
            const combinedPrefixPattern = new RegExp(
              `^${escapeRegExp(authorName)}\\s*[·•]\\s*${escapeRegExp(authorTitle)}\\s*`,
              "i",
            );
            cleaned = cleaned.replace(combinedPrefixPattern, "");
          }
          if (authorName) {
            const authorPrefixPattern = new RegExp(
              `^${escapeRegExp(authorName)}\\s*[·•].{0,220}?\\b(?:seguir|follow)\\b\\s*`,
              "i",
            );
            cleaned = cleaned.replace(authorPrefixPattern, "");
            const authorDegreePattern = new RegExp(
              `^${escapeRegExp(authorName)}\\s*[·•]\\s*(?:\\d+[º°]\\+?\\s*)?`,
              "i",
            );
            cleaned = cleaned.replace(authorDegreePattern, "");
          }
          if (authorTitle && cleaned.startsWith(authorTitle)) {
            cleaned = cleaned.slice(authorTitle.length);
          }
          cleaned = cleaned.replace(
            /^[^.!?]{0,220}\b(?:seguir|follow)\b\s*/i,
            "",
          );
          cleaned = cleaned.replace(
            /^(?:acessar meu site|acesse meu site|visit website)\b\s*/i,
            "",
          );
          return normalizeWhitespace(cleaned);
        }

        function looksLikeAuthorName(value: string): boolean {
          if (value.length > 80 || /\d/.test(value)) return false;
          if (isActionOrNoiseText(value) || socialContextPattern.test(value))
            return false;
          if (/[|@]/.test(value)) return false;
          const parts = value.split(/\s+/).filter(Boolean);
          return parts.length >= 1 && parts.length <= 6;
        }

        function extractAuthorFromMetaLine(value: string | null): {
          authorName: string | null;
          authorTitle: string | null;
        } {
          const cleaned = normalizeWhitespace(value);
          if (!cleaned) return { authorName: null, authorTitle: null };
          const bulletIndex = cleaned.indexOf("•");
          if (bulletIndex <= 0) return { authorName: null, authorTitle: null };
          const maybeName = sanitizeAuthorName(cleaned.slice(0, bulletIndex));
          if (!maybeName || !looksLikeAuthorName(maybeName)) {
            return { authorName: null, authorTitle: null };
          }
          let remainder = normalizeWhitespace(cleaned.slice(bulletIndex + 1));
          if (!remainder) return { authorName: maybeName, authorTitle: null };
          remainder = normalizeWhitespace(
            remainder
              .replace(followCtaPattern, " ")
              .replace(relativeTimeTokenPattern, " ")
              .replace(/[·•]/g, " "),
          );
          return { authorName: maybeName, authorTitle: remainder };
        }

        function extractAuthorNameFromControlLabel(
          root: ParentNode,
        ): string | null {
          const labeledElements =
            root instanceof HTMLElement
              ? [
                  root,
                  ...Array.from(
                    root.querySelectorAll<HTMLElement>("[aria-label]"),
                  ),
                ]
              : Array.from(root.querySelectorAll<HTMLElement>("[aria-label]"));

          for (const element of labeledElements) {
            const ariaLabel = normalizeWhitespace(
              element.getAttribute("aria-label"),
            );
            if (!ariaLabel) {
              continue;
            }
            const match = ariaLabel.match(controlMenuAuthorPattern);
            const candidate = sanitizeAuthorName(match?.[1] ?? null);
            if (candidate && candidate.length <= 120) {
              return candidate;
            }
          }

          return null;
        }

        function collectSelectorTexts(
          root: ParentNode,
          selectors: string[],
        ): string[] {
          const values: string[] = [];
          const seen = new Set<string>();
          for (const selector of selectors) {
            for (const element of root.querySelectorAll<HTMLElement>(
              selector,
            )) {
              const value = normalizeWhitespace(
                element.innerText || element.textContent,
              );
              if (!value || seen.has(value)) continue;
              seen.add(value);
              values.push(value);
            }
          }
          return values;
        }

        function collectStructuredTexts(
          root: ParentNode,
          selectors: string[],
        ): string[] {
          const values: string[] = [];
          const seen = new Set<string>();
          for (const selector of selectors) {
            for (const element of root.querySelectorAll<HTMLElement>(
              selector,
            )) {
              const value = normalizeWhitespace(
                element.textContent ?? element.innerText,
              );
              if (
                !value ||
                value.length < 20 ||
                value.length > 8000 ||
                seen.has(value)
              )
                continue;
              seen.add(value);
              values.push(value);
            }
          }
          return values;
        }

        function resolveAuthorName(root: ParentNode): string | null {
          const authorFromControlLabel =
            extractAuthorNameFromControlLabel(root);
          if (authorFromControlLabel) {
            return authorFromControlLabel;
          }

          const headerScope = getHeaderScope(root);
          for (const candidate of collectSelectorTexts(
            headerScope,
            authorNameSelectors,
          )) {
            const fromMeta = extractAuthorFromMetaLine(candidate);
            if (fromMeta.authorName) return fromMeta.authorName;
            const sanitized = sanitizeAuthorName(candidate);
            if (sanitized && looksLikeAuthorName(sanitized)) return sanitized;
          }
          return fallbackAuthorName(headerScope);
        }

        function resolveAuthorTitle(
          root: ParentNode,
          authorName: string | null,
        ): string | null {
          const headerScope = getHeaderScope(root);
          for (const candidate of collectSelectorTexts(
            headerScope,
            authorTitleSelectors,
          )) {
            const sanitized = sanitizeAuthorTitle(candidate, authorName);
            if (sanitized) return sanitized;
          }
          for (const candidate of collectSelectorTexts(
            headerScope,
            authorNameSelectors,
          )) {
            const fromMeta = extractAuthorFromMetaLine(candidate);
            if (
              fromMeta.authorName &&
              fromMeta.authorName === authorName &&
              fromMeta.authorTitle
            ) {
              return fromMeta.authorTitle;
            }
          }
          return fallbackAuthorTitle(headerScope, authorName);
        }

        function isLikelyAuthorText(
          value: string,
          authorName: string | null,
          authorTitle: string | null,
        ): boolean {
          if (!value) return false;
          if (value === authorName || value === authorTitle) return true;
          if (authorTitle && value.length < authorTitle.length + 30) {
            if (value.startsWith(authorTitle.slice(0, 40))) return true;
            if (authorTitle.startsWith(value.slice(0, 40))) return true;
          }
          if (authorName && value.startsWith(authorName)) {
            const afterName = value.slice(authorName.length).trim();
            if (
              afterName.startsWith("•") ||
              afterName.startsWith("·") ||
              afterName.length < 30
            )
              return true;
          }
          return false;
        }

        function extractPostText(
          root: ParentNode,
          authorName: string | null,
          authorTitle: string | null,
        ): string | null {
          const expandableTextCandidates = collectStructuredTexts(root, [
            "span[data-testid='expandable-text-box']",
          ])
            .map((c) => sanitizePostText(c, authorName, authorTitle))
            .filter(
              (c): c is string =>
                !!c &&
                c.length >= 20 &&
                !isActionOrNoiseText(c) &&
                !isSocialProofOrMetricsText(c) &&
                !followCtaPattern.test(c) &&
                !isLikelyAuthorText(c, authorName, authorTitle),
            );
          if (expandableTextCandidates.length > 0) {
            return chooseLongestText(expandableTextCandidates);
          }

          const structuredCandidates = collectStructuredTexts(
            root,
            postTextSelectors,
          )
            .map((c) => sanitizePostText(c, authorName, authorTitle))
            .filter(
              (c): c is string =>
                !!c &&
                c.length >= 20 &&
                !isActionOrNoiseText(c) &&
                !isSocialProofOrMetricsText(c) &&
                !followCtaPattern.test(c) &&
                !isLikelyAuthorText(c, authorName, authorTitle),
            );
          if (structuredCandidates.length > 0) {
            return chooseLongestText(structuredCandidates);
          }

          for (const selector of postTextSelectors) {
            for (const element of root.querySelectorAll<HTMLElement>(
              selector,
            )) {
              const text = sanitizePostText(
                normalizeWhitespace(element.innerText),
                authorName,
                authorTitle,
              );
              if (
                text &&
                text.length >= 20 &&
                !isActionOrNoiseText(text) &&
                !isSocialProofOrMetricsText(text) &&
                !isLikelyAuthorText(text, authorName, authorTitle)
              ) {
                return text;
              }
            }
          }

          // Strategy 3: Generic span[dir='ltr'] outside header scope
          const headerScope = getHeaderScope(root);
          const dirLtrCandidates: string[] = [];
          for (const span of root.querySelectorAll<HTMLElement>(
            "span[dir='ltr']",
          )) {
            if (
              headerScope instanceof HTMLElement &&
              headerScope.contains(span)
            ) {
              continue;
            }
            const text = sanitizePostText(
              normalizeWhitespace(span.textContent ?? span.innerText),
              authorName,
              authorTitle,
            );
            if (
              text &&
              text.length >= 30 &&
              !isActionOrNoiseText(text) &&
              !isSocialProofOrMetricsText(text) &&
              !followCtaPattern.test(text) &&
              !isLikelyAuthorText(text, authorName, authorTitle)
            ) {
              dirLtrCandidates.push(text);
            }
          }
          if (dirLtrCandidates.length > 0) {
            return chooseLongestText(dirLtrCandidates);
          }

          return fallbackPostText(root, authorName, authorTitle);
        }

        function normalizeLinkedInPostUrl(
          rawUrl: string | null | undefined,
        ): string | null {
          const cleaned = normalizeWhitespace(rawUrl);
          if (!cleaned) {
            return null;
          }

          if (postUrnPattern.test(cleaned)) {
            return buildLinkedInFeedUrlFromUrn(cleaned);
          }

          try {
            const parsed = new URL(cleaned, window.location.origin);
            for (const key of [
              "url",
              "destRedirectUrl",
              "destUrl",
              "redirect",
              "redirectUrl",
              "destination",
              "href",
            ]) {
              const nestedValue = normalizeWhitespace(
                parsed.searchParams.get(key),
              );
              if (!nestedValue) {
                continue;
              }
              const nestedResolved = normalizeLinkedInPostUrl(nestedValue);
              if (nestedResolved) {
                return nestedResolved;
              }
            }

            const updateEntityUrn = normalizeWhitespace(
              parsed.searchParams.get("updateEntityUrn"),
            );
            if (updateEntityUrn && postUrnPattern.test(updateEntityUrn)) {
              return `${parsed.origin}/feed/update/${updateEntityUrn.replace(/\/+$/, "")}/`;
            }

            const pathname = parsed.pathname.replace(/\/+$/, "");
            const isCanonicalPostsPath = /\/posts\/[^/]+$/i.test(pathname);
            if (
              isCanonicalPostsPath ||
              pathname.includes("/feed/update/") ||
              pathname.includes("/activity-") ||
              pathname.includes("/activity/")
            ) {
              return `${parsed.origin}${pathname}/`;
            }

            const fullUrlStr = parsed.toString();
            const encodedUrnMatch = fullUrlStr.match(
              /urn(?:%3A|:)li(?:%3A|:)(?:activity|ugcPost|share|update)(?:%3A|:)(\d+)/i,
            );
            if (encodedUrnMatch) {
              return `https://www.linkedin.com/feed/update/urn:li:activity:${encodedUrnMatch[1]}/`;
            }
          } catch {
            return cleaned;
          }

          return null;
        }

        function buildLinkedInFeedUrlFromUrn(
          postUrn: string | null,
        ): string | null {
          const normalizedUrn = normalizeWhitespace(postUrn);
          if (!normalizedUrn || !postUrnPattern.test(normalizedUrn)) {
            return null;
          }
          return `https://www.linkedin.com/feed/update/${normalizedUrn}/`;
        }

        function extractPostUrnFromMetadataValue(
          value: string | null | undefined,
        ): string | null {
          const normalized = normalizeWhitespace(value);
          if (!normalized) {
            return null;
          }

          const directUrnMatch = normalized.match(postUrnPattern);
          if (directUrnMatch) {
            return directUrnMatch[0];
          }

          const encodedUrnMatch = normalized.match(encodedPostUrnPattern);
          if (encodedUrnMatch) {
            return `urn:li:${encodedUrnMatch[1]}:${encodedUrnMatch[2]}`;
          }

          const shareMatch = normalized.match(metadataShareIdPattern);
          if (shareMatch) {
            return `urn:li:share:${shareMatch[1]}`;
          }

          const ugcPostMatch = normalized.match(metadataUgcPostIdPattern);
          if (ugcPostMatch) {
            return `urn:li:ugcPost:${ugcPostMatch[1]}`;
          }

          const keyedIdMatch = normalized.match(metadataKeyedUrnIdPattern);
          if (keyedIdMatch) {
            return `urn:li:${keyedIdMatch[1]}:${keyedIdMatch[2]}`;
          }

          return null;
        }

        function extractPostUrn(root: ParentNode): string | null {
          // Walk up ancestors and check ALL attributes for activity URN pattern
          let currentElement = root instanceof HTMLElement ? root : null;
          for (let depth = 0; currentElement && depth < 30; depth += 1) {
            for (const attr of Array.from(currentElement.attributes)) {
              const urn = extractPostUrnFromMetadataValue(attr.value);
              if (urn) return urn;
            }
            currentElement = currentElement.parentElement;
          }

          // Search descendants — any element with any attribute containing URN
          for (const element of root.querySelectorAll<HTMLElement>("*")) {
            for (const attr of Array.from(element.attributes)) {
              const urn = extractPostUrnFromMetadataValue(attr.value);
              if (urn) return urn;
            }
          }

          return null;
        }

        function firstPostUrl(root: ParentNode): string | null {
          // Strategy 1: URN from data attributes (most reliable — scans all attributes)
          const urnUrl = buildLinkedInFeedUrlFromUrn(extractPostUrn(root));
          if (urnUrl) return urnUrl;

          // Strategy 2: Known selectors in container + ancestors
          for (const searchRoot of collectSearchRoots(root)) {
            for (const selector of postUrlSelectors) {
              const anchor =
                searchRoot.querySelector<HTMLAnchorElement>(selector);
              const href = normalizeLinkedInPostUrl(anchor?.href);
              if (href) return href;
            }
          }

          // Strategy 3: Link wrapping <time> or link with timestamp text
          for (const link of root.querySelectorAll<HTMLAnchorElement>(
            "a[href]",
          )) {
            const linkText = (normalizeWhitespace(link.innerText) ?? "").trim();
            if (link.querySelector("time") || timestampPattern.test(linkText)) {
              const href = normalizeLinkedInPostUrl(link.href);
              if (href) return href;
            }
          }

          // Strategy 4: Any <a> with LinkedIn post URL pattern
          for (const searchRoot of collectSearchRoots(root)) {
            const anchors =
              searchRoot.querySelectorAll<HTMLAnchorElement>("a[href]");
            for (const anchor of anchors) {
              const href = normalizeLinkedInPostUrl(anchor.href);
              if (href) return href;
            }
          }

          // Strategy 5: Extract activity ID from any href containing it
          for (const searchRoot of collectSearchRoots(root)) {
            const anchors =
              searchRoot.querySelectorAll<HTMLAnchorElement>("a[href]");
            for (const anchor of anchors) {
              const hrefText = anchor.href ?? "";
              const activityMatch = hrefText.match(/activity[:\-](\d{15,25})/i);
              if (activityMatch) {
                return `https://www.linkedin.com/feed/update/urn:li:activity:${activityMatch[1]}/`;
              }
            }
          }

          // Strategy 6: Scan all attributes for raw LinkedIn ids as a last fallback.
          for (const element of root.querySelectorAll<HTMLElement>("*")) {
            for (const attr of Array.from(element.attributes)) {
              const idMatch = attr.value.match(rawLinkedInIdPattern);
              if (idMatch) {
                return `https://www.linkedin.com/feed/update/urn:li:activity:${idMatch[1]}/`;
              }
            }
          }

          // Also check ancestors for raw LinkedIn ids.
          let urlAncestor =
            root instanceof HTMLElement ? root.parentElement : null;
          for (let depth = 0; urlAncestor && depth < 30; depth += 1) {
            for (const attr of Array.from(urlAncestor.attributes)) {
              const idMatch = attr.value.match(rawLinkedInIdPattern);
              if (idMatch) {
                return `https://www.linkedin.com/feed/update/urn:li:activity:${idMatch[1]}/`;
              }
            }
            urlAncestor = urlAncestor.parentElement;
          }

          return null;
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

        function readElementText(element: HTMLElement | null): string | null {
          if (!element) {
            return null;
          }
          const ariaLabel = normalizeWhitespace(
            element.getAttribute("aria-label"),
          );
          const text = normalizeWhitespace(
            element.innerText || element.textContent,
          );
          return normalizeWhitespace(
            [ariaLabel, text].filter(Boolean).join(" "),
          );
        }

        function parseNamedMetricValue(
          rawText: string | null,
          pattern: RegExp,
        ): number {
          if (!rawText) {
            return 0;
          }
          const source = pattern.source;
          const flags = pattern.flags.includes("g")
            ? pattern.flags
            : `${pattern.flags}g`;
          const regex = new RegExp(
            `(\\d+(?:[\\.,]\\d+)?)(\\s*[km])?\\s*(?:${source})`,
            flags,
          );
          let lastMatch = null;
          for (const match of rawText.toLowerCase().matchAll(regex)) {
            lastMatch = match;
          }
          if (!lastMatch) {
            return 0;
          }
          return parseMetricValue(`${lastMatch[1]}${lastMatch[2] ?? ""}`);
        }

        function findMetricBySelectors(
          root: ParentNode,
          selectors: string[],
          pattern?: RegExp,
        ): number {
          for (const selector of selectors) {
            for (const element of root.querySelectorAll<HTMLElement>(
              selector,
            )) {
              const text = readElementText(element);
              if (!text) {
                continue;
              }
              if (pattern) {
                const namedMetric = parseNamedMetricValue(text, pattern);
                if (namedMetric > 0) {
                  return namedMetric;
                }
                continue;
              }
              const parsed = parseMetricValue(text);
              if (parsed > 0) {
                return parsed;
              }
            }
          }
          return 0;
        }

        function findNamedMetric(
          root: ParentNode,
          selectors: string[],
          pattern: RegExp,
        ): number {
          const directMetric = findMetricBySelectors(root, selectors, pattern);
          if (directMetric > 0) {
            return directMetric;
          }

          const scope = getMetricScope(root);
          for (const element of scope.querySelectorAll<HTMLElement>(
            "button, a, span, div, li",
          )) {
            const text = readElementText(element);
            if (!text) {
              continue;
            }
            const namedMetric = parseNamedMetricValue(text, pattern);
            if (namedMetric > 0) {
              return namedMetric;
            }
          }
          return 0;
        }

        function findReactionMetric(root: ParentNode): number {
          const directMetric = findMetricBySelectors(
            root,
            reactionCountSelectors,
          );
          if (directMetric > 0) {
            return directMetric;
          }

          const scope = getMetricScope(root);
          for (const element of scope.querySelectorAll<HTMLElement>(
            "button, a, span, div, li",
          )) {
            const text = readElementText(element);
            if (!text) {
              continue;
            }
            if (
              commentPattern.test(text) ||
              sharePattern.test(text) ||
              socialContextPattern.test(text)
            ) {
              continue;
            }
            const namedMetric = parseNamedMetricValue(text, reactionPattern);
            if (namedMetric > 0) {
              return namedMetric;
            }

            const othersMatch = text.match(reactionSocialProofOthersPattern);
            if (othersMatch) {
              const othersCount = parseMetricValue(
                othersMatch[1] ?? othersMatch[2],
              );
              if (othersCount > 0) {
                return othersCount + 1;
              }
            }

            const peopleMatch = text.match(reactionSocialProofTotalPattern);
            if (peopleMatch) {
              const peopleCount = parseMetricValue(peopleMatch[1]);
              if (peopleCount > 0) {
                return peopleCount;
              }
            }

            if (/^\d+(?:[\.,]\d+)?\s*[km]?$/i.test(text)) {
              return parseMetricValue(text);
            }
          }
          return 0;
        }

        function fallbackAuthorName(root: ParentNode): string | null {
          const headerScope = getHeaderScope(root);
          const candidates = collectVisibleTextCandidates(headerScope, 3);
          for (const candidate of candidates) {
            const fromMeta = extractAuthorFromMetaLine(candidate);
            if (fromMeta.authorName) return fromMeta.authorName;
            if (candidate.length > 80 || isActionOrNoiseText(candidate)) {
              continue;
            }
            if (socialContextPattern.test(candidate)) {
              continue;
            }
            if (
              /\b(linkedin|premium|seguir|follow|repost)\b/i.test(candidate)
            ) {
              continue;
            }
            if (!looksLikeAuthorName(candidate)) {
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
            const fromMeta = extractAuthorFromMetaLine(candidate);
            if (
              fromMeta.authorName &&
              fromMeta.authorName === authorName &&
              fromMeta.authorTitle
            ) {
              return fromMeta.authorTitle;
            }
            if (candidate === authorName) {
              continue;
            }
            if (candidate.length > 160 || isActionOrNoiseText(candidate)) {
              continue;
            }
            if (socialContextPattern.test(candidate)) {
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
          const candidates = collectVisibleTextCandidates(root, 20, 5000);
          const filtered = candidates
            .map((candidate) =>
              sanitizePostText(candidate, authorName, authorTitle),
            )
            .filter((candidate): candidate is string => {
              if (!candidate) return false;
              if (isLikelyAuthorText(candidate, authorName, authorTitle)) {
                return false;
              }
              if (candidate.length < 20 || candidate.length > 5000) {
                return false;
              }
              if (
                isActionOrNoiseText(candidate) ||
                isSocialProofOrMetricsText(candidate)
              ) {
                return false;
              }
              return true;
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
            .match(
              /gostar|like|comentar|comment|compartilhar|share|repost|enviar|send/g,
            );
          return matches ? Array.from(new Set(matches)).sort().join("|") : "";
        }

        function findActionAnchors(scope: ParentNode): HTMLElement[] {
          const anchors =
            scope.querySelectorAll<HTMLElement>("button, span, div");
          return Array.from(anchors).filter((element) => {
            const text = normalizeWhitespace(element.innerText);
            return !!text && text.length <= 40 && actionTextPattern.test(text);
          });
        }

        function findActionBarFromAnchor(
          anchor: HTMLElement,
        ): HTMLElement | null {
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
          if (allText.length < 40 || allText.length > 20000) {
            return false;
          }
          const hasPostUrl = !!firstPostUrl(container);
          const hasMetrics =
            findReactionMetric(container) > 0 ||
            findNamedMetric(container, commentCountSelectors, commentPattern) >
              0 ||
            findNamedMetric(container, shareCountSelectors, sharePattern) > 0;
          const hasHeader = !!resolveAuthorName(getHeaderScope(container));
          return hasPostUrl || hasMetrics || hasHeader;
        }

        function findContainerFromActionBar(
          actionBar: HTMLElement,
        ): HTMLElement | null {
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
            const elements = Array.from(
              document.querySelectorAll<HTMLElement>(selector),
            );
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
          discardReasonCounts.set(
            reason,
            (discardReasonCounts.get(reason) ?? 0) + 1,
          );
        }

        for (const container of containers) {
          const authorName = resolveAuthorName(container);
          const authorTitle = resolveAuthorTitle(container, authorName);
          const postText = extractPostText(container, authorName, authorTitle);
          const postUrl = firstPostUrl(container);
          const likes = findReactionMetric(container);
          const comments = findNamedMetric(
            container,
            commentCountSelectors,
            commentPattern,
          );
          const shares = findNamedMetric(
            container,
            shareCountSelectors,
            sharePattern,
          );
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
        const discard_reason_counts = Object.fromEntries(
          discardReasonCounts.entries(),
        );

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
            error_message:
              posts.length === 0
                ? "Nenhum post valido foi confirmado pelas heuristicas atuais."
                : null,
          },
        } satisfies InPageScanResult;
      },
    });

    const scanResult = results[0]?.result as
      | ActiveTabPostScanResult
      | undefined;
    if (scanResult) {
      try {
        const response = (await chrome.tabs.sendMessage(tab.id, {
          type: MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS,
        })) as ExtensionMessageResponse<CapturePreview[]>;
        if (response.ok && (response.data?.length ?? 0) > 0) {
          const posts = mergePreviewLists(
            scanResult.posts,
            response.data ?? [],
          );
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
      error instanceof Error
        ? error.message
        : "Falha desconhecida ao analisar a aba ativa.";
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

  const candidates: ImportedPostStatusCandidate[] = scan.posts.map(
    (preview) => {
      const normalized = normalizePreview(preview);
      return {
        candidate_key: buildPreviewKey(normalized),
        post_url: normalized.post_url,
        canonical_post_url: normalized.post_url,
        post_text: normalized.post_text,
        author_name: normalized.author_name,
      };
    },
  );

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
      (preview) =>
        !importedKeys.has(buildPreviewKey(normalizePreview(preview))),
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
      await clearSelectedPreviews();
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS:
      return { ok: true, data: await listPostsFromActiveTab() };

    case MESSAGE_TYPES.GET_ACTIVE_TAB_SCAN:
      return { ok: true, data: await getActiveTabScan() };

    case MESSAGE_TYPES.SAVE_CAPTURED_POST:
      await saveSelectedPreview(message.payload);
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.REMOVE_CAPTURED_POST:
      await removeSelectedPreview(message.payload.candidateKey);
      return { ok: true, data: await getState() };

    case MESSAGE_TYPES.CLEAR_CAPTURED_POSTS:
      await clearSelectedPreviews();
      await clearPreview();
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
