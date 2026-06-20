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
 * NOSCRIPT, TEMPLATE, SVG. Also skips any element with
 * `data-no-scramble` (escape hatch) or `data-wip-scrambled` (marks
 * spans pre-scrambled by the inline <WipScramble /> component).
 *
 * Uses a MutationObserver to re-scramble dynamically added content
 * (route changes, async data, chat messages, etc.).
 *
 * Use LayoutEffect (not Effect) so the scramble happens before the
 * first paint — no flicker.
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
  // Skip whitespace-only nodes
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

export function WipScrambleAll() {
  useLayoutEffect(() => {
    if (!WIP_SCRAMBLE) return;
    if (typeof document === "undefined") return;

    // Mark the body as scrambling (CSS hides content) so the user
    // doesn't see the original text for one frame before the digits.
    document.body.classList.add("wip-scrambling");

    // Initial pass
    walkAndScramble(document.body);

    // Reveal the body now that everything is scrambled
    document.body.classList.remove("wip-scrambling");
    document.body.classList.add("wip-scrambled");

    // Watch for new content
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        m.addedNodes.forEach((n) => {
          if (n.nodeType === Node.TEXT_NODE) {
            scrambleTextNode(n as Text);
          } else if (n.nodeType === Node.ELEMENT_NODE) {
            walkAndScramble(n);
          }
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    return () => observer.disconnect();
  }, []);

  return null;
}
