import type { CapturePreview, CapturedFrom } from "../shared/types";

const ACTION_TEXT_PATTERN =
  /\b(gostar|like|comentar|comment|compartilhar|share|repost|enviar|send)\b/i;
const SOCIAL_CONTEXT_PATTERN =
  /\b(gostou|liked|comentou|commented|repostou|reposted|compartilhou|shared|seguem a empresa|follows the company|conexoes seguem|connections follow)\b/i;
const FOLLOW_CTA_PATTERN =
  /\b(seguir|follow|conectar|connect|acessar meu site|acesse meu site|visit website)\b/i;
const TIMESTAMP_PATTERN =
  /^(\d+\s*(min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo)\b|edited|editado|promoted|patrocinado)$/i;
const RELATIVE_TIME_TOKEN_PATTERN =
  /\b(\d+\s*(?:min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo))\b/i;
const POST_TEXT_COLLAPSE_PATTERN = /(?:\.\.\.|…)\s*(mais|more)\b/gi;
const REACTION_PATTERN = /reaction|reactions|reac|curtida|curtidas|like|likes/i;
const COMMENT_PATTERN = /comment|comments|comentario|comentarios|comentário|comentários/i;
const SHARE_PATTERN = /repost|reposts|share|shares|compartilhamento|compartilhamentos|compartilhar/i;

const POST_URL_SELECTORS = [
  ".update-components-actor__meta-link",
  ".feed-shared-actor__container-link",
  ".feed-shared-actor__meta-link",
  ".update-components-actor__sub-description-link",
  ".feed-shared-actor__sub-description-link",
  'a[href*="/posts/"]',
  'a[href*="/feed/update/"]',
  'a[href*="/activity-"]',
];

const POST_URN_ATTRIBUTE_SELECTORS =
  "[data-urn], [data-id], [data-activity-urn], [data-entity-urn], [data-update-urn], [data-content-urn]";
const POST_URN_PATTERN = /urn:li:(activity|share|ugcPost|update):\d+/i;

