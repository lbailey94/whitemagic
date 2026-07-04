"use client";

import dynamic from "next/dynamic";

const MatrixRainCSR = dynamic(
  () => import("@/components/MatrixRain").then((m) => ({ default: m.MatrixRain })),
  { ssr: false },
);

export function MatrixRainLazy() {
  return <MatrixRainCSR />;
}
