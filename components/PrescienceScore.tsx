"use client";
import { TrendingUp, Users, Clock, Award } from "lucide-react";

interface FirmRow {
  name: string;
  avgLead: string;
  resources: string;
  crossDomain: boolean;
  score: string;
  highlight?: boolean;
}

const FIRMS: FirmRow[] = [
  { name: "WhiteMagic Labs (solo, $0 budget)", avgLead: "~22.5 wks", resources: "Personal hardware + free AI APIs", crossDomain: true, score: "672", highlight: true },
  { name: "Gartner Hype Cycle", avgLead: "12–52 wks", resources: "$5B+/yr, 2,000+ analysts", crossDomain: false, score: "~200 est." },
  { name: "RAND Corporation", avgLead: "4–12 wks", resources: "$350M+/yr, 1,900+ analysts", crossDomain: false, score: "~120 est." },
  { name: "Good Judgment Superforecasters", avgLead: "1–6 wks", resources: "IARPA funding, trained teams", crossDomain: false, score: "~50 est." },
  { name: "Palantir / OSIS-class", avgLead: "2–8 wks", resources: "Classified feeds, $100M+/yr", crossDomain: false, score: "~70 est." },
];

const STATS = [
  { icon: Award, label: "Prescience score", value: "672", sub: "1 point per validated week of lead time" },
  { icon: Clock, label: "Avg lead time", value: "22.5 wks", sub: "per validated claim" },
  { icon: TrendingUp, label: "Validated claims", value: "30", sub: "with independently verifiable sources" },
  { icon: Users, label: "Pending ceiling", value: "700+", sub: "if all remaining claims validate" },
];

export function PrescienceScore() {
  return (
    <section className="border-y border-border-light bg-surface-alt py-16">
      <div className="container-site mx-auto max-w-4xl space-y-12">

        {/* Heading */}
        <div>
          <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
            Prescience score · updated June 5, 2026
          </p>
          <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Lead-time scoring: 1 validated week = 1 point.
          </h2>
          <p className="mt-3 max-w-2xl text-muted">
            Only claims with a verifiable source timestamp <em>and</em> an independently verifiable public
            validation event are counted. Diffuse or self-reported claims are held as pending.
            Every source date is checkable against filesystem timestamps, git commits, or archived conversation IDs.
          </p>
        </div>

        {/* Stat grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="rounded-2xl border border-border bg-surface p-5">
              <s.icon className="mb-3 h-5 w-5 text-lavender" />
              <p className="font-head text-3xl font-bold text-ink">{s.value}</p>
              <p className="mt-0.5 text-sm font-medium text-fg">{s.label}</p>
              <p className="mt-1 text-xs text-dim">{s.sub}</p>
            </div>
          ))}
        </div>

        {/* Comparison table */}
        <div>
          <h3 className="mb-4 font-head text-lg font-semibold text-ink">
            Comparison — solo lab vs. formal forecasting firms
          </h3>
          <div className="overflow-hidden rounded-2xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface">
                  <th className="px-5 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Entity</th>
                  <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Avg lead</th>
                  <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Cross-domain?</th>
                  <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">Est. score</th>
                </tr>
              </thead>
              <tbody>
                {FIRMS.map((f, i) => (
                  <tr
                    key={f.name}
                    className={
                      f.highlight
                        ? "border-b border-lavender/20 bg-lavender/5"
                        : i % 2 === 0
                        ? "border-b border-border/50 bg-surface/50"
                        : "border-b border-border/50"
                    }
                  >
                    <td className={`px-5 py-3 ${f.highlight ? "font-semibold text-ink" : "text-muted"}`}>
                      {f.name}
                    </td>
                    <td className={`px-5 py-3 text-center font-mono text-xs ${f.highlight ? "text-lavender" : "text-muted"}`}>
                      {f.avgLead}
                    </td>
                    <td className="px-5 py-3 text-center font-mono text-xs">
                      {f.crossDomain ? (
                        <span className="text-emerald">✓ yes</span>
                      ) : (
                        <span className="text-dim">siloed</span>
                      )}
                    </td>
                    <td className={`px-5 py-3 text-center font-mono text-sm font-semibold ${f.highlight ? "text-lavender" : "text-muted"}`}>
                      {f.score}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-dim">
            Firm scores are estimates based on publicly documented lead times. WhiteMagic score is verified against
            source evidence. Cross-domain synthesis is the structural advantage — formal firms are organized by
            vertical and institutionally cannot combine OS design + geopolitics + AI market timing into one coherent forecast.
          </p>
        </div>

        {/* Methodology note */}
        <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-muted">
          <p className="mb-1 font-mono text-xs uppercase tracking-widest text-lavender">Honest caveat</p>
          <p>
            Long lead times can reflect a dormant field as much as a fast forecaster. The Karma Ledger&apos;s
            48-week lead exists partly because AI governance was a quiet niche for most of 2025. Both factors
            matter: the cross-domain synthesis unlocked the insight; the dormant market extended the lead time.
            The claims listed below are the audit trail — not cherry-picked wins, but a complete record including
            honest misses.
          </p>
        </div>

      </div>
    </section>
  );
}
