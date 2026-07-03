import { DomainIndex } from "@/components/essay/DomainIndex";
import type { EssayMeta } from "@/components/essay/EssayCard";

const ESSAYS: EssayMeta[] = [
  {
    slug: "ai-energy-infrastructure-2026",
    title: "AI's energy appetite is reshaping infrastructure — here's the data",
    blurb:
      "IEA revised projections to 1,100 TWh by 2030. Google contracted 500MW from Kairos SMR. Data centers are becoming power plants. What this means for energy markets and AI deployment costs.",
    date: "2026-05",
    domain: "horizons",
    epistemicTag: "Proven",
    ready: false,
  },
  {
    slug: "bci-neural-telepathy-landscape",
    title: "Brain-computer interfaces are realer than you think",
    blurb:
      "Meta's Brain2Qwerty, Stanford's 19-month chronic BCI, and the emerging telepathy stack. Separating the proven from the speculative.",
    date: "2026-05",
    domain: "horizons",
    epistemicTag: "Promising",
    ready: false,
  },
];

export default function HorizonsPage() {
  return (
    <DomainIndex
      domain="horizons"
      title="Horizons"
      description="Emerging technology frontiers — energy, space, BCI, UAP, and the edges of what's physically possible."
      essays={ESSAYS}
    />
  );
}
