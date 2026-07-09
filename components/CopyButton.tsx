"use client";

import { useState, useCallback } from "react";

/**
 * CopyButton — copies text to clipboard with visual feedback.
 */
export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [text]);

  return (
    <button
      onClick={onCopy}
      className="rounded-md border border-border bg-surface px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-dim transition hover:border-lavender hover:text-lavender"
      aria-label="Copy to clipboard"
    >
      {copied ? "✓ 已複製" : label}
    </button>
  );
}
