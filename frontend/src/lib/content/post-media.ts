import { env } from "@/env"

interface PostImageMediaSource {
  id: string
  image_url?: string | null
  image_s3_key?: string | null
}

interface PostVideoMediaSource {
  id: string
  video_url?: string | null
  video_s3_key?: string | null
}

export function withMediaCacheBuster(url: string, cacheBuster?: number | string | null): string {
  if (cacheBuster == null) return url
  const separator = url.includes("?") ? "&" : "?"
  return `${url}${separator}t=${encodeURIComponent(String(cacheBuster))}`
}

export function getPostImageProxyUrl(
  postId: string,
  options?: { cacheBuster?: number | string | null },
): string {
  return withMediaCacheBuster(
    `${env.NEXT_PUBLIC_API_URL}/api/content/posts/${postId}/image`,
    options?.cacheBuster ?? null,
  )
}

export function resolvePostImageUrl(
  post: PostImageMediaSource | null | undefined,
  options?: { cacheBuster?: number | string | null },
): string | null {
  if (!post) return null

  const baseUrl = post.image_s3_key ? getPostImageProxyUrl(post.id) : (post.image_url ?? null)

  if (!baseUrl) return null
  return withMediaCacheBuster(baseUrl, options?.cacheBuster ?? null)
}

export function resolvePostVideoUrl(post: PostVideoMediaSource | null | undefined): string | null {
  if (!post) return null

  if (post.video_s3_key) {
    return `${env.NEXT_PUBLIC_API_URL}/api/content/posts/${post.id}/video`
  }

  return post.video_url ?? null
}
