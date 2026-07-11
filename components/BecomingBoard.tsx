"use client";

import Link from "next/link";
import { HEXAGRAMS, SECTIONS, TRIGRAMS } from "@/lib/data/hexagrams";

type CellStatus = "published" | "draft" | "placeholder";

// For now, only the Prologue is "published" — the rest are placeholders.
// As chapters get written, update this manifest.
const CHAPTER_STATUS: Record<number, CellStatus> = {
  // Prologue: always accessible
  0: "published",
  // The full 64 — starting as placeholders, upgrade to "draft" then "published"
};

function getStatus(chapter: number): CellStatus {
  return CHAPTER_STATUS[chapter] || "placeholder";
}

const STATUS_STYLES: Record<CellStatus, { bg: string; border: string; text: string; cursor: string }> = {
  published:   { bg: "bg-lavender/15 hover:bg-lavender/25", border: "border-lavender", text: "text-lavender", cursor: "cursor-pointer" },
  draft:       { bg: "bg-amber-500/5 hover:bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-500", cursor: "cursor-pointer" },
  placeholder: { bg: "bg-surface-alt/30", border: "border-border", text: "text-dim/40", cursor: "cursor-not-allowed" },
};

function BoardCell({ number, hexagram, section }: { number: number; hexagram: (typeof HEXAGRAMS)[1]; section: { trigram: string } }) {
  const status = getStatus(number);
  const style = STATUS_STYLES[status];
  const trigram = TRIGRAMS[section.trigram];
  const href = status === "placeholder" ? "#" : `/becoming/${number}`;

  return (
    <Link
      href={href}
      className={`group flex aspect-square flex-col items-center justify-center rounded-lg border text-center transition-all ${style.bg} ${style.border} ${style.cursor}`}
      aria-disabled={status === "placeholder"}
    >
      <span className="font-mono text-[10px] leading-none text-dim/50">
        {trigram?.symbol}
      </span>
      <span className={`mt-0.5 font-mono text-xs font-semibold ${style.text}`}>
        {number}
      </span>
      <span className={`mt-0.5 font-head text-[11px] leading-tight ${style.text}`}>
        {hexagram.name}
      </span>
      {status === "draft" && (
        <span className="mt-1 rounded-full bg-amber-500/10 px-1.5 py-0.5 font-mono text-[9px] text-amber-500">
          draft
        </span>
      )}
    </Link>
  );
}

export function BecomingBoard() {
  return (
    <div className="overflow-x-auto">
      {/* Section legends — vertical trigram labels */}
      <div className="mb-6 space-y-3">
        {SECTIONS.map((section) => {
          const trigram = TRIGRAMS[section.trigram];
          const publishedCount = section.chapters.filter((ch) => getStatus(ch) === "published").length;
          return (
            <Link
              key={section.slug}
              href={`/becoming/section/${section.slug}`}
              className="group flex items-center gap-3 rounded-lg border border-border p-3 transition hover:border-lavender"
            >
              <span className="font-mono text-xl text-lavender">{trigram?.symbol}</span>
              <div className="flex-1">
                <span className="font-head text-sm font-semibold text-ink">{section.name}</span>
                <span className="ml-2 font-mono text-[11px] text-dim">{trigram?.element}</span>
              </div>
              <span className="font-mono text-xs text-muted">{section.question}</span>
              <div className="flex gap-1">
                {section.chapters.map((ch) => {
                  const s = getStatus(ch);
                  return (
                    <div
                      key={ch}
                      className={`h-1.5 w-1.5 rounded-full ${
                        s === "published" ? "bg-lavender" : s === "draft" ? "bg-amber-500" : "bg-border"
                      }`}
                      title={`Chapter ${ch}: ${s}`}
                    />
                  );
                })}
              </div>
            </Link>
          );
        })}
      </div>

      {/* The full 8×8 grid */}
      <div className="overflow-x-auto">
        <div className="mb-2 flex items-center justify-between font-mono text-[10px] text-dim">
          <span>☰ Heaven →</span>
          <span>Upper Canon (1–30) · 乾 坤 屯 蒙 需 訟 師 比</span>
          <span>Lower Canon (31–64) · 咸 恆 遯 大壯 晉 明夷 家人 睽</span>
          <span>→ 未濟 Before Completion</span>
        </div>

        {/* 8 columns — each group of 8 hexagrams */}
        <div className="grid grid-cols-8 gap-1.5" style={{ minWidth: 640 }}>
          {Array.from({ length: 8 }, (_, col) => (
            <div key={col} className="flex flex-col gap-1.5">
              {Array.from({ length: 8 }, (_, row) => {
                const hexNumber = col * 8 + row + 1;
                const hexagram = HEXAGRAMS[hexNumber];
                const section = SECTIONS[row];
                if (!hexagram || !section) return null;
                return (
                  <BoardCell
                    key={hexNumber}
                    number={hexNumber}
                    hexagram={hexagram}
                    section={section}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-6 flex items-center gap-4 font-mono text-xs text-dim">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-lavender" /> Published
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-amber-500" /> Draft
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm border border-border" /> Placeholder
        </span>
        <span className="ml-auto">1 of 64 chapters published. The board fills in over time.</span>
      </div>
    </div>
  );
}
