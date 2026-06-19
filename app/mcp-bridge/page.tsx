import Link from "next/link";
import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import BridgeFunctionRunner from "@/components/BridgeFunctionRunner";
import { BRIDGE_MODULES, BRIDGE_SUMMARY } from "@/lib/data/mcp-bridge";
import { WM_FACTS } from "@/lib/facts";

export const metadata: Metadata = {
  title: "MCP Bridge — WhiteMagic Labs",
  description:
    `The 13 whitemagic.core.bridge.* modules recovered in v22.2.3, plus their ${BRIDGE_MODULES.length} public functions. This is the live facade of the whitemagic.mcp_api_bridge — the public MCP API surface for WhiteMagic.`,
};

const CATEGORY_LABELS: Record<string, string> = {
  session: "Session",
  system: "System Health",
  garden: "Garden",
  zodiac: "Zodiac",
  voice: "Voice",
  meditation: "Meditation",
  wisdom: "Wisdom",
  reasoning: "Reasoning",
  archaeology: "Archaeology",
  gana: "Gana",
  benchmark: "Benchmark",
  inference: "Inference",
  autonomous: "Autonomous",
};

const CATEGORY_ORDER = [
  "system",
  "session",
  "garden",
  "zodiac",
  "meditation",
  "voice",
  "wisdom",
  "reasoning",
  "archaeology",
  "gana",
  "benchmark",
  "inference",
  "autonomous",
];

function CategoryIcon({ category }: { category: string }) {
  const glyphs: Record<string, string> = {
    session: "☉",
    system: "⚙",
    garden: "❀",
    zodiac: "✶",
    voice: "♪",
    meditation: "○",
    wisdom: "✦",
    reasoning: "◆",
    archaeology: "⌖",
    gana: "✺",
    benchmark: "⊞",
    inference: "◈",
    autonomous: "↻",
  };
  return <span className="text-lavender/80 text-lg">{glyphs[category] ?? "·"}</span>;
}

