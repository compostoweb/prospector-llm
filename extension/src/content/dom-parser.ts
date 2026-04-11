import type { CapturePreview, CapturedFrom } from "../shared/types";

const ACTION_TEXT_PATTERN =
  /\b(gostar|like|comentar|comment|compartilhar|share|repost|enviar|send)\b/i;
const TIMESTAMP_PATTERN =
  /^(\d+\s*(min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo)\b|edited|editado|promoted|patrocinado)$/i;

const POST_URL_SELECTORS = [
  'a[href*="/posts/"]',
  'a[href*="/feed/update/"]',
  'a[href*="/activity-"]',
];

const AUTHOR_NAME_SELECTORS = [
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

const METRIC_SCOPE_SELECTORS = [
  ".social-details-social-counts",
  ".social-details-social-activity",
  ".feed-shared-social-action-bar",
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
  if (/^(seguir|follow|conectar|connect)$/i.test(value)) return true;
  return false;
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

function collectVisibleTextCandidates(
  root: ParentNode,
  minLength = 12,
): string[] {
  const values: string[] = [];
  const seen = new Set<string>();
  const elements = root.querySelectorAll<HTMLElement>("span, div, p, a, li");

  for (const element of elements) {
    if (!isVisible(element)) {
      continue;
    }
    const text = normalizeWhitespace(element.innerText);
    if (!text || text.length < minLength) {
      continue;
    }
    if (text.length > 700) {
      continue;
    }
    if (isActionOrNoiseText(text)) {
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
  const hasHeader = !!firstText(getHeaderScope(container), AUTHOR_NAME_SELECTORS);
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

function firstText(root: ParentNode, selectors: string[]): string | null {
  for (const selector of selectors) {
    const element = root.querySelector<HTMLElement>(selector);
    const value = normalizeWhitespace(element?.innerText);
    if (value) {
      return value;
    }
  }
  return null;
}

function firstPostUrl(root: ParentNode): string | null {
  for (const selector of POST_URL_SELECTORS) {
    const anchor = root.querySelector<HTMLAnchorElement>(selector);
    const href = normalizeWhitespace(anchor?.href);
    if (href) {
      return href;
    }
  }

  const anchors = root.querySelectorAll<HTMLAnchorElement>("a[href]");
  for (const anchor of anchors) {
    const href = normalizeWhitespace(anchor.href);
    if (!href) {
      continue;
    }
    if (href.includes("/posts/") || href.includes("/feed/update/") || href.includes("/activity-")) {
      return href;
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

function findMetric(root: ParentNode, pattern: RegExp): number {
  const scope = getMetricScope(root);
  const elements = scope.querySelectorAll<HTMLElement>("button, span, li, div");
  for (const element of elements) {
    const text = element.innerText?.trim();
    if (!text || !pattern.test(text.toLowerCase())) continue;
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

function fallbackAuthorTitle(root: ParentNode, authorName: string | null): string | null {
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
    if (candidate.length < 20) {
      return false;
    }
    if (candidate.length > 1500) {
      return false;
    }
    if (isActionOrNoiseText(candidate)) {
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
  const authorName =
    firstText(getHeaderScope(container), AUTHOR_NAME_SELECTORS) ??
    fallbackAuthorName(container);
  const authorTitle =
    firstText(getHeaderScope(container), AUTHOR_TITLE_SELECTORS) ??
    fallbackAuthorTitle(container, authorName);
  const postText =
    firstText(container, POST_TEXT_SELECTORS) ??
    fallbackPostText(container, authorName, authorTitle);
  if (!postText) return null;

  const postUrl = firstPostUrl(container);

  return {
    post_url: postUrl,
    post_text: postText,
    author_name: authorName,
    author_title: authorTitle,
    author_company: parseAuthorCompany(authorTitle),
    author_profile_url: null,
    likes: findMetric(container, /like|curt/),
    comments: findMetric(container, /comment|coment/),
    shares: findMetric(container, /repost|share|compart/),
    post_type: capturedFrom === "post_detail" ? "icp" : "reference",
    captured_from: capturedFrom,
    page_url: window.location.href,
    captured_at: new Date().toISOString(),
  };
}
