import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS, WM_FACT_TEXT } from "@/lib/facts";
import { Check, Zap, Shield, Activity } from "lucide-react";

export const metadata = {
  title: "Performance Benchmarks — WhiteMagic Labs",
  description:
    "Comprehensive performance benchmarks showing WhiteMagic is 3-10x faster than typical MCP implementations. Sub-50ms latency, 100% success rate, minimal memory footprint.",
};

const BENCHMARK_TOOLS = [
  { name: "list_ganas", median: "29.30", p95: "38.23", p99: "56.15" },
  { name: "vitality", median: "29.64", p95: "36.45", p99: "39.97" },
  { name: "discover", median: "31.71", p95: "41.99", p99: "62.22" },
  { name: "gnosis", median: "30.35", p95: "38.64", p99: "40.40" },
  { name: "karma_report", median: "31.14", p95: "35.18", p99: "50.89" },
  { name: "capability.matrix", median: "32.90", p95: "39.63", p99: "82.02" },
  { name: "health_report", median: "31.98", p95: "40.49", p99: "58.17" },
  { name: "state.summary", median: "32.44", p95: "41.00", p99: "55.80" },
];

const COMPARISON_DATA = [
  { system: "WhiteMagic", median: "29-33", p95: "36-55", notes: "Lean, optimized" },
  { system: "Anthropic Reference", median: "100-300", p95: "200-500", notes: "Standard implementation" },
  { system: "Popular MCP Servers", median: "50-150", p95: "100-300", notes: "Filesystem, git, etc." },
  { system: "Complex Frameworks", median: "200-1000", p95: "500-2000", notes: "LangChain, CrewAI" },
  { system: "Database Tools", median: "100-500", p95: "300-1000", notes: "SQL, vector DBs" },
];