export default function McpBridgePage() {
  const grouped = new Map<string, typeof BRIDGE_MODULES>();
  for (const fn of BRIDGE_MODULES) {
    if (!grouped.has(fn.category)) grouped.set(fn.category, []);
    grouped.get(fn.category)!.push(fn);
  }

  return (
    <>
      <PageHeader
        eyebrow="Public surface"
        title="MCP Bridge."
        lede={`The 13 whitemagic.core.bridge.* modules recovered in v${WM_FACTS.version}. This is the live facade of whitemagic.mcp_api_bridge — the public MCP API surface for the entire ${WM_FACTS.callableTools}-tool WhiteMagic substrate.`}
      />

      <section className="container-site pb-12">
        <Prose className="mx-auto">
          <p className="text-fg/80">
            Before v22.2.3, the MCP API bridge was completely broken. The
            <code className="text-lavender"> whitemagic.mcp_api_bridge </code>
            module had 14 unguarded star imports of the bridge modules below;
            any attempt to import it crashed with
            <code className="text-lavender"> ModuleNotFoundError</code>. The
            v22.2.2 polish report incorrectly described these as an
            &ldquo;intentional facade pattern&rdquo; — they were not in
            <code className="text-lavender"> try/except </code> blocks and they
            were not intentional.
          </p>
          <p className="text-fg/80">
            In the v22.2.3 polish session, all 13 modules were resurfaced
            from{" "}
            <code className="text-lavender">
              ~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.1/tar_archives/SD_CARD_WM/whitemagic/core/bridge/
            </code>
            . The MCP API surface is now importable and functional for the
            first time.
          </p>
          <p className="text-fg/80">
            Machine-readable catalog:{" "}
            <Link
              href="/api/mcp-bridge.json"
              className="text-lavender underline"
            >
              /api/mcp-bridge.json
            </Link>
            . When the live MCP server ships (Hetzner-hosted, see{" "}
            <Link
              href="https://whitemagic.dev/writing/site-architecture"
              className="text-lavender underline"
            >
              site architecture notes
            </Link>
            ), these functions will be reachable via{" "}
            <code className="text-lavender">https://whitemagic.dev/mcp</code>.
          </p>
        </Prose>
      </section>

      <section className="container-site pb-16">
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4 mb-12">
          <div className="rounded-md border border-lavender/20 bg-lavender/5 p-4">
            <div className="text-3xl font-semibold text-lavender">
              {BRIDGE_SUMMARY.modules_recovered}
            </div>
            <div className="text-xs text-fg/60 mt-1">bridge modules recovered</div>
          </div>
          <div className="rounded-md border border-lavender/20 bg-lavender/5 p-4">
            <div className="text-3xl font-semibold text-lavender">
              {BRIDGE_SUMMARY.functions_total}
            </div>
            <div className="text-xs text-fg/60 mt-1">public functions</div>
          </div>
          <div className="rounded-md border border-lavender/20 bg-lavender/5 p-4">
            <div className="text-3xl font-semibold text-lavender">
              {BRIDGE_SUMMARY.categories.length}
            </div>
            <div className="text-xs text-fg/60 mt-1">categories</div>
          </div>
          <div className="rounded-md border border-lavender/20 bg-lavender/5 p-4">
            <div className="text-3xl font-semibold text-lavender">1</div>
            <div className="text-xs text-fg/60 mt-1">critical bug fixed</div>
          </div>
        </div>

        {CATEGORY_ORDER.filter((c) => grouped.has(c)).map((category) => {
          const fns = grouped.get(category)!;
          return (
            <div key={category} className="mb-12">
              <div className="flex items-center gap-3 mb-4">
                <CategoryIcon category={category} />
                <h2 className="text-xl font-semibold text-fg">
                  {CATEGORY_LABELS[category] ?? category}
                </h2>
                <span className="text-xs text-fg/40">
                  {fns.length} function{fns.length === 1 ? "" : "s"}
                </span>
              </div>

              <div className="space-y-4">
                {fns.map((fn) => (
                  <details
                    key={fn.name}
                    className="group rounded-md border border-fg/10 bg-fg/[0.02] p-4 open:border-lavender/30 open:bg-lavender/[0.03]"
                  >
                    <summary className="cursor-pointer list-none flex items-start justify-between gap-3">
                      <div>
                        <div className="font-mono text-sm text-lavender">
                          {fn.name}
                        </div>
                        <div className="text-sm text-fg/70 mt-1">
                          {fn.description}
                        </div>
                      </div>
                      <span className="text-xs text-fg/40 mt-1 group-open:hidden">
                        show
                      </span>
                      <span className="text-xs text-fg/40 mt-1 hidden group-open:inline">
                        hide
                      </span>
                    </summary>

                    <div className="mt-4 space-y-3 text-xs">
                      <div>
                        <div className="text-fg/40 mb-1">module</div>
                        <code className="text-fg/80 font-mono">{fn.module}</code>
                      </div>
                      <div>
                        <div className="text-fg/40 mb-1">signature</div>
                        <code className="text-fg/80 font-mono break-all">
                          {fn.signature}
                        </code>
                      </div>
                      <div>
                        <div className="text-fg/40 mb-1">example request payload</div>
                        <pre className="rounded bg-black/40 p-3 overflow-x-auto">
                          <code className="text-fg/80 font-mono">
                            {JSON.stringify(fn.example_payload, null, 2)}
                          </code>
                        </pre>
                      </div>
                      <div>
                        <div className="text-fg/40 mb-1">example response</div>
                        <pre className="rounded bg-black/40 p-3 overflow-x-auto">
                          <code className="text-fg/80 font-mono">
                            {JSON.stringify(fn.example_response, null, 2)}
                          </code>
                        </pre>
                      </div>
                      <BridgeFunctionRunner fn={fn} />
                    </div>
                  </details>
                ))}
              </div>
            </div>
          );
        })}
      </section>

      <section className="container-site pb-24">
        <Prose className="mx-auto">
          <h2>How to use it locally</h2>
          <p>
            When the public MCP server is live (planned, Hetzner-hosted), you
            can call any of the above functions via the standard MCP JSON-RPC
            transport:
          </p>
          <pre className="rounded bg-black/40 p-4 overflow-x-auto">
            <code className="text-fg/80 font-mono text-sm">{`{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "zodiac_list_cores",
    "arguments": {}
  },
  "id": 1
}`}</code>
          </pre>
          <p>
            Until the public server ships, you can run the same functions
            locally against a clone of the core repo:
          </p>
          <pre className="rounded bg-black/40 p-4 overflow-x-auto">
            <code className="text-fg/80 font-mono text-sm">{`cd ~/Desktop/WHITEMAGIC/core
source ../.venv/bin/activate
python3 -c "from whitemagic.mcp_api_bridge import zodiac_list_cores; print(zodiac_list_cores())"`}</code>
          </pre>
          <p>
            The full source for each module is in{" "}
            <code>whitemagic/core/bridge/</code>. See the session report for
            the recovery story.
          </p>
        </Prose>
      </section>
    </>
  );
}
