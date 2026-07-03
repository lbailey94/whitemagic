"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { EpistemicTag } from "@/lib/design-tokens";
import { EpistemicBadge } from "@/components/essay/EpistemicBadge";

interface EssayIntro {
  thesis: string;
  takeaways: string[];
  hook: string;
}

interface ShortFormIntroProps {
  title: string;
  epistemicTag: EpistemicTag;
  intro: EssayIntro;
  readTimeMin: number;
}

export function ShortFormIntro({
  title,
  epistemicTag,
  intro,
  readTimeMin,
}: ShortFormIntroProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="my-8 rounded-2xl border border-border bg-surface-alt/50">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between p-4 text-left transition hover:bg-surface-alt"
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm text-lavender">
            {open ? "−" : "+"}
          </span>
          <span className="font-head text-lg font-semibold text-ink">
            Quick intro
          </span>
          <EpistemicBadge tag={epistemicTag} />
          <span className="font-mono text-xs text-dim">{readTimeMin} min</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-border p-4">
          <div className="mb-4">
            <h3 className="mb-1 font-mono text-xs uppercase tracking-wider text-dim">
              Thesis
            </h3>
            <p className="text-fg">{intro.thesis}</p>
          </div>

          <div className="mb-4">
            <h3 className="mb-1 font-mono text-xs uppercase tracking-wider text-dim">
              3 Takeaways
            </h3>
            <ul className="list-disc pl-5 space-y-1">
              {intro.takeaways.map((t, i) => (
                <li key={i} className="text-muted">
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="mb-1 font-mono text-xs uppercase tracking-wider text-dim">
              Curiosity Hook
            </h3>
            <p className="text-muted italic">{intro.hook}</p>
          </div>
        </div>
      )}
    </div>
  );
}
