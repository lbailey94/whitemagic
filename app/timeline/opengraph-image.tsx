import { renderOg, OG_SIZE, OG_CONTENT_TYPE } from "@/lib/og";

export const runtime = "edge";
export const alt = "Timeline — WhiteMagic";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image() {
  return renderOg({
    eyebrow: "Timeline",
    title: "Shipped before the market caught up.",
    tagline:
      "40+ entries tracking WhiteMagic primitives against the industry's published standards.",
    footerRight: "Prescience Gap",
  });
}
