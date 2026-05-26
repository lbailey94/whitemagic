import { PageHeader } from "@/components/PageHeader";
import { PrescienceScore } from "@/components/PrescienceScore";
import { ClaimsList } from "@/components/ClaimsList";
import { PendingList } from "@/components/PendingList";
import { BrierScoreSection } from "@/components/BrierScoreSection";

export const metadata = {
  title: "Prescience Audit — WhiteMagic Labs",
  description:
    "15 validated claims. 380+ prescience points. Brier Index 70.9%. A complete, independently verifiable forecasting track record with source evidence.",
};

export default function PresciencePage() {
  return (
    <>
      <PageHeader
        eyebrow="Prescience Audit"
        title="What I saw before the market."
        lede="A complete, verifiable forecasting track record. Every claim has a source timestamp and an independent validation event. No cherry-picking."
      />

      {/* Scorecard + comparison table */}
      <PrescienceScore />

      {/* Brier scoring + benchmark */}
      <BrierScoreSection />

      {/* Validated claims */}
      <section className="container-site py-16">
        <div className="mx-auto max-w-3xl space-y-6">
          <div>
            <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
              Validated claims · 15
            </p>
            <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
              The audit trail.
            </h2>
            <p className="mt-3 text-muted">
              Each claim links to a verifiable source (OpenAI archive ID, git commit, filesystem timestamp)
              and a public validation event (Microsoft blog, Anthropic release, Cloudflare announcement).
            </p>
          </div>
          <ClaimsList />
        </div>
      </section>

      {/* Pending / arriving */}
      <PendingList />

      {/* Methodology footer */}
      <section className="border-t border-border-light bg-surface-alt py-16">
        <div className="container-site mx-auto max-w-3xl space-y-6">
          <div>
            <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
              Methodology
            </p>
            <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
              How the score is computed.
            </h2>
          </div>

          <div className="space-y-4 text-muted">
            <p>
              <strong className="text-ink">1 point = 1 verified week of lead time.</strong> If a claim
              is made on May 26, 2025 and validated on April 23, 2026, that is 48 weeks = 48 points.
              The source date must be independently verifiable (filesystem mtime, git commit hash,
              or server-timestamped conversation archive). The validation must be a public announcement
              by a credible external entity, not self-reported.
            </p>
            <p>
              <strong className="text-ink">Conservative scoring.</strong> Claims without a clean single
              validation event are held as pending and score 0. The UAP May window predicted May 2;
              the actual PURSUE release was May 8 — 4 points were awarded for the window, but the exact
              date miss is noted. No points are awarded for directionally correct but unvalidated claims.
            </p>
            <p>
              <strong className="text-ink">Brier scoring.</strong> Each claim is scored with a confidence
              level at the time of prediction. The Brier score is the mean squared error between predicted
              probability and binary outcome. Brier Index = (1 − √BS) × 100% rescales this to an intuitive
              0–100% metric used by ForecastBench. A calibrated forecaster with a mix of hits and misses will
              produce a more informative decomposition than a 100% hit rate.
            </p>
            <p>
              <strong className="text-ink">Cross-domain synthesis.</strong> The structural advantage is not
              speed alone — it is combining AI governance, hardware, geopolitics, and agent architecture into
              a single coherent model. Most research institutions are siloed by department. WhiteMagic is a
              single operator with full context across all domains, which produces structural isomorphisms
              that siloed analysts miss.
            </p>
          </div>

          <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-muted">
            <p className="mb-1 font-mono text-xs uppercase tracking-widest text-amber-400">Honest misses</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>
                <strong>UAP May window:</strong> Predicted May 2; actual PURSUE release May 8. Direction
                correct, date off by 6 days. Scored 4 pts (window validated) with note.
              </li>
              <li>
                <strong>Agent identity coherence:</strong> Shipped Nov 2025; no single public validation
                event as of May 2026. Held as pending (0 pts) despite clear emergent behavior.
              </li>
              <li>
                <strong>Bicameral reasoning / voice audit:</strong> Shipped Feb 2026; no industry equivalent
                announced as of May 2026. Held as pending. May validate later or may remain unique.
              </li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
