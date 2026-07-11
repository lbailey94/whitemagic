import { renderOg, OG_SIZE, OG_CONTENT_TYPE } from "@/lib/og";

export const runtime = "edge";
export const alt = "Agent Economy — WhiteMagic";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image() {
  return renderOg({
    eyebrow: "Thesis",
    title: "Gratitude-grade economics for agents.",
    tagline:
      "Dual-rail payments. Proof of Gratitude. Voluntary-tier x402. The governance-first agent economy.",
    footerRight: "/economy",
  });
}
