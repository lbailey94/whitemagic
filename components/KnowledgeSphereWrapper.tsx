"use client";

import dynamic from "next/dynamic";

const KnowledgeSphereCSR = dynamic(
  () =>
    import("@/components/KnowledgeSphere").then((m) => ({
      default: m.KnowledgeSphere,
    })),
  { ssr: false },
);

export function KnowledgeSphereWrapper() {
  return <KnowledgeSphereCSR />;
}
