"use client";

import { AnimatedTriquetra } from "../AnimatedTriquetra";

/**
 * TomeCover — the front cover of the grimoire.
 * Static section at the top of the page (not an overlay).
 */
export function TomeCover() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center px-4 py-20">
      {/* Sigil */}
      <div className="relative mb-8 h-64 w-64 md:h-80 md:w-80">
        <AnimatedTriquetra rainbow rainbowSpeed={8} className="h-full w-full opacity-90" />
      </div>

      {/* Title */}
      <h1
        className="font-head text-5xl font-semibold tracking-[0.3em] text-ink md:text-7xl"
        style={{ textShadow: "0 0 30px rgba(212, 175, 55, 0.15)" }}
      >
        WHITEMAGIC
      </h1>

      {/* Subtitle */}
      <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.4em] text-dim md:text-xs">
        Cognitive Operating System for AI Agents
      </p>

      {/* Scroll prompt */}
      <div className="mt-16 animate-pulse">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-dim">
          scroll to begin
        </p>
      </div>

      {/* Ornamental flourish */}
      <div className="tome-ornament mt-8">❧</div>
    </section>
  );
}
