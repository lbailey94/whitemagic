"use client";

import { useState } from "react";
import { KnowledgeSphereWrapper } from "@/components/KnowledgeSphereWrapper";
import { ConsolidatedSphere } from "@/components/ConsolidatedSphere";

type SphereMode = "raw" | "consolidated";

export function SphereViewToggle() {
  const [mode, setMode] = useState<SphereMode>("consolidated");

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <span className="font-mono text-xs uppercase tracking-wider text-dim">
          View:
        </span>
        <button
          onClick={() => setMode("consolidated")}
          className={`rounded-lg px-3 py-1 font-mono text-xs transition ${
            mode === "consolidated"
              ? "bg-lavender text-white"
              : "border border-border text-dim hover:text-fg"
          }`}
        >
          793 clusters
        </button>
        <button
          onClick={() => setMode("raw")}
          className={`rounded-lg px-3 py-1 font-mono text-xs transition ${
            mode === "raw"
              ? "bg-lavender text-white"
              : "border border-border text-dim hover:text-fg"
          }`}
        >
          10,768 chunks
        </button>
      </div>

      {mode === "consolidated" ? (
        <ConsolidatedSphere />
      ) : (
        <KnowledgeSphereWrapper />
      )}

      <p className="mt-2 font-mono text-xs text-dim">
        {mode === "consolidated"
          ? "793 semantic clusters — 13.6x compression from raw chunks. Each cluster merges related chunks via label-propagation. Includes titles and keywords from local synthesis."
          : "10,768 raw chunks from the CODEX pipeline. Color-coded by source: blue (library), green (conversations), orange (research)."}
      </p>
    </div>
  );
}
