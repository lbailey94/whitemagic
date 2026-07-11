"use client";

import { useMemo, createElement, type ReactNode } from "react";
import type { JSX } from "react";
import { WIP_SCRAMBLE } from "@/lib/wip";

/**
 * Digits used to visually scramble text in WIP mode. Each visible
 * character is replaced with a random digit 0-9, so the prose
 * renders as a stream of numbers (e.g., "4 7 2 1 8 3 9 0").
 * Looks like a numeric cipher / instrument readout.
 */
const SCRAMBLE_GLYPHS = "0123456789";

/**
 * Deterministic seeded scramble. Same text + seed always produces
 * the same glyph sequence, so server and client agree (no hydration
 * mismatch). The scramble looks "encrypted" but is just visual.
 */
function scrambleText(text: string, seed = 0x5f3759df): string {
  let out = "";
  let s = seed >>> 0;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === " " || c === "\n" || c === "\t") {
      out += c;
    } else if (/[a-zA-Z0-9]/.test(c)) {
      s = (s * 1664525 + 1013904223) >>> 0;
      out += SCRAMBLE_GLYPHS[s % SCRAMBLE_GLYPHS.length];
    } else {
      out += c;
    }
  }
  return out;
}

/**
 * WipScramble — wraps a string in a span. In WIP_SCRAMBLE mode, the
 * text is replaced with a stream of Unicode block glyphs that look
 * like a code block (illegible at a glance). The original text is
 * preserved in `data-original` and `title` for DevTools / hover.
 *
 * Use for any long-form WIP copy: hero lede, banner message,
 * placeholder prose, footer blurb. Don't use for short labels
 * (button text, nav items) — those should stay readable so users
 * can navigate.
 */
export function WipScramble({
  text,
  as = "span",
  className = "",
  scramble,
}: {
  text: string;
  as?: keyof JSX.IntrinsicElements;
  className?: string;
  /** Optional override; set false to show plain text even in WIP_SCRAMBLE mode */
  scramble?: boolean;
}): ReactNode {
  const doScramble = scramble ?? WIP_SCRAMBLE;
  const scrambled = useMemo(() => scrambleText(text), [text]);

  if (!doScramble) {
    return createElement(as, { className }, text);
  }

  return createElement(
    as,
    {
      className: `wip-scramble ${className}`.trim(),
      "data-wip-scrambled": "manual",
      "data-original": text,
      title: "[encrypted — original is in data-original]",
      "aria-label": "Encrypted text in WIP mode",
    },
    scrambled,
  );
}
