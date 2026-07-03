import { renderOg, OG_SIZE, OG_CONTENT_TYPE } from "@/lib/og";

export const runtime = "edge";
export const alt = "MCP Governance & Scale — WhiteMagic Labs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image() {
  return renderOg({
    eyebrow: "Service",
    title: "MCP at scale: governance, compression, observability.",
    tagline:
      "Custom servers, tool-contract design, 28-Gana compression — 87% token reduction on tool payloads.",
    footerRight: "MCP Governance & Scale",
  });
}
