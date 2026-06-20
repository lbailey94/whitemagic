"use client";

import { useEffect } from "react";
import { WIP_SCRAMBLE } from "@/lib/wip";

/**
 * WipScrambleAll — when WIP_SCRAMBLE is on, walks the entire DOM
 * and replaces every text node's content with a stream of random
 * digits. The original text is preserved in the parent's
 * `data-original-text` attribute.
 *
 * Uses useEffect (not useLayoutEffect) because in Next.js App
 * Router, the body content is created by React from RSC data
 * AFTER the initial commit. We need to wait for the next
 * animation frame to ensure the full DOM is in place before
 * walking.
 *
 * Skips: SCRIPT, STYLE, CODE, PRE, TEXTAREA, INPUT, SELECT, OPTION,
 * NOSCRIPT, TEMPLATE, SVG, IFRAME, EMBED, OBJECT. Also skips any
 * element with `data-no-scramble` or `data-wip-scrambled`.
 *
 * MutationObserver watches for new content and re-renders that
 * reset scrambled text. Debounced via rAF.
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

function rescrambleIfReset(node: Text): void {
  if (!node.nodeValue) return;
  const parent = node.parentElement;
  if (!parent) return;
  if (shouldSkipElement(parent)) return;
  const original = parent.getAttribute("data-original-text");
  if (!original) return;
  if (node.nodeValue === original) {
    node.nodeValue = scrambleText(original, SEED + original.length);
  }
}

export function WipScrambleAll() {
  useEffect(() => {
    if (!WIP_SCRAMBLE) return;
    if (typeof document === "undefined") return;

    // Run the scramble on the next animation frame, after React
    // has fully committed the DOM (including RSC data).
    const raf1 = requestAnimationFrame(() => {
      // Do two passes: one immediately, one more on the next frame
      // in case React is still streaming in content.
      walkAndScramble(document.body);

      // Reveal the body
      document.body.classList.remove("wip-scrambling");
      document.body.classList.add("wip-scrambled");

      // Mark document so DevTools can confirm
      document.documentElement.setAttribute("data-wip-scrambled-by", "WipScrambleAll");

      // Second pass on the next frame to catch any late-arriving
      // content (RSC streaming, async data, etc.)
      requestAnimationFrame(() => {
        walkAndScramble(document.body);
      });
    });

    // Watch for mutations: new content, React re-renders
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
    });

    return () => {
      cancelAnimationFrame(raf1);
      observer.disconnect();
    };
  }, []);

  return null;
}
