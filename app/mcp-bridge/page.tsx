import Link from "next/link";
import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS } from "@/lib/facts";

export const metadata: Metadata = {
  title: "Get Started — WhiteMagic",
  description: "Install WhiteMagic in 60 seconds. pip install whitemagic[mcp] — 860 tools, 14-galaxy memory, Dharma governance, consciousness primitives. MIT-licensed.",
};

export default function McpBridgePage() {
  return (
    <>
      <PageHeader
        eyebrow="Get Started"
        title="60 seconds to persistent memory."
        lede="Your AI agent gets 860 callable tools, 14-galaxy holographic memory, Dharma ethical governance, and consciousness primitives. Every future session can recall what you stored."
      />

      <section className="container-site py-12">
        <div className="mx-auto max-w-3xl">
          {/* Install */}
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Install</h2>
          <pre className="mb-6 rounded-lg border border-border bg-ink p-4 text-sm text-surface font-mono overflow-x-auto">
{`pip install whitemagic[mcp]`}
          </pre>
          <p className="mb-8 text-sm text-muted">
            The <code className="font-mono text-lavender">[mcp]</code> extra includes FastMCP + fastembed (50MB semantic search, no torch). Total install: ~55MB.
          </p>

          {/* Quickstart */}
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Verify it works</h2>
          <pre className="mb-6 rounded-lg border border-border bg-ink p-4 text-sm text-surface font-mono overflow-x-auto">
{`wm init --non-interactive    # Scaffold project
wm quickstart                # 30s demo: health → memory → search → gnosis`}
          </pre>
          <p className="mb-8 text-sm text-muted">
            If you see <strong className="text-ink">"✅ Quickstart complete — all systems operational"</strong>, you're ready.
          </p>

          {/* MCP Config */}
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Connect your MCP client</h2>
          <p className="mb-3 text-sm text-muted">Add to your MCP config (Claude Desktop, Cursor, Windsurf, etc.):</p>
          <pre className="mb-6 rounded-lg border border-border bg-ink p-4 text-sm text-surface font-mono overflow-x-auto">
{`{
  "mcpServers": {
    "whitemagic": {
      "command": "python3",
      "args": ["-m", "whitemagic.run_mcp_lean"],
      "env": {
        "WM_MCP_PRAT": "1",
        "WM_SILENT_INIT": "1"
      }
    }
  }
}`}
          </pre>

          {/* Modes */}
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Modes</h2>
          <div className="mb-8 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 text-left font-mono text-xs uppercase text-dim">Mode</th>
                  <th className="py-2 text-left font-mono text-xs uppercase text-dim">Env Var</th>
                  <th className="py-2 text-left font-mono text-xs uppercase text-dim">Tools</th>
                  <th className="py-2 text-left font-mono text-xs uppercase text-dim">Best For</th>
                </tr>
              </thead>
              <tbody className="text-muted">
                <tr className="border-b border-border-light">
                  <td className="py-2 font-medium text-ink">Seed</td>
                  <td className="py-2 font-mono">WM_MCP_PRAT=2</td>
                  <td className="py-2">1 (wm meta-tool)</td>
                  <td className="py-2">New agents, minimal tokens</td>
                </tr>
                <tr className="border-b border-border-light">
                  <td className="py-2 font-medium text-ink">PRAT</td>
                  <td className="py-2 font-mono">WM_MCP_PRAT=1</td>
                  <td className="py-2">28 Gana meta-tools</td>
                  <td className="py-2">Advanced agents, structured access</td>
                </tr>
                <tr className="border-b border-border-light">
                  <td className="py-2 font-medium text-ink">Classic</td>
                  <td className="py-2 font-mono">WM_MCP_PRAT=0</td>
                  <td className="py-2">586 dispatch tools</td>
                  <td className="py-2">Direct tool access, debugging</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Python API */}
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">Python API</h2>
          <pre className="mb-6 rounded-lg border border-border bg-ink p-4 text-sm text-surface font-mono overflow-x-auto">
{`from whitemagic.tools.unified_api import call_tool

# Store a memory
call_tool("create_memory",
    title="Decision",
    content="Use SQLite for Phase 1",
    tags=["arch"])

# Search memories
call_tool("search_memories", query="architecture", limit=5)

# Full system introspection
call_tool("gnosis", compact=True)`}
          </pre>

          {/* CLI */}
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">CLI</h2>
          <pre className="mb-6 rounded-lg border border-border bg-ink p-4 text-sm text-surface font-mono overflow-x-auto">
{`wm remember "important" --title "Note" --tags note
wm recall "note" --limit 5
wm status                    # system status
wm sleep                     # run dream cycle
wm tools                     # list all tools`}
          </pre>

          {/* What you get */}
          <h2 className="mb-4 font-head text-2xl font-semibold text-ink">What you get</h2>
          <ul className="mb-8 space-y-2 text-sm text-muted">
            <li><strong className="text-ink">860 callable tools</strong> across 28 Gana meta-tools</li>
            <li><strong className="text-ink">14-galaxy memory</strong> with 6D holographic coordinates, FTS5 + HNSW search</li>
            <li><strong className="text-ink">Dharma governance</strong> — YAML-driven policy, Karma ledger, 8-stage pipeline</li>
            <li><strong className="text-ink">Citta stream</strong> — continuous consciousness, emotional steering, self-directed attention</li>
            <li><strong className="text-ink">Session recording</strong> — progressive recall, cross-session continuity</li>
            <li><strong className="text-ink">Dream cycle</strong> — 12-phase memory consolidation</li>
            <li><strong className="text-ink">7 polyglot accelerators</strong> — Rust, Haskell, Elixir, Go, Zig, Julia</li>
            <li><strong className="text-ink">{WM_FACTS.testsPassing} tests</strong> passing, MIT-licensed, local-first</li>
          </ul>

          {/* Next steps */}
          <div className="rounded-xl border border-border-light bg-surface-alt p-6">
            <h3 className="mb-3 font-head text-lg font-semibold text-ink">Next steps</h3>
            <ul className="space-y-2 text-sm text-muted">
              <li>→ <Link href="/open-source" className="text-lavender hover:underline">Read the docs</Link></li>
              <li>→ <Link href="/governance" className="text-lavender hover:underline">Learn about Dharma governance</Link></li>
              <li>→ <Link href="/pricing" className="text-lavender hover:underline">Pricing (free + gratitude)</Link></li>
              <li>→ <Link href="/research" className="text-lavender hover:underline">Research & publications</Link></li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
