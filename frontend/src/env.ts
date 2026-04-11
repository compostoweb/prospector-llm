import { createEnv } from "@t3-oss/env-nextjs"
import { z } from "zod"

export const env = createEnv({
  skipValidation: process.env["SKIP_ENV_VALIDATION"] === "1",

  client: {
    NEXT_PUBLIC_API_URL: z.string().url(),
    NEXT_PUBLIC_WS_URL: z.string().min(1),
    NEXT_PUBLIC_APP_URL: z.string().url(),
  },

  server: {
    NEXTAUTH_SECRET: z.string().min(32),
    NEXTAUTH_URL: z.string().url(),
    API_URL: z.string().url(),
    NODE_ENV: z.enum(["development", "production", "test"]),
  },

  runtimeEnv: {
    NEXT_PUBLIC_API_URL: process.env["NEXT_PUBLIC_API_URL"],
    NEXT_PUBLIC_WS_URL: process.env["NEXT_PUBLIC_WS_URL"],
    NEXT_PUBLIC_APP_URL: process.env["NEXT_PUBLIC_APP_URL"],
    NEXTAUTH_SECRET: process.env["NEXTAUTH_SECRET"],
    NEXTAUTH_URL: process.env["NEXTAUTH_URL"],
    API_URL: process.env["API_URL"],
    NODE_ENV: process.env["NODE_ENV"],
  },
})
