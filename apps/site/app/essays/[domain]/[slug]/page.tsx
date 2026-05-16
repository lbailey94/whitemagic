import { EssayLayout } from "@/components/essay/EssayLayout";
import type { EpistemicTag } from "@/lib/design-tokens";

// Essay content registry — maps domain+slug to essay metadata and content.
// Content is stored as MDX in content/essays/<domain>/<slug>.mdx
// This page renders the MDX content via the EssayLayout wrapper.

interface EssayData {
  title: string;
  date: string;
  epistemicTag: EpistemicTag;
  lastVerified?: string;
}

const REGISTRY: Record<string, Record<string, EssayData>> = {
  intelligence: {
    "agent-governance-before-microsoft": {
      title: "I built agent governance before Microsoft — here's what I learned",
      date: "2026-04",
      epistemicTag: "Proven",
    },
    "private-ai-deployment-guide": {
      title: "How I deploy private AI for regulated teams",
      date: "2026-04",
      epistemicTag: "Proven",
    },
  },
  horizons: {
    "ai-energy-infrastructure-2026": {
      title:
        "AI's energy appetite is reshaping infrastructure — here's the data",
      date: "2026-05",
      epistemicTag: "Proven",
    },
    "bci-neural-telepathy-landscape": {
      title: "Brain-computer interfaces are realer than you think",
      date: "2026-05",
      epistemicTag: "Promising",
    },
  },
  worldbuilding: {
    "five-schools-of-civilization-design": {
      title: "The Five Schools of Civilization Design",
      date: "2026-05",
      epistemicTag: "Mythopoetic",
    },
    "uplift-convergence-thresholds": {
      title: "UPLIFT: Convergence Thresholds for a Post-Scarcity Civilization",
      date: "2026-05",
      epistemicTag: "Speculative",
    },
  },
  philosophy: {
    "karma-ledger-ethical-governance": {
      title: "Karma Ledger: ethical governance as a computational primitive",
      date: "2026-04",
      epistemicTag: "Promising",
    },
    "epistemic-honesty-in-ai-systems": {
      title: "Epistemic honesty is the missing AI safety primitive",
      date: "2026-05",
      epistemicTag: "Contested",
    },
  },
};

export function generateStaticParams() {
  const params: { domain: string; slug: string }[] = [];
  for (const [domain, essays] of Object.entries(REGISTRY)) {
    for (const slug of Object.keys(essays)) {
      params.push({ domain, slug });
    }
  }
  return params;
}

export default async function EssayPage({
  params,
}: {
  params: Promise<{ domain: string; slug: string }>;
}) {
  const { domain, slug } = await params;
  const essay = REGISTRY[domain]?.[slug];

  if (!essay) {
    return (
      <main className="container-site py-16">
        <h1 className="font-head text-4xl font-semibold text-ink">
          Essay not found
        </h1>
        <p className="mt-4 text-muted">
          No essay found at /essays/{domain}/{slug}.
        </p>
      </main>
    );
  }

  // Dynamic MDX import — loads content/essays/<domain>/<slug>.mdx
  let Content: React.ComponentType | null = null;
  try {
    const mod = await import(
      `@/content/essays/${domain}/${slug}.mdx`
    );
    Content = mod.default;
  } catch {
    Content = null;
  }

  return (
    <EssayLayout
      title={essay.title}
      domain={domain}
      date={essay.date}
      epistemicTag={essay.epistemicTag}
      lastVerified={essay.lastVerified}
    >
      {Content ? (
        <Content />
      ) : (
        <div className="rounded-2xl border border-dashed border-border bg-surface-alt/50 p-8 text-center">
          <p className="text-muted">
            This essay is listed but its content has not been published yet.
          </p>
        </div>
      )}
    </EssayLayout>
  );
}
