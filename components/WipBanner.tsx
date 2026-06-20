"use client";

import Link from "next/link";
import { WIP_BANNER } from "@/lib/wip";
import { WipScramble } from "@/components/WipScramble";

/**
 * Site-wide Work in Progress banner. Only renders when WIP_MODE is
 * true. Sits at the top of every page in the root layout.
 *
 * In production (WIP_MODE off), the banner returns null and the layout
 * renders nothing.
 */
export function WipBanner() {
  if (!WIP_BANNER) return null;

  return (
    <div
      className="border-b border-lavender/30 bg-lavender/5 px-4 py-2.5 text-center text-sm"
      role="status"
      aria-live="polite"
    >
      <span className="font-mono text-xs uppercase tracking-widest text-lavender">
        Work in Progress
      </span>
      <span className="mx-2 text-muted">·</span>
      <WipScramble text={WIP_BANNER.message} className="text-ink" />
      <span className="mx-2 text-muted">·</span>
      <Link
        href={WIP_BANNER.cta.href}
        className="font-mono text-xs uppercase tracking-widest text-lavender underline-offset-4 hover:underline"
      >
        {WIP_BANNER.cta.label} →
      </Link>
    </div>
  );
}
