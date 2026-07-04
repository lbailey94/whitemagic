"use client";

import dynamic from "next/dynamic";

const MemoryBrowserCSR = dynamic(
  () =>
    import("@/components/MemoryBrowser").then((m) => ({
      default: m.MemoryBrowser,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[500px] items-center justify-center rounded-2xl border border-border bg-surface">
        <div className="text-sm text-dim">Loading memory browser...</div>
      </div>
    ),
  },
);

export function MemoryBrowserLazy(props: {
  apiUrl?: string;
  height?: number;
}) {
  return <MemoryBrowserCSR {...props} />;
}
