import { DomainIndex } from "@/components/essay/DomainIndex";
import type { EssayMeta } from "@/components/essay/EssayCard";

const ESSAYS: EssayMeta[] = [
  {
    slug: "five-schools-of-civilization-design",
    title: "The Five Schools of Civilization Design",
    blurb:
      "From Long Now to Solarpunk to Accelerationist — mapping the intellectual landscape of people who think in centuries, not quarters.",
    date: "2026-05",
    domain: "worldbuilding",
    epistemicTag: "Mythopoetic",
    ready: false,
  },
  {
    slug: "uplift-convergence-thresholds",
    title: "UPLIFT: Convergence Thresholds for a Post-Scarcity Civilization",
    blurb:
      "Energy abundance, compute abundance, material abundance, governance coherence — four thresholds that, once crossed, change the shape of civilization.",
    date: "2026-05",
    domain: "worldbuilding",
    epistemicTag: "Speculative",
    ready: false,
  },
];

export default function WorldbuildingPage() {
  return (
    <DomainIndex
      domain="worldbuilding"
      title="Worldbuilding"
      description="Civilizational design, speculative futures, and the Sci-Fi World 2.0 narrative layer. Explicitly tagged as speculative or mythopoetic."
      essays={ESSAYS}
    />
  );
}
