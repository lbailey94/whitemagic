"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { emitUnlock } from "@/store/neoStore";

/**
 * NEO Arcade Code System — Konami-style 3-letter code input.
 *
 * Listens for keystrokes globally, maintains a rolling buffer of the
 * last 3 characters. When the buffer matches a registered code, the
 * associated panel is unlocked.
 */

export interface NEOCode {
  code: string; // 3 uppercase letters, e.g. "NEO"
  panel: string; // panel name to unlock
  label: string; // human-readable effect name
}

export const NEO_CODES: NEOCode[] = [
  { code: "NEO", panel: "rain", label: "Matrix Controls" },
  { code: "DNA", panel: "hue", label: "Color Shift" },
  { code: "GOD", panel: "all", label: "Full Access" },
];

const CODE_MAP = new Map(NEO_CODES.map((c) => [c.code, c]));

export function useNEO() {
  const [buffer, setBuffer] = useState("");
  const [lastMatch, setLastMatch] = useState<NEOCode | null>(null);
  const [flash, setFlash] = useState(false);
  const bufferRef = useRef("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Keep bufferRef in sync
  useEffect(() => {
    bufferRef.current = buffer;
  }, [buffer]);

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      // Ignore if user is typing in a real input/textarea (except our own)
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      const ch = e.key.toUpperCase();
      if (!/^[A-Z]$/.test(ch)) return;

      e.preventDefault();

      const next = (bufferRef.current + ch).slice(-3);
      bufferRef.current = next;
      setBuffer(next);

      // Check for match
      const match = CODE_MAP.get(next);
      if (match) {
        setLastMatch(match);
        setFlash(true);
        setTimeout(() => setFlash(false), 600);
        emitUnlock(match.panel);
        bufferRef.current = "";
        setTimeout(() => setBuffer(""), 800);
      }
    },
    [],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  const reset = useCallback(() => {
    bufferRef.current = "";
    setBuffer("");
    setLastMatch(null);
  }, []);

  return { buffer, lastMatch, flash, reset, inputRef };
}
