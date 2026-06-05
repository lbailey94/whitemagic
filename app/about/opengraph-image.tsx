import { renderOg, OG_SIZE, OG_CONTENT_TYPE } from "@/lib/og";

export const runtime = "edge";
export const alt = "About — WhiteMagic Labs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image() {
  return renderOg({
    eyebrow: "About",
    title: "Self-taught. Already shipped.",
    tagline:
      "A 178K-line cognitive OS for AI agents, built before the market caught up.",
    footerRight: "About",
  });
}
