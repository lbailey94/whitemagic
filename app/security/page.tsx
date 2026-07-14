import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { SecurityDashboard } from "@/components/SecurityDashboard";
import { WM_FACTS } from "@/lib/facts";

export const metadata: Metadata = {
  title: "Security Posture — WhiteMagic Labs",
  description: `Real-time security dashboard — threat level, HermitCrab state, transaction firewall, engagement tokens, MCP integrity, and security event feed. Part of the ${WM_FACTS.callableTools}-tool substrate.`,
};

export default function SecurityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Security"
        title="Security Dashboard"
        lede="Live view of the WhiteMagic security posture — threat detection, HermitCrab protection states, transaction firewall, engagement tokens, and the unified security event bus."
      />

      <section className="container-site py-12">
        <SecurityDashboard />
      </section>
    </>
  );
}
