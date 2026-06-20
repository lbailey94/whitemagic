"use client";

import { useLayoutEffect } from "react";
import { WIP_SCRAMBLE } from "@/lib/wip";

/**
 * WipScrambleAll — when WIP_SCRAMBLE is on, walks the entire DOM
 * and replaces every text node's content with a stream of random
 * digits. The original text is preserved in the parent's
 * `data-original-text` attribute (and via DevTools).
 *
 * Skips: SCRIPT, STYLE, CODE, PRE, TEXTAREA, INPUT, SELECT, OPTION,
 * NOSCRIPT, TEMPLATE, SVG, IFRAME, EMBED, OBJECT. Also skips any
 * element with `data-no-scramble` (escape hatch) or
 * `data-wip-scrambled` (marks spans pre-scrambled by the inline
 * <WipScramble /> component).
 *
 * Uses useLayoutEffect (synchronous, before paint) so the scramble
 * happens before the user sees the original text. Body starts with
 * wip-scrambling class (opacity 0.01) and is revealed (wip-scrambled,
 * opacity 1) after scrambling.
 *
 * MutationObserver watches for:
 * - childList: new elements added to the DOM (route changes, async
 *   data, chat messages)
 * - characterData: text node content changes (React re-renders
 *   that might reset scrambled text to original)
 *
 * Both trigger a re-scramble pass. Debounced via rAF to avoid
 * thrashing on rapid mutations.
 */

const SCRAMBLE_GLYPHS = "0123456789";
const SEED = 0x5f3759df;

const SKIP_TAGS = new Set([
  "SCRIPT",
  "STYLE",
  "CODE",
  "PRE",
  "TEXTAREA",
  "INPUT",
  "SELECT",
  "OPTION",
  "NOSCRIPT",
  "TEMPLATE",
  "SVG",
  "IFRAME",
  "EMBED",
  "OBJECT",
]);

function scrambleText(text: string, seed: number): string {
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

function shouldSkipElement(el: Element | null): boolean {
  let cur: Element | null = el;
  while (cur) {
    if (SKIP_TAGS.has(cur.tagName)) return true;
    if (cur.hasAttribute("data-no-scramble")) return true;
    if (cur.hasAttribute("data-wip-scrambled")) return true;
    cur = cur.parentElement;
  }
  return false;
}

function scrambleTextNode(node: Text): void {
  if (!node.nodeValue) return;
  const parent = node.parentElement;
  if (!parent) return;
  if (shouldSkipElement(parent)) return;
  if (parent.hasAttribute("data-original-text")) return;
  if (!node.nodeValue.trim()) return;

  const original = node.nodeValue;
  parent.setAttribute("data-original-text", original);
  node.nodeValue = scrambleText(original, SEED + original.length);
}

function walkAndScramble(root: Node): void {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let n: Node | null = walker.nextNode();
  while (n) {
    scrambleTextNode(n as Text);
    n = walker.nextNode();
  }
}

// Re-scramble a text node IF its current value matches the
// original (meaning it was reset by a re-render). If it's
// already scrambled, leave it.
function rescrambleIfReset(node: Text): void {
  if (!node.nodeValue) return;
  const parent = node.parentElement;
  if (!parent) return;
  if (shouldSkipElement(parent)) return;
  const original = parent.getAttribute("data-original-text");
  if (!original) return;
  if (node.nodeValue === original) {
    // React re-rendered — re-scramble
    node.nodeValue = scrambleText(original, SEED + original.length);
  } else {
    // Already scrambled or replaced by something else — re-anchor
    // the original so future resets get caught
    parent.setAttribute("data-original-text", original);
  }
}

export function WipScrambleAll() {
  useLayoutEffect(() => {
    if (!WIP_SCRAMBLE) return;
    if (typeof document === "undefined") return;

    // Initial pass
    walkAndScramble(document.body);

    // Reveal
    document.body.classList.remove("wip-scrambling");
    document.body.classList.add("wip-scrambled");

    // Mark a sentinel on document so we can confirm from DevTools
    // that this component actually ran
    document.documentElement.setAttribute("data-wip-scrambled-by", "WipScrambleAll");

    let rafPending = false;
    const scheduleRescramble = (mutations: MutationRecord[]) => {
      if (rafPending) return;
      rafPending = true;
      requestAnimationFrame(() => {
        rafPending = false;
        for (const m of mutations) {
          if (m.type === "characterData") {
            if (m.target.nodeType === Node.TEXT_NODE) {
              rescrambleIfReset(m.target as Text);
            }
          } else if (m.type === "childList") {
            m.addedNodes.forEach((n) => {
              if (n.nodeType === Node.TEXT_NODE) {
                scrambleTextNode(n as Text);
              } else if (n.nodeType === Node.ELEMENT_NODE) {
                walkAndScramble(n);
              }
            });
          }
        }
      });
    };

    const observer = new MutationObserver(scheduleRescramble);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      characterDataOldValue: false,
    });

    return () => observer.disconnect();
  }, []);

  return null;
}
