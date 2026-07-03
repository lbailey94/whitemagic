import type { ReactNode } from "react";
import Link from "next/link";
import { Prose } from "@/components/Prose";
import { EpistemicBadge } from "@/components/essay/EpistemicBadge";
import type { EpistemicTag } from "@/lib/design-tokens";

interface EssayLayoutProps {
  title: string;
  domain: string;
  date: string;
  epistemicTag: EpistemicTag;
  lastVerified?: string;
  children: ReactNode;
}

export function EssayLayout({
  title,
  domain,
  date,
  epistemicTag,
  lastVerified,
  children,
}: EssayLayoutProps) {
  return (
    <article className="container-site py-16">
      <nav className="mb-8">
        <Link
          href={`/essays/${domain}`}
          className="font-mono text-sm text-lavender hover:text-lavender-dark"
        >
          ← {domain}
        </Link>
      </nav>

      <header className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="font-mono uppercase tracking-wider text-lavender">
            {domain}
          </span>
          <span className="text-dim">·</span>
          <span className="font-mono text-dim">{date}</span>
          <EpistemicBadge tag={epistemicTag} />
        </div>

        <h1 className="font-head text-4xl font-semibold text-ink">
          {title}
        </h1>

        {lastVerified && (
          <p className="mt-3 font-mono text-xs text-dim">
            Evidence last verified: {lastVerified}
          </p>
        )}
      </header>

      <Prose>{children}</Prose>

      <footer className="mt-16 border-t border-border pt-8">
        <Link
          href="/essays"
          className="font-mono text-sm text-lavender hover:text-lavender-dark"
        >
          ← All essays
        </Link>
      </footer>
    </article>
  );
}
