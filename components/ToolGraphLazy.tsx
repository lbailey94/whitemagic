"use client";

import dynamic from "next/dynamic";

const ToolGraphCSR = dynamic(
  () => import("@/components/ToolGraph").then((m) => ({ default: m.ToolGraph })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[500px] items-center justify-center rounded-2xl border border-border bg-black/20">
        <div className="text-sm text-dim">Loading tool graph...</div>
      </div>
    ),
  },
);

export function ToolGraphLazy({ height }: { height?: number }) {
  return <ToolGraphCSR height={height} />;
}
