/**
 * Boot Sequence — Terminal-style diagnostic loader
 *
 * Ported from whitemagic-aux/whitemagic-frontend/web/js/boot-sequence.js
 * Adapted to React with IntersectionObserver trigger, typewriter effect,
 * and animated progress bars. Uses WM_FACTS for current numbers.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { WM_FACTS } from "@/lib/facts";

interface BootLine {
  text: string;
  delay: number;
  progress?: { duration: number; status: string };
}

const BOOT_LINES: BootLine[] = [
  { text: `WHITE MAGIC v${WM_FACTS.version} Initializing...`, delay: 40 },
  { text: "Core Engine Status............. OK", delay: 30 },
  { text: `PRAT Router (${WM_FACTS.ganaTools} Ganas)........ ACTIVE`, delay: 30 },
  {
    text: "Loading MCP Tool Registry.....",
    delay: 20,
    progress: { duration: 800, status: `${WM_FACTS.callableTools} TOOLS LOADED` },
  },
  { text: "Polyglot Bridge Check:", delay: 30 },
  { text: `  Python 83.5%................ OK`, delay: 20 },
  { text: `  Rust (PyO3)................. OK  [${WM_FACTS.bridgeFunctions} functions]`, delay: 20 },
  { text: "  Zig SIMD.................... OK  [<2\u00b5s dispatch]", delay: 20 },
  { text: "  Go Gossipsub................ OK  [mesh ready]", delay: 20 },
  { text: "  Haskell FFI................. OK  [boundary engine]", delay: 15 },
  { text: "  Elixir OTP.................. OK  [supervisor trees]", delay: 15 },
  { text: "  TypeScript SDK.............. OK  [type-safe bindings]", delay: 15 },
  { text: "  Mojo/Julia/SQL/Proto........ OK", delay: 15 },
  { text: "Initializing Memory Subsystem..", delay: 25 },
  { text: "  5D Holographic Coordinates.. CALIBRATED", delay: 20 },
  { text: "  Galactic Map Lifecycle...... ACTIVE", delay: 20 },
  { text: "  HNSW Semantic Index......... READY", delay: 20 },
  { text: "Security Pipeline (8-stage):", delay: 25 },
  { text: "  Input Sanitizer............. ARMED", delay: 15 },
  { text: "  Circuit Breakers............ ARMED", delay: 15 },
  { text: "  Rate Limiter (Rust)......... 452K ops/sec", delay: 15 },
  { text: "  RBAC + Dharma Rules......... ENFORCING", delay: 15 },
  { text: "  Karma Ledger................ AUDITING", delay: 15 },
  { text: "  Violet Layer................ SCANNING", delay: 15 },
  {
    text: "Loading Governance Stack......",
    delay: 20,
    progress: { duration: 600, status: "DHARMA ACTIVE" },
  },
  { text: "Dream Cycle Engine............ STANDBY", delay: 20 },
  { text: "Harmony Vector................ 7D INITIALIZED", delay: 20 },
  { text: "EventRing (Rust).............. 2.58M events/sec", delay: 20 },
  { text: "Tokio Clone Army.............. 534K clones/sec", delay: 20 },
  { text: "", delay: 10 },
  { text: `SYSTEM STATUS: ${WM_FACTS.testsPassing} TESTS PASSING, 0 FAILURES`, delay: 40 },
  { text: "\u767d\u8853 COGNITIVE OS READY", delay: 50 },
];

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function BootSequence({ className = "" }: { className?: string }) {
  const containerRef = useRef<HTMLPreElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const [output, setOutput] = useState<string>("");
  const [isComplete, setIsComplete] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    let cancelled = false;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasStarted) {
            setHasStarted(true);
            if (reducedMotion) {
              // Show all at once
              const fullText = BOOT_LINES.map((l) => l.text).join("\n");
              setOutput(fullText);
              setIsComplete(true);
            } else {
              runSequence();
            }
          }
        });
      },
      { threshold: 0.3 },
    );

    observer.observe(trigger);

    async function runSequence() {
      let text = "";
      await sleep(300);

      for (const line of BOOT_LINES) {
        if (cancelled) return;

        if (line.progress) {
          // Type the label
          for (const ch of line.text) {
            if (cancelled) return;
            text += ch;
            setOutput(text);
            await sleep(line.delay);
          }

          // Progress bar
          const barLen = 20;
          const filled = "\u2588";
          const empty = "\u2591";
          const stepDur = line.progress.duration / barLen;

          text += " [";
          for (let i = 0; i < barLen; i++) {
            text += empty;
          }
          text += "] ";
          setOutput(text);

          for (let i = 1; i <= barLen; i++) {
            if (cancelled) return;
            await sleep(stepDur);
            const barStart = text.indexOf(" [") + 2;
            text =
              text.substring(0, barStart) +
              filled.repeat(i) +
              empty.repeat(barLen - i) +
              "] ";
            setOutput(text);
          }
          text += line.progress.status + "\n";
          setOutput(text);
        } else if (line.text === "") {
          text += "\n";
          setOutput(text);
          await sleep(line.delay);
        } else {
          for (const ch of line.text) {
            if (cancelled) return;
            text += ch;
            setOutput(text);
            await sleep(line.delay);
          }
          text += "\n";
          setOutput(text);
        }
        await sleep(20);
      }

      await sleep(500);
      if (!cancelled) setIsComplete(true);
    }

    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [hasStarted]);

  return (
    <div ref={triggerRef} className={className}>
      <pre
        ref={containerRef}
        className={`overflow-auto rounded-xl border border-border bg-black/90 p-6 font-mono text-xs leading-relaxed text-green-400 shadow-lg transition-opacity duration-500 ${
          hasStarted ? "opacity-100" : "opacity-0"
        } ${isComplete ? "ring-1 ring-green-500/20" : ""}`}
        aria-label="WhiteMagic system boot sequence"
      >
        {output}
        {!isComplete && hasStarted && (
          <span className="animate-pulse text-green-300">_</span>
        )}
      </pre>
    </div>
  );
}
