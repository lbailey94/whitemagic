import { PageHeader } from "@/components/PageHeader";
import { PrescienceScore } from "@/components/PrescienceScore";
import { ClaimsList } from "@/components/ClaimsList";
import { PendingList } from "@/components/PendingList";
import { BrierScoreSection } from "@/components/BrierScoreSection";
import {
  PRESCIENCE_METHODLOGY_NOTE,
  STATED_BRIER_INDEX,
  BEHAVIORAL_BRIER_INDEX,
} from "@/lib/data/prescience";

export const metadata = {
  title: "Convergence Audit — WhiteMagic Labs",
  description:
    `17 validated claims. 420+ prescience points. Stated Brier Index ${STATED_BRIER_INDEX}%; behavioral recalibration ${BEHAVIORAL_BRIER_INDEX}%. A complete, independently verifiable cross-domain forecasting track record with source evidence. Not to be confused with AllenAI's PreScience benchmark for scientific contribution forecasting.`,
};

export default function PresciencePage() {
  return (
    <>
      <PageHeader
        eyebrow="Convergence Audit"
        title="What the lab documented before the market shipped it."
        lede="A complete, verifiable cross-domain forecasting track record. Every claim has a source timestamp and an independent validation event. No cherry-picking."
      />

      {/* AllenAI disambiguation */}
      <section className="container-site pt-4 pb-0">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs text-dim">
            <strong>Note:</strong> AllenAI published{" "}
            <em>PreScience</em> (arXiv 2602.20459, Feb 2026) — a benchmark for
            AI forecasting of <em>scientific contributions</em>. This page is
            unrelated: it documents cross-domain <em>technology convergence</em>{" "}
            forecasting with independently verifiable timestamps and validation events.
          </p>
        </div>
      </section>

      {/* Scorecard + comparison table */}
      <PrescienceScore />

      {/* Brier scoring + benchmark */}
      <BrierScoreSection />

      {/* Validated claims */}
      <section className="container-site py-16">
        <div className="mx-auto max-w-3xl space-y-6">
          <div>
            <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
              Validated claims · 17
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
              <strong className="text-ink">Behavioral recalibration.</strong> A May 2026 archive deep dive
              analyzed 317 conversations for explicit probability language. The predictor rarely stated
              probabilities; instead, designs were presented as measurements or completed architectures.
              Post-hoc behavioral confidence estimates are systematically higher (stated Brier Index
              {STATED_BRIER_INDEX}% vs. behavioral {BEHAVIORAL_BRIER_INDEX}%). Both scores are published for
              transparency.
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
                <strong>Memory-as-a-service monetization:</strong> Expected memory to be a standalone product. Reality: governance infrastructure was the urgent need; memory was absorbed as a first-party feature by Anthropic, Microsoft, and OpenAI by mid-2026.
              </li>
              <li>
                <strong>Agent economy payments-first:</strong> Expected micropayments and agent-to-agent transactions to crystallize before governance. Reality: governance and observability arrived first. Payments (x402, A2A) are still emerging.
              </li>
              <li>
                <strong>Governance as a defensible solo-developer moat:</strong> Expected governance-first positioning to be unique. Reality: Microsoft AGT, Chitragupta, Sgraal, Aevum, Ardur, and DingDawg all shipped governance layers by May 2026. The category went from empty to crowded in 3 months.
              </li>
              <li>
                <strong>UAP May window:</strong> Predicted May 2; actual PURSUE release May 8. Direction correct, date off by 6 days. Scored 4 pts (window validated) with note.
              </li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
