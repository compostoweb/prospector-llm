import { beforeAll, describe, expect, it } from "vitest"

let resolvePostImageUrl: typeof import("@/lib/content/post-media").resolvePostImageUrl
let resolvePostVideoUrl: typeof import("@/lib/content/post-media").resolvePostVideoUrl

beforeAll(async () => {
  process.env["SKIP_ENV_VALIDATION"] = "1"
  process.env["NEXT_PUBLIC_API_URL"] = "http://localhost:8000"
  process.env["NEXT_PUBLIC_WS_URL"] = "ws://localhost:8000/ws/events"
  process.env["NEXT_PUBLIC_APP_URL"] = "http://localhost:3000"

  ;({ resolvePostImageUrl, resolvePostVideoUrl } = await import("@/lib/content/post-media"))
})

describe("post media resolver", () => {
  it("prefere o proxy da API para imagem quando existe s3_key", () => {
    expect(
      resolvePostImageUrl({
        id: "post-123",
        image_url: "https://private-bucket.example.com/image.png",
        image_s3_key: "posts/post-123/image.png",
      }),
    ).toBe("http://localhost:8000/api/content/posts/post-123/image")
  })

  it("mantem fallback para image_url legado quando nao existe s3_key", () => {
    expect(
      resolvePostImageUrl({
        id: "post-456",
        image_url: "https://cdn.example.com/image.png",
        image_s3_key: null,
      }),
    ).toBe("https://cdn.example.com/image.png")
  })

  it("adiciona cache buster ao proxy da imagem", () => {
    expect(
      resolvePostImageUrl(
        {
          id: "post-789",
          image_url: null,
          image_s3_key: "posts/post-789/image.png",
        },
        { cacheBuster: 123 },
      ),
    ).toBe("http://localhost:8000/api/content/posts/post-789/image?t=123")
  })

  it("prefere o proxy da API para video quando existe s3_key", () => {
    expect(
      resolvePostVideoUrl({
        id: "post-321",
        video_url: "https://private-bucket.example.com/video.mp4",
        video_s3_key: "posts/post-321/video.mp4",
      }),
    ).toBe("http://localhost:8000/api/content/posts/post-321/video")
  })

  it("mantem fallback para video_url legado quando nao existe s3_key", () => {
    expect(
      resolvePostVideoUrl({
        id: "post-654",
        video_url: "https://cdn.example.com/video.mp4",
        video_s3_key: null,
      }),
    ).toBe("https://cdn.example.com/video.mp4")
  })
})