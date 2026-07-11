import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    template: "%s — Essays — WhiteMagic Labs",
    default: "Essays — WhiteMagic Labs",
  },
  description:
    "Technical essays on intelligence, horizons, worldbuilding, and philosophy — all grounded in an epistemic framework.",
};

export default function EssaysLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
