import { renderOg, OG_SIZE, OG_CONTENT_TYPE } from "@/lib/og";

export const runtime = "edge";
export const alt = "Private AI Deployment — WhiteMagic Labs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image() {
  return renderOg({
    eyebrow: "Service",
    title: "AI that lives inside your walls.",
    tagline:
      "Private LLM + agent systems on your infrastructure. HIPAA, SOC2, air-gap-friendly.",
    footerRight: "Private AI Deployment",
  });
}
