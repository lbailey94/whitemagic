import { renderOg, OG_SIZE, OG_CONTENT_TYPE } from "@/lib/og";

export const runtime = "edge";
export const alt = "Pricing — WhiteMagic Labs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image() {
  return renderOg({
    eyebrow: "Pricing",
    title: "Three tiers. One principle.",
    tagline:
      "Office Hours $1,000 · Architecture Review $12,000 · Engagements from $35,000.",
    footerRight: "Pricing",
  });
}
