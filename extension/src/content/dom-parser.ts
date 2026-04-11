import type { CapturePreview, CapturedFrom } from "../shared/types";

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

function firstText(root: ParentNode, selectors: string[]): string | null {
  for (const selector of selectors) {
    const element = root.querySelector<HTMLElement>(selector);
    const value = element?.innerText?.trim();
    if (value) {
      return value;
    }
  }
  return null;
}

function firstPostUrl(root: ParentNode): string | null {
  for (const selector of POST_URL_SELECTORS) {
    const anchor = root.querySelector<HTMLAnchorElement>(selector);
    const href = anchor?.href?.trim();
    if (href) {
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
  const postText = firstText(container, POST_TEXT_SELECTORS);
  if (!postText) return null;

  const authorName = firstText(container, AUTHOR_NAME_SELECTORS);
  const authorTitle = firstText(container, AUTHOR_TITLE_SELECTORS);
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
