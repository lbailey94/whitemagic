"use client";

// Module-level log — fires as soon as the module is imported.
// If you see this in the console, the WipScrambleAll module loaded.
// eslint-disable-next-line no-console
console.log("[wip-scramble] MODULE LOADED", new Date().toISOString());

import { useEffect, useState } from "react";
import { WIP_SCRAMBLE } from "@/lib/wip";

/**
 * WipScrambleAll — when WIP_SCRAMBLE is on, walks the entire DOM
 * and replaces every text node's content with a stream of random
 * digits. The original text is preserved in the parent's
 * `data-original-text` attribute.
 *
 * Renders a visible status badge as a React component (not via
 * DOM manipulation) so React manages it. The badge is always
 * visible in the bottom-left and shows the scramble progress.
 * data-no-scramble keeps it readable.
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

export function WipScrambleAll() {
  const [status, setStatus] = useState<string>("scramble: mounted, waiting...");
  const [count, setCount] = useState<number>(0);
  const [show, setShow] = useState<boolean>(true);

  useEffect(() => {
    // eslint-disable-next-line no-console
    console.log("[wip-scramble] useEffect FIRED, WIP_SCRAMBLE=", WIP_SCRAMBLE);
    if (!WIP_SCRAMBLE) {
      setStatus("scramble: OFF (WIP_SCRAMBLE is false)");
      return;
    }
    if (typeof document === "undefined") {
      setStatus("scramble: SSR (no document)");
      return;
    }

    setStatus("scramble: init");

    const doWalk = (label: string): number => {
      const n = walkAndScramble(document.body);
      // eslint-disable-next-line no-console
      console.log(`[wip-scramble] ${label}: scrambled ${n} text nodes`);
      setStatus(`scramble: ${label} (+${n})`);
      setCount((c) => {
        const total = c + n;
        if (label === "done") {
          setTimeout(() => setShow(false), 3000);
        }
        return total;
      });
      return n;
    };

    // Reveal the body so user can see what's happening
    document.body.classList.remove("wip-scrambling");
    document.body.classList.add("wip-scrambled");
    document.documentElement.setAttribute("data-wip-scrambled-by", "WipScrambleAll");

    // First pass: next animation frame
    const raf1 = requestAnimationFrame(() => {
      doWalk("rAF1");
      // Second pass
      requestAnimationFrame(() => {
        doWalk("rAF2");
        setTimeout(() => doWalk("t=1s"), 1000);
        setTimeout(() => doWalk("t=2s"), 2000);
        setTimeout(() => doWalk("done"), 3000);
      });
    });

    // MutationObserver
    let rafPending = false;
    const onMutate = (mutations: MutationRecord[]) => {
      if (rafPending) return;
      rafPending = true;
      requestAnimationFrame(() => {
        rafPending = false;
        for (const m of mutations) {
          if (m.type === "characterData" && m.target.nodeType === Node.TEXT_NODE) {
            rescrambleIfReset(m.target as Text);
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

    const observer = new MutationObserver(onMutate);
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

  if (!show) return null;

  return (
    <div
      data-no-scramble
      data-wip-scramble-badge
      style={{
        position: "fixed",
        bottom: 16,
        left: 16,
        zIndex: 99999,
        background: "#1a1a1a",
        color: "#fff",
        padding: "8px 12px",
        borderRadius: 6,
        fontFamily: "monospace",
        fontSize: 11,
        border: "1px solid #8b7ec7",
        maxWidth: 500,
        pointerEvents: "none",
      }}
    >
      <div style={{ fontWeight: "bold", color: "#8b7ec7" }}>WIP SCRAMBLE</div>
      <div>WIP_SCRAMBLE: {String(WIP_SCRAMBLE)}</div>
      <div>status: {status}</div>
      <div>total scrambled: {count}</div>
    </div>
  );
}
