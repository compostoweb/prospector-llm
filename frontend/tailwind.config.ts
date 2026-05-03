import type { Config } from "tailwindcss"
import typography from "@tailwindcss/typography"

// Tailwind CSS v4 — a maioria das configurações fica em globals.css via @theme e @custom-variant
// Este arquivo é mantido para compatibilidade e plugins futuros
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  plugins: [typography],
}

export default config
