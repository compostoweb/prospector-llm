export function extractGeneratedPostParts(text: string): { body: string; hashtags: string } {
  const trimmedText = text.trim()
  const trailingHashtagsMatch = trimmedText.match(
    /([\s\S]*?)(?:\s+((?:#[\p{L}\p{N}_-]+(?:\s+#[\p{L}\p{N}_-]+)*)))\s*$/u,
  )

  const hashtagRegex = /#[\p{L}\p{N}_-]+/gu
  const hashtags = trailingHashtagsMatch?.[2]?.match(hashtagRegex) ?? []
  const uniqueHashtags = [...new Set(hashtags)]

  return {
    body: (trailingHashtagsMatch?.[1] ?? trimmedText).trim(),
    hashtags: uniqueHashtags.join(" "),
  }
}

export function buildGeneratedTitle(text: string, fallback: string): string {
  const firstMeaningfulLine = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith("#"))

  const baseTitle = firstMeaningfulLine || fallback.trim()
  return baseTitle.slice(0, 80)
}
