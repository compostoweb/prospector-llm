import type { CapturePreview, CapturedFrom } from "../shared/types";

const ACTION_TEXT_PATTERN =
  /\b(gostar|like|comentar|comment|compartilhar|share|repost|enviar|send)\b/i;
const SOCIAL_CONTEXT_PATTERN =
  /\b(gostou|liked|comentou|commented|repostou|reposted|compartilhou|shared|seguem a empresa|follows the company|conexoes seguem|connections follow|reagiram|reacted|reagiu|celebrou|celebrated|apoiou|supported|achou interessante|found insightful|achou engracado|found funny|amou|loved)\b/i;
const SOCIAL_PROOF_PATTERN =
  /\b(e mais \d+|\d+\s*(reações|reactions|curtidas|likes|comentários|comments|compartilhamentos|shares|reposts)|pessoas\s+reagiram|people\s+reacted)\b/i;
const FOLLOW_CTA_PATTERN =
  /\b(seguir|follow|conectar|connect|acessar meu site|acesse meu site|visit website|agende uma reunião|agendar uma reunião|agende|schedule a meeting|book a meeting)\b/i;
const TIMESTAMP_PATTERN =
  /^(\d+\s*(min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo)\b|edited|editado|promoted|patrocinado)$/i;
const RELATIVE_TIME_TOKEN_PATTERN =
  /\b(\d+\s*(?:min|minutos?|h|hora|horas|d|dia|dias|sem|semanas?|m|mes|meses|mo))\b/i;
const CONTROL_MENU_AUTHOR_PATTERN =
  /(?:publica(?:ç|c)[aã]o|publication|post)\s+(?:de|of|by)\s+(.+)$/i;
const POST_TEXT_COLLAPSE_PATTERN = /(?:\.\.\.|…)\s*(mais|more)\b/gi;
const REACTION_PATTERN = /reaction|reactions|reac|curtida|curtidas|like|likes/i;
const COMMENT_PATTERN =
  /comment|comments|comentario|comentarios|comentário|comentários/i;
const SHARE_PATTERN =
  /repost|reposts|share|shares|compartilhamento|compartilhamentos|compartilhar/i;
const AUTHOR_TITLE_NOISE_PATTERN =
  /\b(?:usu[aá]rio verificado|verified user|premium|perfil|profile|seguidores?|followers?|visibilidade|global|promovida|promoted)\b/gi;

const POST_URL_SELECTORS = [
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

const POST_URN_PATTERN = /urn:li:(activity|share|ugcPost|update):\d+/i;
const ENCODED_POST_URN_PATTERN =
  /urn(?:%3A|:)li(?:%3A|:)(activity|share|ugcPost|update)(?:%3A|:)(\d+)/i;
const REACTION_SOCIAL_PROOF_OTHERS_PATTERN =
  /(?:\be\s+mais\s+(\d+(?:[\.,]\d+)?)\s+pessoas\b|\band\s+(\d+(?:[\.,]\d+)?)\s+others\b)/i;
const REACTION_SOCIAL_PROOF_TOTAL_PATTERN =
  /\b(\d+(?:[\.,]\d+)?)\s+(?:pessoas|people)\b/i;

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
  "div[data-id^='urn:li:ugcPost:']",
  "div[data-id^='urn:li:share:']",
  "[data-urn*='urn:li:activity:']",
  "[data-urn*='urn:li:ugcPost:']",
  "article",
];

const HEADER_SCOPE_SELECTORS = [
  ".update-components-actor",
  ".feed-shared-actor",
  ".update-components-actor__container",
  ".feed-shared-actor__container",
];

const METADATA_SHARE_ID_PATTERN =
  /(?:shareId|activityId|updateId)=(\d{15,25})/i;
const METADATA_UGC_POST_ID_PATTERN = /(?:postId|ugcPostId)=(\d{15,25})/i;
const METADATA_KEYED_URN_ID_PATTERN =
  /(activity|share|ugcPost|update)(?:Urn|Id)?[:=](\d{15,25})/i;
const RAW_LINKEDIN_ID_PATTERN = /(?:^|\D)(\d{19,20})(?:\D|$)/;

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

