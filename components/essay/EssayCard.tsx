import Link from "next/link";
import { EpistemicBadge } from "@/components/essay/EpistemicBadge";
import type { EpistemicTag } from "@/lib/design-tokens";

export interface EssayMeta {
  slug: string;
  title: string;
  domain: string;
  blurb: string;
  date: string;
  epistemicTag: EpistemicTag;
  lastVerified?: string;
  ready: boolean;
}

export function EssayCard({ essay }: { essay: EssayMeta }) {
  const href = `/essays/${essay.domain}/${essay.slug}`;

  const content = (
    <>
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="font-mono uppercase tracking-wider text-lavender">
          {essay.domain}
        </span>
        <span className="text-dim">·</span>
        <span className="font-mono text-dim">{essay.date}</span>
        <EpistemicBadge tag={essay.epistemicTag} />
        {!essay.ready && (
          <span className="font-mono uppercase tracking-wider text-dim">
            Draft
          </span>
        )}
      </div>
      <h2 className="mb-2 font-head text-xl font-semibold text-ink">
        {essay.title}
      </h2>
      <p className="text-muted">{essay.blurb}</p>
      {essay.lastVerified && (
        <p className="mt-2 font-mono text-xs text-dim">
          Last verified: {essay.lastVerified}
        </p>
      )}
    </>
  );

  if (essay.ready) {
    return (
      <Link
        href={href}
        className="block rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender hover:bg-lavender-bg"
      >
        {content}
      </Link>
    );
  }

  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface-alt/50 p-6 opacity-80">
      {content}
    </div>
  );
}