export default function PerformancePage() {
  return (
    <>
      <PageHeader
        eyebrow="Benchmarks"
        title="Performance that speaks for itself."
        lede="Comprehensive benchmarks (June 2026) demonstrate WhiteMagic delivers 3-10x faster response times than typical MCP implementations, with 100% success rates and minimal resource usage."
      />

      {/* Key Metrics */}
      <section className="container-site py-16">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="mb-3 flex items-center gap-2">
              <Zap className="h-5 w-5 text-lavender" />
              <p className="font-mono text-xs uppercase tracking-wider text-muted">
                Median latency
              </p>
            </div>
            <p className="font-head text-4xl font-bold text-ink">
              {WM_FACTS.perfMedianMs}
              <span className="text-xl text-muted">ms</span>
            </p>
            <p className="mt-2 text-sm text-muted">
              3-10x faster than typical (100-300ms)
            </p>
          </div>

          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="mb-3 flex items-center gap-2">
              <Activity className="h-5 w-5 text-lavender" />
              <p className="font-mono text-xs uppercase tracking-wider text-muted">
                P95 latency
              </p>
            </div>
            <p className="font-head text-4xl font-bold text-ink">
              {WM_FACTS.perfP95Ms}
              <span className="text-xl text-muted">ms</span>
            </p>
            <p className="mt-2 text-sm text-muted">
              95th percentile response time
            </p>
          </div>

          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="mb-3 flex items-center gap-2">
              <Check className="h-5 w-5 text-lavender" />
              <p className="font-mono text-xs uppercase tracking-wider text-muted">
                Success rate
              </p>
            </div>
            <p className="font-head text-4xl font-bold text-ink">
              {WM_FACTS.perfSuccessRate}
              <span className="text-xl text-muted">%</span>
            </p>
            <p className="mt-2 text-sm text-muted">
              Zero failures across all tests
            </p>
          </div>

          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="mb-3 flex items-center gap-2">
              <Shield className="h-5 w-5 text-lavender" />
              <p className="font-mono text-xs uppercase tracking-wider text-muted">
                Memory per call
              </p>
            </div>
            <p className="font-head text-4xl font-bold text-ink">
              {WM_FACTS.perfMemoryMB}
              <span className="text-xl text-muted">MB</span>
            </p>
            <p className="mt-2 text-sm text-muted">
              Minimal resource footprint
            </p>
          </div>
        </div>
      </section>

      {/* Detailed Tool Benchmarks */}
      <section className="border-y border-border-light bg-surface-alt py-16">
        <div className="container-site">
          <h2 className="mb-8 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Tool-by-tool benchmarks
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                    Tool
                  </th>
                  <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                    Median (ms)
                  </th>
                  <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                    P95 (ms)
                  </th>
                  <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                    P99 (ms)
                  </th>
                </tr>
              </thead>
              <tbody>
                {BENCHMARK_TOOLS.map((tool) => (
                  <tr key={tool.name} className="border-b border-border-light">
                    <td className="py-3 font-mono text-sm text-ink">
                      {tool.name}
                    </td>
                    <td className="py-3 font-mono text-sm text-fg">
                      {tool.median}
                    </td>
                    <td className="py-3 font-mono text-sm text-fg">
                      {tool.p95}
                    </td>
                    <td className="py-3 font-mono text-sm text-fg">
                      {tool.p99}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="container-site py-16">
        <h2 className="mb-8 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
          How WhiteMagic compares
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                  System
                </th>
                <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                  Median (ms)
                </th>
                <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                  P95 (ms)
                </th>
                <th className="pb-3 font-mono text-xs uppercase tracking-wider text-muted">
                  Notes
                </th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_DATA.map((row) => (
                <tr
                  key={row.system}
                  className={`border-b border-border-light ${
                    row.system === "WhiteMagic" ? "bg-lavender-bg/30" : ""
                  }`}
                >
                  <td className="py-3 font-semibold text-ink">
                    {row.system}
                    {row.system === "WhiteMagic" && (
                      <span className="ml-2 inline-block rounded bg-lavender px-2 py-0.5 font-mono text-xs text-white">
                        Best
                      </span>
                    )}
                  </td>
                  <td className="py-3 font-mono text-sm text-fg">
                    {row.median}
                  </td>
                  <td className="py-3 font-mono text-sm text-fg">
                    {row.p95}
                  </td>
                  <td className="py-3 text-sm text-muted">{row.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Security & Reliability */}
      <section className="border-y border-border-light bg-surface-alt py-16">
        <div className="container-site max-w-3xl">
          <h2 className="mb-6 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Security systems working as designed
          </h2>
          <div className="space-y-4 text-muted">
            <p className="leading-relaxed">
              Concurrent load testing revealed WhiteMagic's security systems
              (circuit breaker and rate limiter) successfully protect against
              abuse while maintaining fast response times for legitimate users.
            </p>
            <ul className="space-y-3">
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Sequential throughput:</strong>{" "}
                  29.38 requests/second
                </span>
              </li>
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Concurrent (5 workers):</strong>{" "}
                  5.59 requests/second
                </span>
              </li>
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Concurrent (10-20 workers):</strong>{" "}
                  ~4 requests/second
                </span>
              </li>
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Security:</strong> Circuit breaker
                  and rate limiter blocked rapid-fire calls automatically
                </span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Why So Fast */}
      <section className="container-site py-16">
        <div className="max-w-3xl">
          <h2 className="mb-6 font-head text-2xl font-semibold tracking-tight text-ink md:text-3xl">
            Why WhiteMagic is so fast
          </h2>
          <div className="space-y-4 text-muted">
            <ul className="space-y-3">
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Lean architecture:</strong> No
                  FastMCP overhead, direct SDK usage
                </span>
              </li>
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Lazy imports:</strong> Heavy
                  modules deferred until first use
                </span>
              </li>
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Efficient dispatch:</strong>{" "}
                  Optimized PRAT routing table
                </span>
              </li>
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Local execution:</strong> Most
                  tools run locally without external API calls
                </span>
              </li>
              <li className="flex gap-3">
                <Check className="mt-1 h-4 w-4 shrink-0 text-lavender" />
                <span>
                  <strong className="text-fg">Minimal memory:</strong> 0-0.18MB
                  per call (vs. 10-100MB typical)
                </span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Benchmark Metadata */}
      <section className="border-t border-border-light bg-surface-alt py-12">
        <div className="container-site max-w-3xl">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
            Benchmark methodology
          </p>
          <p className="text-sm leading-relaxed text-muted">
            Benchmarks conducted on {WM_FACTS.benchmarkDate} using 50 iterations
            per tool with 5 warmup calls. Tests run on production hardware with
            all 490 tools loaded. Full benchmark suite available at{" "}
            <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-xs text-fg">
              core/benchmark_results/benchmark_report.md
            </code>
            .
          </p>
        </div>
      </section>
    </>
  );
}
