import { DomainIndex } from "@/components/essay/DomainIndex";
import type { EssayMeta } from "@/components/essay/EssayCard";

const ESSAYS: EssayMeta[] = [
  {
    slug: "karma-ledger-ethical-governance",
    title: "Karma Ledger: ethical governance as a computational primitive",
    blurb:
      "A claim/ledger model for tracking ethical debt in agent systems. Voice audit scanning, deterministic logging, and why governance needs to be a first-class runtime concern, not a policy document.",
    date: "2026-04",
    domain: "philosophy",
    epistemicTag: "Promising",
    ready: false,
  },
  {
    slug: "epistemic-honesty-in-ai-systems",
    title: "Epistemic honesty is the missing AI safety primitive",
    blurb:
      "AI systems confidently assert falsehoods because we haven't taught them to label uncertainty. A proposal for mandatory epistemic tagging in agent outputs — from proven to speculative to mythopoetic.",
    date: "2026-05",
    domain: "philosophy",
    epistemicTag: "Contested",
    ready: false,
  },
];

export default function PhilosophyPage() {
  return (
    <DomainIndex
      domain="philosophy"
      title="Philosophy"
      description="Ethics, governance, epistemic rigor, and the philosophical frameworks that guide what we build and why we build it."
      essays={ESSAYS}
    />
  );
}
