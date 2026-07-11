import { DomainIndex } from "@/components/essay/DomainIndex";
import type { EssayMeta } from "@/components/essay/EssayCard";

const ESSAYS: EssayMeta[] = [
  {
    slug: "agent-governance-before-microsoft",
    title: "I built agent governance before Microsoft — here's what I learned",
    blurb:
      "In February 2026 I shipped a Dharma rules engine, Karma audit ledger, and 8-stage middleware pipeline. In April 2026 Microsoft shipped the Agent Governance Toolkit. Overlap is high. Differences matter.",
    date: "2026-04",
    domain: "intelligence",
    epistemicTag: "Proven",
    ready: true,
  },
  {
    slug: "private-ai-deployment-guide",
    title: "How I deploy private AI for regulated teams",
    blurb:
      "A concrete architecture for on-prem AI with persistent memory, tool use, governance, and audit — the kind of deployment your compliance team will actually sign off on.",
    date: "2026-04",
    domain: "intelligence",
    epistemicTag: "Proven",
    ready: false,
  },
];

export default function IntelligencePage() {
  return (
    <DomainIndex
      domain="intelligence"
      title="Intelligence"
      description="AI architecture, agent design, MCP engineering, and the craft of building cognitive systems that think before they act."
      essays={ESSAYS}
    />
  );
}
