"use client";

import { useNEO } from "@/hooks/useNEO";

/**
 * NEO Code Input Display — shows the current 3-letter buffer beneath
 * the triquetra with an arcade-cabinet aesthetic.
 */
export function NEOCodeInput() {
  const { buffer, flash } = useNEO();
  const isIdle = buffer.length === 0 && !flash;

  const slots = [0, 1, 2];

  return (
    <div className="mt-4 flex flex-col items-center gap-2">
      {/* 3-letter code slots */}
      <div
        className={`flex gap-2 rounded-lg border px-3 py-2 transition-all duration-300 ${
          flash
            ? "border-lavender bg-lavender/10 shadow-[0_0_12px_rgba(124,92,191,0.3)]"
            : isIdle
              ? "neo-slot-idle border-lavender/25 bg-surface/80"
              : "border-border bg-surface/80"
        }`}
      >
        {slots.map((i) => (
          <div
            key={i}
            className="flex h-8 w-8 items-center justify-center rounded border text-xs font-bold transition-all"
            style={{
              fontFamily: '"Press Start 2P", monospace',
              fontSize: '10px',
              lineHeight: 1,
              letterSpacing: '0.05em',
            }}
          >
            <span className={i < buffer.length ? "text-lavender" : "text-text-muted opacity-40"}>
              {buffer[i] || "_"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