function isSocialProofOrMetricsText(value: string): boolean {
  if (SOCIAL_PROOF_PATTERN.test(value)) return true;
  if (SOCIAL_CONTEXT_PATTERN.test(value)) return true;
  // Pure metrics strings: "42 reações 42 28 comentários 28 comentários"
  const withoutNumbers = value.replace(/\d+/g, "").trim();
  if (withoutNumbers.length < 15 && REACTION_PATTERN.test(value)) return true;
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
  let cleaned = normalizeWhitespace(value);
  if (authorName && cleaned) {
    const authorPrefixPattern = new RegExp(
      `^${escapeRegExp(authorName)}\s*[·•-]?\s*`,
      "i",
    );
    cleaned = normalizeWhitespace(cleaned.replace(authorPrefixPattern, " "));
  }
  if (
    !cleaned ||
    cleaned === authorName ||
    SOCIAL_CONTEXT_PATTERN.test(cleaned)
  ) {
    return null;
  }
  cleaned = normalizeWhitespace(
    cleaned
      .replace(FOLLOW_CTA_PATTERN, " ")
      .replace(RELATIVE_TIME_TOKEN_PATTERN, " ")
      .replace(AUTHOR_TITLE_NOISE_PATTERN, " ")
      .replace(/\b\d+(?:º|°|st|nd|rd|th)\+?\b/gi, " ")
      .replace(/[·•]/g, " "),
  );
  if (!cleaned || cleaned === authorName || TIMESTAMP_PATTERN.test(cleaned)) {
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
    value?.replace(POST_TEXT_COLLAPSE_PATTERN, " "),
  );
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
    // Strip "AuthorName • Xº ... Seguir/Follow" prefix
    const authorPrefixPattern = new RegExp(
      `^${escapeRegExp(authorName)}\\s*[·•].{0,220}?\\b(?:seguir|follow)\\b\\s*`,
      "i",
    );
    cleaned = cleaned.replace(authorPrefixPattern, "");
    // Strip "AuthorName • Xº " prefix (connection degree)
    const authorDegreePattern = new RegExp(
      `^${escapeRegExp(authorName)}\\s*[·•]\\s*(?:\\d+[º°]\\+?\\s*)?`,
      "i",
    );
    cleaned = cleaned.replace(authorDegreePattern, "");
  }
  if (authorTitle && cleaned.startsWith(authorTitle)) {
    cleaned = cleaned.slice(authorTitle.length);
  }
  cleaned = cleaned.replace(/^[^.!?]{0,220}\b(?:seguir|follow)\b\s*/i, "");
  cleaned = cleaned.replace(
    /^(?:acessar meu site|acesse meu site|visit website)\b\s*/i,
    "",
  );
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
    const elements = Array.from(root.querySelectorAll<HTMLElement>(selector));
    if (elements.length === 0) continue;

    // If multiple actors exist: social context header comes first, real author comes after
    // Prefer one whose text does NOT contain social context patterns
    if (elements.length >= 2) {
      for (let i = elements.length - 1; i >= 0; i--) {
        const text = normalizeWhitespace(elements[i].innerText) ?? "";
        if (!SOCIAL_CONTEXT_PATTERN.test(text) && text.length > 3) {
          return elements[i];
        }
      }
      // All have social context — return last (deepest/nested = most likely real author)
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
  const elements = root.querySelectorAll<HTMLElement>("span, div, p, a, li");

  for (const element of elements) {
    if (!isVisible(element)) {
      continue;
    }
    const text = normalizeWhitespace(element.innerText);
    if (!text || text.length < minLength || text.length > maxLength) {
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

function collectStructuredTexts(
  root: ParentNode,
  selectors: string[],
): string[] {
  const values: string[] = [];
  const seen = new Set<string>();

  for (const selector of selectors) {
    for (const element of root.querySelectorAll<HTMLElement>(selector)) {
      const value = normalizeWhitespace(
        element.textContent ?? element.innerText,
      );
      if (!value || value.length < 20 || value.length > 8000) {
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
      const value = normalizeWhitespace(
        element.innerText || element.textContent,
      );
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
    .match(
      /gostar|like|comentar|comment|compartilhar|share|repost|enviar|send/g,
    );
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

function extractAuthorNameFromControlLabel(root: ParentNode): string | null {
  const labeledElements =
    root instanceof HTMLElement
      ? [
          root,
          ...Array.from(root.querySelectorAll<HTMLElement>("[aria-label]")),
        ]
      : Array.from(root.querySelectorAll<HTMLElement>("[aria-label]"));

  for (const element of labeledElements) {
    const ariaLabel = normalizeWhitespace(element.getAttribute("aria-label"));
    if (!ariaLabel) {
      continue;
    }
    const match = ariaLabel.match(CONTROL_MENU_AUTHOR_PATTERN);
    const candidate = sanitizeAuthorName(match?.[1] ?? null);
    if (candidate && candidate.length <= 120) {
      return candidate;
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
  const authorFromControlLabel = extractAuthorNameFromControlLabel(root);
  if (authorFromControlLabel) {
    return authorFromControlLabel;
  }

  const headerScope = getHeaderScope(root);
  for (const candidate of collectSelectorTexts(
    headerScope,
    AUTHOR_NAME_SELECTORS,
  )) {
    const authorFromMetaLine = extractAuthorFromMetaLine(candidate);
    if (authorFromMetaLine.authorName) {
      return authorFromMetaLine.authorName;
    }

    const sanitized = sanitizeAuthorName(candidate);
    if (sanitized && looksLikeAuthorName(sanitized)) {
      return sanitized;
    }
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
    AUTHOR_TITLE_SELECTORS,
  )) {
    const sanitized = sanitizeAuthorTitle(candidate, authorName);
    if (sanitized) {
      return sanitized;
    }
  }

  for (const candidate of collectSelectorTexts(
    headerScope,
    AUTHOR_NAME_SELECTORS,
  )) {
    const authorFromMetaLine = extractAuthorFromMetaLine(candidate);
    if (
      authorFromMetaLine.authorName &&
      authorFromMetaLine.authorName === authorName &&
      authorFromMetaLine.authorTitle
    ) {
      return authorFromMetaLine.authorTitle;
    }
  }

  return fallbackAuthorTitle(headerScope, authorName);
}

function normalizeLinkedInPostUrl(
  rawUrl: string | null | undefined,
): string | null {
  const cleaned = normalizeWhitespace(rawUrl);
  if (!cleaned) {
    return null;
  }

  if (POST_URN_PATTERN.test(cleaned)) {
    return buildLinkedInFeedUrlFromUrn(cleaned);
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
      url.searchParams.get("updateEntityUrn") ??
        url.searchParams.get("updateEntityUrn"),
    );
    if (updateEntityUrn && POST_URN_PATTERN.test(updateEntityUrn)) {
      return `${url.origin}/feed/update/${updateEntityUrn.replace(/\/+$/, "")}/`;
    }

    const pathname = url.pathname.replace(/\/+$/, "");
    const isCanonicalPostsPath = /\/posts\/[^/]+$/i.test(pathname);
    if (
      isCanonicalPostsPath ||
      pathname.includes("/feed/update/") ||
      pathname.includes("/activity-") ||
      pathname.includes("/activity/")
    ) {
      return `${url.origin}${pathname}/`;
    }

    // Check full URL for encoded URN (e.g. in query params)
    const fullUrlStr = url.toString();
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

function extractPostUrnFromMetadataValue(
  value: string | null | undefined,
): string | null {
  const normalized = normalizeWhitespace(value);
  if (!normalized) {
    return null;
  }

  const directUrnMatch = normalized.match(POST_URN_PATTERN);
  if (directUrnMatch) {
    return directUrnMatch[0];
  }

  const encodedUrnMatch = normalized.match(ENCODED_POST_URN_PATTERN);
  if (encodedUrnMatch) {
    return `urn:li:${encodedUrnMatch[1]}:${encodedUrnMatch[2]}`;
  }

  const shareMatch = normalized.match(METADATA_SHARE_ID_PATTERN);
  if (shareMatch) {
    return `urn:li:share:${shareMatch[1]}`;
  }

  const ugcPostMatch = normalized.match(METADATA_UGC_POST_ID_PATTERN);
  if (ugcPostMatch) {
    return `urn:li:ugcPost:${ugcPostMatch[1]}`;
  }

  const keyedIdMatch = normalized.match(METADATA_KEYED_URN_ID_PATTERN);
  if (keyedIdMatch) {
    return `urn:li:${keyedIdMatch[1]}:${keyedIdMatch[2]}`;
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
  // Walk up ancestors and check ALL attributes for activity URN pattern
  let currentElement = root instanceof HTMLElement ? root : null;
  for (let depth = 0; currentElement && depth < 30; depth += 1) {
    for (const attr of Array.from(currentElement.attributes)) {
      const urn = extractPostUrnFromMetadataValue(attr.value);
      if (urn) {
        return urn;
      }
    }
    currentElement = currentElement.parentElement;
  }

  // Search descendants — any element with any attribute containing URN
  for (const element of root.querySelectorAll<HTMLElement>("*")) {
    for (const attr of Array.from(element.attributes)) {
      const urn = extractPostUrnFromMetadataValue(attr.value);
      if (urn) {
        return urn;
      }
    }
  }

  return null;
}

function firstPostUrl(root: ParentNode): string | null {
  // Strategy 1: URN from data attributes (most reliable — scans all attributes)
  const urnUrl = buildLinkedInFeedUrlFromUrn(extractPostUrn(root));
  if (urnUrl) {
    return urnUrl;
  }

  // Strategy 2: Known selectors in container + ancestors
  for (const searchRoot of collectSearchRoots(root)) {
    for (const selector of POST_URL_SELECTORS) {
      const anchor = searchRoot.querySelector<HTMLAnchorElement>(selector);
      const href = normalizeLinkedInPostUrl(anchor?.href);
      if (href) {
        return href;
      }
    }
  }

  // Strategy 3: Link wrapping a <time> element OR link with timestamp text
  for (const link of root.querySelectorAll<HTMLAnchorElement>("a[href]")) {
    const linkText = (normalizeWhitespace(link.innerText) ?? "").trim();
    if (link.querySelector("time") || TIMESTAMP_PATTERN.test(linkText)) {
      const href = normalizeLinkedInPostUrl(link.href);
      if (href) {
        return href;
      }
    }
  }

  // Strategy 4: Any <a> with LinkedIn post URL pattern
  for (const searchRoot of collectSearchRoots(root)) {
    const anchors = searchRoot.querySelectorAll<HTMLAnchorElement>("a[href]");
    for (const anchor of anchors) {
      const href = normalizeLinkedInPostUrl(anchor.href);
      if (href) {
        return href;
      }
    }
  }

  // Strategy 5: Extract activity ID from any href containing it
  for (const searchRoot of collectSearchRoots(root)) {
    const anchors = searchRoot.querySelectorAll<HTMLAnchorElement>("a[href]");
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
      const idMatch = attr.value.match(RAW_LINKEDIN_ID_PATTERN);
      if (idMatch) {
        return `https://www.linkedin.com/feed/update/urn:li:activity:${idMatch[1]}/`;
      }
    }
  }

  // Also check ancestors for raw LinkedIn ids.
  let urlAncestor = root instanceof HTMLElement ? root.parentElement : null;
  for (let depth = 0; urlAncestor && depth < 30; depth += 1) {
    for (const attr of Array.from(urlAncestor.attributes)) {
      const idMatch = attr.value.match(RAW_LINKEDIN_ID_PATTERN);
      if (idMatch) {
        return `https://www.linkedin.com/feed/update/urn:li:activity:${idMatch[1]}/`;
      }
    }
    urlAncestor = urlAncestor.parentElement;
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
  const directMetric = findMetricBySelectors(root, REACTION_COUNT_SELECTORS);
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
    if (COMMENT_PATTERN.test(text) || SHARE_PATTERN.test(text)) {
      continue;
    }
    const namedMetric = parseNamedMetricValue(text, REACTION_PATTERN);
    if (namedMetric > 0) {
      return namedMetric;
    }

    const othersMatch = text.match(REACTION_SOCIAL_PROOF_OTHERS_PATTERN);
    if (othersMatch) {
      const othersCount = parseMetricValue(othersMatch[1] ?? othersMatch[2]);
      if (othersCount > 0) {
        return othersCount + 1;
      }
    }

    const peopleMatch = text.match(REACTION_SOCIAL_PROOF_TOTAL_PATTERN);
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
    // "AuthorName • Xº Title..." pattern
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
  // Strategy 1: Prefer the explicit expandable text box used by the current feed DOM.
  const expandableTextCandidates = collectStructuredTexts(root, [
    "span[data-testid='expandable-text-box']",
  ])
    .map((candidate) => sanitizePostText(candidate, authorName, authorTitle))
    .filter(
      (candidate): candidate is string =>
        !!candidate &&
        candidate.length >= 20 &&
        !isActionOrNoiseText(candidate) &&
        !isSocialProofOrMetricsText(candidate) &&
        !FOLLOW_CTA_PATTERN.test(candidate) &&
        !isLikelyAuthorText(candidate, authorName, authorTitle),
    );
  if (expandableTextCandidates.length > 0) {
    return chooseLongestText(expandableTextCandidates);
  }

  // Strategy 2: Use textContent (includes hidden "see more" text) from structured selectors
  const structuredCandidates = collectStructuredTexts(root, POST_TEXT_SELECTORS)
    .map((candidate) => sanitizePostText(candidate, authorName, authorTitle))
    .filter(
      (candidate): candidate is string =>
        !!candidate &&
        candidate.length >= 20 &&
        !isActionOrNoiseText(candidate) &&
        !isSocialProofOrMetricsText(candidate) &&
        !FOLLOW_CTA_PATTERN.test(candidate) &&
        !isLikelyAuthorText(candidate, authorName, authorTitle),
    );
  if (structuredCandidates.length > 0) {
    return chooseLongestText(structuredCandidates);
  }

  // Strategy 3: Use innerText from the same selectors (visible text only)
  for (const selector of POST_TEXT_SELECTORS) {
    for (const element of root.querySelectorAll<HTMLElement>(selector)) {
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

  // Strategy 4: Generic span[dir='ltr'] outside header scope (works even if class names change)
  const headerScope = getHeaderScope(root);
  const dirLtrCandidates: string[] = [];
  for (const span of root.querySelectorAll<HTMLElement>("span[dir='ltr']")) {
    if (headerScope instanceof HTMLElement && headerScope.contains(span)) {
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
      !FOLLOW_CTA_PATTERN.test(text) &&
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
    findNamedMetric(container, COMMENT_COUNT_SELECTORS, COMMENT_PATTERN) > 0 ||
    findNamedMetric(container, SHARE_COUNT_SELECTORS, SHARE_PATTERN) > 0;
  const hasHeader = !!sanitizeAuthorName(
    firstText(getHeaderScope(container), AUTHOR_NAME_SELECTORS),
  );
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

export function collectLikelyPostContainers(scope: ParentNode): HTMLElement[] {
  const containers = new Set<HTMLElement>();

  for (const selector of STATIC_CONTAINER_SELECTORS) {
    for (const element of Array.from(
      scope.querySelectorAll<HTMLElement>(selector),
    )) {
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
  const candidates = collectVisibleTextCandidates(root, 20, 5000);
  const filtered = candidates
    .map((candidate) => sanitizePostText(candidate, authorName, authorTitle))
    .filter((candidate): candidate is string => {
      if (!candidate) {
        return false;
      }
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

export function extractLinkedInPost(
  container: HTMLElement,
  capturedFrom: CapturedFrom,
): CapturePreview | null {
  const authorName = resolveAuthorName(container);
  const authorTitle = resolveAuthorTitle(container, authorName);
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
    comments: findNamedMetric(
      container,
      COMMENT_COUNT_SELECTORS,
      COMMENT_PATTERN,
    ),
    shares: findNamedMetric(container, SHARE_COUNT_SELECTORS, SHARE_PATTERN),
    post_type: capturedFrom === "post_detail" ? "icp" : "reference",
    captured_from: capturedFrom,
    page_url: window.location.href,
    captured_at: new Date().toISOString(),
  };
}