const AUTHOR_NAME_SELECTORS = [
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

const AUTHOR_TITLE_SELECTORS = [
  ".update-components-actor__description",
  ".feed-shared-actor__description",
  ".update-components-actor__subtitle span[aria-hidden='true']",
  ".update-components-actor__sub-description",
  ".feed-shared-actor__sub-description",
];

const POST_TEXT_SELECTORS = [
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

const METRIC_SCOPE_SELECTORS = [
  ".social-details-social-counts",
  ".social-details-social-activity",
  ".feed-shared-social-action-bar",
];

const REACTION_COUNT_SELECTORS = [
  ".social-details-social-counts__reactions-count",
  ".social-details-social-counts__social-proof-text",
  "[aria-label*='reaction']",
  "[aria-label*='reactions']",
  "[aria-label*='curtida']",
  "[aria-label*='curtidas']",
];

const COMMENT_COUNT_SELECTORS = [
  "button[aria-label*='comment']",
  "button[aria-label*='coment']",
  "a[aria-label*='comment']",
  "a[aria-label*='coment']",
  "span[aria-label*='comment']",
  "span[aria-label*='coment']",
];

const SHARE_COUNT_SELECTORS = [
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

const STATIC_CONTAINER_SELECTORS = [
  "div.feed-shared-update-v2",
  "div.occludable-update",
  "div[data-id^='urn:li:activity:']",
  "div[data-urn^='urn:li:activity:']",
  "article",
  ".update-components-actor",
];

const HEADER_SCOPE_SELECTORS = [
  ".update-components-actor",
  ".feed-shared-actor",
  ".update-components-actor__container",
  ".feed-shared-actor__container",
];

function normalizeWhitespace(value: string | null | undefined): string | null {
  if (!value) return null;
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 0 ? normalized : null;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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
  if (ACTION_TEXT_PATTERN.test(value)) return true;
  if (TIMESTAMP_PATTERN.test(value)) return true;
  if (FOLLOW_CTA_PATTERN.test(value)) return true;
  return false;
}

function sanitizeAuthorName(value: string | null): string | null {
  const cleaned = normalizeWhitespace(
    value
      ?.split(/\s*[·•]\s*/)[0]
      .replace(/[✓✔☑]/g, " ")
      .replace(/\s+\d+(?:º|°|st|nd|rd|th)\+?$/i, " "),
  );
  if (!cleaned || SOCIAL_CONTEXT_PATTERN.test(cleaned)) {
    return null;
  }
  return cleaned;
}

function sanitizeAuthorTitle(
  value: string | null,
  authorName: string | null,
): string | null {
  const cleaned = normalizeWhitespace(value);
  if (!cleaned || cleaned === authorName || SOCIAL_CONTEXT_PATTERN.test(cleaned)) {
    return null;
  }
  return normalizeWhitespace(cleaned.replace(FOLLOW_CTA_PATTERN, " "));
}

function sanitizePostText(
  value: string | null,
  authorName: string | null,
  authorTitle: string | null,
): string | null {
  let cleaned = normalizeWhitespace(value?.replace(POST_TEXT_COLLAPSE_PATTERN, " "));
  if (!cleaned) {
    return null;
  }
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
  }
  if (authorTitle && cleaned.startsWith(authorTitle)) {
    cleaned = cleaned.slice(authorTitle.length);
  }
  cleaned = cleaned.replace(/^[^.!?]{0,220}\b(?:seguir|follow)\b\s*/i, "");
  cleaned = cleaned.replace(/^(?:acessar meu site|acesse meu site|visit website)\b\s*/i, "");
  return normalizeWhitespace(cleaned);
}

function looksLikeAuthorName(value: string): boolean {
  if (value.length > 80 || /\d/.test(value)) {
    return false;
  }
  if (isActionOrNoiseText(value) || SOCIAL_CONTEXT_PATTERN.test(value)) {
    return false;
  }
  if (/[|@]/.test(value)) {
    return false;
  }
  const parts = value.split(/\s+/).filter(Boolean);
  return parts.length >= 1 && parts.length <= 6;
}

function getHeaderScope(root: ParentNode): ParentNode {
  for (const selector of HEADER_SCOPE_SELECTORS) {
    const element = root.querySelector<HTMLElement>(selector);
    if (element) {
      return element;
    }
  }
  return root;
}

function collectSearchRoots(root: ParentNode): ParentNode[] {
  const searchRoots: ParentNode[] = [root];
  let current = root instanceof HTMLElement ? root.parentElement : null;
  for (let depth = 0; current && depth < 10; depth += 1) {
    searchRoots.push(current);
    current = current.parentElement;
  }
  return searchRoots;
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
    if (isActionOrNoiseText(text) || SOCIAL_CONTEXT_PATTERN.test(text)) {
      continue;
    }
    if (seen.has(text)) {
      continue;
    }
    seen.add(text);
    values.push(text);
  }

  return values;
}

function collectStructuredTexts(root: ParentNode, selectors: string[]): string[] {
  const values: string[] = [];
  const seen = new Set<string>();

  for (const selector of selectors) {
    for (const element of root.querySelectorAll<HTMLElement>(selector)) {
      const value = normalizeWhitespace(element.textContent ?? element.innerText);
      if (!value || value.length < 20 || value.length > 4000) {
        continue;
      }
      if (seen.has(value)) {
        continue;
      }
      seen.add(value);
      values.push(value);
    }
  }

  return values;
}

function collectSelectorTexts(root: ParentNode, selectors: string[]): string[] {
  const values: string[] = [];
  const seen = new Set<string>();

  for (const selector of selectors) {
    for (const element of root.querySelectorAll<HTMLElement>(selector)) {
      const value = normalizeWhitespace(element.innerText || element.textContent);
      if (!value || seen.has(value)) {
        continue;
      }
      seen.add(value);
      values.push(value);
    }
  }

  return values;
}

function chooseLongestText(values: string[]): string | null {
  const sorted = [...values].sort((left, right) => right.length - left.length);
  return sorted[0] ?? null;
}

function findActionAnchors(scope: ParentNode): HTMLElement[] {
  const anchors = scope.querySelectorAll<HTMLElement>("button, span, div");
  return Array.from(anchors).filter((element) => {
    const text = normalizeWhitespace(element.innerText);
    return !!text && text.length <= 40 && ACTION_TEXT_PATTERN.test(text);
  });
}

function getActionSignature(text: string): string {
  const matches = text
    .toLowerCase()
    .match(/gostar|like|comentar|comment|compartilhar|share|repost|enviar|send/g);
  return matches ? Array.from(new Set(matches)).sort().join("|") : "";
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

function readElementText(element: HTMLElement | null): string | null {
  if (!element) {
    return null;
  }
  const ariaLabel = normalizeWhitespace(element.getAttribute("aria-label"));
  const text = normalizeWhitespace(element.innerText || element.textContent);
  return normalizeWhitespace([ariaLabel, text].filter(Boolean).join(" "));
}

function firstText(root: ParentNode, selectors: string[]): string | null {
  for (const selector of selectors) {
    for (const element of root.querySelectorAll<HTMLElement>(selector)) {
      const value = normalizeWhitespace(element.innerText);
      if (value) {
        return value;
      }
    }
  }
  return null;
}

function extractAuthorFromMetaLine(value: string | null): {
  authorName: string | null;
  authorTitle: string | null;
} {
  const cleaned = normalizeWhitespace(value);
  if (!cleaned) {
    return { authorName: null, authorTitle: null };
  }

  const bulletIndex = cleaned.indexOf("•");
  if (bulletIndex <= 0) {
    return { authorName: null, authorTitle: null };
  }

  const maybeName = sanitizeAuthorName(cleaned.slice(0, bulletIndex));
  if (!maybeName || !looksLikeAuthorName(maybeName)) {
    return { authorName: null, authorTitle: null };
  }

  let remainder = normalizeWhitespace(cleaned.slice(bulletIndex + 1));
  if (!remainder) {
    return { authorName: maybeName, authorTitle: null };
  }

  remainder = normalizeWhitespace(
    remainder
      .replace(FOLLOW_CTA_PATTERN, " ")
      .replace(RELATIVE_TIME_TOKEN_PATTERN, " ")
      .replace(/[·•]/g, " "),
  );
  return {
    authorName: maybeName,
    authorTitle: remainder,
  };
}

function resolveAuthorName(root: ParentNode): string | null {
  for (const candidate of collectSelectorTexts(root, AUTHOR_NAME_SELECTORS)) {
    const authorFromMetaLine = extractAuthorFromMetaLine(candidate);
    if (authorFromMetaLine.authorName) {
      return authorFromMetaLine.authorName;
    }

    const sanitized = sanitizeAuthorName(candidate);
    if (sanitized && looksLikeAuthorName(sanitized)) {
      return sanitized;
    }
  }

  return fallbackAuthorName(root);
}

function resolveAuthorTitle(root: ParentNode, authorName: string | null): string | null {
  for (const candidate of collectSelectorTexts(root, AUTHOR_TITLE_SELECTORS)) {
    const sanitized = sanitizeAuthorTitle(candidate, authorName);
    if (sanitized) {
      return sanitized;
    }
  }

  for (const candidate of collectSelectorTexts(root, AUTHOR_NAME_SELECTORS)) {
    const authorFromMetaLine = extractAuthorFromMetaLine(candidate);
    if (
      authorFromMetaLine.authorName &&
      authorFromMetaLine.authorName === authorName &&
      authorFromMetaLine.authorTitle
    ) {
      return authorFromMetaLine.authorTitle;
    }
  }

  return fallbackAuthorTitle(root, authorName);
}

function normalizeLinkedInPostUrl(rawUrl: string | null | undefined): string | null {
  const cleaned = normalizeWhitespace(rawUrl);
  if (!cleaned) {
    return null;
  }

  try {
    const url = new URL(cleaned, window.location.origin);
    const nestedParamKeys = [
      "url",
      "destRedirectUrl",
      "destUrl",
      "redirect",
      "redirectUrl",
      "destination",
      "href",
    ];
    for (const key of nestedParamKeys) {
      const nestedValue = normalizeWhitespace(url.searchParams.get(key));
      if (!nestedValue) {
        continue;
      }
      const nestedResolvedUrl = normalizeLinkedInPostUrl(nestedValue);
      if (nestedResolvedUrl) {
        return nestedResolvedUrl;
      }
    }

    const updateEntityUrn = normalizeWhitespace(
      url.searchParams.get("updateEntityUrn") ?? url.searchParams.get("updateEntityUrn"),
    );
    if (updateEntityUrn && POST_URN_PATTERN.test(updateEntityUrn)) {
      return `${url.origin}/feed/update/${updateEntityUrn.replace(/\/+$/, "")}/`;
    }

    const pathname = url.pathname.replace(/\/+$/, "");
    if (
      pathname.includes("/posts/") ||
      pathname.includes("/feed/update/") ||
      pathname.includes("/activity-")
    ) {
      return `${url.origin}${pathname}/`;
    }
  } catch {
    return cleaned;
  }

  return null;
}

function buildLinkedInFeedUrlFromUrn(postUrn: string | null): string | null {
  const normalizedUrn = normalizeWhitespace(postUrn);
  if (!normalizedUrn || !POST_URN_PATTERN.test(normalizedUrn)) {
    return null;
  }
  return `https://www.linkedin.com/feed/update/${normalizedUrn}/`;
}

function extractPostUrn(root: ParentNode): string | null {
  const candidates: string[] = [];

  let currentElement = root instanceof HTMLElement ? root : null;
  for (let depth = 0; currentElement && depth < 8; depth += 1) {
    candidates.push(
      ...[
        currentElement.dataset.urn,
        currentElement.dataset.id,
        currentElement.dataset.activityUrn,
        currentElement.dataset.entityUrn,
        currentElement.dataset.updateUrn,
        currentElement.dataset.contentUrn,
        currentElement.getAttribute("data-urn"),
        currentElement.getAttribute("data-id"),
        currentElement.getAttribute("data-activity-urn"),
        currentElement.getAttribute("data-entity-urn"),
        currentElement.getAttribute("data-update-urn"),
        currentElement.getAttribute("data-content-urn"),
      ].filter((value): value is string => !!value),
    );
    currentElement = currentElement.parentElement;
  }

  if (root instanceof HTMLElement) {
    const selfAttributes = [
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
    ];
    candidates.push(...selfAttributes.filter((value): value is string => !!value));
  }

  for (const element of root.querySelectorAll<HTMLElement>(POST_URN_ATTRIBUTE_SELECTORS)) {
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
    const match = candidate.match(POST_URN_PATTERN);
    if (match) {
      return match[0];
    }
  }

  return null;
}

function firstPostUrl(root: ParentNode): string | null {
  for (const searchRoot of collectSearchRoots(root)) {
    for (const selector of POST_URL_SELECTORS) {
      const anchor = searchRoot.querySelector<HTMLAnchorElement>(selector);
      const href = normalizeLinkedInPostUrl(anchor?.href);
      if (href) {
        return href;
      }
    }
  }

  for (const searchRoot of collectSearchRoots(root)) {
    const anchors = searchRoot.querySelectorAll<HTMLAnchorElement>("a[href]");
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
  }

  for (const searchRoot of collectSearchRoots(root)) {
    const postUrl = buildLinkedInFeedUrlFromUrn(extractPostUrn(searchRoot));
    if (postUrl) {
      return postUrl;
    }
  }

  return null;
}

function getMetricScope(root: ParentNode): ParentNode {
  for (const selector of METRIC_SCOPE_SELECTORS) {
    const scope = root.querySelector<HTMLElement>(selector);
    if (scope) {
      return scope;
    }
  }
  return root;
}

function parseMetricValue(rawText: string | null): number {
  if (!rawText) return 0;
  const normalized = rawText.toLowerCase().replace(/\./g, "").replace(/,/g, ".");
  const match = normalized.match(/(\d+(?:\.\d+)?)(\s*[km])?/);
  if (!match) return 0;

  const base = Number(match[1]);
  if (Number.isNaN(base)) return 0;

  const suffix = match[2]?.trim();
  if (suffix === "k") return Math.round(base * 1000);
  if (suffix === "m") return Math.round(base * 1000000);
  return Math.round(base);
}

function parseNamedMetricValue(rawText: string | null, pattern: RegExp): number {
  if (!rawText) {
    return 0;
  }

  const source = pattern.source;
  const flags = pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`;
  const regex = new RegExp(`(\\d+(?:[\\.,]\\d+)?)(\\s*[km])?\\s*(?:${source})`, flags);
  let lastMatch: RegExpExecArray | null = null;
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
    for (const element of root.querySelectorAll<HTMLElement>(selector)) {
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
  for (const element of scope.querySelectorAll<HTMLElement>("button, a, span, div, li")) {
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
  const directMetric = findMetricBySelectors(root, REACTION_COUNT_SELECTORS);
  if (directMetric > 0) {
    return directMetric;
  }

  const scope = getMetricScope(root);
  for (const element of scope.querySelectorAll<HTMLElement>("button, a, span, div, li")) {
    const text = readElementText(element);
    if (!text) {
      continue;
    }
    if (COMMENT_PATTERN.test(text) || SHARE_PATTERN.test(text)) {
      continue;
    }
    const namedMetric = parseNamedMetricValue(text, REACTION_PATTERN);
    if (namedMetric > 0) {
      return namedMetric;
    }
    if (/^\d+(?:[\.,]\d+)?\s*[km]?$/i.test(text)) {
      return parseMetricValue(text);
    }
  }
  return 0;
}

function extractPostText(
  root: ParentNode,
  authorName: string | null,
  authorTitle: string | null,
): string | null {
  const structuredCandidates = collectStructuredTexts(root, POST_TEXT_SELECTORS)
    .map((candidate) => sanitizePostText(candidate, authorName, authorTitle))
    .filter(
      (candidate): candidate is string =>
        !!candidate &&
        candidate.length >= 20 &&
        !isActionOrNoiseText(candidate) &&
        !SOCIAL_CONTEXT_PATTERN.test(candidate) &&
        !FOLLOW_CTA_PATTERN.test(candidate) &&
        !RELATIVE_TIME_TOKEN_PATTERN.test(candidate) &&
        candidate !== authorName &&
        candidate !== authorTitle,
    );
  if (structuredCandidates.length > 0) {
    const preferredCandidate = structuredCandidates.find(
      (candidate) => /[.!?]/.test(candidate) || candidate.length > 70,
    );
    return preferredCandidate ?? chooseLongestText(structuredCandidates);
  }
  return fallbackPostText(root, authorName, authorTitle);
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
    findReactionMetric(container) > 0 ||
    findNamedMetric(container, COMMENT_COUNT_SELECTORS, COMMENT_PATTERN) > 0 ||
    findNamedMetric(container, SHARE_COUNT_SELECTORS, SHARE_PATTERN) > 0;
  const hasHeader = !!sanitizeAuthorName(firstText(getHeaderScope(container), AUTHOR_NAME_SELECTORS));
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

export function collectLikelyPostContainers(scope: ParentNode): HTMLElement[] {
  const containers = new Set<HTMLElement>();

  for (const selector of STATIC_CONTAINER_SELECTORS) {
    for (const element of Array.from(scope.querySelectorAll<HTMLElement>(selector))) {
      if (looksLikePostContainer(element)) {
        containers.add(element);
      }
    }
  }

  for (const anchor of findActionAnchors(scope)) {
    const actionBar = findActionBarFromAnchor(anchor);
    if (!actionBar) {
      continue;
    }
    const container = findContainerFromActionBar(actionBar);
    if (container) {
      containers.add(container);
    }
  }

  return Array.from(containers);
}

function fallbackAuthorName(root: ParentNode): string | null {
  const headerScope = getHeaderScope(root);
  const candidates = collectVisibleTextCandidates(headerScope, 3);
  for (const candidate of candidates) {
    const authorFromMetaLine = extractAuthorFromMetaLine(candidate);
    if (authorFromMetaLine.authorName) {
      return authorFromMetaLine.authorName;
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
    const authorFromMetaLine = extractAuthorFromMetaLine(candidate);
    if (
      authorFromMetaLine.authorName &&
      authorFromMetaLine.authorName === authorName &&
      authorFromMetaLine.authorTitle
    ) {
      return authorFromMetaLine.authorTitle;
    }
    if (candidate === authorName) {
      continue;
    }
    if (candidate.length > 160 || isActionOrNoiseText(candidate)) {
      continue;
    }
    if (SOCIAL_CONTEXT_PATTERN.test(candidate)) {
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
  const filtered = candidates
    .map((candidate) => sanitizePostText(candidate, authorName, authorTitle))
    .filter((candidate): candidate is string => {
      if (!candidate) {
        return false;
      }
      if (candidate === authorName || candidate === authorTitle) {
        return false;
      }
      if (candidate.length < 20 || candidate.length > 1500) {
        return false;
      }
      if (isActionOrNoiseText(candidate) || SOCIAL_CONTEXT_PATTERN.test(candidate)) {
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

export function extractLinkedInPost(
  container: HTMLElement,
  capturedFrom: CapturedFrom,
): CapturePreview | null {
  const headerScope = getHeaderScope(container);
  const authorName = resolveAuthorName(headerScope);
  const authorTitle = resolveAuthorTitle(headerScope, authorName);
  const postText = extractPostText(container, authorName, authorTitle);
  if (!postText) return null;

  const postUrl = firstPostUrl(container);

  return {
    post_url: postUrl,
    post_text: postText,
    author_name: authorName,
    author_title: authorTitle,
    author_company: parseAuthorCompany(authorTitle),
    author_profile_url: null,
    likes: findReactionMetric(container),
    comments: findNamedMetric(container, COMMENT_COUNT_SELECTORS, COMMENT_PATTERN),
    shares: findNamedMetric(container, SHARE_COUNT_SELECTORS, SHARE_PATTERN),
    post_type: capturedFrom === "post_detail" ? "icp" : "reference",
    captured_from: capturedFrom,
    page_url: window.location.href,
    captured_at: new Date().toISOString(),
  };
}
