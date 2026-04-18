"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Minimal language toggle. Routes:
 *   /         → English (default)
 *   /zh/*     → Chinese
 * The Chinese surface is stubbed in Phase 1 (single page at /zh); real content
 * migration happens later. Toggle is always visible so visitors who arrive in
 * the wrong language can switch immediately.
 */
export function LangToggle() {
  const pathname = usePathname() ?? "/";
  const isZh = pathname === "/zh" || pathname.startsWith("/zh/");

  const target = isZh
    ? pathname.replace(/^\/zh(?=\/|$)/, "") || "/"
    : pathname === "/"
      ? "/zh"
      : `/zh${pathname}`;

  return (
    <Link
      href={target}
      aria-label={isZh ? "Switch to English" : "切换到中文"}
      className="inline-flex h-9 items-center gap-1 rounded-full border border-border px-3 font-mono text-xs font-medium text-muted transition hover:border-lavender hover:text-lavender"
    >
      <span className={isZh ? "text-lavender" : ""}>EN</span>
      <span className="text-dim">/</span>
      <span className={isZh ? "" : "font-zh"}>中</span>
    </Link>
  );
}
