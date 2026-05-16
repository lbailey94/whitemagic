import { renderOg, OG_SIZE, OG_CONTENT_TYPE } from "@/lib/og";

export const runtime = "edge";
export const alt = "Agent Governance — WhiteMagic Labs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image() {
  return renderOg({
    eyebrow: "Service",
    title: "Guardrails that turn autonomy into trust.",
    tagline:
      "Dharma Rules, Karma Ledger, Harmony Vector — mapped to OWASP LLM Top 10 (v1.1, covers agentic AI) and EU AI Act.",
    footerRight: "Agent Governance",
  });
}
