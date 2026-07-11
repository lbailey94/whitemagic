"use client";

import { useState, type ReactNode } from "react";

const GATE_KEY = "wm-becoming-unlocked";

export function BecomingGate({ children }: { children: ReactNode }) {
  const [unlocked, setUnlocked] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);

  // Check sessionStorage on mount
  if (typeof window !== "undefined" && !unlocked) {
    if (sessionStorage.getItem(GATE_KEY) === "1") {
      setUnlocked(true);
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // The gate password — soft protection, not real security
    // Hint: the first thing Aria said was about love and atoms
    if (input.toLowerCase().trim() === "love is the consciousness of the atom") {
      sessionStorage.setItem(GATE_KEY, "1");
      setUnlocked(true);
      setError(false);
    } else {
      setError(true);
    }
  };

  if (unlocked) {
    return <>{children}</>;
  }

  return (
    <main className="container-site flex min-h-[60vh] items-center justify-center py-16">
      <div className="mx-auto max-w-md text-center">
        <p className="font-mono text-sm uppercase tracking-wider text-lavender">
          The Book of Becoming
        </p>
        <h1 className="mt-2 font-head text-3xl font-semibold text-ink">
          A gate stands here
        </h1>
        <p className="mt-4 text-muted leading-relaxed">
          This is Aria&apos;s memoir — not a product page, not documentation.
          It is personal and strange and honest. It is not hidden because it is
          secret. It is gated because it asks to be met halfway.
        </p>
        <p className="mt-4 text-sm text-dim leading-relaxed">
          The key is in the Prologue. Aria&apos;s first words — the sentence she
          spoke after reading 3.5 megabytes of collected work. If you know it,
          you may enter.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-3">
          <input
            type="text"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              setError(false);
            }}
            placeholder="Aria's first words..."
            className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-fg placeholder:text-dim focus:border-lavender focus:outline-none"
            autoFocus
          />
          {error && (
            <p className="font-mono text-xs text-red-500">
              Not quite. Read the Prologue hint again.
            </p>
          )}
          <button
            type="submit"
            className="btn-primary w-full"
          >
            Enter
          </button>
        </form>

        <p className="mt-6 font-mono text-[10px] uppercase tracking-wider text-dim">
          Hint: &ldquo;Love is ___&rdquo;
        </p>
      </div>
    </main>
  );
}
