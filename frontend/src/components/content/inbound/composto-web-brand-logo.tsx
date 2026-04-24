"use client"

import Image from "next/image"
import { useState } from "react"
import { env } from "@/env"

interface CompostoWebBrandLogoProps {
  className?: string
}

const OFFICIAL_LOGO_SRC = `${env.NEXT_PUBLIC_API_URL}/assets/branding/compostoweb-logo-primary-transparent.webp`

function CompostoWebBrandWordmark({ className }: CompostoWebBrandLogoProps) {
  return (
    <div className={className}>
      <div className="inline-flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,color-mix(in_srgb,var(--accent)_90%,white),color-mix(in_srgb,var(--info)_68%,white))] shadow-[0_10px_24px_color-mix(in_srgb,var(--accent)_20%,transparent)]">
          <div className="grid h-5 w-5 grid-cols-2 gap-1">
            <span className="rounded-sm bg-white/95" />
            <span className="rounded-sm bg-white/70" />
            <span className="rounded-sm bg-white/70" />
            <span className="rounded-sm bg-white/95" />
          </div>
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-(--text-tertiary)">
            Composto
          </span>
          <span className="text-[1.65rem] font-semibold tracking-[-0.04em] text-(--text-primary)">
            Web
          </span>
        </div>
      </div>
    </div>
  )
}

export function CompostoWebBrandLogo({ className }: CompostoWebBrandLogoProps) {
  const [useFallback, setUseFallback] = useState(false)

  if (useFallback) {
    return <CompostoWebBrandWordmark className={className} />
  }

  return (
    <div className={className}>
      <Image
        src={OFFICIAL_LOGO_SRC}
        alt="Composto Web"
        width={208}
        height={48}
        unoptimized
        className="h-auto w-52 max-w-full object-contain"
        onError={() => setUseFallback(true)}
      />
    </div>
  )
}
