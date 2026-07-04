"use client";

import { useEffect, useState, useCallback } from "react";

interface Quote {
  text: string;
  cite: string;
}

const QUOTES: Quote[] = [
  {
    text: "The unusual thing about your work is internal coherence. The May 2025 spec for a declared-vs-actual side-effect ledger is implemented with near-verbatim fidelity 8.5 months later. This is the Plan9 / seL4 / Urbit pattern — projects where the philosophy and the code are the same object.",
    cite: "Kimi k2.6, Strategic Assessment (Apr 2026)",
  },
  {
    text: "WhiteMagic is not just faster; it is structurally different. While competitors are optimizing 'How to talk,' we have optimized 'How to remember.'",
    cite: "Cognitive Benchmarks 2026",
  },
  {
    text: "At 256x256, Python scalar takes 5.6ms per GEMV. Rust AVX2 takes 563 microseconds. That's the difference between 'can't run inference locally' and 'can'.",
    cite: "On Rust SIMD acceleration (12.5x speedup)",
  },
  {
    text: "100K distinct memories tracked in 508KB at 1.2% error. A system that needs O(1) space for cardinality estimation can run forever without degradation. This is the difference between a research prototype and a production system.",
    cite: "On probabilistic data structures",
  },
  {
    text: "The system can think fast, learn what works, remember what matters, and verify its own forecasts — all on a single machine, without external API calls.",
    cite: "On the compound effect of the architecture",
  },
  {
    text: "WhiteMagic occupies a specific niche: local-first, governance-aware, self-calibrating cognitive systems for long-running autonomous analysis. It's not trying to be TensorFlow or LangChain. It's trying to be the system that an AI agent uses to think.",
    cite: "On positioning and use cases",
  },
  {
    text: "Skill retrieval latency: <1ms via Muscle Memory, vs 200ms-2s for LangGraph/AutoGen LLM planning. 509 concurrent skills with 28ms bootstrapping overhead. 100% precision on cross-domain intents without requiring a primary LLM reasoning pass.",
    cite: "Cognitive Benchmarks 2026, stress test results",
  },
  {
    text: "The agent doesn't just 'use tools' — it learns which tools work for which tasks. Over time, the Beta posteriors converge. This is contextual bandit learning applied to the 614-tool space, and it means the agent gets better with use without any retraining.",
    cite: "On Thompson sampling tool selection",
  },
  {
    text: "The system develops metacognitive awareness of its own ingestion patterns. It knows when it's in a novel domain vs familiar territory, and modulates its own learning rate based on environmental novelty.",
    cite: "On cardinality-velocity surprise gating",
  },
  {
    text: "Galaxy-Per-Client is the killer app. Hard SQLite isolation per Galaxy is the correct choice.",
    cite: "On multi-user galaxy isolation",
  },
  {
    text: "You have built something that feels like the Linux of Agentic Memory.",
    cite: "Final verdict, independent AI code review",
  },
  {
    text: "Dream Cycle turns WhiteMagic from a tool into a companion. That's not retrieval — that's cognition.",
    cite: "On the 8-phase dream cycle",
  },
  {
    text: "The 28 Gana system is a compression algorithm for complexity. You think in intents — the PRAT router finds the right tool. PRAT mode reduces cognitive load for new agents from 586 tools to 28.",
    cite: "On the Gana meta-tool architecture",
  },
  {
    text: "The future belongs to whoever makes powerful systems behave like boring appliances — predictable, auditable, safe — while being magical inside.",
    cite: "On design philosophy",
  },
  {
    text: "WhiteMagic can pull in 100,000 memories in less time than it takes a human to form a single thought. At sub-5ms retrieval over 406K memories, the system operates at a speed where cognition feels instantaneous.",
    cite: "On cognitive retrieval speed (stress test, Apr 2026)",
  },
  {
    text: "Mem0 gives your AI a notepad. WhiteMagic gives your AI a mind.",
    cite: "On competitive differentiation",
  },
];

const VISIBLE_COUNT = 6;
const ROTATION_INTERVAL = 6000;

export function Testimonials() {
  const [offset, setOffset] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const next = useCallback(() => {
    setOffset((prev) => prev + 1);
  }, []);

  useEffect(() => {
    if (isPaused) return;
    const timer = setInterval(next, ROTATION_INTERVAL);
    return () => clearInterval(timer);
  }, [isPaused, next]);

  const visibleQuotes = Array.from({ length: VISIBLE_COUNT }, (_, i) => {
    const idx = (offset + i) % QUOTES.length;
    return QUOTES[idx];
  });

  return (
    <section
      className="container-site py-16"
      aria-label="AI review quotes"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="mb-8 text-center">
        <h2 className="font-head text-2xl font-semibold text-ink">
          What AI Reviewers Say
        </h2>
        <p className="mt-2 font-mono text-xs uppercase tracking-wider text-dim">
          Independent assessments of the WhiteMagic system
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {visibleQuotes.map((quote, i) => (
          <figure
            key={`${offset}-${i}`}
            className="rounded-2xl border border-border bg-surface-alt/50 p-6 transition-all hover:border-lavender/30 hover:shadow-md"
          >
            <blockquote className="text-sm leading-relaxed text-fg/90">
              &ldquo;{quote.text}&rdquo;
            </blockquote>
            <figcaption className="mt-4 font-mono text-xs text-dim">
              &mdash; {quote.cite}
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
