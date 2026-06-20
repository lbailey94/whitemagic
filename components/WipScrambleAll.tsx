"use client";

import { useEffect } from "react";
import { WIP_SCRAMBLE } from "@/lib/wip";

/**
 * WipScrambleAll — when WIP_SCRAMBLE is on, walks the entire DOM
 * and replaces every text node's content with a stream of random
 * digits. The original text is preserved in the parent's
 * `data-original-text` attribute.
 *
 * Approach:
 * 1. useEffect → rAF → walk body (after React first commit)
 * 2. rAF → walk again (catch late RSC streaming)
 * 3. MutationObserver watches for new content + characterData
 *    changes (React re-renders)
 * 4. setTimeout fallback at 1s, 2s, 3s to catch anything missed
 * 5. Visible status badge in bottom-left so user can see progress
 *
 * The status badge is data-no-scramble so it always reads
 * correctly. After the body is fully scrambled, the badge
 * disappears.
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

function scrambleTextNode(node: Text): boolean {
  if (!node.nodeValue) return false;
  const parent = node.parentElement;
  if (!parent) return false;
  if (shouldSkipElement(parent)) return false;
  if (parent.hasAttribute("data-original-text")) return false;
  if (!node.nodeValue.trim()) return false;

  const original = node.nodeValue;
  parent.setAttribute("data-original-text", original);
  node.nodeValue = scrambleText(original, SEED + original.length);
  return true;
}

function walkAndScramble(root: Node): number {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let n: Node | null = walker.nextNode();
  let count = 0;
  while (n) {
    if (scrambleTextNode(n as Text)) count++;
    n = walker.nextNode();
  }
  return count;
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

function showStatus(text: string, kind: "info" | "ok" | "err" = "info"): void {
  let el = document.getElementById("wip-scramble-status");
  if (!el) {
    el = document.createElement("div");
    el.id = "wip-scramble-status";
    el.setAttribute("data-no-scramble", "");
    el.style.cssText =
      "position:fixed;bottom:16px;left:16px;z-index:9999;background:#1a1a1a;color:#fff;padding:8px 12px;border-radius:6px;font-family:monospace;font-size:12px;border:1px solid #8b7ec7;max-width:400px;";
    document.body.appendChild(el);
  }
  const color = kind === "ok" ? "#8b7ec7" : kind === "err" ? "#f87171" : "#fbbf24";
  el.style.borderColor = color;
  el.textContent = text;
}

function hideStatus(): void {
  const el = document.getElementById("wip-scramble-status");
  if (el) el.remove();
}

export function WipScrambleAll() {
  useEffect(() => {
    if (!WIP_SCRAMBLE) return;
    if (typeof document === "undefined") return;

    showStatus("scramble: init", "info");

    let totalScrambled = 0;

    const doWalk = (label: string) => {
      const count = walkAndScramble(document.body);
      totalScrambled += count;
      // eslint-disable-next-line no-console
      console.log(`[wip-scramble] ${label}: scrambled ${count} text nodes (total ${totalScrambled})`);
      showStatus(`scramble: ${label} (${count} new, ${totalScrambled} total)`, "info");
      return count;
    };

    // Reveal the body (even before scramble, so we can see what's happening)
    document.body.classList.remove("wip-scrambling");
    document.body.classList.add("wip-scrambled");
    document.documentElement.setAttribute("data-wip-scrambled-by", "WipScrambleAll");

    // First pass: next animation frame
    const raf1 = requestAnimationFrame(() => {
      doWalk("rAF1");
      // Second pass: another frame later, in case RSC is still streaming
      requestAnimationFrame(() => {
        doWalk("rAF2");
        // Third pass via setTimeout for late-arriving content
        setTimeout(() => doWalk("t=1s"), 1000);
        setTimeout(() => {
          doWalk("t=2s");
          if (totalScrambled > 0) {
            showStatus(`scramble: ok (${totalScrambled} text nodes)`, "ok");
            // Auto-hide the status badge after 3s
            setTimeout(hideStatus, 3000);
          } else {
            showStatus("scramble: WARN no text nodes found", "err");
          }
        }, 2000);
      });
    });

    // MutationObserver for ongoing changes
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
