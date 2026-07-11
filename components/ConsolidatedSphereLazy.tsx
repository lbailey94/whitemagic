"use client";

import dynamic from "next/dynamic";

const ConsolidatedSphereCSR = dynamic(
  () =>
    import("@/components/ConsolidatedSphere").then((m) => ({
      default: m.ConsolidatedSphere,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[400px] items-center justify-center rounded-2xl border border-border bg-black">
        <div className="text-sm text-dim">Loading consolidated sphere...</div>
      </div>
    ),
  },
);

export function ConsolidatedSphereLazy() {
  return <ConsolidatedSphereCSR />;
}
