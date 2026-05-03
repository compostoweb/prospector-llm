import type { NextConfig } from "next"

function readRequiredEnv(name: "NEXT_PUBLIC_APP_URL" | "NEXT_PUBLIC_API_URL" | "NEXT_PUBLIC_WS_URL"): string {
  const value = process.env[name]
  if (!value) {
    throw new Error(`Missing required environment variable in next.config.ts: ${name}`)
  }
  return value
}

function toOrigin(rawUrl: string): string {
  const url = new URL(rawUrl)
  if (url.protocol === "ws:") {
    url.protocol = "http:"
  }
  if (url.protocol === "wss:") {
    url.protocol = "https:"
  }
  return url.origin
}

function buildCspHeader(): string {
  const appOrigin = toOrigin(readRequiredEnv("NEXT_PUBLIC_APP_URL"))
  const apiOrigin = toOrigin(readRequiredEnv("NEXT_PUBLIC_API_URL"))
  const wsOrigin = toOrigin(readRequiredEnv("NEXT_PUBLIC_WS_URL"))
  const imageSrc = [
    "'self'",
    "data:",
    "blob:",
    apiOrigin,
    "https://lh3.googleusercontent.com",
    "https://media.licdn.com",
    "https://media-exp1.licdn.com",
    "https://media-exp2.licdn.com",
    "https://media-exp3.licdn.com",
    "https://media-exp4.licdn.com",
  ]
  const connectSrc = [
    "'self'",
    appOrigin,
    apiOrigin,
    wsOrigin,
    "https://accounts.google.com",
    "https://oauth2.googleapis.com",
    "https://www.googleapis.com",
  ]

  return [
    "default-src 'self'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    `form-action 'self' ${appOrigin} ${apiOrigin}`,
    `connect-src ${connectSrc.join(" ")}`,
    "font-src 'self' data:",
    `img-src ${imageSrc.join(" ")}`,
    `media-src 'self' blob: data: ${apiOrigin}`,
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "worker-src 'self' blob:",
  ].join("; ")
}

const contentSecurityPolicy = buildCspHeader()

const nextConfig: NextConfig = {
  reactStrictMode: true,

  typedRoutes: true,

  // Evita warning de múltiplos lockfiles no monorepo (raiz + frontend)
  turbopack: {
    root: __dirname,
  },

  // Proxy para o backend no dev (evita CORS)
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return []
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.API_URL ?? "http://localhost:8000"}/:path*`,
      },
    ]
  },

  // Headers de segurança
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-DNS-Prefetch-Control", value: "on" },
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
        ],
      },
    ]
  },

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
      {
        protocol: "https",
        hostname: "media.licdn.com",
      },
    ],
  },
}

export default nextConfig
