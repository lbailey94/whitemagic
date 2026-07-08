"use client";

import { useEffect, useState, useRef } from "react";
import { TomeCover } from "./TomeCover";
import { ThemeToggle } from "../ThemeToggle";
import { LangToggle } from "../LangToggle";

/**
 * TomeShell — the reading container.
 * Vertical-only scroll. Golden trim on left/right edges.
 * Progress indicator + section label.
 * Minimal top bar with theme/lang toggles.
 */
export function TomeShell({ children }: { children: React.ReactNode }) {
  const [progress, setProgress] = useState(0);
  const [currentLabel, setCurrentLabel] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onScroll = () => {
      const max = el.scrollHeight - el.clientHeight;
      const pct = max > 0 ? el.scrollTop / max : 0;
      setProgress(Math.min(1, Math.max(0, pct)));

      const pages = el.querySelectorAll("[data-tome-label]");
      let label = "";
      for (const page of pages) {
        const rect = page.getBoundingClientRect();
        if (rect.top <= 120 && rect.bottom > 120) {
          label = page.getAttribute("data-tome-label") || "";
          break;
        }
      }
      if (label) setCurrentLabel(label);
    };

    el.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      {/* Golden trim */}
      <div className="tome-trim-left" />
      <div className="tome-trim-right" />

      {/* Minimal top bar — just toggles */}
      <div className="fixed top-0 left-0 right-0 z-40 flex items-center justify-end gap-2 px-4 py-3 bg-bg/80 backdrop-blur">
        <LangToggle />
        <ThemeToggle />
      </div>

      {/* Progress indicator */}
      <div className="tome-progress">
        <div
          className="tome-progress-bar"
          style={{ width: `${progress * 100}%` }}
        />
      </div>
      {currentLabel && (
        <div className="tome-progress-label">{currentLabel}</div>
      )}

      {/* Content container — vertical scroll */}
      <div
        ref={containerRef}
        className="relative z-10 tome-scroll"
        style={{ height: "100vh" }}
      >
        <TomeCover />
        {children}
      </div>
    </>
  );
}
