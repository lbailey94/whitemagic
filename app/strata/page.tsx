import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";

export const metadata = {
  title: "STRATA — Code Analysis as a Service | WhiteMagic Labs",
  description:
    "10 checkers. 5-phase auto-fix pipeline. 3,008+ findings capacity. Born from WhiteMagic's own code quality needs — now available as a standalone tool.",
};

interface Checker {
  name: string;
  description: string;
  languages: string;
}

const CHECKERS: Checker[] = [
  { name: "Dead Code", description: "Unused functions, classes, variables, and imports across all languages.", languages: "Python, JS, TS, Go, Rust, Java, Swift, Ruby, Lua, Shell" },
  { name: "Copy-Paste", description: "Duplicate code blocks with configurable similarity threshold.", languages: "All languages" },
  { name: "Doc Drift", description: "Documentation that references stale paths, removed modules, or outdated APIs.", languages: "Markdown + code" },
  { name: "Hardcoded Paths", description: "Absolute paths, user-specific paths, and environment-specific URLs.", languages: "All languages" },
  { name: "Config Drift", description: "Configuration files that reference missing keys or stale defaults.", languages: "YAML, TOML, JSON" },
  { name: "Protocol Dead Code", description: "Protocol definitions (gRPC, OpenAPI) that reference unused message types.", languages: "Proto, OpenAPI" },
  { name: "Exceptions", description: "Bare except clauses, swallowed exceptions, and overly broad catches.", languages: "Python, Java, Ruby" },
  { name: "TODO/FIXME Style", description: "Stale TODOs, untracked FIXMEs, and action items without owners.", languages: "All languages" },
  { name: "Native Bindings", description: "FFI bindings (PyO3, cgo, NIF) with missing safety checks or memory leaks.", languages: "Rust, Go, Erlang" },
  { name: "Python Deep", description: "Python-specific deep analysis: metaclass abuse, decorator stacking, circular imports.", languages: "Python" },
];

const PHASES = [
  { name: "Survey", description: "Scan the codebase with all 10 checkers. Produce a findings report with severity, location, and suggested fix." },
  { name: "Triage", description: "Classify each finding: auto-fixable, needs-review, false-positive. Suppress patterns that are intentionally ignored." },
  { name: "Batch Fix", description: "Apply auto-fixes in batches grouped by checker type. Each batch is a single atomic commit." },
  { name: "Verify", description: "Run the test suite after each batch. If tests fail, roll back the batch and mark findings as needs-review." },
  { name: "Report", description: "Generate a final report: findings found, fixed, suppressed, and remaining. Track reduction over time." },
];

