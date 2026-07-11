"use client";

import dynamic from "next/dynamic";

const InteractiveGalaxySphereCSR = dynamic(
  () =>
    import("@/components/InteractiveGalaxySphere").then((m) => ({
      default: m.InteractiveGalaxySphere,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[500px] items-center justify-center rounded-2xl border border-border bg-black">
        <div className="text-sm text-dim">Loading galaxy visualization...</div>
      </div>
    ),
  },
);

export function InteractiveGalaxySphereLazy(props: {
  height?: number;
  autoRotate?: boolean;
}) {
  return <InteractiveGalaxySphereCSR {...props} />;
}
