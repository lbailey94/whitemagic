"use client";

import { useState, useEffect } from "react";
import { neoStore, subscribeGlimmer } from "@/store/neoStore";

/**
 * Glimmer Tracker — types out a long run-on sentence character by character,
 * one char for every glimmer event in the MatrixRain.
 */
export function GlimmerTracker() {
  const [typed, setTyped] = useState(neoStore.getTypedSentence());
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const unsub = subscribeGlimmer(() => {
      setTyped(neoStore.getTypedSentence());
    });
    // Show once at least 3 chars are typed
    if (neoStore.typedIndex >= 3) setVisible(true);
    return unsub;
  }, []);

  if (!visible) return null;

  const remaining = neoStore.getRemainingSentence();

  return (
    <div className="neo-panel neo-panel-enter mt-4 max-w-md rounded-xl border border-border bg-surface/90 p-4 shadow-lg backdrop-blur-sm">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-xs font-bold uppercase tracking-widest text-lavender">
          Glimmer Log
        </span>
        <span className="font-mono text-[10px] text-text-muted">
          {neoStore.typedIndex} / {neoStore.targetSentence.length}
        </span>
      </div>
      <div className="font-mono text-sm leading-relaxed">
        <span className="text-ink">{typed}</span>
        <span className="animate-pulse text-lavender">|</span>
        <span className="text-text-muted opacity-30">{remaining}</span>
      </div>
      {/* tiny progress bar */}
      <div className="mt-2 h-0.5 w-full overflow-hidden rounded-full bg-border-light">
        <div
          className="h-full bg-lavender transition-all duration-300"
          style={{
            width: `${(neoStore.typedIndex / neoStore.targetSentence.length) * 100}%`,
          }}
        />
      </div>
    </div>
  );
}