export default function StrataPage() {
  return (
    <>
      <PageHeader
        eyebrow="STRATA"
        title="Code analysis as a service."
        lede="10 checkers. 5-phase auto-fix pipeline. 3,008+ findings capacity. Born from WhiteMagic's own code quality needs — now available as a standalone tool."
      />

      {/* Stats */}
      <section className="container-site py-12">
        <div className="mx-auto max-w-4xl grid grid-cols-2 gap-6 md:grid-cols-4">
          <div className="rounded-2xl border border-border-light bg-surface p-6 text-center">
            <div className="font-head text-3xl font-bold text-ink">10</div>
            <div className="mt-1 text-sm text-muted">Checkers</div>
          </div>
          <div className="rounded-2xl border border-border-light bg-surface p-6 text-center">
            <div className="font-head text-3xl font-bold text-ink">5</div>
            <div className="mt-1 text-sm text-muted">Auto-Fix Phases</div>
          </div>
          <div className="rounded-2xl border border-border-light bg-surface p-6 text-center">
            <div className="font-head text-3xl font-bold text-ink">58.9%</div>
            <div className="mt-1 text-sm text-muted">Finding Reduction</div>
          </div>
          <div className="rounded-2xl border border-border-light bg-surface p-6 text-center">
            <div className="font-head text-3xl font-bold text-ink">10</div>
            <div className="mt-1 text-sm text-muted">Languages</div>
          </div>
        </div>
      </section>

      {/* Checkers */}
      <section className="container-site py-16">
        <div className="mx-auto max-w-4xl space-y-6">
          <div>
            <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
              Checkers · 10
            </p>
            <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
              What STRATA finds.
            </h2>
            <p className="mt-3 text-muted">
              Each checker targets a specific class of code quality issue. Checkers run in parallel and produce structured findings with severity, location, and suggested fixes.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {CHECKERS.map((c) => (
              <div key={c.name} className="rounded-2xl border border-border-light bg-surface p-5">
                <h3 className="font-head text-lg font-semibold text-ink">{c.name}</h3>
                <p className="mt-2 text-sm text-muted">{c.description}</p>
                <p className="mt-2 font-mono text-xs text-dim">{c.languages}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Auto-Fix Pipeline */}
      <section className="border-t border-border-light bg-surface-alt py-16">
        <div className="container-site mx-auto max-w-4xl space-y-6">
          <div>
            <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
              Auto-Fix Pipeline · 5 Phases
            </p>
            <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
              From findings to fixes, automatically.
            </h2>
            <p className="mt-3 text-muted">
              STRATA doesn't just find problems — it fixes them. The 5-phase pipeline surveys, triages, batches fixes, verifies with tests, and reports.
            </p>
          </div>
          <div className="space-y-4">
            {PHASES.map((p, i) => (
              <div key={p.name} className="flex gap-4">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border border-border-light bg-surface font-mono text-sm font-bold text-lavender">
                  {i + 1}
                </div>
                <div className="flex-1">
                  <h3 className="font-head text-lg font-semibold text-ink">{p.name}</h3>
                  <p className="mt-1 text-sm text-muted">{p.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Evidence */}
      <section className="container-site py-16">
        <div className="mx-auto max-w-3xl space-y-6">
          <div>
            <p className="mb-2 font-mono text-xs uppercase tracking-widest text-lavender">
              Evidence
            </p>
            <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
              STRATA on itself.
            </h2>
            <p className="mt-3 text-muted">
              STRATA was born from WhiteMagic's own code quality needs. We ran it on ourselves:
            </p>
          </div>
          <div className="rounded-2xl border border-border-light bg-surface p-6 space-y-3">
            <div className="flex justify-between border-b border-border-light pb-2">
              <span className="text-muted">Initial findings</span>
              <span className="font-mono font-semibold text-ink">3,787</span>
            </div>
            <div className="flex justify-between border-b border-border-light pb-2">
              <span className="text-muted">After batch resolution</span>
              <span className="font-mono font-semibold text-ink">1,555</span>
            </div>
            <div className="flex justify-between border-b border-border-light pb-2">
              <span className="text-muted">Reduction</span>
              <span className="font-mono font-semibold text-lavender">58.9%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">False positives eliminated</span>
              <span className="font-mono font-semibold text-ink">2,232</span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border-light bg-surface-alt py-16">
        <div className="container-site mx-auto max-w-3xl text-center space-y-4">
          <h2 className="font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Try STRATA on your codebase.
          </h2>
          <p className="text-muted">
            STRATA is part of WhiteMagic's tool suite. Install WhiteMagic and run{" "}
            <code className="rounded bg-surface px-2 py-0.5 font-mono text-sm text-ink">wm strata survey</code>{" "}
            to get started.
          </p>
          <div className="flex flex-wrap justify-center gap-4 pt-4">
            <Link
              href="/getting-started"
              className="rounded-full bg-ink px-6 py-2.5 text-sm font-medium text-paper transition hover:bg-ink/90"
            >
              Get Started
            </Link>
            <Link
              href="/open-source"
              className="rounded-full border border-border-light px-6 py-2.5 text-sm font-medium text-ink transition hover:border-ink/20"
            >
              Documentation
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
